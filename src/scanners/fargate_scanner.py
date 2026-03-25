# src/scanners/fargate_scanner.py
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
def scan_fargate_tasks(region: str, aws_credentials: Dict[str, str] | None = None) -> List[Dict]:
    """
    Scan Fargate tasks in the specified region.
    
    Returns a list of dictionaries containing:
    - task_arn: ARN of the Fargate task
    - cluster_name: Name of the ECS cluster
    - service_name: Name of the ECS service (if part of a service)
    - task_definition_arn: ARN of the task definition
    - task_definition_family: Family name of the task definition
    - cpu: CPU units allocated (e.g., "1024" = 1 vCPU)
    - memory_mb: Memory allocated in MB
    - platform_version: Fargate platform version
    - status: Task status (RUNNING, STOPPED, etc.)
    - desired_status: Desired task status
    - last_status: Last known status
    - started_at: When the task was started (ISO format string)
    - region: AWS region
    """
    ecs_client = _aws_client("ecs", region, aws_credentials)
    
    findings: List[Dict] = []
    
    try:
        # List all clusters
        cluster_paginator = ecs_client.get_paginator("list_clusters")
        cluster_arns = []
        
        for page in cluster_paginator.paginate():
            cluster_arns.extend(page.get("clusterArns", []))
        
        if not cluster_arns:
            return findings
        
        # Get cluster details
        cluster_response = ecs_client.describe_clusters(clusters=cluster_arns)
        clusters = cluster_response.get("clusters", [])
        
        for cluster in clusters:
            cluster_name = cluster.get("clusterName", "")
            cluster_arn = cluster.get("clusterArn", "")
            
            # List tasks in the cluster (both RUNNING and STOPPED)
            task_paginator = ecs_client.get_paginator("list_tasks")
            
            # Get running tasks
            running_tasks = []
            for page in task_paginator.paginate(cluster=cluster_arn, desiredStatus="RUNNING"):
                running_tasks.extend(page.get("taskArns", []))
            
            # Get stopped tasks (last 100 for recent history)
            stopped_tasks = []
            for page in task_paginator.paginate(cluster=cluster_arn, desiredStatus="STOPPED"):
                stopped_tasks.extend(page.get("taskArns", []))
                # Limit to last 100 stopped tasks to avoid excessive scanning
                if len(stopped_tasks) >= 100:
                    break
            
            all_task_arns = running_tasks + stopped_tasks[:100]
            
            if not all_task_arns:
                continue
            
            # Describe tasks in batches (max 100 per call)
            for i in range(0, len(all_task_arns), 100):
                batch = all_task_arns[i:i + 100]
                task_response = ecs_client.describe_tasks(cluster=cluster_arn, tasks=batch)
                tasks = task_response.get("tasks", [])
                
                for task in tasks:
                    # Only process Fargate tasks
                    launch_type = task.get("launchType", "")
                    if launch_type != "FARGATE":
                        continue
                    
                    task_arn = task.get("taskArn", "")
                    task_definition_arn = task.get("taskDefinitionArn", "")
                    desired_status = task.get("desiredStatus", "")
                    last_status = task.get("lastStatus", "")
                    platform_version = task.get("platformVersion", "")
                    
                    # Extract service name from task group if present
                    task_group = task.get("group", "")
                    service_name = ""
                    if task_group and task_group.startswith("service:"):
                        service_name = task_group.replace("service:", "")
                    
                    # Get CPU and memory from task definition
                    cpu = task.get("cpu", "")
                    memory = task.get("memory", "")
                    
                    # Convert memory to MB if in format like "1024" (already in MB) or "1GB"
                    memory_mb = 0
                    if memory:
                        if isinstance(memory, str):
                            if memory.endswith("GB"):
                                memory_mb = int(float(memory.replace("GB", "")) * 1024)
                            elif memory.endswith("MB"):
                                memory_mb = int(float(memory.replace("MB", "")))
                            else:
                                # Assume it's already in MB as integer string
                                try:
                                    memory_mb = int(memory)
                                except ValueError:
                                    memory_mb = 0
                        else:
                            memory_mb = int(memory)
                    
                    # Parse task definition ARN to get family name
                    task_definition_family = ""
                    if task_definition_arn:
                        # ARN format: arn:aws:ecs:region:account:task-definition/family:revision
                        parts = task_definition_arn.split("/")
                        if len(parts) >= 2:
                            family_revision = parts[1]
                            task_definition_family = family_revision.split(":")[0]
                    
                    # Get started at time
                    started_at = ""
                    started_at_timestamp = task.get("startedAt")
                    if started_at_timestamp:
                        try:
                            # Parse AWS timestamp and convert to ISO format
                            if isinstance(started_at_timestamp, datetime):
                                started_at = started_at_timestamp.isoformat()
                            else:
                                # If it's a string, try to parse it
                                started_at_dt = datetime.fromisoformat(
                                    str(started_at_timestamp).replace("Z", "+00:00")
                                )
                                started_at = started_at_dt.isoformat()
                        except (ValueError, AttributeError):
                            started_at = str(started_at_timestamp)
                    
                    # Get container information
                    containers = task.get("containers", [])
                    container_names = [c.get("name", "") for c in containers]
                    
                    finding = {
                        "task_arn": task_arn,
                        "cluster_name": cluster_name,
                        "service_name": service_name if service_name else "Standalone Task",
                        "task_definition_arn": task_definition_arn,
                        "task_definition_family": task_definition_family,
                        "cpu": cpu if isinstance(cpu, str) else str(cpu) if cpu else "",
                        "memory_mb": memory_mb,
                        "platform_version": platform_version,
                        "status": last_status,
                        "desired_status": desired_status,
                        "container_names": ", ".join(container_names) if container_names else "",
                        "started_at": started_at,
                        "region": region,
                    }
                    
                    findings.append(finding)
            
            # Also check for Fargate services (even if no tasks are running)
            try:
                service_paginator = ecs_client.get_paginator("list_services")
                service_arns = []
                
                for page in service_paginator.paginate(cluster=cluster_arn):
                    service_arns.extend(page.get("serviceArns", []))
                
                if service_arns:
                    # Describe services to check launch type
                    for i in range(0, len(service_arns), 10):
                        batch = service_arns[i:i + 10]
                        service_response = ecs_client.describe_services(
                            cluster=cluster_arn, services=batch
                        )
                        services = service_response.get("services", [])
                        
                        for service in services:
                            launch_type = service.get("launchType", "")
                            if launch_type != "FARGATE":
                                continue
                            
                            service_name = service.get("serviceName", "")
                            task_definition_arn = service.get("taskDefinition", "")
                            desired_count = service.get("desiredCount", 0)
                            running_count = service.get("runningCount", 0)
                            
                            # If service has no running tasks but is configured for Fargate,
                            # still include it in findings
                            if running_count == 0 and desired_count > 0:
                                # Get task definition to extract CPU/memory
                                try:
                                    td_response = ecs_client.describe_task_definition(
                                        taskDefinition=task_definition_arn
                                    )
                                    td = td_response.get("taskDefinition", {})
                                    cpu = td.get("cpu", "")
                                    memory = td.get("memory", "")
                                    
                                    # Parse memory
                                    memory_mb = 0
                                    if memory:
                                        if isinstance(memory, str):
                                            if memory.endswith("GB"):
                                                memory_mb = int(float(memory.replace("GB", "")) * 1024)
                                            elif memory.endswith("MB"):
                                                memory_mb = int(float(memory.replace("MB", "")))
                                            else:
                                                try:
                                                    memory_mb = int(memory)
                                                except ValueError:
                                                    memory_mb = 0
                                        else:
                                            memory_mb = int(memory)
                                    
                                    # Parse task definition family
                                    task_definition_family = ""
                                    if task_definition_arn:
                                        parts = task_definition_arn.split("/")
                                        if len(parts) >= 2:
                                            family_revision = parts[1]
                                            task_definition_family = family_revision.split(":")[0]
                                    
                                    finding = {
                                        "task_arn": f"service:{service_name}",
                                        "cluster_name": cluster_name,
                                        "service_name": service_name,
                                        "task_definition_arn": task_definition_arn,
                                        "task_definition_family": task_definition_family,
                                        "cpu": cpu if isinstance(cpu, str) else str(cpu) if cpu else "",
                                        "memory_mb": memory_mb,
                                        "platform_version": "LATEST",
                                        "status": "STOPPED",
                                        "desired_status": "RUNNING",
                                        "container_names": "",
                                        "started_at": "",
                                        "region": region,
                                    }
                                    findings.append(finding)
                                except ClientError:
                                    # Skip if we can't describe task definition
                                    pass
            except ClientError as e:
                # If we can't list services, continue with tasks only
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code != "AccessDenied":
                    print(f"Warning: Could not list services in cluster {cluster_name}: {e}")
    
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        print(f"ERROR: Failed to scan Fargate tasks in {region}: {error_code} - {error_message}")
        # Let the caller distinguish permission vs other AWS errors
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error scanning Fargate tasks in {region}: {str(e)}")
        raise
    
    return findings


