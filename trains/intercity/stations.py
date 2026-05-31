from . import config, http
from urllib.parse import quote

def search(q):
    url = config.WWW + "/station/get/?q=" + quote(q)
    response = http.get(url, extra_headers={
      "Origin": "https://www.intercity.pl",
      "Referer": "https://www.intercity.pl/",
      "X-Requested-With": "XMLHttpRequest",
    })
    return response.json()

def h_to_e(name, h):
    for station in search(name):
        if station["h"] == h:
            return station["e"]
    return None
