"""Service layer: combines the API client, parser and algorithm into a ready journey plan.

Adds caching so repeated queries do not hammer InterCity. Data is cached by how fast it
changes: station codes / routes / compositions sit in the in-memory cache framework for hours,
while volatile seat maps are cached in the database (SeatMapCache) for a short window so they
survive restarts and are shared across worker processes.
"""
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import cache

from . import client, parser, stations, hopping
from .errors import InterCityError
from ..models import SeatMapCache

# A seat identifier across the whole train is a (wagon_number, seat_number) pair.
Seat = tuple

# Cache lifetimes (seconds), chosen by how fast each kind of data changes.
_CODE_TTL = 7 * 24 * 3600     # station h->e codes basically never change
_ROUTE_TTL = 12 * 3600        # train routes change only with timetable editions
_COMP_TTL = 6 * 3600          # train composition rarely changes within a day
_SEATS_TTL = 120              # seat availability changes with bookings -> short


def _cached_h_to_e(name: str, h: str) -> str | None:
    return cache.get_or_set(f"h2e:{h}", lambda: stations.h_to_e(name, h), _CODE_TTL)


def _cached_route(number: str, departure: str, from_h, to_h) -> list[dict]:
    key = f"route:{number}:{departure}:{from_h}:{to_h}"
    return cache.get_or_set(key, lambda: client.get_route(number, departure, from_h, to_h), _ROUTE_TTL)


def _cached_composition(category: str, number: str, dep_e: str, arr_e: str, date: str) -> dict:
    ts = date + "0000"
    key = f"comp:{category}:{number}:{dep_e}:{arr_e}:{date}"
    return cache.get_or_set(
        key, lambda: client.get_composition(category, number, dep_e, arr_e, ts, ts), _COMP_TTL)


def _cached_seats(category: str, number: str, wagon: str, schema: str,
                  dep_e: str, arr_e: str, date: str) -> str:
    """Return a wagon's seat-map SVG, served from the database cache when still fresh.

    Seat availability is volatile, so it lives in the DB (SeatMapCache) instead of local memory:
    the cache survives restarts and is shared across worker processes.
    """
    ident = dict(category=category, number=number, wagon=wagon,
                 dep_code=dep_e, arr_code=arr_e, journey_date=date)
    cached = SeatMapCache.get_fresh(**ident, ttl=_SEATS_TTL)
    if cached is not None:
        return cached
    ts = date + "0000"
    svg = client.get_seats(category, number, wagon, schema, dep_e, arr_e, ts, ts)
    SeatMapCache.store(**ident, svg=svg)
    return svg


def wagon_legs_free(category: str, number: str, wagon: str, schema: str,
                    stop_e: list[str], date: str) -> list[set]:
    """For one wagon, return the set of free seats per leg as (wagon, number) pairs."""
    legs_free = []
    for i in range(len(stop_e) - 1):
        svg = _cached_seats(category, number, wagon, schema, stop_e[i], stop_e[i + 1], date)
        seats = parser.parse_seats(svg)
        legs_free.append({(wagon, s["number"]) for s in seats if s["free"]})
    return legs_free


def train_legs_free(category: str, number: str, stops: list[dict], date: str,
                    wagons: list, schemas: dict) -> list[set]:
    """Collect free seats from ALL wagons, per leg (wagons fetched in parallel)."""
    stop_e = [_cached_h_to_e(s["nazwaStacji"], s["kodStacji"]) for s in stops]
    n = len(stops) - 1
    valid_wagons = [str(w) for w in wagons if schemas.get(str(w))]

    def fetch_wagon(wagon: str) -> list[set]:
        return wagon_legs_free(category, number, wagon, schemas[wagon], stop_e, date)

    legs_free = [set() for _ in range(n)]
    # Wagons are independent, so fetch them in parallel (network waits overlap).
    # Keep concurrency low to avoid overloading InterCity's API (rate limit).
    with ThreadPoolExecutor(max_workers=4) as pool:
        for wagon_legs in pool.map(fetch_wagon, valid_wagons):
            for i in range(n):
                legs_free[i] |= wagon_legs[i]
    return legs_free


def plan_journey(category: str, number: str, departure: str,
                 from_h, to_h, date: str, limit: int = 5) -> dict:
    """Build journey options: route -> composition -> free seats -> best plans (with/without transfers).

    Returns ``{'options': [{'transfers': int, 'segments': [{'wagon','seat','from','to'}, ...]}, ...]}``,
    ordered by fewest transfers; an empty list means no seats even with changes.
    """
    stops = _cached_route(number, departure, from_h, to_h)
    if not stops:
        raise InterCityError("No route found for this train with the given parameters.")

    dep_e = _cached_h_to_e(stops[0]["nazwaStacji"], stops[0]["kodStacji"])
    arr_e = _cached_h_to_e(stops[-1]["nazwaStacji"], stops[-1]["kodStacji"])
    composition = _cached_composition(category, number, dep_e, arr_e, date)
    try:
        wagons, schemas = composition["wagony"], composition["wagonySchemat"]
    except (KeyError, TypeError) as exc:
        raise InterCityError("Unexpected composition response shape from InterCity.") from exc

    legs = train_legs_free(category, number, stops, date, wagons, schemas)
    plans = hopping.find_plans(legs, limit)

    names = [s["nazwaStacji"] for s in stops]
    options = []
    for plan in plans:
        segments = [
            {"wagon": wagon, "seat": seat, "from": names[leg_from], "to": names[leg_to]}
            for (wagon, seat), leg_from, leg_to in plan
        ]
        options.append({"transfers": len(plan) - 1, "segments": segments})
    return {"options": options}
