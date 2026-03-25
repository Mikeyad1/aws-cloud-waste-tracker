# AWS setup content (used by Setup page). No page header.
from __future__ import annotations

import os
import json
import streamlit as st

from cwt_ui.components.settings.settings_config import SettingsManager
from cwt_ui.components.settings.settings_aws import render_clean_credentials_form
from cwt_ui.components.services.scan_service import run_aws_scan
from cwt_ui.services.aws_connection_check import verify_assumed_role_access


def _debug_write(message: str) -> None:
    pass


# Maps to settings aws.account_context — sets expectations for Cost Explorer vs resource scope (one IAM role = one account).
_ACCOUNT_CONTEXT_OPTIONS: dict[str, str] = {
    "standalone": "Single AWS account — you’re connecting one account (most common)",
    "org_member": "Member account in an Organization — workload / linked account",
    "org_payer": "Management or payer account — consolidated billing or org admin",
}


def _run_connection_verification_and_store() -> None:
    """Assume role and run STS / CE / EC2 smoke checks; store result on session."""
    region = (
        st.session_state.get("selected_region")
        or st.session_state.get("aws_default_region")
        or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    )
    result = verify_assumed_role_access(
        role_arn=st.session_state.get("aws_role_arn", ""),
        external_id=st.session_state.get("aws_external_id", ""),
        session_name=st.session_state.get("aws_role_session_name", "CloudWasteTracker"),
        ec2_region=str(region),
    )
    st.session_state["aws_connection_verify"] = result


def _render_connection_verification_panel(account_ctx: str) -> None:
    """Show results of automatic connection test (after Apply role or Re-test)."""
    v = st.session_state.get("aws_connection_verify")
    if not v:
        return

    st.markdown("##### Connection test")
    if not v.get("assume_ok"):
        st.error(v.get("assume_error") or "Could not assume the IAM role.")
    else:
        ident = v.get("identity") or {}
        if ident.get("ok"):
            arn = ident.get("arn") or "—"
            acct = ident.get("account") or "—"
            st.success(f"✅ **Identity** — `{arn}` · account `{acct}`")
        else:
            st.error(f"❌ **Identity** — {ident.get('error', 'unknown error')}")

        ec2 = v.get("ec2") or {}
        if ec2.get("ok"):
            st.success("✅ **Resource access (EC2)** — DescribeInstances succeeded in the test region.")
        else:
            st.error(f"❌ **Resource access (EC2)** — {ec2.get('error_code') or ''} {ec2.get('error') or 'failed'}".strip())

        ce = v.get("cost_explorer") or {}
        if ce.get("ok"):
            st.success("✅ **Billing (Cost Explorer)** — GetCostAndUsage succeeded.")
        else:
            st.warning(
                f"❌ **Billing access (Cost Explorer)** — {ce.get('error_code') or 'Error'}: "
                f"{ce.get('error') or 'not available'}"
            )
            if account_ctx == "org_member":
                st.caption(
                    "Org-wide spend visibility often requires a role on the **management / payer** account, or broader billing IAM. "
                    "Many teams also use a **member** account by policy—both are valid."
                )
            st.caption(
                "Billing can also be blocked by **IAM**, **SCPs**, **no usage yet**, or **delay** (see below)—not only account type."
            )

    st.caption(
        "Billing data in AWS Cost Explorer often **lags actual usage by up to ~24 hours**."
    )

    if st.button("Re-test connection", key="connection_verify_retest", use_container_width=False):
        _run_connection_verification_and_store()
        st.rerun()


def _account_context_help(ctx: str) -> str:
    """Detail copy for expander: resources vs Cost Explorer vs multi-account."""
    if ctx == "org_member":
        return (
            "- **Resources (EC2, S3, …):** We only read APIs in the **account where this IAM role exists**—your member account.\n"
            "- **Cost Explorer:** Usually shows spend for **this account**. Organization-wide totals often need the "
            "**management or payer** account (or a role there with billing visibility).\n"
            "- **More accounts:** Create **another IAM role** in each account you want; each connection is one account."
        )
    if ctx == "org_payer":
        return (
            "- **Resources:** The role runs in **this** account—by default that is **this account’s** resources, not every member’s. "
            "To include other accounts, add the same trust pattern **per account** (or automation such as StackSets).\n"
            "- **Cost Explorer:** Often aligns with **payer / consolidated** visibility, subject to your IAM policy and AWS behavior.\n"
            "- **More accounts:** Same as above—**one role per account** unless you use org-wide tooling elsewhere."
        )
    return (
        "- **Resources & Cost Explorer:** Both use **this account**—the one where you create the IAM role.\n"
        "- **Organizations:** If your company uses AWS Organizations and this role is **not** in the management account, choose "
        "**Member account in an Organization** so spend expectations match reality."
    )


