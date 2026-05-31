# InterCity API — notatki (źródło danych dla OpenSeat)

Nieoficjalne, nieudokumentowane API InterCity pod `https://api-gateway.intercity.pl`
(za Akamai). Używamy go jako źródła realnych danych o pociągach i miejscach.

## Dostęp (potwierdzone 2026-05-29)

- **Bez logowania** — żadnych cookies, tokenów ani `Authorization`.
- **WYMAGANY nagłówek `Origin: https://ebilet.intercity.pl`.** Bez niego Akamai
  resetuje połączenie HTTP/2 (`curl: INTERNAL_ERROR err 2`, kod 92). To była jedyna
  przeszkoda.
- Warto dorzucić też przeglądarkowy `User-Agent` i `Referer: https://ebilet.intercity.pl/`.
- Odpowiedzi bywają spakowane gzipem → `curl --compressed`.

Minimalny działający request:

```bash
curl -s --compressed \
  -H 'Origin: https://ebilet.intercity.pl' \
  -H 'Referer: https://ebilet.intercity.pl/' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36' \
  'https://api-gateway.intercity.pl/grm/sklad/wbnet/IC/8314/202605301707/5100143/202605301130/5100096'
```

## Znane endpointy

### 1. Skład pociągu — `/grm/sklad/...`

```
GET /grm/sklad/wbnet/{KAT}/{NR}/{ARR_TS}/{DEP_STATION_e}/{DEP_TS}/{ARR_STATION_e}
```
⚠️ **Stacje są „skrzyżowane" z godzinami!** Slot po `ARR_TS` to kod **odjazdu**, a po
`DEP_TS` to kod **przyjazdu**. (To mnie myliło — naiwne sparowanie dawało 404.)

| Slot | Znaczenie | Przykład (6304 Wro→Kra) |
|---|---|---|
| `KAT` | kategoria pociągu | `IC` |
| `NR` | numer pociągu | `6304` |
| `ARR_TS` | godz. **przyjazdu** do celu `YYYYMMDDHHMM` | `202605300808` |
| `DEP_STATION_e` | kod `e` stacji **odjazdu** | `5100143` (Wrocław) |
| `DEP_TS` | godz. **odjazdu** z początku | `202605300510` |
| `ARR_STATION_e` | kod `e` stacji **przyjazdu** | `5100051` (Kraków) |

Zwraca JSON: `pojazdTyp`, `pojazdNazwa`, `wagony[]`, `klasa1[]/klasa2[]`,
`wagonyNiedostepne[]`, `wagonySchemat` (per wagon: `"<schemat>,<typ_przedzialu>"`),
`wagonyUdogodnienia`, `kierunekJazdy`, `klasaDomyslnyWagon`.

Przykład fragmentu:
```json
{ "pojazdTyp": "EU160", "pojazdNazwa": "MATEJKO",
  "wagony": [10,11,12,13,14,15,17,18,19],
  "klasa1": [11], "klasa2": [10,13,14,15,17,18,19],
  "wagonyNiedostepne": [12],
  "wagonySchemat": {"10":"1356,WITHOUT_COMPARTMENTS","11":"2022,WITH_COMPARTMENTS"} }
```

### 2. Mapa miejsc wagonu — `/grm/wagon/svg/...`

```
GET /grm/wagon/svg/wbnet/{KAT}/{NR}/{WAGON}/{SCHEMA},{TYP}/{DEP_TS}/{ARR_TS}/{DEP_STATION_e}/{ARR_STATION_e}
```
Tu (inaczej niż `sklad`) kolejność jest naturalna: **DEP_TS, ARR_TS, DEP_stacja, ARR_stacja**.
`WAGON` to numer wagonu; `SCHEMA,TYP` z `wagonySchemat` składu (np. `1070,WITH_COMPARTMENTS`).
Przykład odcinka Wrocław→Opole (6304, wagon 15):
`/grm/wagon/svg/wbnet/IC/6304/15/1070,WITH_COMPARTMENTS/202605300510/202605300549/5100143/5100085`

> ⚠️ Pobieraj curlem (`--compressed`). Python `urllib` z gołymi nagłówkami dostawał tu
> losowo HTTP 500 — curl z tymi samymi parametrami zwraca 200.

