"""
Scan service component for running AWS scans.
Handles the actual scanning functionality and updates session state.
"""

import streamlit as st
import pandas as pd
import os
from typing import Tuple, Optional, Dict, Any, List

from botocore.exceptions import ClientError

from cwt_ui.services.scans import fetch_savings_plan_utilization
from cwt_ui.services.spend_aggregate import normalize_optimization_df
from cwt_ui.utils.resolved_persistence import clear_resolved

# Shown when a scanner fails so users know where to find required IAM permissions
_IAM_PERMISSIONS_HINT = ' Open **Setup** and expand **IAM role setup in AWS (console)** to see which actions to attach to your role.'


def _scan_lambda_functions(region: Optional[str] | List[str] | None, ec2_df: pd.DataFrame) -> None:
    """Helper function to scan Lambda functions and store in session state.
    
    Note: This function expects AWS credentials to be available in the environment
    variables (via _temporary_env context manager or system environment).
    """
    try:
        import traceback
        from scanners.lambda_scanner import scan_lambda_functions
        
        # Determine regions to scan (reuse logic from EC2 scan)
        if region is None:
            # Extract regions from EC2 results if available
            if not ec2_df.empty and "region" in ec2_df.columns:
                lambda_regions = sorted(ec2_df["region"].unique().tolist())
                print(f"DEBUG: Using regions from EC2 scan results: {lambda_regions}")
            else:
                # Fallback: Try to discover enabled regions or use common ones
                try:
                    from core.services.region_service import discover_enabled_regions
                    # Try to discover regions (credentials should be in environment)
                    lambda_regions = discover_enabled_regions(None, "user")
                    if not lambda_regions:
                        from core.services.region_service import _common_regions
                        lambda_regions = _common_regions()
                    print(f"DEBUG: Discovered regions for Lambda scan: {lambda_regions}")
                except Exception as e:
                    print(f"DEBUG: Region discovery failed, using common regions: {e}")
                    from core.services.region_service import _common_regions
                    lambda_regions = _common_regions()
        elif isinstance(region, str):
            lambda_regions = [region]
            print(f"DEBUG: Using specified region for Lambda scan: {lambda_regions}")
        else:
            lambda_regions = region
            print(f"DEBUG: Using specified regions for Lambda scan: {lambda_regions}")
        
        if not lambda_regions:
            print("Warning: No regions available for Lambda scan")
            st.session_state["lambda_df"] = pd.DataFrame()
            return
        
        print(f"DEBUG: Starting Lambda scan for regions: {lambda_regions}")
        
        # Scan Lambda functions (credentials should be in environment)
        all_lambda_findings: list[dict[str, Any]] = []
        access_denied_regions: list[str] = []
        api_error_regions: list[str] = []

        for reg in lambda_regions:
            try:
                # Pass None for credentials - rely on environment variables already set
                findings = scan_lambda_functions(reg, None)
                if findings:
                    all_lambda_findings.extend(findings)
                    print(f"DEBUG: Found {len(findings)} Lambda functions in {reg}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                print(f"ERROR: Failed to scan Lambda functions in {reg}: {error_code} - {e}")
                if error_code in ("AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "UnauthorizedException"):
                    access_denied_regions.append(reg)
                else:
                    api_error_regions.append(reg)
            except Exception as e:
                error_trace = traceback.format_exc()
                print(f"ERROR: Failed to scan Lambda functions in {reg}: {e}")
                print(f"ERROR: Full traceback:\n{error_trace}")
                api_error_regions.append(reg)

        # Convert to DataFrame and store in session state (canonical columns: recommendation, potential_savings_usd)
        if all_lambda_findings:
            lambda_df = pd.DataFrame(all_lambda_findings)
            lambda_df = lambda_df.sort_values("function_name").reset_index(drop=True)
            lambda_df = normalize_optimization_df(lambda_df)
            st.session_state["lambda_df"] = lambda_df
            print(f"DEBUG: Lambda scan complete. Total functions: {len(lambda_df)}")
        else:
            print("DEBUG: Lambda scan complete but no functions found")
            print(f"DEBUG: Scanned regions: {lambda_regions}")

            # Distinguish between "no resources", "missing permissions", and "other AWS errors"
            if access_denied_regions:
                regions_str = ", ".join(sorted(set(access_denied_regions)))
                st.warning(
                    f"⚠️ **Lambda scan skipped in {regions_str}** – missing permission `lambda:ListFunctions`. "
                    "Open **Setup** to see the required IAM permissions."
                )
            elif api_error_regions:
                regions_str = ", ".join(sorted(set(api_error_regions)))
                st.warning(
                    f"⚠️ Could not scan Lambda in {regions_str} due to an AWS API error. "
                    "Check the console/terminal logs for details."
                )
            elif lambda_regions:
                # Call succeeded but returned zero functions
                regions_str = ", ".join(lambda_regions)
                st.info(f"ℹ️ No Lambda functions found in {regions_str}.")

            st.session_state["lambda_df"] = pd.DataFrame()
    except Exception as e:
        # Log error but don't fail the scan
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR: Lambda scan failed: {e}")
        print(f"ERROR: Full traceback:\n{error_trace}")
        st.warning(f"⚠️ **Lambda scanning failed:** {str(e)}. Check the console/terminal for details.{_IAM_PERMISSIONS_HINT}")
        st.session_state.pop("lambda_df", None)


def _scan_fargate_tasks(region: Optional[str] | List[str] | None, ec2_df: pd.DataFrame) -> None:
    """Helper function to scan Fargate tasks and store in session state.
    
    Note: This function expects AWS credentials to be available in the environment
    variables (via _temporary_env context manager or system environment).
    """
    try:
        import traceback
        from scanners.fargate_scanner import scan_fargate_tasks
        
        # Determine regions to scan (reuse logic from EC2 scan)
        if region is None:
            # Extract regions from EC2 results if available
            if not ec2_df.empty and "region" in ec2_df.columns:
                fargate_regions = sorted(ec2_df["region"].unique().tolist())
                print(f"DEBUG: Using regions from EC2 scan results: {fargate_regions}")
            else:
                # Fallback: Try to discover enabled regions or use common ones
                try:
                    from core.services.region_service import discover_enabled_regions
                    # Try to discover regions (credentials should be in environment)
                    fargate_regions = discover_enabled_regions(None, "user")
                    if not fargate_regions:
                        from core.services.region_service import _common_regions
                        fargate_regions = _common_regions()
                    print(f"DEBUG: Discovered regions for Fargate scan: {fargate_regions}")
                except Exception as e:
                    print(f"DEBUG: Region discovery failed, using common regions: {e}")
                    from core.services.region_service import _common_regions
                    fargate_regions = _common_regions()
        elif isinstance(region, str):
            fargate_regions = [region]
            print(f"DEBUG: Using specified region for Fargate scan: {fargate_regions}")
        else:
            fargate_regions = region
            print(f"DEBUG: Using specified regions for Fargate scan: {fargate_regions}")
        
        if not fargate_regions:
            print("Warning: No regions available for Fargate scan")
            st.session_state["fargate_df"] = pd.DataFrame()
            return
        
        print(f"DEBUG: Starting Fargate scan for regions: {fargate_regions}")
        
        # Scan Fargate tasks (credentials should be in environment)
        all_fargate_findings: list[dict[str, Any]] = []
        access_denied_regions: list[str] = []
        api_error_regions: list[str] = []

        for reg in fargate_regions:
            try:
                # Pass None for credentials - rely on environment variables already set
                findings = scan_fargate_tasks(reg, None)
                if findings:
                    all_fargate_findings.extend(findings)
                    print(f"DEBUG: Found {len(findings)} Fargate tasks in {reg}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                print(f"ERROR: Failed to scan Fargate tasks in {reg}: {error_code} - {e}")
                if error_code in ("AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "UnauthorizedException"):
                    access_denied_regions.append(reg)
                else:
                    api_error_regions.append(reg)
            except Exception as e:
                error_trace = traceback.format_exc()
                print(f"ERROR: Failed to scan Fargate tasks in {reg}: {e}")
                print(f"ERROR: Full traceback:\n{error_trace}")
                api_error_regions.append(reg)
        
        # Convert to DataFrame and store in session state (canonical columns: recommendation, potential_savings_usd)
        if all_fargate_findings:
            fargate_df = pd.DataFrame(all_fargate_findings)
            fargate_df = fargate_df.sort_values(["cluster_name", "service_name"]).reset_index(drop=True)
            fargate_df = normalize_optimization_df(fargate_df)
            st.session_state["fargate_df"] = fargate_df
            print(f"DEBUG: Fargate scan complete. Total tasks: {len(fargate_df)}")
        else:
            print("DEBUG: Fargate scan complete but no tasks found")
            print(f"DEBUG: Scanned regions: {fargate_regions}")

            if access_denied_regions:
                regions_str = ", ".join(sorted(set(access_denied_regions)))
                st.warning(
                    "⚠️ **Fargate scan skipped** – missing ECS permissions "
                    "(for example `ecs:ListClusters`, `ecs:ListTasks`, or `ecs:DescribeTasks`). "
                    f"Affected regions: {regions_str}. Open **Setup** to see the required IAM permissions."
                )
            elif api_error_regions:
                regions_str = ", ".join(sorted(set(api_error_regions)))
                st.warning(
                    f"⚠️ Could not scan Fargate in {regions_str} due to an AWS API error. "
                    "Check the console/terminal logs for details."
                )
            elif fargate_regions:
                regions_str = ", ".join(fargate_regions)
                st.info(f"ℹ️ No Fargate tasks found in {regions_str}.")

            st.session_state["fargate_df"] = pd.DataFrame()
    except Exception as e:
        # Log error but don't fail the scan
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR: Fargate scan failed: {e}")
        print(f"ERROR: Full traceback:\n{error_trace}")
        st.warning(f"⚠️ **Fargate scanning failed:** {str(e)}. Check the console/terminal for details.{_IAM_PERMISSIONS_HINT}")
        st.session_state.pop("fargate_df", None)


def _scan_storage(region: Optional[str] | List[str] | None, ec2_df: pd.DataFrame) -> None:
    """Scan S3 storage and store in session state. Uses same region list as EC2/Lambda/Fargate."""
    try:
        import traceback
        from scanners.storage_scanner import scan_storage

        if region is None:
            if not ec2_df.empty and "region" in ec2_df.columns:
                storage_regions = sorted(ec2_df["region"].unique().tolist())
            else:
                try:
                    from core.services.region_service import discover_enabled_regions
                    storage_regions = discover_enabled_regions(None, "user")
                    if not storage_regions:
                        from core.services.region_service import _common_regions
                        storage_regions = _common_regions()
                except Exception as e:
                    print(f"DEBUG: Region discovery failed for Storage: {e}")
                    from core.services.region_service import _common_regions
                    storage_regions = _common_regions()
        elif isinstance(region, str):
            storage_regions = [region]
        else:
            storage_regions = region

        if not storage_regions:
            st.session_state["storage_df"] = pd.DataFrame()
            return

        findings = scan_storage(regions=storage_regions, aws_credentials=None)
        if findings:
            storage_df = pd.DataFrame(findings)
            storage_df = normalize_optimization_df(storage_df)
            st.session_state["storage_df"] = storage_df
            print(f"DEBUG: Storage scan complete. Buckets: {len(storage_df)}")
        else:
            st.session_state["storage_df"] = pd.DataFrame()
            print("DEBUG: Storage scan complete but no buckets found")
            regions_str = ", ".join(storage_regions)
            st.info(f"ℹ️ No S3 buckets found in {regions_str}.")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        print(f"ERROR: Storage scan failed: {error_code} - {error_message}")
        if error_code in ("AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "UnauthorizedException"):
            st.warning(
                "⚠️ Missing S3 permission for bucket listing (for example `s3:ListAllMyBuckets`). "
                "Open **Setup** to see the required IAM permissions."
            )
        else:
            st.warning(
                "⚠️ Could not scan S3 storage due to an AWS API error. "
                "Check the console/terminal logs for details."
            )
        st.session_state["storage_df"] = pd.DataFrame()
    except Exception as e:
        import traceback
        print(f"ERROR: Storage scan failed: {e}\n{traceback.format_exc()}")
        st.warning(
            "⚠️ Could not scan S3 storage due to an unexpected error. "
            "Check the console/terminal logs for details."
        )
        st.session_state["storage_df"] = pd.DataFrame()


def _scan_data_transfer() -> None:
    """Scan data transfer costs via Cost Explorer and store in session state. No region loop (CE is global)."""
    try:
        import traceback
        from scanners.data_transfer_scanner import scan_data_transfer

        findings = scan_data_transfer(aws_credentials=None)
        if findings:
            dt_df = pd.DataFrame(findings)
            dt_df = normalize_optimization_df(dt_df)
            st.session_state["data_transfer_df"] = dt_df
            print(f"DEBUG: Data Transfer scan complete. Rows: {len(dt_df)}")
        else:
            st.session_state["data_transfer_df"] = pd.DataFrame()
            print("DEBUG: Data Transfer scan complete but no rows found")
    except Exception as e:
        import traceback
        print(f"ERROR: Data Transfer scan failed: {e}\n{traceback.format_exc()}")
        st.warning(f"⚠️ **Data Transfer scan failed:** {str(e)}. Check the console for details.{_IAM_PERMISSIONS_HINT}")
        st.session_state["data_transfer_df"] = pd.DataFrame()


def _scan_databases(region: Optional[str] | List[str] | None, ec2_df: pd.DataFrame) -> None:
    """Scan RDS + DynamoDB and store in session state. Uses same region list as EC2/Lambda/Fargate."""
    try:
        import traceback
        from scanners.databases_scanner import scan_databases

        if region is None:
            if not ec2_df.empty and "region" in ec2_df.columns:
                db_regions = sorted(ec2_df["region"].unique().tolist())
            else:
                try:
                    from core.services.region_service import discover_enabled_regions
                    db_regions = discover_enabled_regions(None, "user")
                    if not db_regions:
                        from core.services.region_service import _common_regions
                        db_regions = _common_regions()
                except Exception as e:
                    print(f"DEBUG: Region discovery failed for Databases: {e}")
                    from core.services.region_service import _common_regions
                    db_regions = _common_regions()
        elif isinstance(region, str):
            db_regions = [region]
        else:
            db_regions = region

        if not db_regions:
            st.session_state["databases_df"] = pd.DataFrame()
            return

        findings = scan_databases(regions=db_regions, aws_credentials=None)
        if findings:
            db_df = pd.DataFrame(findings)
            db_df = normalize_optimization_df(db_df)
            st.session_state["databases_df"] = db_df
            print(f"DEBUG: Databases scan complete. Rows: {len(db_df)}")
        else:
            st.session_state["databases_df"] = pd.DataFrame()
            print("DEBUG: Databases scan complete but no rows found")
            regions_str = ", ".join(db_regions)
            st.info(f"ℹ️ No RDS or DynamoDB resources found in {regions_str}.")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        print(f"ERROR: Databases scan failed: {error_code} - {error_message}")
        if error_code in ("AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "UnauthorizedException"):
            st.warning(
                "⚠️ Missing database permissions (for example `rds:DescribeDBInstances` or `dynamodb:ListTables`). "
                "Open **Setup** to see the required IAM permissions."
            )
        else:
            st.warning(
                "⚠️ Could not scan RDS/DynamoDB due to an AWS API error. "
                "Check the console/terminal logs for details."
            )
        st.session_state["databases_df"] = pd.DataFrame()
    except Exception as e:
        import traceback
        print(f"ERROR: Databases scan failed: {e}\n{traceback.format_exc()}")
        st.warning(
            "⚠️ Could not scan RDS/DynamoDB due to an unexpected error. "
            "Check the console/terminal logs for details."
        )
        st.session_state["databases_df"] = pd.DataFrame()


def run_aws_scan(region: Optional[str] | List[str] | None = None) -> pd.DataFrame:
    """
    Run AWS scan for specified region(s) or globally.
    
    Args:
        region: AWS region(s) to scan. Can be:
            - None: Auto-discover and scan all enabled regions (global scan)
            - Single region string (e.g., "us-east-1"): Scan only that region
            - List of regions: Scan multiple specific regions
    
    Returns:
        EC2 DataFrame with results from scanned regions
    """
    
    # Show loading state with region info
    if isinstance(region, list):
        scan_text = f"🔍 Scanning {len(region)} regions: {', '.join(region)}..."
    elif isinstance(region, str):
        scan_text = f"🔍 Scanning {region}..."
    else:
        scan_text = "🔍 Discovering and scanning all enabled regions automatically..."
    
    with st.spinner(scan_text):
        try:
            # Store previous metrics for "vs last scan" on Overview and Spend
            st.session_state["previous_optimization_potential"] = st.session_state.get("optimization_potential", 0)
            st.session_state["previous_action_count"] = st.session_state.get("action_count", 0)
            try:
                from cwt_ui.services.spend_aggregate import get_spend_from_scan
                prev_total, _ = get_spend_from_scan()
                st.session_state["previous_spend_total"] = float(prev_total or 0)
            except Exception:
                st.session_state["previous_spend_total"] = None
            # Import the scans service
            try:
                from cwt_ui.services.enhanced_scans import run_all_scans
            except ImportError:
                from cwt_ui.services.scans import run_all_scans
            
            # Prepare AWS credentials
            aws_credentials = {}
            aws_auth_method = st.session_state.get("aws_auth_method", "role")  # Default to role
            
            if st.session_state.get("aws_override_enabled", False):
                # Use session-scoped role configuration
                default_region = None
                if isinstance(region, list) and region:
                    default_region = region[0]
                elif isinstance(region, str):
                    default_region = region
                else:
                    default_region = st.session_state.get("aws_default_region", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
                
                # For role-based auth, base credentials come from environment variables
                if st.session_state.get("aws_auth_method") == "role":
                    aws_auth_method = "role"
                    aws_credentials = {
                        "AWS_DEFAULT_REGION": default_region
                    }
                    # Add role-specific fields
                    if st.session_state.get("aws_role_arn"):
                        aws_credentials["AWS_ROLE_ARN"] = st.session_state.get("aws_role_arn", "")
                        aws_credentials["AWS_EXTERNAL_ID"] = st.session_state.get("aws_external_id", "")
                        aws_credentials["AWS_ROLE_SESSION_NAME"] = st.session_state.get("aws_role_session_name", "CloudWasteTracker")
                else:
                    # Legacy: IAM User auth (if needed for backward compatibility)
                    aws_auth_method = "user"
                    aws_credentials = {
                        "AWS_ACCESS_KEY_ID": st.session_state.get("aws_access_key_id", ""),
                        "AWS_SECRET_ACCESS_KEY": st.session_state.get("aws_secret_access_key", ""),
                        "AWS_SESSION_TOKEN": st.session_state.get("aws_session_token", ""),
                        "AWS_DEFAULT_REGION": default_region
                    }
            else:
                # No override - use environment variables directly
                # Default to role if role ARN is in environment, otherwise user
                if os.getenv("AWS_ROLE_ARN"):
                    aws_auth_method = "role"
                else:
                    aws_auth_method = "user"
            
            # Prepare credential context for scanning (needed for both EC2 and Lambda)
            from cwt_ui.services.scans import _assume_role, _temporary_env
            
            # If role-based auth, assume role first to get temporary credentials
            final_creds = None
            if aws_auth_method == "role" and aws_credentials and "AWS_ROLE_ARN" in aws_credentials:
                final_creds = _assume_role(aws_credentials)
                if not final_creds:
                    st.error(f"Failed to assume IAM role: {aws_credentials.get('AWS_ROLE_ARN', 'Unknown')}")
                    return pd.DataFrame()
            elif aws_credentials and "AWS_ACCESS_KEY_ID" in aws_credentials:
                final_creds = aws_credentials
            
            # Use credential context for all scans
            if final_creds:
                with _temporary_env(final_creds):
                    # Run EC2 scan
                    ec2_df = run_all_scans(region=region, aws_credentials=None, aws_auth_method="user")
                    ec2_df = normalize_optimization_df(ec2_df)
                    # Update session state
                    st.session_state["ec2_df"] = ec2_df
                    st.session_state["last_scan_at"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state["data_source"] = "real"
                    st.session_state["resolved_recommendations"] = []
                    clear_resolved()

                    # Fetch Savings Plans data
                    sp_df, sp_summary, sp_util_trend, sp_coverage_trend = fetch_savings_plan_utilization(None)
                    
                    # Store Savings Plans data
                    st.session_state["SP_DF"] = sp_df
                    st.session_state["SP_SUMMARY"] = sp_summary
                    st.session_state["SP_UTIL_TREND"] = sp_util_trend
                    st.session_state["SP_COVERAGE_TREND"] = sp_coverage_trend
                    
                    # Scan Lambda functions (within same credential context)
                    with st.spinner("Scanning Lambda functions..."):
                        _scan_lambda_functions(region, ec2_df)
                    
                    # Scan Fargate tasks (within same credential context)
                    with st.spinner("Scanning Fargate tasks..."):
                        _scan_fargate_tasks(region, ec2_df)
                    # Scan Storage (S3)
                    with st.spinner("Scanning S3 storage..."):
                        _scan_storage(region, ec2_df)
                    # Scan Data Transfer (Cost Explorer, global)
                    with st.spinner("Scanning data transfer..."):
                        _scan_data_transfer()
                    # Scan Databases (RDS + DynamoDB)
                    with st.spinner("Scanning RDS & DynamoDB..."):
                        _scan_databases(region, ec2_df)
            else:
                # Use environment credentials directly
                # If we have explicit credentials, wrap in context to keep them available for Lambda scan
                if aws_credentials:
                    with _temporary_env(aws_credentials):
                        # Run EC2 scan
                        ec2_df = run_all_scans(region=region, aws_credentials=None, aws_auth_method="user")
                        ec2_df = normalize_optimization_df(ec2_df)
                        # Update session state
                        st.session_state["ec2_df"] = ec2_df
                        st.session_state["last_scan_at"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.session_state["data_source"] = "real"
                        st.session_state["resolved_recommendations"] = []
                        clear_resolved()

                        # Fetch Savings Plans data
                        sp_df, sp_summary, sp_util_trend, sp_coverage_trend = fetch_savings_plan_utilization(None)
                        
                        # Store Savings Plans data
                        st.session_state["SP_DF"] = sp_df
                        st.session_state["SP_SUMMARY"] = sp_summary
                        st.session_state["SP_UTIL_TREND"] = sp_util_trend
                        st.session_state["SP_COVERAGE_TREND"] = sp_coverage_trend
                        
                        # Scan Lambda functions (within same credential context)
                        with st.spinner("Scanning Lambda functions..."):
                            _scan_lambda_functions(region, ec2_df)
                        # Scan Fargate tasks (within same credential context)
                        with st.spinner("Scanning Fargate tasks..."):
                            _scan_fargate_tasks(region, ec2_df)
                        # Scan Storage (S3)
                        with st.spinner("Scanning S3 storage..."):
                            _scan_storage(region, ec2_df)
                        # Scan Data Transfer (Cost Explorer, global)
                        with st.spinner("Scanning data transfer..."):
                            _scan_data_transfer()
                        # Scan Databases (RDS + DynamoDB)
                        with st.spinner("Scanning RDS & DynamoDB..."):
                            _scan_databases(region, ec2_df)
                else:
                    # No explicit credentials - use environment variables directly
                    # Run EC2 scan
                    ec2_df = run_all_scans(region=region, aws_credentials=aws_credentials, aws_auth_method=aws_auth_method)
                    ec2_df = normalize_optimization_df(ec2_df)
                    # Update session state
                    st.session_state["ec2_df"] = ec2_df
                    st.session_state["last_scan_at"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state["data_source"] = "real"
                    st.session_state["resolved_recommendations"] = []
                    clear_resolved()

                    # Fetch Savings Plans data
                    sp_df, sp_summary, sp_util_trend, sp_coverage_trend = fetch_savings_plan_utilization(
                        aws_credentials if aws_credentials else None
                    )
                    
                    # Store Savings Plans data
                    st.session_state["SP_DF"] = sp_df
                    st.session_state["SP_SUMMARY"] = sp_summary
                    st.session_state["SP_UTIL_TREND"] = sp_util_trend
                    st.session_state["SP_COVERAGE_TREND"] = sp_coverage_trend
                    
                    # Scan Lambda functions (using environment credentials)
                    with st.spinner("Scanning Lambda functions..."):
                        _scan_lambda_functions(region, ec2_df)
                    # Scan Fargate tasks (using environment credentials)
                    with st.spinner("Scanning Fargate tasks..."):
                        _scan_fargate_tasks(region, ec2_df)
                    # Scan Storage (S3)
                    with st.spinner("Scanning S3 storage..."):
                        _scan_storage(region, ec2_df)
                    # Scan Data Transfer (Cost Explorer, global)
                    with st.spinner("Scanning data transfer..."):
                        _scan_data_transfer()
                    # Scan Databases (RDS + DynamoDB)
                    with st.spinner("Scanning RDS & DynamoDB..."):
                        _scan_databases(region, ec2_df)
            # Clear legacy keys if present
            st.session_state.pop("savings_plans_df", None)
            st.session_state.pop("savings_plans_summary", None)
            
            # Compute EC2 vs SP alignment if both EC2 and SP data exist
            if not ec2_df.empty and not sp_df.empty:
                try:
                    from scanners.ec2_sp_alignment_scanner import scan_ec2_sp_alignment
                    alignment_df = scan_ec2_sp_alignment(
                        ec2_df, sp_df, aws_credentials if aws_credentials else None
                    )
                    st.session_state["EC2_SP_ALIGNMENT_DF"] = alignment_df
                except Exception as e:
                    # Log error but don't fail the scan
                    print(f"Warning: Failed to compute EC2-SP alignment: {e}")
                    st.session_state.pop("EC2_SP_ALIGNMENT_DF", None)
            elif not ec2_df.empty:
                # If we have EC2 but no SP, still create alignment (all instances uncovered)
                try:
                    from scanners.ec2_sp_alignment_scanner import scan_ec2_sp_alignment
                    alignment_df = scan_ec2_sp_alignment(
                        ec2_df, pd.DataFrame(), aws_credentials if aws_credentials else None
                    )
                    st.session_state["EC2_SP_ALIGNMENT_DF"] = alignment_df
                except Exception as e:
                    print(f"Warning: Failed to compute EC2-SP alignment: {e}")
                    st.session_state.pop("EC2_SP_ALIGNMENT_DF", None)

            # MVP command 27: after any scan (EC2-only or EC2+Lambda+Fargate), recompute unified waste number
            from cwt_ui.services.spend_aggregate import get_unified_optimization_metrics
            _opt, _act = get_unified_optimization_metrics()
            st.session_state["optimization_potential"] = _opt
            st.session_state["action_count"] = _act

            # Show success message with region info
            if isinstance(region, list):
                st.success(f"✅ Scan complete! Found resources in {len(region)} regions: {', '.join(region)}")
            elif isinstance(region, str):
                st.success(f"✅ Scan complete for {region}!")
            else:
                # Count unique regions in results
                regions_scanned = set()
                if not ec2_df.empty and "region" in ec2_df.columns:
                    regions_scanned.update(ec2_df["region"].unique())
                if regions_scanned:
                    regions_list = sorted(list(regions_scanned))
                    st.success(f"✅ Scan complete! Discovered and scanned {len(regions_scanned)} regions: {', '.join(regions_list)}")
                else:
                    st.success("✅ Scan complete!")
            
            return ec2_df
            
        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ Scan failed: {error_msg}")
            st.info(
                'If the failure is due to **missing IAM permissions**, go to **Setup** and open **IAM role setup in AWS (console)** to see which actions to attach to your role.'
            )
            import traceback
            full_traceback = traceback.format_exc()
            print(f"ERROR: Full traceback:\n{full_traceback}")
            # Show exception details to help debug
            with st.expander("🔍 View Error Details"):
                st.code(full_traceback, language="python")
            return pd.DataFrame()


def render_scan_button(show_region_selector: bool = True) -> bool:
    """Render scan button with optional region selector.
    
    Args:
        show_region_selector: Whether to show region selection UI
    
    Returns:
        True if scan button was clicked
    """
    if show_region_selector:
        from cwt_ui.components.services.region_selector import render_region_selector
        
        st.markdown("---")
        st.markdown("### 🔍 Scan Configuration")
        
        # Render region selector
        selected_regions = render_region_selector()
        
        # Store selected regions in session state
        if selected_regions is not None:
            st.session_state["scan_regions"] = selected_regions
        else:
            st.session_state["scan_regions"] = None  # Auto-discover
    
    return st.button("🔄 Run AWS Scan", type="primary", width="stretch")
