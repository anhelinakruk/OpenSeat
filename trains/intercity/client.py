"""Functions that call individual InterCity API endpoints (formats per docs/INTERCITY_API.md)."""
from . import config, http
from .errors import InterCityError

_POCIAGI_URL = f"{config.API_GATEWAY}/server/public/endpoint/Pociagi"


def get_composition(category: str, number: str, dep_e: str, arr_e: str,
                    dep_ts: str, arr_ts: str) -> dict:
    """Fetch the train composition (wagons and their schemas). Note: codes are 'crossed' in the URL."""
    url = f"{config.API_GATEWAY}/grm/sklad/wbnet/{category}/{number}/{arr_ts}/{dep_e}/{dep_ts}/{arr_e}"
    return http.get(url).json()


def get_seats(category: str, number: str, wagon: str, schema: str,
              dep_e: str, arr_e: str, dep_ts: str, arr_ts: str) -> str:
    """Fetch a wagon's seat map (SVG) for a given leg."""
    url = (f"{config.API_GATEWAY}/grm/wagon/svg/wbnet/{category}/{number}/{wagon}/{schema}"
           f"/{dep_ts}/{arr_ts}/{dep_e}/{arr_e}")
    return http.get(url).text


def _call_pociagi(body: dict) -> dict:
    """Call the ``Pociagi`` RPC endpoint and return JSON; raise InterCityError if it reports errors."""
    data = http.post(_POCIAGI_URL, body).json()
    if data.get("bledy"):
        descriptions = data["bledy"][0].get("opisy", [{}])
        message = descriptions[0].get("komunikat", "unknown error")
        raise InterCityError(f"InterCity: {message}")
    return data


def get_route(number: str, departure: str, from_h, to_h) -> list[dict]:
    """Return the train's ordered list of stops (with ``h`` codes, names and times)."""
    body = {
        "metoda": "pobierzTrasePrzejazdu", "jezyk": "PL", "wersja": config.VERSION,
        "numerPociagu": number, "dataWyjazdu": departure,
        "stacjaWyjazdu": from_h, "stacjaPrzyjazdu": to_h,
        "url": "https://ebilet.intercity.pl/wybormiejsc", "urzadzenieNr": config.DEVICE_NR,
    }
    data = _call_pociagi(body)
    try:
        return data["trasePrzejezdu"]["trasaPrzejazdu"]
    except (KeyError, TypeError) as exc:
        raise InterCityError("Unexpected route response shape from InterCity.") from exc


def search_connections(from_h, to_h, date: str) -> list[dict]:
    """Return direct trains for a relation (``h`` codes) and a 'YYYY-MM-DD' date."""
    body = {
        "metoda": "wyszukajPolaczenia", "wersja": config.VERSION,
        "dataWyjazdu": f"{date} 00:00:00", "dataPrzyjazdu": f"{date} 23:59:59",
        "stacjaWyjazdu": from_h, "stacjaPrzyjazdu": to_h,
        "czasNaPrzesiadkeMin": 5, "czasNaPrzesiadkeMax": 1440, "liczbaPrzesiadekMax": 0,
        "stacjePrzez": [], "polaczeniaBezposrednie": 1, "polaczeniaNajszybsze": 0,
        "kategoriePociagow": [], "rodzajeMiejsc": [], "typyMiejsc": [],
        "atrybutyHandlowe": [], "braille": 0, "urzadzenieNr": config.DEVICE_NR,
    }
    data = _call_pociagi(body)
    try:
        trains = []
        for connection in data["polaczenia"]:
            if len(connection["pociagi"]) == 1:           # direct connections only (a single train)
                t = connection["pociagi"][0]
                trains.append({
                    "category": t["kategoriaPociagu"],
                    "number": str(t["nrPociagu"]),
                    "name": t["nazwaPociagu"],
                    "departure": t["dataWyjazdu"],
                })
        return trains
    except (KeyError, TypeError, IndexError) as exc:
        raise InterCityError("Unexpected connections response shape from InterCity.") from exc