Zwraca **SVG** (`application/xml`). Każde miejsce to grupa:
```xml
<g aria-label="Miejsce 15 klasa 2,  okno,  Niedostepne , niewybrane ">
  <image class="place" status="3" xlink:href="https://img.intercity.pl/grm/3R.png" .../>
  <text class="seatNum" data-class="class 2">15</text>
</g>
```
Z czego czytamy: **numer** (`seatNum` / aria), **klasę**, **okno/korytarz**, **dostępność**
(`Niedostepne` w aria-label, `status` w `<image>`; `status="3"` = zajęte).

**KLUCZOWE:** dostępność jest **per-odcinek** — kody stacji i godziny są w URL-u.
Ten sam wagon odpytany dla różnych pododcinków zwraca różne zbiory wolnych miejsc.
To jest fundament funkcji „przesiadki na inne miejsce" w OpenSeat.

### 3. Autouzupełnianie stacji — `/station/get/`

> Uwaga: inny host — **`https://www.intercity.pl`** (nie api-gateway).

```
GET https://www.intercity.pl/station/get/?q={fraza}
```

Działa bez cookies (warto dodać `X-Requested-With: XMLHttpRequest` i `Origin/Referer`
na `https://www.intercity.pl`). Zwraca JSON — listę stacji:

```json
[ { "n": "Wrocław Główny", "p": "Wroclaw Glowny", "h": "5100069", "e": "5100143", "z": "2" } ]
```

| Pole | Znaczenie |
|---|---|
| `n` | nazwa stacji |
| `p` | nazwa bez polskich znaków |
| `h` | kod stacji (system rozkładowy/inny) |
| `e` | **kod używany przez api-gateway (`sklad`/`wagon/svg`)** ← ten bierzemy |
| `z` | strefa/kategoria |

**Klucz:** do endpointów api-gateway używamy kodu **`e`**, nie `h`.
(Potwierdzone: Wrocław Główny `e=5100143` = `ARR_STATION` z przykładu.)

### 4. Wyszukiwarka połączeń — `POST /server/public/endpoint/Pociagi` ✅ DZIAŁA

To jest GŁÓWNA wyszukiwarka (zwraca listę pociągów). **POST**, body JSON.
Działa bez cookies/logowania — kluczem jest pole **`urzadzenieNr`** w body (np. `956`);
bez niego/`{}` zwraca `kod:96 "Urządzenie nieaktywne"`.

Body żądania (`metoda: "wyszukajPolaczenia"`):
```json
{ "metoda":"wyszukajPolaczenia", "wersja":"1.5.10_mobile",
  "dataWyjazdu":"2026-05-30 00:00:00", "dataPrzyjazdu":"2026-05-30 23:59:59",
  "stacjaWyjazdu": 5104134, "stacjaPrzyjazdu": 5100234,   // UWAGA: kody h
  "czasNaPrzesiadkeMin":5, "czasNaPrzesiadkeMax":1440, "liczbaPrzesiadekMax":2,
  "stacjePrzez":[], "polaczeniaBezposrednie":0, "polaczeniaNajszybsze":0,
  "kategoriePociagow":[], "rodzajeMiejsc":[], "typyMiejsc":[],
  "urzadzenieNr": 956 }
```

Odpowiedź: `{ "polaczenia": [ { "pociagi": [ <leg>, ... ] }, ... ], "bledy": [] }`.
Każdy `<leg>` (pociąg): `kategoriaPociagu` (IC), `nrPociagu` (8314), `nazwaPociagu`
(Matejko), `dataWyjazdu`/`dataPrzyjazdu` (`YYYY-MM-DD HH:MM:SS`), `czasJazdy` (min),
`stacjaWyjazdu`/`stacjaPrzyjazdu` (**trzeci system kodów — małe int, np. 248, 162** — NIE
h, NIE e), `rodzajeMiejsc`, `typyMiejsc`, `uwagi`. Połączenie z >1 `pociagi` = z przesiadką.

### 4b. Podsumowanie dostępności — `/availability/frequency/...`  ⚠️ 503

```
GET /availability/frequency/{KAT}/{NR}/{DEP_TS}/{ARR_TS}/{FROM_e}/{TO_e}/
```
np. `/availability/frequency/IC/8331/2026-05-30T09:02:00/2026-05-30T14:00:00/5100085/5100096/`
(starszy wariant: `/availability/frequency/c/{NR}/{start}/{koniec}/{e}/{e}`).

