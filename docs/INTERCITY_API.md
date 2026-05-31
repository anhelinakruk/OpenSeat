# InterCity API — notes (data source for OpenSeat)

InterCity's unofficial, undocumented API at `https://api-gateway.intercity.pl` (behind
Akamai). OpenSeat uses it as the source of real train and seat data.

## Access (confirmed 2026-05-29)

- **No login** — no cookies, tokens or `Authorization`.
- **The `Origin: https://ebilet.intercity.pl` header is REQUIRED.** Without it Akamai resets
  the HTTP/2 connection (`curl: INTERNAL_ERROR err 2`, exit 92). This was the only blocker.
- It is worth also sending a browser `User-Agent` and `Referer: https://ebilet.intercity.pl/`.
- Responses may be gzip-compressed → `curl --compressed`.

Minimal working request:

```bash
curl -s --compressed \
  -H 'Origin: https://ebilet.intercity.pl' \
  -H 'Referer: https://ebilet.intercity.pl/' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36' \
  'https://api-gateway.intercity.pl/grm/sklad/wbnet/IC/8314/202605301707/5100143/202605301130/5100096'
```

## Known endpoints

### 1. Train composition — `/grm/sklad/...`

```
GET /grm/sklad/wbnet/{KAT}/{NR}/{ARR_TS}/{DEP_STATION_e}/{DEP_TS}/{ARR_STATION_e}
```
⚠️ **Stations are "crossed" with the timestamps!** The slot after `ARR_TS` is the
**departure** code, and the one after `DEP_TS` is the **arrival** code. (Naively pairing them
returns 404.)

| Slot | Meaning | Example (6304 Wro→Kra) |
|---|---|---|
| `KAT` | train category | `IC` |
| `NR` | train number | `6304` |
| `ARR_TS` | **arrival** time at destination, `YYYYMMDDHHMM` | `202605300808` |
| `DEP_STATION_e` | `e` code of the **departure** station | `5100143` (Wrocław) |
| `DEP_TS` | **departure** time from origin | `202605300510` |
| `ARR_STATION_e` | `e` code of the **arrival** station | `5100051` (Kraków) |

Returns JSON: `pojazdTyp`, `pojazdNazwa`, `wagony[]`, `klasa1[]/klasa2[]`,
`wagonyNiedostepne[]`, `wagonySchemat` (per wagon: `"<schema>,<compartment_type>"`),
`wagonyUdogodnienia`, `kierunekJazdy`, `klasaDomyslnyWagon`.

Sample fragment:
```json
{ "pojazdTyp": "EU160", "pojazdNazwa": "MATEJKO",
  "wagony": [10,11,12,13,14,15,17,18,19],
  "klasa1": [11], "klasa2": [10,13,14,15,17,18,19],
  "wagonyNiedostepne": [12],
  "wagonySchemat": {"10":"1356,WITHOUT_COMPARTMENTS","11":"2022,WITH_COMPARTMENTS"} }
```

### 2. Wagon seat map — `/grm/wagon/svg/...`

```
GET /grm/wagon/svg/wbnet/{KAT}/{NR}/{WAGON}/{SCHEMA},{TYP}/{DEP_TS}/{ARR_TS}/{DEP_STATION_e}/{ARR_STATION_e}
```
Here (unlike `sklad`) the order is natural: **DEP_TS, ARR_TS, DEP_station, ARR_station**.
`WAGON` is the wagon number; `SCHEMA,TYP` comes from the composition's `wagonySchemat`
(e.g. `1070,WITH_COMPARTMENTS`). Example, Wrocław→Opole leg (6304, wagon 15):
`/grm/wagon/svg/wbnet/IC/6304/15/1070,WITH_COMPARTMENTS/202605300510/202605300549/5100143/5100085`

> ⚠️ Fetch with curl (`--compressed`). Python `urllib` with bare headers randomly returned
> HTTP 500 here; `requests`/curl with the same parameters return 200.

Returns **SVG** (`application/xml`). Each seat is a group:
```xml
<g aria-label="Miejsce 15 klasa 2,  okno,  Niedostepne , niewybrane ">
  <image class="place" status="3" xlink:href="https://img.intercity.pl/grm/3R.png" .../>
  <text class="seatNum" data-class="class 2">15</text>
</g>
```
From which we read: **number** (`seatNum` / aria-label), **class**, **window/aisle**, and
**availability** (`Niedostepne` in the aria-label, `status` in `<image>`; `status="3"` = taken).

**KEY:** availability is **per-leg** — station codes and times are in the URL. The same wagon
queried for different sub-legs returns different sets of free seats. This is the foundation of
OpenSeat's seat-hopping feature.

### 3. Station autocomplete — `/station/get/`

> Note: different host — **`https://www.intercity.pl`** (not api-gateway).

```
GET https://www.intercity.pl/station/get/?q={query}
```

