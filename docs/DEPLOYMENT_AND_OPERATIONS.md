# Deployment and Operations

## Where it runs

The project is deployed as multiple Render components (web, worker, and cron) based on `render.yaml`.

## Deployment commands

The Render build steps install dependencies and create DB tables:

- `pip install -r requirements.txt`
- `python create_tables.py`

The web service starts the Streamlit UI:

- `streamlit run src/cwt_ui/app.py --server.port $PORT --server.address 0.0.0.0`

Workers and scheduling start the scan runner:

- `python apps/worker/main.py --region us-east-1`

## Operational controls to mention

Feature flags in `src/config/settings.py` control which capabilities are enabled per environment.

Examples you can reference:

- API endpoints are disabled by default in production configuration (and enabled in development).
- Web UI auto-scan on start can be controlled via `CWT_AUTO_SCAN_ON_START`.

## Environments and required variables

At a minimum, production requires:

- `DATABASE_URL` (must be PostgreSQL in production)
- AWS credential inputs via environment variables (keys and/or role configuration)

## Evidence in the repo

- Render config: `render.yaml`
- App start: `src/cwt_ui/app.py`
- Worker runtime: `apps/worker/main.py`
- DB tables init: `create_tables.py`

