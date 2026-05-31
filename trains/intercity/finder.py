from . import client, parser, stations, hopping

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


def plan_journey(category, number, departure, from_h, to_h, date):
    # 1. trasa pociągu (przystanki z kodami h + nazwami)
    stops = client.get_route(number, departure, from_h, to_h)
    # 2. kody e początku i końca trasy (potrzebne do składu)
    dep_e = stations.h_to_e(stops[0]["nazwaStacji"], stops[0]["kodStacji"])
    arr_e = stations.h_to_e(stops[-1]["nazwaStacji"], stops[-1]["kodStacji"])
    # 3. skład pociągu (wagony + schematy)
    sk = client.get_composition(category, number, dep_e, arr_e, date + "0000", date + "0000")
    # 4. wolne miejsca per noga, w całym pociągu (pary (wagon, miejsce))
    legs = train_legs_free(category, number, stops, date, sk["wagony"], sk["wagonySchemat"])
    # 5. najlepszy plan (0 przesiadek jeśli się da, inaczej najmniej przesiadek)
    plan = hopping.find_plan(legs)

    names = [s["nazwaStacji"] for s in stops]
    segments = []
    if plan:
        for (wagon, seat), a, b in plan:               # ((wagon, miejsce), od_przystanku, do_przystanku)
            segments.append({
                "wagon": wagon, "seat": seat,
                "from": names[a], "to": names[b],
            })
    return {
        "transfers": (len(plan) - 1) if plan else None,
        "segments": segments,
    }