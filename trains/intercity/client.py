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