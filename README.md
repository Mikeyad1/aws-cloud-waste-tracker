# Cloud Waste Tracker

Cloud Waste Tracker is a personal engineering project that scans AWS infrastructure and estimates potential monthly cloud waste. The app presents the result as a single "waste" number and a prioritized recommendation list, with drill-down into how each estimate is derived.

## Key capabilities

- **Synthetic mode**: explore the UI and recommendation logic without AWS credentials.
- **Live scanning** (when AWS credentials are available): EC2, S3, Lambda, Fargate, Databases, Savings Plans, and data transfer.
- **Action-focused output**: one waste number plus a ranked list of recommendations (with explanations per item).
- **Persistence**: stores scan runs and normalized findings in a SQL database (PostgreSQL in production, SQLite for local/dev).
- **Optional integration API**: feature-flagged FastAPI endpoints for health and scan data.
- **Background execution**: worker + cron jobs for scheduled re-scans without blocking the UI.

## Architecture overview

- **Web UI (Streamlit)**: `src/cwt_ui/app.py` and `src/cwt_ui/pages/*`
- **Scan engine**: scanner modules in `src/scanners/*` and orchestration/services in `src/core/services/*` and `src/cwt_ui/services/*`
- **Data model & persistence**: SQLAlchemy models in `src/db/models.py` and DB setup in `src/db/db.py`
- **Optional backend (FastAPI)**: `src/api/main.py`
- **Deployment topology**: `render.yaml` defines web, worker, and cron components

## Tech stack

- Python: Streamlit, FastAPI, SQLAlchemy, boto3, pandas
- Database: PostgreSQL (production), SQLite (local/dev)
- Deployment: Render
- Optional Node.js: `tools/api_healthcheck.js` (example client for API health)

## Documentation

- CV-ready project description: `docs/CV_PROJECT.md`
- Architecture notes: `docs/SYSTEM_ARCHITECTURE.md`
- Security overview: `docs/PRIVACY_AND_SECURITY.md`

## Run the app locally

```bash
streamlit run src/cwt_ui/app.py
```

## Run the API (optional)

Set `FEATURE_API_ENDPOINTS=true` and then run:

```bash
python run_api.py
```

## Run the worker (optional)

```bash
python apps/worker/main.py --region us-east-1
```
