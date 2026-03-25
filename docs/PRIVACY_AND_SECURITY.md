# Privacy & security

This page is a **technical overview** of how **Cloud Waste Tracker** handles data and credentials in plain language. For **binding Terms/Privacy**, use the policy templates included in this repository.

It reflects how the application is built today; if you deploy it yourself, your environment may differ.

---

## What the product does

Cloud Waste Tracker helps you see **estimated cloud waste** (as a dollar figure) and a **list of recommendations** (resources, rough savings, and suggested actions). It can operate on **synthetic sample data** without AWS, or run **live scans** against your AWS account when you provide a supported way to authenticate.

---

## What runs where

| Component | Role |
|-----------|------|
| **Web app** | A **Streamlit** application serves the UI. In hosted deployments (for example **Render**), it runs on the provider’s infrastructure. |
| **Database** | Application data is stored in a **PostgreSQL** database (for example a managed database attached to your hosting account). |
| **Background jobs** (if enabled) | Optional **worker** or **scheduled** jobs may run the same scanning logic on a timer. They use **environment credentials** on that service, not your browser session. |

You are responsible for **who can open the app URL** and for **secrets** (database URL, AWS keys, external IDs) in your hosting dashboard or `.env` files.

---

## What we store in the database

When scans are saved successfully, the database may hold:

- **Scan records** — timing and status of a scan run.
- **Findings** — items such as resource identifiers (for example instance or bucket IDs), resource type, region, issue category, **estimated monthly savings in USD**, and **extra attributes** derived from the scan (stored as JSON) to power the UI and recommendations.

The schema is oriented around **inventory and savings estimates**, not around copying full AWS API payloads or billing exports.

**User accounts:** The codebase includes a minimal `users` table for future use. The product does not rely on full end-user login flows for the core waste number and list in the same way a typical SaaS account system would; treat access to the deployed app as your **trust boundary** unless you add authentication in front of the app.

---

## How AWS credentials are handled

### Credentials you put in the hosting environment

For deployments that use **environment variables** (for example `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, or role-related variables used by workers), those values live in the **host’s secret store** (for example Render environment variables). They are **not** written into the PostgreSQL database by the application as part of normal scan storage.

Use **least-privilege IAM** and rotate keys on your own schedule.

### Credentials and role details in the web UI

When you configure **AssumeRole** or similar options in the app:

- **Role ARN**, **external ID**, and related fields are kept in **Streamlit session state** on the server for **that browser session**. They are intended for **session use**, not for long-term storage in the app database as secret material.
- If you use **temporary access keys in the session**, those also live in **session state** for the lifetime of that session.

Closing the session or the server clearing state removes that data from the app’s memory; it does not “follow” you in a separate user profile inside the product unless you add that.

### What the app does with AWS access

With valid credentials, the scanners call **AWS APIs** (for example EC2, S3, Lambda, RDS, Cost Explorer–related usage, etc., depending on configuration) to **read** resource and cost-related information needed to compute waste and recommendations. The goal is **analysis**, not changing your resources, unless you explicitly act in AWS outside this tool.

---

## Preferences and local settings files

Non-secret preferences (for example default region, display options) may be saved to a **local settings file** (for example under your user home directory or a project `settings.json` when present). Those files are **not** a substitute for securing the host: anyone with access to the machine or repo can read them.

---

## Synthetic data

If you use **“Load synthetic data”** or similar paths, **no live AWS APIs** are required for that dataset. No AWS credentials are needed for that mode.

---

## What we do not do (product intent)

- We do **not** sell your cloud inventory or scan results to third parties.
- We do **not** use your data to train public machine-learning models (this product is not built around that).
- This document is **not** professional advice and is **not** a substitute for your own privacy policy, data protection review, or security review if you offer the app to customers or employees.

---

## Updates

When behavior or hosting changes, this page should be updated to stay accurate. **Last updated:** March 2026.
