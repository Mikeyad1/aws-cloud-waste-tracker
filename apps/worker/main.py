#!/usr/bin/env python3
"""
Worker application for running cloud waste scans and persisting results to database.
Usage: python apps/worker/main.py --region us-east-1
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Load .env file first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add src to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Import our modules
from config.factory import settings
from core.services.scan_service import scan_service


def main():
    parser = argparse.ArgumentParser(description="Cloud Waste Tracker - Worker")
    parser.add_argument("--region", default=settings.AWS_DEFAULT_REGION, help="AWS region to scan")
    args = parser.parse_args()
    
    print(f"🔍 Starting scan for region: {args.region}")
    print(f"🔧 Environment: {settings.APP_ENV}")
    
    try:
        # Prepare AWS credentials from environment variables
        aws_credentials = None
        aws_auth_method = "user"
        
        # Check if we have role-based credentials in environment
        if os.getenv("AWS_ROLE_ARN"):
            aws_credentials = {
                "AWS_ROLE_ARN": os.getenv("AWS_ROLE_ARN"),
                "AWS_EXTERNAL_ID": os.getenv("AWS_EXTERNAL_ID", ""),
                "AWS_ROLE_SESSION_NAME": os.getenv("AWS_ROLE_SESSION_NAME", "CloudWasteTracker"),
                "AWS_DEFAULT_REGION": args.region,
            }
            # Add base credentials if available
            if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
                aws_credentials.update({
                    "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
                    "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
                })
            aws_auth_method = "role"
            print("🔐 Using IAM Role authentication")
        elif os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            aws_credentials = {
                "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
                "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
                "AWS_DEFAULT_REGION": args.region,
            }
            if os.getenv("AWS_SESSION_TOKEN"):
                aws_credentials["AWS_SESSION_TOKEN"] = os.getenv("AWS_SESSION_TOKEN")
            aws_auth_method = "user"
            print("🔐 Using IAM User authentication")
        else:
            # No credentials found in environment - this should not happen in production
            print("❌ No AWS credentials found in environment variables")
            print("   Required: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            print("   Optional: AWS_ROLE_ARN, AWS_EXTERNAL_ID")
            sys.exit(1)
        
        # Run the scans using the new service
        print("📊 Running EC2 scans...")
        ec2_df, scanned_at = scan_service.run_full_scan(
            region=args.region, 
            aws_credentials=aws_credentials, 
            aws_auth_method=aws_auth_method,
            save_to_db=True
        )
        
        # Generate summary
        summary = scan_service.get_scan_summary(ec2_df)
        
        print(f"✅ Scan completed successfully at {scanned_at}")
        print(f"   - EC2 findings: {summary['ec2_instances']}")
        print(f"   - Estimated monthly waste: ${summary['estimated_monthly_waste']:.2f}")
        
    except Exception as e:
        print(f"❌ Scan failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