# ----------------------
# Public entry points
# ----------------------
def scan_fargate(region: str | None = None, aws_credentials: Dict[str, str] | None = None) -> List[Dict]:
    """
    Primary entry point for Fargate scanning.
    
    Args:
        region: AWS region to scan (defaults to DEFAULT_REGION)
        aws_credentials: Optional credentials dictionary
        
    Returns:
        List of Fargate task findings
    """
    region = region or DEFAULT_REGION
    return scan_fargate_tasks(region, aws_credentials)


def run(region: str | None = None, aws_credentials: Dict[str, str] | None = None) -> List[Dict]:
    """
    Backward-compatible CLI entry point.
    
    Args:
        region: AWS region to scan
        aws_credentials: Optional credentials dictionary
        
    Returns:
        List of Fargate task findings
    """
    region = region or DEFAULT_REGION
    findings = scan_fargate_tasks(region, aws_credentials)
    
    # Brief console output
    for finding in findings:
        print(
            f"[Fargate] {finding.get('service_name') or finding.get('task_definition_family')} "
            f"cluster={finding.get('cluster_name')} "
            f"cpu={finding.get('cpu')} "
            f"memory={finding.get('memory_mb')}MB "
            f"status={finding.get('status')}"
        )
    
    return findings


if __name__ == "__main__":
    # Allow standalone testing: python -m scanners.fargate_scanner --region us-east-1
    import argparse
    
    parser = argparse.ArgumentParser(description="Cloud Waste Tracker – Fargate Tasks Scanner")
    parser.add_argument("--region", default=DEFAULT_REGION)
    args = parser.parse_args()
    
    run(region=args.region)
