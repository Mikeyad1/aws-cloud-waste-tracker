# src/scanners/lambda_scanner.py
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Dict

import boto3
from botocore.exceptions import ClientError

# ----------------------
# Settings / constants
# ----------------------
DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


# ----------------------
# Helpers
# ----------------------
def _aws_client(service: str, region: str, aws_credentials: Dict[str, str] | None = None):
    """Create AWS client with optional credentials override.
    
    When aws_credentials is None, explicitly use environment variables to ensure
    we use the temporary role credentials from _temporary_env context manager.
    """
    # If credentials provided, use them; otherwise rely on environment variables
    if aws_credentials and "AWS_ACCESS_KEY_ID" in aws_credentials:
        # For role-based auth, credentials are already assumed role credentials
        # For user-based auth, use access key and secret key
        return boto3.client(
            service,
            region_name=region,
            aws_access_key_id=aws_credentials.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=aws_credentials.get("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=aws_credentials.get("AWS_SESSION_TOKEN")
        )
    else:
        # Explicitly use environment variables (important for temporary role credentials)
        return boto3.client(
            service,
            region_name=region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN")
        )


# ----------------------
# Scanner
# ----------------------
def scan_lambda_functions(region: str, aws_credentials: Dict[str, str] | None = None) -> List[Dict]:
    """
    Scan Lambda functions in the specified region.
    
    Returns a list of dictionaries containing:
    - function_name: Name of the Lambda function
    - region: AWS region
    - runtime: Runtime environment (e.g., python3.11, nodejs18.x)
    - memory_size_mb: Memory size in MB
    - timeout_seconds: Timeout in seconds
    - last_modified: Last modified date (ISO format string)
    """
    lambda_client = _aws_client("lambda", region, aws_credentials)
    
    findings: List[Dict] = []
    
    try:
        # List all Lambda functions
        paginator = lambda_client.get_paginator("list_functions")
        
        for page in paginator.paginate():
            functions = page.get("Functions", [])
            
            for func in functions:
                function_name = func.get("FunctionName", "")
                runtime = func.get("Runtime", "unknown")
                memory_size = func.get("MemorySize", 0)
                timeout = func.get("Timeout", 0)
                last_modified_str = func.get("LastModified", "")
                
                # Convert last modified to ISO format if present
                last_modified = ""
                if last_modified_str:
                    try:
                        # Parse the AWS timestamp and convert to ISO format
                        last_modified_dt = datetime.fromisoformat(
                            last_modified_str.replace("Z", "+00:00")
                        )
                        last_modified = last_modified_dt.isoformat()
                    except (ValueError, AttributeError):
                        # If parsing fails, use the original string
                        last_modified = last_modified_str
                
                finding = {
                    "function_name": function_name,
                    "region": region,
                    "runtime": runtime,
                    "memory_size_mb": memory_size,
                    "timeout_seconds": timeout,
                    "last_modified": last_modified,
                }
                
                findings.append(finding)
    
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        print(f"ERROR: Failed to scan Lambda functions in {region}: {error_code} - {error_message}")
        # Let the caller distinguish permission vs other AWS errors
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error scanning Lambda functions in {region}: {str(e)}")
        raise
    
    return findings


# ----------------------
# Public entry points
# ----------------------
def scan_lambda(region: str | None = None, aws_credentials: Dict[str, str] | None = None) -> List[Dict]:
    """
    Primary entry point for Lambda scanning.
    
    Args:
        region: AWS region to scan (defaults to DEFAULT_REGION)
        aws_credentials: Optional credentials dictionary
        
    Returns:
        List of Lambda function findings
    """
    region = region or DEFAULT_REGION
    return scan_lambda_functions(region, aws_credentials)


def run(region: str | None = None, aws_credentials: Dict[str, str] | None = None) -> List[Dict]:
    """
    Backward-compatible CLI entry point.
    
    Args:
        region: AWS region to scan
        aws_credentials: Optional credentials dictionary
        
    Returns:
        List of Lambda function findings
    """
    region = region or DEFAULT_REGION
    findings = scan_lambda_functions(region, aws_credentials)
    
    # Brief console output
    for finding in findings:
        print(
            f"[Lambda] {finding.get('function_name')} "
            f"runtime={finding.get('runtime')} "
            f"memory={finding.get('memory_size_mb')}MB "
            f"timeout={finding.get('timeout_seconds')}s"
        )
    
    return findings


if __name__ == "__main__":
    # Allow standalone testing: python -m scanners.lambda_scanner --region us-east-1
    import argparse
    
    parser = argparse.ArgumentParser(description="Cloud Waste Tracker – Lambda Functions Scanner")
    parser.add_argument("--region", default=DEFAULT_REGION)
    args = parser.parse_args()
    
    run(region=args.region)

