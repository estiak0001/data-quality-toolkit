# dqtk — Data Quality & Observability Toolkit

An installable Python package (`pip install -e .`) that profiles tables and
runs data-quality checks against them — freshness, row-count anomalies, null
rates, and schema drift — persists every run to history, and alerts on
failures via Slack or email. Built to be dropped into any pipeline (dbt,
Airflow, a cron job) as a dependency, not just run standalone.

## Why this exists

Pipelines break in a handful of recurring ways: a source stops updating
(staleness), a load silently drops most of a batch (row-count anomaly), a
upstream schema change breaks a downstream join (schema drift), or a field
that used to be populated starts coming back empty (null-rate creep). This
toolkit codifies those four checks behind one pluggable interface so they
can run against any SQL warehouse without rewriting the logic per project.

## Architecture

```
            ┌──────────────┐
  config.yml│   dqtk run   │
 ───────────►              │
            └──────┬───────┘
                   │ for each table:
                   │   1. load baseline from run history
       ┌───────────┼────────────────┐
       ▼           ▼                ▼
  ┌─────────┐ ┌───────────┐  ┌─────────────┐
  │ Adapter │ │  Checks    │  │ Run History │
  │(Postgres│ │(freshness, │  │ (Postgres:  │
  │/ClickH.)│ │ row_count, │  │ check_runs, │
  └─────────┘ │ null_rate, │  │check_results)│
              │schema_drift)│  └──────┬──────┘
              └──────┬──────┘        │
                     │ non-passing    │ read by
                     ▼                ▼
              ┌──────────────┐  ┌──────────────┐
              │  Notifiers   │  │  Streamlit    │
              │ (Slack/Email)│  │  Dashboard    │
              └──────────────┘  └──────────────┘
```

Checks never touch storage directly — the runner loads whatever baseline a
check needs (row-count history, the last schema snapshot) from `RunHistory`
and passes it in. That keeps every check unit-testable against a fake
in-memory adapter with no database involved (see `tests/test_checks.py`).

## Package layout

```
data-quality-toolkit/
  src/dqtk/
    adapters/       # Adapter interface + Postgres/ClickHouse implementations
    checks/         # freshness, row_count, null_rate, schema_drift
    notifiers/      # Slack webhook, SMTP email
    storage/        # SQLAlchemy models + RunHistory (check_runs/check_results)
    integrations/    # dbt run_results.json parser, Great Expectations checkpoint parser
    config.py       # loads config.yml into adapters/checks/notifiers
    runner.py       # orchestrates one run across all configured tables
    cli.py          # `dqtk run --config config.yml`
  dashboard/app.py   # Streamlit app reading run history
  demo/              # docker-compose demo: seed data, config, dashboard
  tests/             # unit tests, no live database required
```

## Checks

| Check | Flags | Needs |
|---|---|---|
| `freshness` | `max(column)` older than `max_age_minutes` | a timestamp column |
| `row_count` | current row count deviates `> max_pct_change` from the mean of recent runs | `min_history` prior runs to baseline against (passes trivially until then) |
| `null_rate` | fraction of NULLs in `column` exceeds `max_null_rate` | — |
| `schema_drift` | columns added/removed/type-changed since the last run | a prior run (first run just snapshots the baseline) |

Each check is a small class implementing `Check.run(adapter, table, **context) -> CheckResult`. Adding a new one means writing one class and registering it in `checks/__init__.py`'s `REGISTRY` — the CLI, config loader, and runner pick it up automatically.

## Installing

```bash
pip install -e ".[dev]"       # core + pytest
pip install -e ".[dashboard]" # core + streamlit
```

## Configuring

```yaml
storage:
  dsn: "postgresql+psycopg2://dqtk:dqtk@localhost:5432/dqtk"

adapters:
  main:
    type: postgres   # or: clickhouse
    dsn: "postgresql+psycopg2://dqtk:dqtk@localhost:5432/dqtk"

notifiers:
  - type: slack
    webhook_url: "https://hooks.slack.com/services/..."
  # - type: email
  #   smtp_host: smtp.example.com
  #   smtp_port: 587
  #   sender: dqtk@example.com
  #   recipients: ["oncall@example.com"]

tables:
  - name: public.orders
    adapter: main
    checks:
      - type: freshness
        column: updated_at
        max_age_minutes: 60
      - type: row_count
        max_pct_change: 0.3
      - type: null_rate
        column: customer_id
        max_null_rate: 0.01
      - type: schema_drift
```

## Running

```bash
dqtk run --config config.yml       # exits non-zero if any check fails/errors
dqtk run --config config.yml -v    # verbose per-check logging
```

## Integration shims

- **dbt**: `dqtk.integrations.parse_dbt_run_results("target/run_results.json")`
  converts dbt test results into the same `CheckResult` objects the native
  checks produce, so a `dbt test` run and a `dqtk run` land in one run
  history and one alert. See [retail-lakehouse](../retail-lakehouse) for a
  project this is designed to plug into.
- **Great Expectations**: `dqtk.integrations.parse_ge_checkpoint_result(checkpoint_result)`
  converts an already-run GE `CheckpointResult` the same way. No hard
  dependency on `great_expectations` — only pass it an object you already have.

## Demo (Docker Compose)

Spins up Postgres seeded with a 5,000-row "dirty" `demo.orders` table
(~1% null emails), a scheduler container that runs `dqtk run` every 60
seconds, and a Streamlit dashboard over the resulting run history.

```bash
docker compose up -d --build
```

- **Dashboard**: http://localhost:8501 — status counts, pass/warn/fail over
  time, per-table run list, and per-run check detail.
- **Postgres**: `localhost:15432` (user/password/db: `dqtk`/`dqtk`/`dqtk`) —
  `demo.orders` is the sample table being checked; `public.check_runs` /
  `public.check_results` is the run history `dqtk` writes to.

The row-count check needs `min_history` prior runs before it has a baseline
to compare against — it reports "not enough history yet" for the first few
runs, then starts flagging real deviations once one exists.

## Tests

```bash
pytest -q
```

All 21 tests run against an in-memory `FakeAdapter` or a throwaway SQLite
file — no live Postgres/ClickHouse needed, so they run in CI on every PR
(`.github/workflows/ci.yml`: ruff + pytest).

## Why this project

Demonstrates packaging a reusable internal tool properly: a clean adapter
interface so new backends are one class, checks that are unit-testable in
isolation from storage, a typed run-history schema, and shims that let it
sit alongside existing dbt/GE test suites instead of replacing them.
