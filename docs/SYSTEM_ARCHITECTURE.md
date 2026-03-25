# System Architecture

## High-level overview

Cloud Waste Tracker is designed as an end-to-end pipeline with three execution contexts:

1. **Web app (Streamlit)**: the interactive UI where users connect/choose a data source, trigger scans, and review the “waste” number and recommendations.
2. **Backend API (optional, FastAPI)**: integration endpoints that expose health and scan results to potential clients (future mobile apps, webhooks, or dashboards).
3. **Workers + scheduler**: long-running scan execution that persists results to the database on a schedule (or on demand in worker contexts).

## Component map

### Web app path

Streamlit UI (pages/components) -> scan orchestration -> scanner modules -> normalized findings -> persistence (DB) -> UI rendering.

### Worker path

Worker process -> scan orchestration -> scanner modules -> DB persistence -> data available to UI/API.

### API path (optional)

FastAPI endpoints -> DB reads + scan summary generation -> JSON responses.

## Data model responsibilities

- **Scan records** represent scan runs (status, timing).
- **Findings** represent normalized inventory items (resource identifiers, region/type, estimated monthly waste/savings, and extra attributes required for UI and recommendations).
- The database schema is oriented around enabling the product experience, not around storing full raw AWS payloads.

## Key engineering choices

- **Separation of scan execution from UI rendering** to avoid blocking user interactions.
- **Feature flags** to control which capabilities are enabled in each environment (example: API endpoints are disabled by default in production configuration).
- **Synthetic sample mode** so the UI and recommendation logic can be validated without AWS connectivity.

## Where to look in the repo

- Render deployment: `render.yaml`
- Web entrypoint: `src/cwt_ui/app.py`
- API: `src/api/main.py`
- Core orchestration/services: `src/core/services/scan_service.py` and `src/cwt_ui/services/*`
- Data model: `src/db/models.py`

