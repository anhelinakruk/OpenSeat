from . import http, config

def get_composition(category, nr, dep_e, arr_e, dep_ts, arr_ts):
    url = f"{config.API_GATEWAY}/grm/sklad/wbnet/{category}/{nr}/{arr_ts}/{dep_e}/{dep_ts}/{arr_e}"
    response = http.get(url)
    return response.json()

def get_seats(category, nr, wagon, schema, dep_e, arr_e, dep_ts, arr_ts):
    url = f"{config.API_GATEWAY}/grm/wagon/svg/wbnet/{category}/{nr}/{wagon}/{schema}/{dep_ts}/{arr_ts}/{dep_e}/{arr_e}"
    response = http.get(url)
    return response.text

def get_route(nr, departure, from_h, to_h):
    body = {
        "metoda": "pobierzTrasePrzejazdu",       
        "jezyk": "PL",
        "wersja": config.VERSION,
        "numerPociagu": nr,                    
        "dataWyjazdu": departure,                
        "stacjaWyjazdu": from_h,                 
        "stacjaPrzyjazdu": to_h,
        "url": "https://ebilet.intercity.pl/wybormiejsc",
        "urzadzenieNr": config.DEVICE_NR,
    }
    url = f"{config.API_GATEWAY}/server/public/endpoint/Pociagi"
    response = http.post(url, data=body)
    return response.json()["trasePrzejezdu"]["trasaPrzejazdu"]

def search_connections(from_h, to_h, date):
    body = {
        "metoda": "wyszukajPolaczenia", "wersja": config.VERSION,
        "dataWyjazdu": f"{date} 00:00:00", "dataPrzyjazdu": f"{date} 23:59:59",
        "stacjaWyjazdu": from_h, "stacjaPrzyjazdu": to_h,
        "czasNaPrzesiadkeMin": 5, "czasNaPrzesiadkeMax": 1440, "liczbaPrzesiadekMax": 0,
        "stacjePrzez": [], "polaczeniaBezposrednie": 1, "polaczeniaNajszybsze": 0,
        "kategoriePociagow": [], "rodzajeMiejsc": [], "typyMiejsc": [],
        "atrybutyHandlowe": [], "braille": 0, "urzadzenieNr": config.DEVICE_NR,
    }
    url = f"{config.API_GATEWAY}/server/public/endpoint/Pociagi"
    response = http.post(url, body)
    trains = []
    for c in response.json()["polaczenia"]:
        if len(c["pociagi"]) == 1:                
            t = c["pociagi"][0]
            trains.append({
                "category": t["kategoriaPociagu"],
                "number": str(t["nrPociagu"]),
                "name": t["nazwaPociagu"],
                "departure": t["dataWyjazdu"],
            })
    return trains