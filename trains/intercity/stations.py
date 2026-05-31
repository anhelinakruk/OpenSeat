"""Station search and code mapping (InterCity autocomplete).

InterCity identifies a station by two codes: ``h`` (used by search and route) and ``e``
(used by the ``sklad``/``wagon`` endpoints). Autocomplete returns both, so it doubles as an
``h`` -> ``e`` translator.
"""
from urllib.parse import quote

from . import config, http


def search(q: str) -> list[dict]:
    """Return stations matching ``q`` (each a dict with fields including ``n``, ``h``, ``e``)."""
    url = config.WWW + "/station/get/?q=" + quote(q)
    response = http.get(url, extra_headers={
        "Origin": "https://www.intercity.pl",
        "Referer": "https://www.intercity.pl/",
        "X-Requested-With": "XMLHttpRequest",
    })
    return response.json()


def h_to_e(name: str, h: str) -> str | None:
    """Translate a station's ``h`` code to its ``e`` code (by name). Returns None if not found."""
    for station in search(name):
        if station["h"] == h:
            return station["e"]
    return None
