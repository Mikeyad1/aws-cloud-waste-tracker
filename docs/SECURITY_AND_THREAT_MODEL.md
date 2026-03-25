# Security and Threat Model

This document is meant for resume/interview clarity and for engineering review. It focuses on the practical trust boundaries of this project.

## Trust boundaries

- **App access is the trust boundary** unless you add authentication in front of the UI.
- **AWS credentials boundary:** credentials are expected to be provided via the hosting environment (or worker environment variables) and not persisted in the database as part of normal scan storage.
- **Data boundary:** scan findings are stored as normalized inventory + estimate data used by the UI.

## Main threats to consider

1. **Secret exposure**
   - Risk: AWS keys/role details could be logged or stored where they shouldn't be.
   - Mitigation: keep credentials in environment/host secret stores; avoid writing secrets into DB rows; restrict access to logs.

2. **Over-privileged AWS access**
   - Risk: credentials might allow destructive operations.
   - Mitigation: use least-privilege IAM; prefer roles with read-only permissions for the scanner operations.

3. **Incorrect assumptions leading to unsafe decisions**
   - Risk: recommendation text and estimated values could be misunderstood.
   - Mitigation: product messaging should clearly label estimates as approximate and driven by data/heuristics; security review should ensure no “guarantee” language.

4. **Abuse of integration endpoints**
   - Risk: open CORS or enabled endpoints could allow unwanted usage.
   - Mitigation: keep API endpoints gated behind feature flags; tighten allowed origins and methods when enabling outside development.

## What the project already does (and how to describe it)

- Credentials are sourced from environment variables via the app configuration (`src/config/settings.py`) and are not written into the database during normal scan persistence.
- The system supports synthetic sample mode so you can verify UI and core logic without live AWS access.
- Deployment uses separate processes for web and scan execution (web UI vs worker/cron), reducing the chance of long-running AWS calls blocking UI and helping you reason about runtime contexts.

## Evidence in the repo

- Security overview: `docs/PRIVACY_AND_SECURITY.md`
- Runtime settings and feature flags: `src/config/settings.py`
- Web entrypoint: `src/cwt_ui/app.py`
- Worker execution: `apps/worker/main.py`

