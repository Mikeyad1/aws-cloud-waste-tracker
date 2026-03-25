# AI-Assisted Development Notes

This project uses AI coding assistants to accelerate implementation while keeping engineering review in control.

## How AI was used

- Assisted with endpoint scaffolding and wiring in the FastAPI layer (routing, request/response model structure, and integration points).
- Helped with refactors and repetitive code cleanup across the Streamlit UI and recommendation rendering flow.
- Supported integration glue between scanners, orchestration/services, and the persistence layer.

## Critical review and validation

- Verified data contracts and response shapes (including empty scan results and optional fields).
- Reviewed scanner iteration patterns where multiple pages/collections can be involved, to ensure correct parsing.
- Ensured database writes match the SQLAlchemy models and correct data types for stored findings and derived attributes.
- Exercised the end-to-end flow in synthetic mode to confirm UI behavior and recommendation logic without requiring live AWS credentials.

## Repo evidence

- Web UI wiring: `src/cwt_ui/app.py`
- Scan orchestration and services: `src/core/services/scan_service.py` and `src/cwt_ui/services/*`
- Optional API: `src/api/main.py`
- Data persistence: `src/db/models.py` and `src/db/db.py`
- Security overview: `docs/PRIVACY_AND_SECURITY.md`
- Deployment: `render.yaml`

