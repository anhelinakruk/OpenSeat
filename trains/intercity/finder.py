from . import client, parser, stations

def wagon_legs_free(category, number, wagon, schema, stops, date):
    ts = date + "0000"
    legs_free = []
    for i in range(len(stops) - 1):
        a = stops[i]
        b = stops[i + 1]
        dep_e = stations.h_to_e(a["nazwaStacji"], a["kodStacji"])
        arr_e = stations.h_to_e(b["nazwaStacji"], b["kodStacji"])
        svg = client.get_seats(category, number, wagon, schema, dep_e, arr_e, ts, ts)
        seats = parser.parse_seats(svg)
        free_seats = set((wagon, s["number"]) for s in seats if s["free"])
        legs_free.append(free_seats)
    return legs_free

def train_legs_free(category, number, stops, date, wagons, schemas):
    n = len(stops) - 1
    legs_free = [set() for _ in range(n)]          # pusta lista n zbiorów (po jednym na nogę)
    for wagon in wagons:
        schema = schemas.get(str(wagon))
        if not schema:
            continue
        wlegs = wagon_legs_free(category, number, str(wagon), schema, stops, date)
        for i in range(n):
            legs_free[i] |= wlegs[i]               # |= to UNIA zbiorów: dorzuć wolne tego wagonu
    return legs_free