def _render_account_context_block(settings_manager: SettingsManager) -> str:
    """Card: which account type — avoids surprise when CE data scope differs from org expectations."""
    cfg = settings_manager.load_settings()
    default_ctx = (cfg.get("aws") or {}).get("account_context", "standalone")
    if "aws_account_context" not in st.session_state:
        st.session_state["aws_account_context"] = default_ctx if default_ctx in _ACCOUNT_CONTEXT_OPTIONS else "standalone"

    st.markdown(
        '<div class="setup-card"><h3>Which AWS account is this?</h3>'
        '<p class="setup-card-caption">Choose what best describes this AWS account (where the IAM role lives).</p>'
        '<p class="setup-card-caption setup-card-caption--tight">This only affects how we explain spend vs resource data — '
        "it doesn’t create any IAM role.</p>",
        unsafe_allow_html=True,
    )
    labels = list(_ACCOUNT_CONTEXT_OPTIONS.values())
    keys = list(_ACCOUNT_CONTEXT_OPTIONS.keys())
    current = st.session_state["aws_account_context"]
    try:
        index = keys.index(current)
    except ValueError:
        index = 0
        st.session_state["aws_account_context"] = keys[0]

    choice_label = st.selectbox(
        "Account type",
        options=labels,
        index=index,
        key="aws_account_context_selectbox",
        help=(
            "AWS Organizations uses a management account and member accounts. "
            "Consolidated billing is tied to the payer/management account. "
            "Cost Explorer returns data AWS allows for the credentials you use."
        ),
    )
    new_ctx = keys[labels.index(choice_label)]
    if new_ctx != st.session_state.get("aws_account_context"):
        st.session_state["aws_account_context"] = new_ctx
        settings_manager.set_setting("aws", "account_context", new_ctx)

    with st.expander("What this affects (resources vs spend)", expanded=False):
        st.markdown(_account_context_help(new_ctx))
    st.markdown("</div>", unsafe_allow_html=True)
    return new_ctx


def _render_setup_intro() -> None:
    st.markdown(
        '<div class="setup-intro"><p class="setup-intro-lead">You’ll go through three steps:</p>'
        "<ol class=\"setup-intro-list\">"
        "<li><strong>Choose your account type</strong> — so spend and resource insights match your AWS setup.</li>"
        "<li><strong>Create an IAM role</strong> — we use a secure, read‑only role to discover your resources.</li>"
        "<li><strong>Start a scan</strong> — pick regions to scan and review your waste.</li>"
        "</ol></div>",
        unsafe_allow_html=True,
    )


