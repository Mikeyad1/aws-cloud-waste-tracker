"""
AWS Region Discovery Service
Handles discovering enabled regions for multi-region scanning.
"""

from __future__ import annotations
from typing import List, Optional
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def _is_debug_mode() -> bool:
    """Check if running in debug/development mode."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    return app_env != "production"


def _debug_print(message: str):
    """Print debug message only if in debug mode."""
    if _is_debug_mode():
        print(message)


def discover_enabled_regions(
    aws_credentials: Optional[dict] = None,
    aws_auth_method: str = "user"
) -> List[str]:
    """
    Discover all enabled AWS regions for the current account.
    
    Args:
        aws_credentials: Optional credential overrides
        aws_auth_method: "user" or "role"
    
    Returns:
        List of region names (e.g., ["us-east-1", "us-west-2", ...])
    """
    try:
        # Use a default region to query for all regions
        default_region = aws_credentials.get("AWS_DEFAULT_REGION", "us-east-1") if aws_credentials else os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        # DEBUG: show which credentials / profile boto3 is about to use
        from boto3.session import Session as _Session
        _debug_print("DEBUG: discover_enabled_regions credential context:")
        _debug_print("  AWS_PROFILE: {!r}".format(os.getenv("AWS_PROFILE")))
        _debug_print("  AWS_ACCESS_KEY_ID (set?): {}".format(bool(os.getenv("AWS_ACCESS_KEY_ID"))))
        _debug_print("  AWS_SECRET_ACCESS_KEY (set?): {}".format(bool(os.getenv("AWS_SECRET_ACCESS_KEY"))))
        try:
            _sess = _Session()
            _creds = _sess.get_credentials()
            profile_name = _sess.profile_name if hasattr(_sess, "profile_name") else None
            _debug_print("  boto3.Session profile: {!r}".format(profile_name))
            _debug_print(
                "  boto3.Session credentials: {}".format(
                    _creds.get_frozen_credentials() if _creds else None
                )
            )
        except Exception as _e:
            _debug_print("  boto3.Session() introspection failed: {}".format(_e))

        # Create EC2 client with credentials
        # Note: For role auth, the credentials should already contain temporary role credentials
        if aws_credentials:
            ec2_client = _create_ec2_client(default_region, aws_credentials)
        else:
            # Use environment variables / default session
            ec2_client = boto3.client("ec2", region_name=default_region)
        
        # Describe regions - this works from any region
        response = ec2_client.describe_regions()
        regions = [r["RegionName"] for r in response.get("Regions", [])]
        
        # For global scanning, return ALL regions from describe_regions
        # The accessibility check was too restrictive and could skip regions with resources
        # If a region truly isn't accessible, the scan will fail gracefully for that region
        _debug_print(f"DEBUG: Found {len(regions)} total AWS regions")
        _debug_print(f"DEBUG: Regions list (first 10): {regions[:10]}")
        return regions
        
    except (NoCredentialsError, ClientError) as e:
        print(f"⚠️  Region discovery failed: {e}")
        # Fallback to static region catalog so we still attempt all commercial regions
        return _common_regions()


def _create_ec2_client(region: str, credentials: Optional[dict] = None) -> boto3.client:
    """Create an EC2 client with optional credential overrides."""
    if credentials:
        return boto3.client(
            "ec2",
            region_name=region,
            aws_access_key_id=credentials.get("AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=credentials.get("AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=credentials.get("AWS_SESSION_TOKEN") or os.getenv("AWS_SESSION_TOKEN")
        )
    return boto3.client("ec2", region_name=region)


def _region_accessible(region: str, credentials: Optional[dict], auth_method: str) -> bool:
    """Quick check if a region is accessible (doesn't require listing resources)."""
    try:
        client = _create_ec2_client(region, credentials)
        # Simple API call to test access
        client.describe_availability_zones(MaxResults=1)
        return True
    except ClientError:
        return False


def _common_regions() -> List[str]:
    """Fallback list of AWS commercial regions when live discovery fails."""
    try:
        from boto3.session import Session

        regions = Session().get_available_regions("ec2")
        if regions:
            return sorted(set(regions))
    except Exception:
        pass

    # Absolute fallback – keep wide coverage even if boto3 session is unavailable
    return [
        "af-south-1",     # Cape Town
        "ap-east-1",      # Hong Kong
        "ap-south-1",     # Mumbai
        "ap-south-2",     # Hyderabad
        "ap-southeast-1", # Singapore
        "ap-southeast-2", # Sydney
        "ap-southeast-3", # Jakarta
        "ap-southeast-4", # Melbourne
        "ap-northeast-1", # Tokyo
        "ap-northeast-2", # Seoul
        "ap-northeast-3", # Osaka
        "ca-central-1",   # Canada (Central)
        "eu-central-1",   # Frankfurt
        "eu-central-2",    # Zurich
        "eu-west-1",      # Ireland
        "eu-west-2",      # London
        "eu-west-3",      # Paris
        "eu-north-1",     # Stockholm
        "eu-south-1",     # Milan
        "eu-south-2",     # Spain
        "il-central-1",   # Tel Aviv
        "me-south-1",     # Bahrain
        "me-central-1",   # UAE
        "sa-east-1",      # São Paulo
        "us-east-1",      # N. Virginia
        "us-east-2",      # Ohio
        "us-west-1",      # N. California
        "us-west-2",      # Oregon
    ]


def get_region_display_name(region: str) -> str:
    """Get human-readable name for a region."""
    region_names = {
        "us-east-1": "US East (N. Virginia)",
        "us-east-2": "US East (Ohio)",
        "us-west-1": "US West (N. California)",
        "us-west-2": "US West (Oregon)",
        "eu-west-1": "EU (Ireland)",
        "eu-west-2": "EU (London)",
        "eu-central-1": "EU (Frankfurt)",
        "ap-southeast-1": "Asia Pacific (Singapore)",
        "ap-southeast-2": "Asia Pacific (Sydney)",
        "ap-northeast-1": "Asia Pacific (Tokyo)",
    }
    return region_names.get(region, region)

