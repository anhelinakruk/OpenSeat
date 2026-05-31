"""Service layer: combines the API client, parser and algorithm into a ready journey plan."""
from concurrent.futures import ThreadPoolExecutor

from . import client, parser, stations, hopping
from .errors import InterCityError

# A seat identifier across the whole train is a (wagon_number, seat_number) pair.
Seat = tuple


def wagon_legs_free(category: str, number: str, wagon: str, schema: str,
                    stop_e: list[str], date: str) -> list[set]:
    """For one wagon, return the set of free seats per leg as (wagon, number) pairs."""
    ts = date + "0000"                                    # the time is irrelevant, only the date matters
    legs_free = []
    for i in range(len(stop_e) - 1):
        svg = client.get_seats(category, number, wagon, schema, stop_e[i], stop_e[i + 1], ts, ts)
        seats = parser.parse_seats(svg)
        legs_free.append({(wagon, s["number"]) for s in seats if s["free"]})
    return legs_free


def train_legs_free(category: str, number: str, stops: list[dict], date: str,
                    wagons: list, schemas: dict) -> list[set]:
    """Collect free seats from ALL wagons, per leg (wagons fetched in parallel)."""
    # Resolve each stop's ``e`` code once (instead of inside every wagon).
    stop_e = [stations.h_to_e(s["nazwaStacji"], s["kodStacji"]) for s in stops]
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
                 from_h, to_h, date: str) -> dict:
    """Build a journey plan: route -> composition -> free seats -> best plan (with or without transfers).

    Returns ``{'transfers': int | None, 'segments': [{'wagon', 'seat', 'from', 'to'}, ...]}``.
    """
    stops = client.get_route(number, departure, from_h, to_h)
    if not stops:
        raise InterCityError("No route found for this train with the given parameters.")

    dep_e = stations.h_to_e(stops[0]["nazwaStacji"], stops[0]["kodStacji"])
    arr_e = stations.h_to_e(stops[-1]["nazwaStacji"], stops[-1]["kodStacji"])
    composition = client.get_composition(category, number, dep_e, arr_e, date + "0000", date + "0000")

    legs = train_legs_free(category, number, stops, date,
                           composition["wagony"], composition["wagonySchemat"])
    plan = hopping.find_plan(legs)

    names = [s["nazwaStacji"] for s in stops]
    segments = []
    if plan:
        for (wagon, seat), leg_from, leg_to in plan:
            segments.append({
                "wagon": wagon, "seat": seat,
                "from": names[leg_from], "to": names[leg_to],
            })
    return {
        "transfers": (len(plan) - 1) if plan else None,
        "segments": segments,
    }