def _render_scan_mode_toggle() -> str:
    if "scan_mode" not in st.session_state:
        st.session_state["scan_mode"] = "regional"
    st.markdown("""
    <style>
        .scan-mode-row { display:flex; gap:12px; align-items:flex-start; margin-bottom:12px; }
        .scan-mode-label { font-size:0.8rem; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; color:#9ca3af; margin-bottom:4px; }
        .scan-mode-toggle {
            display:inline-flex;
            background:#020617;
            border-radius:999px;
            padding:4px;
            border:1px solid #1f2937;
            box-shadow:0 10px 26px rgba(15,23,42,0.75);
        }
        .scan-mode-pill {
            border-radius:999px;
            border:0;
            padding:6px 14px;
            font-size:0.85rem;
            font-weight:500;
            color:#9ca3af;
            background:transparent;
            cursor:pointer;
            white-space:nowrap;
        }
        .scan-mode-pill--active {
            background:linear-gradient(145deg,#22d3ee,#0ea5e9);
            color:#0b1120;
            font-weight:600;
        }
    </style>
    """, unsafe_allow_html=True)
    col_label, col_toggle = st.columns([1, 3])
    with col_label:
        st.markdown('<div class="scan-mode-label">Scan scope</div>', unsafe_allow_html=True)
    with col_toggle:
        mode = st.session_state["scan_mode"]
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(
                "📍 Regional scan",
                key="regional_scan_toggle",
                type="primary" if mode == "regional" else "secondary",
                use_container_width=True,
                help="Scan a single region for faster feedback. You choose the region below.",
            ):
                st.session_state["scan_mode"] = "regional"
                st.rerun()
        with col_b:
            if st.button(
                "🌍 Global scan",
                key="global_scan_toggle",
                type="primary" if mode == "global" else "secondary",
                use_container_width=True,
                help="Scan all enabled AWS regions automatically. Slower but most complete.",
            ):
                st.session_state["scan_mode"] = "global"
                st.rerun()
    return st.session_state["scan_mode"]


def _group_regions_by_area(regions: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"USA": [], "Europe": [], "Asia Pacific": [], "Middle East": [], "Africa": [], "South America": [], "Canada": [], "Other": []}
    for region in regions:
        if any(region.startswith(p) for p in ["us-"]): groups["USA"].append(region)
        elif any(region.startswith(p) for p in ["eu-"]): groups["Europe"].append(region)
        elif any(region.startswith(p) for p in ["ap-", "ap-south"]): groups["Asia Pacific"].append(region)
        elif any(region.startswith(p) for p in ["me-"]): groups["Middle East"].append(region)
        elif any(region.startswith(p) for p in ["af-"]): groups["Africa"].append(region)
        elif any(region.startswith(p) for p in ["sa-"]): groups["South America"].append(region)
        elif any(region.startswith(p) for p in ["ca-"]): groups["Canada"].append(region)
        else: groups["Other"].append(region)
    return {k: sorted(v) for k, v in groups.items() if v}


def _render_region_selector() -> str | None:
    try:
        from core.services.region_service import discover_enabled_regions, get_region_display_name
        aws_credentials = None
        if st.session_state.get("aws_override_enabled"):
            aws_credentials = {"AWS_DEFAULT_REGION": st.session_state.get("aws_default_region", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))}
        try:
            available_regions = discover_enabled_regions(aws_credentials, st.session_state.get("aws_auth_method", "role"))
        except Exception:
            from core.services.region_service import _common_regions
            available_regions = _common_regions()
        if not available_regions:
            available_regions = ["us-east-1"]
        if "selected_region" not in st.session_state:
            st.session_state["selected_region"] = st.session_state.get("aws_default_region", "us-east-1")
        grouped = _group_regions_by_area(available_regions)
        region_options: dict[str, str | None] = {}
        ordered_options: list[str] = []
        for group_name in ["USA", "Canada", "Europe", "Asia Pacific", "Middle East", "Africa", "South America", "Other"]:
            if group_name not in grouped or not grouped[group_name]:
                continue
            ordered_options.append(f"━━━ {group_name} ━━━")
            region_options[f"━━━ {group_name} ━━━"] = None
            for region in grouped[group_name]:
                opt = f"  └─ {get_region_display_name(region)} ({region})"
                region_options[opt] = region
                ordered_options.append(opt)
        current_region = st.session_state["selected_region"]
        current_index = 0
        option_values = [v for v in region_options.values() if v is not None]
        for idx, opt in enumerate(ordered_options):
            if region_options.get(opt) == current_region:
                current_index = idx
                break
        selected_display = st.selectbox("📍 Select AWS Region", options=ordered_options, index=current_index, key="region_selector")
        if selected_display.startswith("━━━"):
            selected_region = current_region if current_region in option_values else (option_values[0] if option_values else "us-east-1")
            st.rerun()
        else:
            selected_region = region_options[selected_display]
        st.session_state["selected_region"] = selected_region
        return selected_region
    except Exception as e:
        st.error(f"❌ Error loading regions: {str(e)}")
        return "us-east-1"


