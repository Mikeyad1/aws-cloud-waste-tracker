# Governance service: synthetic policies and violations derived from scan data.
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

# Approved regions for production (policy: production restricted to these)
APPROVED_REGIONS = ["us-east-1", "us-east-2", "us-west-2"]

# GPU instance type patterns (policy: no GPU instances)
GPU_PATTERNS = ("p2", "p3", "p4", "g4", "g5")


@dataclass
class Policy:
    id: str
    name: str
    policy_type: str
    severity: str  # "critical" | "high" | "medium"
    violation_count: int


@dataclass
class Violation:
    id: str
    resource_id: str
    resource_type: str
    policy_id: str
    policy_name: str
    account: str
    region: str
    date: str
    status: str  # "Open" | "Acknowledged"
    action_hint: str


def _env_to_account(env: str) -> str:
    try:
        from cwt_ui.services.synthetic_data import ENV_TO_LINKED_ACCOUNT_ID, LINKED_ACCOUNT_DISPLAY
        aid = ENV_TO_LINKED_ACCOUNT_ID.get(env, "456789012345")
        return LINKED_ACCOUNT_DISPLAY.get(aid, aid)
    except Exception:
        return "—"


def _get_acknowledged_ids() -> set[str]:
    return set(st.session_state.get("governance_acknowledged", []))


def _acknowledge(violation_id: str) -> None:
    ack = list(st.session_state.get("governance_acknowledged", []))
    if violation_id not in ack:
        ack.append(violation_id)
        st.session_state["governance_acknowledged"] = ack


def _derive_violations_from_ec2(ec2_df: pd.DataFrame) -> list[Violation]:
    violations: list[Violation] = []
    ack = _get_acknowledged_ids()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if ec2_df is None or ec2_df.empty:
        return violations

    itype_col = next((c for c in ["instance_type", "Instance Type"] if c in ec2_df.columns), None)
    rid_col = next((c for c in ["instance_id", "Instance ID", "InstanceId"] if c in ec2_df.columns), None)
    region_col = next((c for c in ["region", "Region"] if c in ec2_df.columns), None)
    dept_col = next((c for c in ["department", "Department"] if c in ec2_df.columns), None)
    env_col = next((c for c in ["environment", "Environment"] if c in ec2_df.columns), None)

    if not rid_col or not itype_col:
        return violations

    for _, row in ec2_df.iterrows():
        resource_id = str(row.get(rid_col, ""))
        instance_type = str(row.get(itype_col, ""))
        region = str(row.get(region_col, "—"))
        department = str(row.get(dept_col, ""))
        environment = str(row.get(env_col, "prod"))

        # Policy: No GPU instances
        if any(p in instance_type.lower() for p in GPU_PATTERNS):
            vid = f"no_gpu|{resource_id}"
            status = "Acknowledged" if vid in ack else "Open"
            violations.append(Violation(
                id=vid,
                resource_id=resource_id,
                resource_type="EC2",
                policy_id="no_gpu",
                policy_name="No GPU instances",
                account=_env_to_account(environment),
                region=region,
                date=now,
                status=status,
                action_hint="Terminate or replace with non-GPU instance; request exception if needed.",
            ))

        # Policy: All resources must have cost allocation tags
        if dept_col and department == "Unassigned":
            vid = f"cost_allocation|{resource_id}"
            status = "Acknowledged" if vid in ack else "Open"
            violations.append(Violation(
                id=vid,
                resource_id=resource_id,
                resource_type="EC2",
                policy_id="cost_allocation",
                policy_name="All resources must have cost allocation tags",
                account=_env_to_account(environment),
                region=region,
                date=now,
                status=status,
                action_hint="Add cost allocation tags (team, environment, cost-center).",
            ))

        # Policy: Production resources restricted to approved regions
        if env_col and environment == "prod" and region not in APPROVED_REGIONS:
            vid = f"approved_regions|{resource_id}"
            status = "Acknowledged" if vid in ack else "Open"
            violations.append(Violation(
                id=vid,
                resource_id=resource_id,
                resource_type="EC2",
                policy_id="approved_regions",
                policy_name="Production resources restricted to approved regions",
                account=_env_to_account(environment),
                region=region,
                date=now,
                status=status,
                action_hint=f"Move to {', '.join(APPROVED_REGIONS)} or request region exception.",
            ))

    return violations


def get_policies() -> list[Policy]:
    """Return synthetic policies with violation counts."""
    violations = get_violations()
    by_policy: dict[str, int] = {}
    for v in violations:
        by_policy[v.policy_id] = by_policy.get(v.policy_id, 0) + 1

    open_by_policy: dict[str, int] = {}
    for v in violations:
        if v.status == "Open":
            open_by_policy[v.policy_id] = open_by_policy.get(v.policy_id, 0) + 1

    policies = [
        Policy("no_gpu", "No GPU instances", "compliance", "high", open_by_policy.get("no_gpu", 0)),
        Policy("cost_allocation", "All resources must have cost allocation tags", "tagging", "medium", open_by_policy.get("cost_allocation", 0)),
        Policy("approved_regions", "Production resources restricted to approved regions", "compliance", "high", open_by_policy.get("approved_regions", 0)),
    ]
    return policies


def get_violations() -> list[Violation]:
    """Return violations derived from EC2 (and optionally other) scan data."""
    ec2_df = st.session_state.get("ec2_df", pd.DataFrame())
    return _derive_violations_from_ec2(ec2_df)


def get_open_violations_count() -> int:
    """Count of Open violations for Overview KPI."""
    return sum(1 for v in get_violations() if v.status == "Open")


def acknowledge_violation(violation_id: str) -> None:
    """Mark a violation as Acknowledged (session state only)."""
    _acknowledge(violation_id)
