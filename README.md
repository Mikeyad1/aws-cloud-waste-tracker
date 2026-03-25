# Cloud Waste Tracker

Tool that scans AWS infrastructure and estimates potential monthly cloud waste. Results are shown as a single waste figure and a prioritized recommendation list, with detail on how estimates are derived.

## Live Demo
https://cloud-waste-tracker.onrender.com/Waste

## Features

- Synthetic mode for UI and logic without AWS credentials; live scans when credentials are configured (EC2, S3, Lambda, Fargate, databases, Savings Plans, data transfer, and more).
- Scan runs and findings persisted in PostgreSQL (production) or SQLite (local development).
- Optional FastAPI endpoints (feature-flagged) and background workers/cron for scheduled scans.

## Architecture

| Layer | Location |
|-------|----------|
| Web UI (Streamlit) | `src/cwt_ui/app.py`, `src/cwt_ui/pages/` |
| Scanners & orchestration | `src/scanners/`, `src/core/services/`, `src/cwt_ui/services/` |
| Data layer | `src/db/models.py`, `src/db/db.py` |
| Optional API | `src/api/main.py` |
| Deployment | `render.yaml` (web, worker, cron) |

Stack: Python (Streamlit, FastAPI, SQLAlchemy, boto3, pandas), PostgreSQL or SQLite, optional Node example at `tools/api_healthcheck.js`.

## Documentation

- [Architecture](docs/SYSTEM_ARCHITECTURE.md)
- [Deployment and operations](docs/DEPLOYMENT_AND_OPERATIONS.md)
- [Privacy and security](docs/PRIVACY_AND_SECURITY.md)
- [AI-assisted development](AI_WORKFLOW.md)

## Run locally

1. Create a virtual environment (recommended) and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Start the app:

   ```bash
   streamlit run src/cwt_ui/app.py
   ```

**Optional — API:** set `FEATURE_API_ENDPOINTS=true`, then `python run_api.py`.

**Optional — worker:** `python apps/worker/main.py --region us-east-1` (requires AWS credentials in the environment).

Production-style runs need `DATABASE_URL` and related settings as described in [Deployment and operations](docs/DEPLOYMENT_AND_OPERATIONS.md).
