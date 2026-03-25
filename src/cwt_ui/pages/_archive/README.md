# Hidden pages (v1 wedge)

These page files are **not** in Streamlit’s discovered `pages/` location, so they do **not** appear in the sidebar or app navigation.

**Why:** For the v1 wedge we focus on **one number (your waste) + one list (what to turn off)**. Spend, Budgets, Governance, and Chargeback are available later; hiding them keeps the first-screen experience simple.

**Pages in this folder:**

| File | Page |
|------|------|
| `2_Spend.py` | Spend (where money goes) |
| `3_Budgets_Forecast.py` | Budgets & Forecast |
| `5_Governance.py` | Governance |
| `6_Chargeback.py` | Chargeback |

## How to restore them

1. Move the `.py` files from `pages/_archive/` back into `pages/`:
   - `2_Spend.py` → `pages/2_Spend.py`
   - `3_Budgets_Forecast.py` → `pages/3_Budgets_Forecast.py`
   - `5_Governance.py` → `pages/5_Governance.py`
   - `6_Chargeback.py` → `pages/6_Chargeback.py`
2. Restart the Streamlit app. They will show up in the sidebar again.

No code has been deleted; everything remains in the repo.
