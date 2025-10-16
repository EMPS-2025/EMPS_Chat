# EnergyMinds Price Bot

EnergyMinds Price Bot ingests Indian Energy Exchange (IEX) market snapshots into PostgreSQL and exposes both REST and conversational interfaces for price analytics.

## Architecture Overview

```
┌────────────────┐      ┌──────────────────┐      ┌────────────────┐
│ Excel Snapshots├────▶ │ ETL Pipelines    │────▶ │ PostgreSQL DB │
└────────────────┘      │  (pandas + ORM)  │      └────────────────┘
                        └───────┬──────────┘                ▲
                                │                           │
                                ▼                           │
                        ┌──────────────────┐                 │
                        │ FastAPI REST API │◀───────────────┘
                        └────────┬─────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ Chainlit Chat Interface │
                    └─────────────────────────┘
```

Key principles:

* Deterministic, idempotent ETL for wide (`DAMGDAM.xlsx`) and tall snapshot layouts.
* Normalized schema with referential integrity and upsert-based ingestion.
* Query layer that supports hour-window and monthly aggregations with optional volume-weighting.
* 12-factor readiness: environment-driven config, Docker Compose stack, CI/CD pipeline.

## Data Model

| Table | Purpose | Notable Columns |
|-------|---------|-----------------|
| `market_day` | Uniquely identifies a trading day for DAM, GDAM, or RTM | `market`, `trade_date` |
| `dam_price` | Hourly DAM MCP values | `hour_block`, `mcp_rs_per_mwh` |
| `gdam_price` | GDAM 15-minute MCP values with volumes | `quarter_index`, `scheduled_volume_mw`, `hydro_fsv_mw` |
| `rtm_price` | RTM 15-minute MCP values with session metadata | `hour`, `session_id`, `quarter_index`, `fsv_mw` |
| `market_summary` | Aggregated metrics from wide snapshots | `label`, `value` |

All fact tables reference `market_day` via foreign keys and enforce uniqueness constraints for idempotent upserts. Helpful indexes are added on `(market_day_id, hour_block|quarter_index)` for efficient window queries.

## ETL Workflows

| File | Layout | Handler | Highlights |
|------|--------|---------|------------|
| `DAMGDAM.xlsx` | Wide (dates as columns, time blocks as rows) | `ingest_damgdam.py` | Splits DAM & GDAM sheets, converts to long format, replicates GDAM hours into 15-minute quarters, captures `RTC` and `Avg.(hh-hh)` summaries. |
| `DAM_Market Snapshot.xlsx` | Tall | `ingest_dam_snapshot.py` | Maps `Hour` → `hour_block` and upserts weighted MCP. |
| `GDAM_Market Snapshot.xlsx` | Tall (15-min) | `ingest_gdam_snapshot.py` | Derives `quarter_index` from `Time Block`, supports volume-weighted data. |
| `RTM_Market Snapshot.xlsx` | Tall (15-min with session) | `ingest_rtm_snapshot.py` | Handles session metadata and final scheduled volume. |

All loaders wrap inserts in SQLAlchemy sessions and fall back to generic upserts when PostgreSQL-specific `ON CONFLICT` is unavailable (enables SQLite-based unit tests). Failed parses are validated and logged.

## REST API

* `GET /api/health` – readiness probe.
* `GET /api/prices` – query prices with parameters:
  * `market`: `DAM|GDAM|RTM`
  * `date` (`YYYY-MM-DD`) or `month` (`YYYY-MM`)
  * `start_hour` / `end_hour` (window `[start, end)`)
  * `weighted` (bool) – volume-weighted averages for GDAM/RTM
  * `aggregate`: `avg|min|max`

Response includes Rs/MWh and Rs/kWh averages, the count of data points, and optional daily breakdowns for monthly queries.

* `POST /api/ingest/file` – upload an Excel snapshot for auto-detection and ingestion.
* `POST /api/ingest/batch` – ingest all Excel files in a mounted directory.

### Example

```bash
curl "http://localhost:8000/api/prices?market=DAM&date=2024-08-01&start_hour=0&end_hour=8"
```

## Chainlit Chatbot

Run on port `8001` with `chainlit run app/chatbot/app.py`. A lightweight NLP parser converts user prompts into API parameters (e.g., “gdam 7-10 hrs 2024-08-12 weighted”). Optional LLM-based intent parsing can be enabled via `OPENAI_API_KEY`.

## Local Development

1. Copy `.env.example` to `.env` and adjust credentials if needed.
2. Install dependencies:

```bash
./scripts/bootstrap.sh
```

> **Note:** Chainlit depends on an older FastAPI release. If you need to run the chatbot outside Docker, create a separate
> virtual environment and install `requirements.chainlit.txt` there to avoid dependency conflicts with the backend stack.

3. Run the stack:

```bash
docker-compose up --build
```

4. Drop Excel files in `./data` and ingest via:

```bash
./scripts/load_historical.sh ./data
```

FastAPI is available at `http://localhost:8000`, Chainlit at `http://localhost:8001`.

## Testing & CI

Unit tests use SQLite with ORM upserts to validate parsing and query logic:

```bash
pytest
```

GitHub Actions (`.github/workflows/ci.yml`) runs Ruff, Black, Mypy, pytest (against Postgres service), and builds Docker images on every push/PR to `main`.

## Troubleshooting

* **Duplicate key violations:** The ETL performs upserts, so ensure Excel headers are parsed correctly. If time blocks drift, adjust `parse_common.py` patterns.
* **Unexpected time ranges:** Validate hour labels in DAMGDAM wide files; regex matches `HH - HH`. Non-standard labels should be added to the parser.
* **Excel schema drift:** Update column detection logic in `ingest_*_snapshot.py` with new aliases.
* **Chainlit errors:** Verify `BACKEND_URL` points to the FastAPI service; inspect API logs for request validation issues.

## Demo Data

Place the provided files into `./data/` and run `./scripts/load_historical.sh` to seed the database. The ingest scripts are idempotent, so re-running the loader is safe.
