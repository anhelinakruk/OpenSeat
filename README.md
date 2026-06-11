# OpenSeat

Find a seat on a "sold out" InterCity train by **changing seats along the way**.

InterCity sells seats **per route segment**, so a seat taken A→B may be free on a sub-segment.
When no single seat is free for the whole trip, OpenSeat searches every wagon and proposes a
sequence of seats (with the fewest seat changes) that together cover the journey.

The data comes live from InterCity's undocumented API — see [`docs/INTERCITY_API.md`](docs/INTERCITY_API.md).

## Architecture

```
Browser (HTML + JS)  →  Django REST API  →  InterCity client + hopping algorithm  →  InterCity API
```

- `trains/intercity/` — framework-agnostic InterCity client (HTTP, station codes, SVG parser),
  the seat-hopping algorithm (`hopping.py`) and the service layer (`finder.py`).
- `trains/models.py` — `SeatMapCache`, a database-backed cache of volatile seat maps.
- `trains/middleware.py` — per-IP rate limiting for `/api/`, to keep upstream traffic down.
- `trains/signals.py` — prunes stale `SeatMapCache` rows on save.
- `trains/api.py`, `trains/urls.py` — REST API endpoints.
- `trains/templates/index.html` — single-page frontend.

### Caching

Data is cached by how fast it changes. Slow-changing data (station codes, routes, train
compositions) lives in the in-memory cache framework. The volatile seat maps are cached in the
database (`SeatMapCache`) with a short TTL, so the cache survives restarts and is shared across
worker processes — which also keeps request volume to InterCity low.

## Requirements

- Python 3.12+ (developed on 3.14)
- Dependencies in `requirements.txt` (Django, Django REST Framework, requests)

## Setup & run

```bash
cd OpenSeat

# 1. install dependencies (into the bundled venv)
./venv/bin/python -m pip install -r requirements.txt

# 2. apply migrations for Django's built-in apps
./venv/bin/python manage.py migrate

# 3. start the development server
./venv/bin/python manage.py runserver
```

Then open <http://127.0.0.1:8000/>.

> Tip: activate the venv (`source venv/bin/activate`) and you can drop the `./venv/bin/` prefix.

## Tests

```bash
./venv/bin/python manage.py test trains
```

The tests cover the hopping algorithm, the SVG seat parser, the client's upstream-error
mapping and the `SeatMapCache` model (`trains/tests.py`). They need no network; the model tests
run against a throwaway test database that Django creates automatically.

## API

| Endpoint | Description |
|---|---|
| `GET /api/stations/?q=` | station autocomplete |
| `GET /api/connections/?from=&to=&date=` | direct trains for a relation (`from`/`to` are `h` codes, `date` is `YYYY-MM-DD`) |
| `GET /api/journey/?category=&number=&departure=&from=&to=&date=` | seat / seat-hopping plan for a chosen train |

`/api/journey/` returns options ordered by fewest seat changes (`transfers`):

```json
{
  "options": [
    {
      "transfers": 1,
      "segments": [
        {"wagon": "15", "seat": "61", "from": "Wrocław Główny", "to": "Katowice"},
        {"wagon": "15", "seat": "16", "from": "Katowice", "to": "Kraków Główny"}
      ]
    }
  ]
}
```

An empty `options` list means no seat is available, even with changes.

## Notes

- The InterCity API is unofficial and rate-limited; heavy or bursty use can get the IP
  temporarily blocked. The client retries transient errors and reports rate limiting clearly.
