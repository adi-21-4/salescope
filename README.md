# SalesCope

A hosted, multi-tenant SaaS tool that turns a shop's raw sales spreadsheet into a
dashboard, AI-written insights, a natural-language query box, and a revenue
forecast — no data science required. Upload a CSV/Excel export, confirm how its
columns map to canonical fields, and get an analytics product for your shop in
under a minute.

Built end-to-end: FastAPI + Postgres backend, React + TypeScript frontend, Claude
(Anthropic API) for narration and query translation.

## Features

- **Upload & auto-mapping** — drag in a CSV/XLSX; a heuristic column detector
  (name-keyword + dtype-sniffing) guesses which column is the date, product,
  quantity, price, category, location, and payment method, with a confidence
  score per guess. Nothing is written to the database until the mapping is
  confirmed — a wrong silent guess would otherwise produce a dashboard full of
  plausible-looking wrong numbers.
- **Data cleaning** — parses dates, flags incomplete rows instead of fabricating
  values for them, and deduplicates re-uploads via a content hash so re-importing
  the same file is a no-op.
- **Auto-generated dashboard** — revenue over time (day/week/month), top/bottom
  products, day-of-week and seasonal trends, and category/location/payment-method
  breakdowns, all computed server-side from one shared aggregates module so every
  chart and the AI narration agree with each other.
- **AI insights panel** — Claude reads the same computed aggregates the dashboard
  shows (never raw rows) and writes plain-language findings, each required to
  cite a real number from the input. Results are cached per dataset to avoid
  re-billing on every page load.
- **Natural-language query box** — ask a question in plain English; Claude
  translates it into a constrained, schema-validated query spec (never
  generated code), which a small deterministic DSL executes against the data.
  There is no `exec()` and no LLM-authored code path.
- **Forecasting** — projects the next few weeks of revenue using a method that
  scales with how much history exists: linear trend for a handful of weeks,
  Holt-Winters exponential smoothing once there's enough data, and Holt-Winters
  with yearly seasonality once there are 2+ years of history. Always reports
  which method was used and an appropriate confidence caveat.
- **Multi-tenant from day one** — every table is scoped by `shop_id`, enforced
  centrally by a FastAPI dependency (never trusted from a client-supplied
  parameter); cross-tenant access returns 404, not 403, to avoid leaking
  existence.

## Tech stack

**Backend:** FastAPI, SQLAlchemy 2.0, Alembic, Postgres, Pandas, statsmodels
(Holt-Winters forecasting), Anthropic SDK (Claude), JWT auth, pytest.

**Frontend:** React, TypeScript, Vite, Tailwind CSS, Recharts, React Router.

## Architecture notes

- **LLM calls are isolated behind a provider interface** (`services/llm/`) — only
  one file imports the `anthropic` SDK, so the provider is swappable and every
  SDK exception is translated into a clean, user-facing error before it leaves
  that module.
- **Structured outputs, not free text** — both the insights generator and the
  query translator return schema-validated Pydantic objects
  (`client.messages.parse(..., output_format=...)`), so the LLM can never
  produce malformed data the rest of the app has to defensively parse.
- **Hybrid schema** — canonical typed columns for anything charted/aggregated,
  plus a JSONB `extra` column for whatever else a shop's file contains, so an
  unusual column layout degrades gracefully instead of breaking ingestion.
- **Revenue is a generated column** (`quantity * unit_price`, computed by
  Postgres), so it's impossible for application code and the database to
  disagree on it.

## Prerequisites

- Python 3.11+
- Node 20+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for local Postgres)

## First-time setup

```bash
# 1. Start Postgres
docker compose up -d postgres

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy ..\.env.example .env     # then edit backend/.env (DB URL, JWT secret, Anthropic API key)
alembic upgrade head          # applies all migrations

# 3. Frontend
cd ../frontend
npm install
```

## Running in dev

Two terminals:

```bash
# Terminal 1 — backend (from backend/, with venv active)
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

Frontend runs at http://localhost:5173. API docs (Swagger UI): http://localhost:8000/docs.

A `.vscode/` folder is included with tasks (`Ctrl+Shift+B` to start Postgres +
backend + frontend together) and a debug launch config for the FastAPI backend.

## Tests

```bash
cd backend
pytest
```

## Project layout

- `backend/` — FastAPI + SQLAlchemy + Alembic. Key modules under `app/`:
  `services/ingestion/` (column detection + cleaning), `services/aggregates.py`
  (dashboard math), `services/forecasting.py`, `services/llm/` (provider
  abstraction + prompts + schemas), `services/query_dsl.py` (safe NL-query
  execution), `routers/` (API endpoints).
- `frontend/` — Vite + React + TypeScript + Tailwind.
- `docker-compose.yml` — local Postgres only; backend/frontend run natively via
  `uvicorn`/`npm run dev` for fast reload during dev.
