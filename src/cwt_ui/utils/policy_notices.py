"""
Short policy / trust copy for the Streamlit UI.

Optional env vars point to published URLs for in-app links:
  CWT_TERMS_URL, CWT_PRIVACY_URL
"""

from __future__ import annotations

import os

import streamlit as st


def get_terms_url() -> str | None:
    u = os.getenv("CWT_TERMS_URL", "").strip()
    return u or None


def get_privacy_url() -> str | None:
    u = os.getenv("CWT_PRIVACY_URL", "").strip()
    return u or None


def render_setup_policy_panel() -> None:
    """Policy summary and links on the AWS Setup (Connect) page."""
    terms = get_terms_url()
    privacy = get_privacy_url()
    with st.expander("Terms/Privacy & AWS access", expanded=False):
        st.markdown(
            "**By using this Service (including connecting AWS or running scans), you agree to our "
            "Terms of Use and Privacy Policy.** If you do not agree, do not use the Service."
        )
        st.markdown(
            "**Summary (not a substitute for the full documents):**\n"
            "- **Estimates:** Dollar figures and “waste” or savings amounts are **approximate** and depend on AWS data, "
            "heuristics, and timing. They are **not** a guarantee of actual bills, refunds, or business outcomes.\n"
            "- **Recommendations:** Suggestions are **informational** only. **You** decide and apply changes in AWS; "
            "the product does not exist to modify your resources without your direction and credentials.\n"
            "- **AWS access:** Scanning uses **read-oriented** API calls (describe/list/get and, where you grant it, "
            "Cost Explorer–style reads). Use **least-privilege IAM** and protect who can access this app.\n"
            "- **Credentials:** Session fields (for example role details) are held in **server session memory** for "
            "that browser session; host secrets are configured in your deployment environment.\n"
            "- **Not professional advice:** Nothing here is financial, tax, or compliance advice."
        )
        if terms or privacy:
            c1, c2 = st.columns(2)
            with c1:
                if terms:
                    st.markdown(f"[Terms of Use]({terms})")
                else:
                    st.caption("Set `CWT_TERMS_URL` for a public Terms link.")
            with c2:
                if privacy:
                    st.markdown(f"[Privacy Policy]({privacy})")
                else:
                    st.caption("Set `CWT_PRIVACY_URL` for a public Privacy link.")
        else:
            st.info(
                "Full **Terms of Use** and **Privacy Policy** templates are included in the repository. "
                "For a public launch, publish those documents on your site and set **`CWT_TERMS_URL`** and "
                "**`CWT_PRIVACY_URL`** on your host so users can open them here."
            )


def render_waste_policy_footer() -> None:
    """Brief estimate disclaimer near the Waste page footer."""
    terms = get_terms_url()
    if terms:
        link_tail = f" [Terms of Use]({terms})."
    else:
        link_tail = " Full Terms & Privacy docs are in the repository."
    st.caption(
        "**Estimates and recommendations are informational only**—not a guarantee of savings, billing, or results."
        + link_tail
    )