def _render_clean_css() -> None:
    st.markdown("""
    <style>
        .main .block-container { max-width: 960px; }
        .setup-step-title {
            font-size: 0.9rem;
            font-weight: 650;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #9ca3af;
            margin-top: 1.5rem;
            margin-bottom: 0.25rem;
        }
        .setup-step-title--active {
            color: #e5e7eb;
        }
        .setup-step-title--disabled {
            color: #4b5563;
        }
        .setup-card {
            background:
                radial-gradient(circle at top left, rgba(56,189,248,0.12), transparent 55%),
                linear-gradient(145deg,#020617,#020617);
            border-radius: 18px;
            border: 1px solid #1f2937;
            padding: 16px 18px 18px 18px;
            margin-bottom: 18px;
            box-shadow: 0 18px 46px rgba(15,23,42,0.9);
        }
        .setup-card--disabled {
            opacity: 0.5;
        }
        .setup-card h3 {
            margin-top: 0;
            margin-bottom: 0.5rem;
            font-size: 1rem;
            font-weight: 600;
            color: #e5e7eb;
        }
        .setup-card-caption {
            font-size: 0.85rem;
            color: #9ca3af;
            margin-bottom: 0.75rem;
        }
        .setup-card-caption--tight { margin-top: -0.35rem; margin-bottom: 0.75rem; }
        .stButton > button { font-weight: 500; transition: all 0.18s ease; border-radius: 999px; }
        .stButton > button:enabled:hover { transform: translateY(-1px); box-shadow: 0 10px 26px rgba(15,23,42,0.7); }
        .scan-mode-label { font-size:0.8rem; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; color:#9ca3af; margin-bottom:4px; }
        .setup-intro { margin-bottom: 1rem; }
        .setup-intro-lead { font-size: 0.88rem; color: #9ca3af; margin-bottom: 0.35rem; }
        .setup-intro-list { color: #d1d5db; font-size: 0.88rem; margin: 0 0 0.25rem 0; padding-left: 1.2rem; line-height: 1.45; }
        .setup-intro-list li { margin-bottom: 0.4rem; }
    </style>
    """, unsafe_allow_html=True)


