# Cloud Waste Tracker (Engineering Project)

## Project summary

Cloud Waste Tracker is an AI-assisted tool that scans AWS infrastructure and estimates potential cloud waste. It presents the result as a single monthly "waste" number plus a prioritized recommendation list.

## Engineering highlights

- Built an end-to-end tool that scans AWS infrastructure and estimates potential cloud waste, presented as a single "waste" number and a prioritized recommendation list.
- Implemented the scan pipeline and persistence layer using SQLAlchemy models, storing scan runs and normalized findings to support UI drill-down.
- Developed a Streamlit web UI that drives the workflow from connection to waste review, including interactive recommendation actions (mark resolved / exclude) and per-item explanation of how estimates are derived.
- Added an optional FastAPI backend (feature-flagged) with Pydantic schemas, including health and scan data endpoints for future integrations.
- Implemented background workers and scheduled jobs (Render) to run scans asynchronously and keep stored results updated without blocking the UI.
- Designed security-friendly trust boundaries for AWS access: credentials are provided through the runtime environment, and persisted outputs are non-secret inventory/estimate data.
- Used AI coding assistants to accelerate scaffolding and refactoring, then applied manual review to ensure correct handling of edge cases (empty results, missing fields) and safe persistence.

## Architecture overview

- Web UI: `src/cwt_ui/app.py` and `src/cwt_ui/pages/*`
- Scan orchestration and services: `src/cwt_ui/services/*` and `src/core/services/scan_service.py`
- Scanners per AWS surface: `src/scanners/*`
- Data model and persistence: `src/db/models.py` and `src/db/db.py`
- Optional API: `src/api/main.py`
- Deployment configuration: `render.yaml`

## Tech stack

- Python: Streamlit, FastAPI, SQLAlchemy, boto3, pandas
- JavaScript (Node.js): `tools/api_healthcheck.js` (simple client for `/health`)
- Database: PostgreSQL (production) and SQLite (local/dev)
- Deployment: Render (web + worker + cron)

## Security and reliability notes

- AWS credentials are sourced from environment/host secrets; scan logic is read-oriented (Describe/List/Get APIs and, where permitted, Cost Explorer reads).
- The project supports a synthetic sample mode so the core recommendation flow can be validated without live AWS access.
- Feature flags are used to enable/disable optional capabilities like API endpoints.

## AI-assisted development workflow

Cursor and GPT-based coding assistants helped with implementation speed and code organization in several areas:

- AI-assisted endpoint scaffolding and wiring in the FastAPI layer (routing + Pydantic request/response models).
- Integration glue between scanners, orchestration services, and the persistence layer.
- Streamlit UI refactors and cleanup of repetitive rendering logic.

Critical review before shipping:

- Verified data contracts and response shapes (including empty results and optional fields).
- Reviewed scanner iteration patterns (including pagination/collection handling where applicable).
- Ensured database writes match the SQLAlchemy models and correct data types for findings and attributes.
- Exercised the end-to-end flow in synthetic mode to confirm the UI and recommendation logic behave consistently without AWS credentials.

## Repo docs to reference

- Architecture notes: `docs/SYSTEM_ARCHITECTURE.md`
- Security overview: `docs/PRIVACY_AND_SECURITY.md`
- Threat model notes: `docs/SECURITY_AND_THREAT_MODEL.md`
- Deployment notes: `docs/DEPLOYMENT_AND_OPERATIONS.md`