Works without cookies (worth adding `X-Requested-With: XMLHttpRequest` and `Origin/Referer`
for `https://www.intercity.pl`). Returns JSON — a list of stations:

```json
[ { "n": "Wrocław Główny", "p": "Wroclaw Glowny", "h": "5100069", "e": "5100143", "z": "2" } ]
```

| Field | Meaning |
|---|---|
| `n` | station name |
| `p` | name without Polish diacritics |
| `h` | station code (timetable/other system) |
| `e` | **code used by api-gateway (`sklad`/`wagon/svg`)** ← this is the one we use |
| `z` | zone/category |

**Key:** api-gateway endpoints use the **`e`** code, not `h`.
(Confirmed: Wrocław Główny `e=5100143` = the `ARR_STATION` from the example.)

### 4. Connection search — `POST /server/public/endpoint/Pociagi` ✅ WORKS

This is the MAIN search (returns the list of trains). **POST**, JSON body. Works without
cookies/login — the key is the **`urzadzenieNr`** field in the body (e.g. `956`); without it
(or with `{}`) it returns `kod:96 "Urządzenie nieaktywne"` (device inactive).

Request body (`metoda: "wyszukajPolaczenia"`):
```json
{ "metoda":"wyszukajPolaczenia", "wersja":"1.5.10_mobile",
  "dataWyjazdu":"2026-05-30 00:00:00", "dataPrzyjazdu":"2026-05-30 23:59:59",
  "stacjaWyjazdu": 5104134, "stacjaPrzyjazdu": 5100234,   // NOTE: h codes
  "czasNaPrzesiadkeMin":5, "czasNaPrzesiadkeMax":1440, "liczbaPrzesiadekMax":2,
  "stacjePrzez":[], "polaczeniaBezposrednie":0, "polaczeniaNajszybsze":0,
  "kategoriePociagow":[], "rodzajeMiejsc":[], "typyMiejsc":[],
  "urzadzenieNr": 956 }
```

Response: `{ "polaczenia": [ { "pociagi": [ <leg>, ... ] }, ... ], "bledy": [] }`.
Each `<leg>` (train): `kategoriaPociagu` (IC), `nrPociagu` (8314), `nazwaPociagu` (Matejko),
`dataWyjazdu`/`dataPrzyjazdu` (`YYYY-MM-DD HH:MM:SS`), `czasJazdy` (min),
`stacjaWyjazdu`/`stacjaPrzyjazdu` (**a third code system — small ints, e.g. 248, 162** — NOT
h, NOT e), `rodzajeMiejsc`, `typyMiejsc`, `uwagi`. A connection with >1 `pociagi` has transfers.

### 4b. Availability summary — `/availability/frequency/...`  ⚠️ 503

```
GET /availability/frequency/{KAT}/{NR}/{DEP_TS}/{ARR_TS}/{FROM_e}/{TO_e}/
```
e.g. `/availability/frequency/IC/8331/2026-05-30T09:02:00/2026-05-30T14:00:00/5100085/5100096/`
(older variant: `/availability/frequency/c/{NR}/{start}/{end}/{e}/{e}`).

