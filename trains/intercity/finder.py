from concurrent.futures import ThreadPoolExecutor

from . import client, parser, stations, hopping

def wagon_legs_free(category, number, wagon, schema, stop_e, date):
    # stop_e: gotowa lista kodów e przystanków (policzona raz w train_legs_free)
    ts = date + "0000"
    legs_free = []
    for i in range(len(stop_e) - 1):
        svg = client.get_seats(category, number, wagon, schema, stop_e[i], stop_e[i + 1], ts, ts)
        seats = parser.parse_seats(svg)
        free_seats = set((wagon, s["number"]) for s in seats if s["free"])
        legs_free.append(free_seats)
    return legs_free

def train_legs_free(category, number, stops, date, wagons, schemas):
    # kody e każdego przystanku liczymy RAZ (zamiast w każdym wagonie z osobna)
    stop_e = [stations.h_to_e(s["nazwaStacji"], s["kodStacji"]) for s in stops]
    n = len(stops) - 1
    valid = [str(w) for w in wagons if schemas.get(str(w))]   # tylko wagony ze schematem

    def fetch_wagon(wagon):                                   # praca dla jednego wagonu
        return wagon_legs_free(category, number, wagon, schemas[wagon], stop_e, date)

    legs_free = [set() for _ in range(n)]                     # po jednym zbiorze na nogę
    # ThreadPoolExecutor pobiera wszystkie wagony RÓWNOLEGLE (czekanie na sieć się nakłada)
    with ThreadPoolExecutor(max_workers=4) as pool:         # delikatnie, żeby nie zalać API
        for wlegs in pool.map(fetch_wagon, valid):
            for i in range(n):
                legs_free[i] |= wlegs[i]                      # unia: dorzuć wolne tego wagonu
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