def render_aws_setup_content() -> None:
    _render_clean_css()
    settings_manager = SettingsManager()
    cfg = settings_manager.load_settings()
    st.session_state.setdefault("aws_override_enabled", False)
    st.session_state.setdefault("aws_role_arn", "")
    st.session_state.setdefault("aws_external_id", "")
    st.session_state.setdefault("aws_default_region", os.getenv("AWS_DEFAULT_REGION", cfg.get("aws", {}).get("default_region", "us-east-1")))
    st.session_state.setdefault("aws_role_session_name", "CloudWasteTracker")
    st.session_state.setdefault("aws_auth_method", "role")
    st.session_state.setdefault("credentials_applied", False)
    _render_setup_intro()
    st.markdown('<div class="setup-step-title setup-step-title--active">Step 1 — Account type</div>', unsafe_allow_html=True)
    account_ctx = _render_account_context_block(settings_manager)
    st.markdown('<div class="setup-step-title setup-step-title--active">Step 2 — IAM role</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="setup-card"><h3>IAM role & credentials</h3>'
        "<p class=\"setup-card-caption\">Read-only access: we discover resources and (where permitted) Cost Explorer data. "
        "Nothing in your account is modified.</p>",
        unsafe_allow_html=True,
    )
    scan_mode = _render_scan_mode_toggle()
    if scan_mode == "global":
        st.caption("Global: assumes your role and walks every **enabled** region—slower, most complete.")
    else:
        st.caption("Regional: faster feedback; choose the region below after you connect.")
    credentials_applied = render_clean_credentials_form(settings_manager)
    if st.session_state.get("_credentials_just_applied", False):
        st.session_state["credentials_applied"] = True
        st.session_state["_credentials_just_applied"] = False
        st.success("✅ **Role configured.** Continue to Step 3 — run a scan when you’re ready.")
        _run_connection_verification_and_store()
    elif (
        st.session_state.get("credentials_applied")
        and st.session_state.get("aws_override_enabled")
        and st.session_state.get("aws_role_arn")
        and "aws_connection_verify" not in st.session_state
    ):
        _run_connection_verification_and_store()
    # Values for documentation snippets – safe fallbacks if not set
    # Default to the CloudWasteTracker AWS account ID used to assume roles.
    product_account_id = os.getenv("CWT_AWS_ACCOUNT_ID", "761095311396")
    example_external_id = st.session_state.get("aws_external_id") or "<your-external-id>"
    with st.expander("📋 **IAM role setup in AWS (console)**", expanded=False):
        st.markdown(
            "**What this role does**  \n"
            "Read-only: describe EC2, S3, RDS, Lambda, metrics, and (if allowed) Cost Explorer. **No write** actions."
        )
        st.markdown(
            "**Cost Explorer** (`ce:GetCostAndUsage`)  \n"
            "Shows spend when AWS exposes it for these credentials. Empty or partial results are often **missing permission**, "
            "**Service Control Policy**, or **account scope**—see **Which AWS account is this?** above. "
            f"Your choice there: **{_ACCOUNT_CONTEXT_OPTIONS.get(account_ctx, '—')}**."
        )
        st.markdown(
            "**Connection model**  \n"
            "We use **STS AssumeRole** into **one** AWS account per role. Create the role in **that** account, "
            "trust CloudWasteTracker’s account, use an **External ID**, then paste the role ARN here. "
            "Repeat in each account you want to connect."
        )
        st.markdown("---")
        st.markdown("#### A — Create the IAM role (AWS console)")
        st.markdown(
            "1. Sign in to the AWS console in the account you want to scan.\n"
            "2. Go to `IAM → Roles → Create role`.\n"
            "3. Choose **Trusted entity type**: `Another AWS account`.\n"
            "4. In **Account ID**, enter:"
        )
        st.code(product_account_id, language="text")
        st.markdown(
            "5. Check **Require external ID** and enter the same value you will use below in **External ID**.\n"
            "6. Click **Next**.\n"
            "7. On **Add permissions**, you don't need to attach anything yet – just click **Next**.\n"
            "8. Choose a role name (for example `CloudWasteTrackerFullScanRole`) and click **Create role**."
        )
        st.markdown("---")
        st.markdown("#### B — Attach the read‑only inline policy")
        st.markdown(
            "1. In `IAM → Roles`, click the role you just created.\n"
            "2. On the **Permissions** tab, click **Add permissions ▾ → Create inline policy**.\n"
            "3. Switch to the **JSON** tab in the policy editor.\n"
            "4. Replace any existing JSON with this example policy:\n"
        )
        st.code(
            """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWasteTrackerReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeAddresses",
        "ec2:DescribeRegions",
        "rds:DescribeDBInstances",
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "s3:GetBucketVersioning",
        "s3:GetLifecycleConfiguration",
        "lambda:ListFunctions",
        "ecs:ListClusters",
        "ecs:DescribeClusters",
        "ecs:ListTasks",
        "ecs:DescribeTasks",
        "ecs:ListServices",
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "dynamodb:ListTables",
        "dynamodb:DescribeTable",
        "ce:GetCostAndUsage",
        "cloudwatch:GetMetricStatistics"
      ],
      "Resource": "*"
    }
  ]
}""",
            language="json",
        )
        st.markdown(
            "5. Click **Next**, give the policy a name (for example `CloudWasteTrackerReadOnlyPolicy`), and click **Create policy**."
        )
        st.markdown("---")
        st.markdown("#### C — Confirm the trust policy")
        st.markdown(
            "After the role is created, open it and go to **Trust relationships → Edit trust policy**.  \n"
            "The **Principal** must be CloudWasteTracker’s account (below); the **Condition** must include the **External ID** you chose:"
        )
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": f"arn:aws:iam::{product_account_id}:root"
                    },
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {
                            "sts:ExternalId": example_external_id
                        }
                    },
                }
            ],
        }
        st.code(json.dumps(trust_policy, indent=2), language="json")
        st.markdown("---")
        st.markdown("#### D — Paste the Role ARN into this app")
        st.markdown(
            "1. In the AWS console, open the role you just created.\n"
            "2. Copy the **Role ARN** shown at the top (for example "
            "`arn:aws:iam::123456789012:role/CloudWasteTrackerFullScanRole`).\n"
            "3. Paste it into the **Role ARN** field above.\n"
            "4. Paste the same **External ID** you used in AWS into the **External ID** field.\n"
            "5. Click **Apply Role** to test the connection."
        )
    if (
        st.session_state.get("aws_override_enabled")
        and st.session_state.get("aws_role_arn")
        and st.session_state.get("aws_connection_verify")
    ):
        _render_connection_verification_panel(account_ctx)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")
    has_credentials = st.session_state.get("credentials_applied", False) or st.session_state.get("aws_override_enabled", False)
    step3_class = "setup-step-title--active" if has_credentials else "setup-step-title--disabled"
    st.markdown(f'<div class="setup-step-title {step3_class}">Step 3 — Scan</div>', unsafe_allow_html=True)
    card_disabled_class = "" if has_credentials else " setup-card--disabled"
    st.markdown(f'<div class="setup-card{card_disabled_class}"><h3>Run a scan</h3><p class="setup-card-caption">After the role works, scan here anytime for an updated waste view.</p>', unsafe_allow_html=True)
    if has_credentials:
        status_text = "✅ **Ready.** Run a scan below to see your waste." + (" Select a region for regional scan." if scan_mode == "regional" else "")
        status_bg, status_border, status_text_color = "#e7f5e7", "#28a745", "#155724"
    else:
        status_text = "⏳ **Complete Step 2** (IAM role) to connect and find your waste."
        status_bg, status_border, status_text_color = "#f8f9fa", "#6c757d", "#495057"
    st.markdown(f"<div style='padding: 0.75rem 1rem; background-color: {status_bg}; border-left: 4px solid {status_border}; border-radius: 6px; margin-bottom: 1rem; color: {status_text_color};'>{status_text}</div>", unsafe_allow_html=True)
    selected_region = _render_region_selector() if (scan_mode == "regional" and has_credentials) else None
    scan_region = None if scan_mode == "global" else selected_region
    run_scan_this_run = st.session_state.pop("_retry_scan", False)
    if run_scan_this_run:
        scan_region = st.session_state.pop("_retry_scan_region", scan_region)
    if has_credentials:
        button_text = "🌍 Run scan (all regions)" if scan_mode == "global" else f"📍 Run scan ({selected_region})"
        if not run_scan_this_run and st.button(button_text, type="primary", use_container_width=True):
            run_scan_this_run = True
        if run_scan_this_run:
            with st.spinner("Scanning..." if scan_mode == "regional" else "Scanning all enabled AWS regions..."):
                try:
                    ec2_df = run_aws_scan(region=scan_region)
                    if not ec2_df.empty:
                        st.success("✅ **Scan complete.** See your waste number and list below.")
                        st.info(f"📊 Found {len(ec2_df)} EC2 instances.")
                        st.balloons()
                        # Prominent primary CTA: See your waste (WEDGE command 4)
                        st.markdown("")
                        if st.button("See your waste →", type="primary", use_container_width=True, key="post_scan_see_waste"):
                            try:
                                st.switch_page("pages/1_Waste.py")
                            except Exception:
                                pass
                        st.caption("Your waste number and the recommendations to lower it are on the waste home.")
                    else:
                        st.warning("⚠️ **Scan completed but no resources found.**")
                except Exception as e:
                    st.error(f"❌ **Scan failed:** {str(e)}")
                    st.exception(e)
                    st.info(
                        'If the failure is **permissions**, open **\"IAM role setup in AWS (console)\"** above and attach the listed actions to your role.'
                    )
                    if st.button("Retry scan", type="primary", key="retry_scan_btn", use_container_width=True):
                        st.session_state["_retry_scan"] = True
                        st.session_state["_retry_scan_region"] = scan_region
                        st.rerun()
    else:
        st.button("Run scan", type="secondary", use_container_width=True, disabled=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")
    if st.session_state.get("last_scan_at"):
        st.markdown("### See your waste")
        try:
            st.page_link("pages/1_Waste.py", label="See your waste →", icon="📊", use_container_width=True)
        except Exception:
            st.markdown("[**See your waste →**](pages/1_Waste.py)")
        st.caption("Your waste number and the recommendations to lower it are on the waste home.")