Daje tylko **podsumowanie** (liczba wolnych miejsc) do listy wyników. 2026-05-29 wieczór
zwraca **HTTP 503** (przerwa techniczna IC). **Niekrytyczne dla OpenSeat** — pełną
dostępność miejsc bierzemy z `/grm/wagon/svg/` (endpoint #2).

### 5. Trasa przejazdu pociągu — `POST /server/public/endpoint/Pociagi` ✅ DZIAŁA

Ten sam endpoint RPC, **inna metoda: `pobierzTrasePrzejazdu`**. Zwraca uporządkowaną
listę przystanków pociągu z godzinami — **to jest dane do funkcji przesiadek między
miejscami.**

Body:
```json
{ "metoda":"pobierzTrasePrzejazdu", "jezyk":"PL", "wersja":"1.5.10_mobile",
  "numerPociagu": 6304,
  "dataWyjazdu":"2026-05-30T05:10:00",       // MUSI trafić w realny odjazd kursu
  "stacjaWyjazdu": 5100069, "stacjaPrzyjazdu": 5100028,   // kody h
  "url":"https://ebilet.intercity.pl/wybormiejsc?...", "urzadzenieNr": 956 }
```
Odpowiedź: `{ "trasePrzejezdu": { "trasaPrzejazdu": [ <stop>... ], "trasaPrzejazduInformacje": [...] }, "bledy": [] }`.
Każdy `<stop>`: `nazwaStacji`, `kodStacji`/`numerStacji` (**kod h**, mimo etykiety
`rodzajKodStacji:"EVA"`), `dataPrzyjazdu`/`dataWyjazdu` (`"Sat May 30 05:49:00 CEST 2026"`),
`peron`, `tor`, `dozwoloneWsiadanie/Wysiadanie`.

⚠️ Czuły na parametry: jeśli `dataWyjazdu`/kody nie trafią w realny kurs → `trasaPrzejazdu`
pusta. Trzeba podać dokładny czas odjazdu z origin (z wyszukiwarki [2]).

### Trzy systemy kodów stacji — jak je łączyć

| System | Gdzie | Wrocław Gł. | Kraków Gł. | Przemyśl Gł. |
|---|---|---|---|---|
| `h` | input `Pociagi`, output `trasaPrzejazdu` (`kodStacji`) | `5100069` | `5100028` | `5100234` |
| `e` | URL-e `sklad` / `wagon` / `availability` | `5100143` | `5100051` | `5100096` |
| małe int | output wyszukiwarki `wyszukajPolaczenia` | `248`/`162`/… (zależne od kursu) |

**MOST:** autocomplete `/station/get/` zwraca dla każdej stacji OBA kody `h` i `e`.
Trasa daje `h` → autocomplete → `e` → `sklad`/`wagon`. (Małe inty z wyszukiwarki na razie
omijamy — origin/dest i tak znamy z autocomplete, a trasę pobieramy po `numerPociagu`+`h`.)

### Strona wyszukiwania ebilet (parametry URL frontu)

Z telemetrii GA wyciekł adres strony wyników ebilet:
```
https://ebilet.intercity.pl/wyszukiwanie?dwyj={data}&swyj={H_z}&sprzy={H_do}&time={HH:MM}&przy=0&...
```
- `dwyj` = data wyjazdu (`2026-05-30`), `time` = godzina (`04:00`)
- `swyj` / `sprzy` = stacja wyjazdu / przyjazdu — **UŻYWA KODÓW `h`** (np. `5104134` =
  Wrocław Mikołajów `h`), a NIE `e`. Front gdzieś tłumaczy `h`→`e` zanim woła api-gateway.
- pozostałe: `przy`, `sprzez`, `ticket100`, `ticket50`, `polbez` (typy biletu/opcje).

To tylko adres strony (SPA) — same dane połączeń ładuje osobny request do api-gateway,
którego wciąż szukamy (usługa `/availability/` bywa 503).

## Łańcuch zależności (cały rozpracowany ✅)

```
[1] nazwa "Wrocław" ──/station/get/?q=─────────▶ kody h + e               ✅
[2] relacja(h)+data ──POST Pociagi:wyszukaj…────▶ lista pociągów (KAT,NR,godz.) ✅
[5] NR+h+data       ──POST Pociagi:pobierzTrase─▶ przystanki trasy (h + godz.)  ✅
    (h→e przez autocomplete dla każdego przystanku)
[3] pociąg+odcinek(e)──/grm/sklad/──────────────▶ wagony + schematy        ✅ (8314)
[4] wagon+odcinek(e) ──/grm/wagon/svg/───────────▶ miejsca wolne/zajęte     ✅ (8314)
    (opcjonalnie)    ──/availability/frequency/──▶ podsumowanie            ⚠️503
```

## ✅ Dowód koncepcji przesiadek (2026-05-29, dane na żywo)

Pociąg **IC 6304 (Grottger)**, Wrocław→Kraków, **wagon 15** (`1070,WITH_COMPARTMENTS`):
- Pełna trasa: 60 miejsc, **wolne tylko 2** (58 zajętych).
- Po pododcinkach: Wrocław→Opole **34 wolne**, … , Katowice→Kraków **3 wolne**.
- Przykład przesiadki: miejsce **61** wolne `█████·` (Wrocław→Katowice), miejsce **16**
  wolne `██···█` (m.in. Katowice→Kraków) → **siedzisz na 61 do Katowic, przesiadasz się na
  16 do Krakowa = cała trasa pokryta**, choć żadne z nich nie jest wolne na całość.

To potwierdza, że `/grm/wagon/svg/` odpytywane per-pododcinek daje dane wystarczające do
algorytmu przesiadek. **Cały łańcuch [1]→[5] zweryfikowany end-to-end.**

## Otwarte pytania / TODO

- `pobierzTrasePrzejazdu` dla 8314 zwróciło pustą trasę — `dataWyjazdu` musi dokładnie
  trafić w odjazd kursu; ustalić właściwy czas/kody (8314 raczej nie odj. z Przemyśla 11:30).
- `urzadzenieNr:956` — czy stałe i długo ważne, czy wymaga rejestracji. Na razie działa.
- Małe int-kody z `wyszukajPolaczenia` (np. 248) — wciąż bez mapowania, ale obchodzimy je
  (origin/dest z autocomplete, trasę pobieramy po `numerPociagu`+`h`).
- `/availability/frequency/` = 503 (niekrytyczne — `wagon/svg` daje pełną mapę).
- Algorytm przesiadek = pokrycie przedziału [origin,dest] wolnymi pododcinkami miejsc,
  z ograniczeniem: przesiadki tylko na stacjach pośrednich, min. liczba przesiadek.

## Słowniczek kodów stacji (kod `e`)

| Stacja | `h` | `e` |
|---|---|---|
| Wrocław Główny | `5100069` | `5100143` |
| Wrocław Mikołajów | `5104134` | `5100742` |
| Kraków Główny | `5100028` | `5100051` |
| Opole Główne | `5100046` | `5100085` |
| Przemyśl Główny | `5100234` | `5100096` |
| Przemyśl Zasanie | `5102825` | `5100582` |
| Gdańsk Główny | `?` | `5100022` |

(Przykład IC 8314 jedzie więc Przemyśl Gł. `5100096` → Wrocław Gł. `5100143`.)

## Co potwierdzone nt. „dowolny dzień / dowolny pociąg"

- **Dowolna przyszła data — DZIAŁA.** Wystarczy podmienić datę w timestampach URL-a
  `sklad`/`wagon`. Sprawdzone: IC 8314 na 2026-05-30 i 2026-06-10 → różne dane
  (inny zestaw wagonów), więc to realne dane per-dzień.
- **Dowolny pociąg — wymaga numeru pociągu + kodów stacji + godzin.** To wszystko
  „produkuje" wyszukiwarka [2]. Bez niej działamy tylko na pociągu, którego parametry
  już znamy.
- Uwaga do [2]: złapany request `/availability/frequency/c/{73150}/...` wygląda na
  **sprawdzenie dostępności konkretnego połączenia** (`c/{id}` = id połączenia), a NIE
  na podstawową wyszukiwarkę zwracającą LISTĘ pociągów. Czyli wciąż brakuje requestu
  „znajdź połączenia" (ten, który po kliknięciu „Szukaj" zwraca listę pociągów z
  godzinami) — i to on pewnie zwraca owo `id`. Do złapania, gdy usługa wróci z 503.