Only a **summary** (count of free seats) for the results list. On the evening of 2026-05-29 it
returned **HTTP 503** (IC maintenance). **Not critical for OpenSeat** — full seat availability
comes from `/grm/wagon/svg/` (endpoint #2).

### 5. Train route — `POST /server/public/endpoint/Pociagi` ✅ WORKS

Same RPC endpoint, **different method: `pobierzTrasePrzejazdu`**. Returns the train's ordered
list of stops with times — **this is the data for the seat-hopping feature.**

Body:
```json
{ "metoda":"pobierzTrasePrzejazdu", "jezyk":"PL", "wersja":"1.5.10_mobile",
  "numerPociagu": 6304,
  "dataWyjazdu":"2026-05-30T05:10:00",       // MUST match a real departure of the run
  "stacjaWyjazdu": 5100069, "stacjaPrzyjazdu": 5100028,   // h codes
  "url":"https://ebilet.intercity.pl/wybormiejsc?...", "urzadzenieNr": 956 }
```
Response: `{ "trasePrzejezdu": { "trasaPrzejazdu": [ <stop>... ], "trasaPrzejazduInformacje": [...] }, "bledy": [] }`.
Each `<stop>`: `nazwaStacji`, `kodStacji`/`numerStacji` (**h code**, despite the
`rodzajKodStacji:"EVA"` label), `dataPrzyjazdu`/`dataWyjazdu` (`"Sat May 30 05:49:00 CEST 2026"`),
`peron`, `tor`, `dozwoloneWsiadanie/Wysiadanie`.

⚠️ Parameter-sensitive: if `dataWyjazdu`/codes don't match a real run, `trasaPrzejazdu` is
empty. Pass the exact departure time from the origin (from search [2]).

### Three station-code systems — how to bridge them

| System | Where | Wrocław Gł. | Kraków Gł. | Przemyśl Gł. |
|---|---|---|---|---|
| `h` | `Pociagi` input, `trasaPrzejazdu` output (`kodStacji`) | `5100069` | `5100028` | `5100234` |
| `e` | `sklad` / `wagon` / `availability` URLs | `5100143` | `5100051` | `5100096` |
| small int | `wyszukajPolaczenia` output | `248`/`162`/… (per run) |

**BRIDGE:** autocomplete `/station/get/` returns BOTH `h` and `e` for each station.
The route gives `h` → autocomplete → `e` → `sklad`/`wagon`. (The search's small ints are
skipped for now — we already know origin/dest from autocomplete and fetch the route by
`numerPociagu`+`h`.)

### ebilet search page (frontend URL parameters)

GA telemetry leaked the ebilet results-page URL:
```
https://ebilet.intercity.pl/wyszukiwanie?dwyj={date}&swyj={H_from}&sprzy={H_to}&time={HH:MM}&przy=0&...
```
- `dwyj` = departure date (`2026-05-30`), `time` = time (`04:00`)
- `swyj` / `sprzy` = departure / arrival station — **USES `h` CODES** (e.g. `5104134` =
  Wrocław Mikołajów `h`), NOT `e`. The frontend translates `h`→`e` somewhere before calling
  api-gateway.
- others: `przy`, `sprzez`, `ticket100`, `ticket50`, `polbez` (ticket types/options).

This is just the (SPA) page URL — the connection data is loaded by a separate api-gateway
request.

## Dependency chain (fully worked out ✅)

```
[1] name "Wrocław" ──/station/get/?q=─────────▶ h + e codes              ✅
[2] relation(h)+date ──POST Pociagi:search…────▶ train list (KAT,NR,time) ✅
[5] NR+h+date       ──POST Pociagi:route───────▶ route stops (h + times)  ✅
    (h→e via autocomplete for each stop)
[3] train+leg(e)    ──/grm/sklad/──────────────▶ wagons + schemas         ✅
[4] wagon+leg(e)    ──/grm/wagon/svg/──────────▶ free/taken seats         ✅
    (optional)      ──/availability/frequency/─▶ summary                  ⚠️503
```

## ✅ Seat-hopping proof of concept (2026-05-29, live data)

Train **IC 6304 (Grottger)**, Wrocław→Kraków, **wagon 15** (`1070,WITH_COMPARTMENTS`):
- Whole route: 60 seats, **only 2 free** (58 taken).
- Per sub-leg: Wrocław→Opole **34 free**, … , Katowice→Kraków **3 free**.
- Hop example: seat **61** free `█████·` (Wrocław→Katowice), seat **16** free `██···█`
  (incl. Katowice→Kraków) → **sit in 61 to Katowice, switch to 16 to Kraków = the whole route
  is covered**, even though neither seat is free for the whole trip.

This confirms that `/grm/wagon/svg/` queried per sub-leg provides enough data for the hopping
algorithm. **The whole chain [1]→[5] was verified end-to-end.**

## Open questions / TODO

- `pobierzTrasePrzejazdu` returned an empty route for 8314 — `dataWyjazdu` must exactly match
  the run's departure; find the correct time/codes (8314 likely does not depart Przemyśl 11:30).
- `urzadzenieNr:956` — is it fixed and long-lived, or does it require registration? Works for now.
- Small int codes from `wyszukajPolaczenia` (e.g. 248) — still unmapped, but we route around
  them (origin/dest from autocomplete, route fetched by `numerPociagu`+`h`).
- `/availability/frequency/` = 503 (non-critical — `wagon/svg` gives the full map).
- Hopping algorithm = cover the interval [origin, dest] with seats' free sub-legs, constraint:
  changes only at intermediate stations, minimise the number of transfers.

## Station code glossary (`e` code)

| Station | `h` | `e` |
|---|---|---|
| Wrocław Główny | `5100069` | `5100143` |
| Wrocław Mikołajów | `5104134` | `5100742` |
| Kraków Główny | `5100028` | `5100051` |
| Opole Główne | `5100046` | `5100085` |
| Przemyśl Główny | `5100234` | `5100096` |
| Przemyśl Zasanie | `5102825` | `5100582` |
| Gdańsk Główny | `?` | `5100022` |

(So example IC 8314 runs Przemyśl Gł. `5100096` → Wrocław Gł. `5100143`.)

## Confirmed about "any day / any train"

- **Any future date — WORKS.** Just swap the date in the `sklad`/`wagon` URL timestamps.
  Verified: IC 8314 on 2026-05-30 and 2026-06-10 returned different data (different wagon set),
  so it is real per-day data.
- **Any train — needs the train number + station codes + times.** All of that is produced by
  search [2]. Without it we only work with a train whose parameters we already know.
