# Energy Grid Intelligence — Live US Grid Demand

A full-stack analytics platform built on **EIA's live Open Data API**
(`electricity/rto/region-data`) — hourly electricity demand (MW) for four
US grid regions: NYISO (New York), PJM, CAISO (California), and ERCOT
(Texas).

**Business question:** How does electricity demand vary by region and by
time of day, and how do we keep that picture current without re-running a
one-time import every time we want fresh numbers?

This project intentionally replaced an earlier idea built on NYC's Local
Law 84 building-energy-disclosure dataset — that dataset is self-reported
**once a year per building**, so no amount of "live" API polling makes it
behave like a continuously updated feed. EIA's grid-demand series is
updated hourly and is the right fit for an actual live-refresh ETL.
<img width="897" height="790" alt="image" src="https://github.com/user-attachments/assets/24f873ef-4a18-4279-bc8b-17de39253883" />

## Architecture

```
EIA v2 API (electricity/rto/region-data)
        |
        v
   ETL (etl/run.py)  --  backfill OR incremental refresh, both UPSERT
        |
        v
   SQLite (balancing_authorities / hourly_demand)
        |
        v
   FastAPI backend (api/main.py)  --  /regions, /demand-history,
                                       /region-comparison, /hour-of-day,
                                       /refresh-status
        |
        v
   React + Recharts frontend (frontend/)  --  region/window pickers,
                                               demand trend, region
                                               comparison, daily load
                                               curve, freshness panel
```

## Why upsert, not insert-or-ignore

The sibling `retail-price-intelligence` project (source: static CSV
exports) uses insert-or-ignore, because a source row never changes after
the fact. This project can't make that assumption: **EIA revises recently
published hours** as utilities submit corrected meter reads. The
incremental refresh re-pulls a rolling 48-hour window every run and
upserts on `(ba_code, period_start)` with an on-conflict **UPDATE**, so a
later, corrected value actually overwrites the earlier one instead of
leaving stale data in place forever.

## Data quality issues found and fixed

1. **EIA revises recently published hours after the fact.** A naive
   insert-or-ignore loader would silently keep the first (possibly wrong)
   value. Fixed with upsert-on-conflict-update, re-pulling a 48h window
   each refresh (`etl/run.py::load_window`).
2. **Missing hours come back as `value: null`, not zero.** Coercing that
   to `0.0` would read as "zero demand," which is never actually true for
   a grid region. Stored as SQL `NULL` and rendered as a gap in the chart,
   not a dip to zero (`etl/transform.py::safe_float`).
3. **Period timestamps have no explicit UTC offset in the raw API**
   (`"2026-09-30T14"`). The series is documented as already normalized to
   UTC across regions; parsing it naively as each respondent's local time
   would shift non-UTC regions' charts by several hours relative to each
   other. Parsed explicitly as UTC (`etl/transform.py::parse_period`).
4. **A full backfill blows past SQLite's per-statement parameter limit.**
   A 90-day backfill across 4 regions is ~8,640 rows; pushed into one
   `INSERT` that's ~34,500 bound parameters, which fails with
   `sqlite3.OperationalError: too many SQL variables` on builds that cap
   at 999 (observed on the Python.org Windows build). Fixed by
   sub-batching the upsert well under that limit, the same fix
   `retail-price-intelligence`'s loader uses for the same reason
   (`etl/run.py::load_window`, `SQL_VARIABLE_BUDGET`). Covered by
   `tests/test_run.py`, which simulates a full-size backfill.

## Project structure

```
etl/            SQLAlchemy models, DB helpers, EIA API client, pure
                transform functions, CLI (backfill / incremental)
api/            FastAPI app + Pydantic response schemas
frontend/       React (Vite) + Recharts dashboard
tests/          pytest unit tests for the transform layer
.github/workflows/ci.yml        tests + frontend build on every push
.github/workflows/refresh.yml   scheduled hourly live-data refresh
Dockerfile, frontend/Dockerfile, docker-compose.yml
```

## Running locally

### 0. Get a free EIA API key

Register at <https://www.eia.gov/opendata/register.php> and export it:

```bash
export EIA_API_KEY=your_key_here
```

### 1. Backend

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# One-time historical backfill (e.g. the last 90 days):
python -m etl.run --backfill-days 90

uvicorn api.main:app --reload
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

To keep the data current afterward, re-run on a schedule:

```bash
python -m etl.run --incremental
```

(`.github/workflows/refresh.yml` does this automatically once per hour in
CI — it needs an `EIA_API_KEY` repo secret and a `DATABASE_URL` pointing
at a persistent database, since SQLite on a GitHub-hosted runner doesn't
survive between runs.)

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api/*` to the
FastAPI backend on port 8000.

### 3. Tests

```bash
pytest tests/ -v
```

### 4. Docker (both services)

```bash
EIA_API_KEY=your_key_here docker compose up --build
```

Frontend at `http://localhost:5173`, API at `http://localhost:8000`.

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /regions` | List tracked balancing authorities |
| `GET /demand-history/{ba_code}?hours=` | Hourly demand series for one region |
| `GET /region-comparison?hours=` | Avg/peak/min demand by region over a trailing window |
| `GET /hour-of-day/{ba_code}?hours=` | Average demand by hour-of-day (UTC) — the daily load curve |
| `GET /refresh-status` | Latest hour on record and last-pulled time per region — the point of a live pipeline over a static import |

## Possible extensions

- Swap SQLite for Postgres for the scheduled-refresh workflow (the code
  already uses SQLAlchemy; just change `DATABASE_URL`).
- Add more balancing authorities — `etl/transform.py::TRACKED_BAS` is the
  only place that needs a new entry.
- Alert on anomalies (e.g. a region's demand reading missing for >2 hours)
  using the same data the `/refresh-status` endpoint already surfaces.
