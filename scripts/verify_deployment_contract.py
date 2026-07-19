#!/usr/bin/env python3
"""Fail CI when release configuration drifts from the service runtime contract.

This deliberately uses only the standard library so Terraform CI can run it
without an extra toolchain. It checks the source-controlled boundary where a
wrong name, port, or mutable image reference otherwise reaches production.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TERRAFORM_ROOT = ROOT / "deployment" / "terraform-azure"
CONTAINER_APPS = TERRAFORM_ROOT / "modules" / "container_apps" / "main.tf"

SERVICES = {
    "backend": ("backend/Dockerfile", "backend"),
    "ai_review": ("ai_review_service/Dockerfile", "ai_review"),
    "receipt_intelligence": ("receipt_intelligence_service/Dockerfile", "receipt_intelligence"),
    "policy_assistant": ("policy_assistant_service/Dockerfile", "policy_assistant"),
}


def fail(message: str) -> None:
    raise AssertionError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> int:
    contract = json.loads((TERRAFORM_ROOT / "service-contract.json").read_text())
    terraform = CONTAINER_APPS.read_text()
    root_variables = (TERRAFORM_ROOT / "variables.tf").read_text()
    versions = (TERRAFORM_ROOT / "versions.tf").read_text()
    deploy_workflow = (ROOT / ".github" / "workflows" / "deploy-azure.yml").read_text()

    for key, (dockerfile_name, terraform_name) in SERVICES.items():
        service = contract.get(key)
        require(isinstance(service, dict), f"service-contract.json is missing {key}")
        port = service.get("port")
        repository = service.get("repository")
        require(isinstance(port, int) and 1 <= port <= 65535, f"{key} must define a valid port")
        require(isinstance(repository, str) and repository, f"{key} must define a repository")

        dockerfile = (ROOT / dockerfile_name).read_text()
        require(f"EXPOSE {port}" in dockerfile, f"{dockerfile_name} must expose contract port {port}")
        require(f'"--port", "{port}"' in dockerfile, f"{dockerfile_name} must run on contract port {port}")
        require(
            "@sha256:" in dockerfile,
            f"{dockerfile_name} must pin each Python base by immutable digest",
        )
        require(
            f"var.service_contract.{terraform_name}.port" in terraform,
            f"Terraform must consume {key}'s contract port",
        )
        require(
            f"var.service_contract.{terraform_name}.repository" in terraform,
            f"Terraform must consume {key}'s contract repository",
        )

    for expected in (
        "AI_REVIEW_SERVICE_TOKEN",
        "AI_REVIEW_REFERENCE_HMAC_KEY",
        "RECEIPT_INTELLIGENCE_SERVICE_TOKEN",
        "POLICY_ASSISTANT_SERVICE_TOKEN",
        "POLICY_ASSISTANT_REFERENCE_HMAC_KEY",
        "AI_REVIEW_DATABASE_URL",
        "RECEIPT_INTELLIGENCE_DATABASE_URL",
        "POLICY_ASSISTANT_DATABASE_URL",
        "STORAGE_BACKEND",
        "AZURE_STORAGE_ACCOUNT_URL",
        "AZURE_STORAGE_CONTAINER",
        "EMAIL_DELIVERY_ENABLED",
        "AZURE_COMMUNICATION_CONNECTION_STRING",
        "AZURE_COMMUNICATION_SENDER",
    ):
        require(f'name        = "{expected}"' in terraform or f'name  = "{expected}"' in terraform, f"missing Terraform env {expected}")

    require('name        = "SERVICE_TOKEN"' not in terraform, "generic SERVICE_TOKEN must not be injected")
    require('name        = "REFERENCE_HMAC_KEY"' not in terraform, "generic REFERENCE_HMAC_KEY must not be injected")
    require(":latest" not in terraform, "Terraform must never deploy a mutable latest image")
    require(
        'resource "azurerm_container_app_job" "durable_worker"' in terraform,
        "Terraform must schedule the durable backend worker",
    )
    require('cron_expression          = "*/5 * * * *"' in terraform, "durable worker cadence must be explicit")
    worker_start = terraform.index('resource "azurerm_container_app_job" "durable_worker"')
    worker_end = terraform.index('# --- Container App: ai_review_service', worker_start)
    worker = terraform[worker_start:worker_end]
    for required in (
        "DATABASE_URL",
        "JWT_SECRET",
        "DEPLOYMENT_ENVIRONMENT",
        "STORAGE_BACKEND",
        "AZURE_STORAGE_ACCOUNT_URL",
        "AZURE_STORAGE_CONTAINER",
        "EMAIL_DELIVERY_ENABLED",
        "AZURE_COMMUNICATION_CONNECTION_STRING",
        "AZURE_COMMUNICATION_SENDER",
    ):
        require(required in worker, f"durable worker must receive {required}")
    for variable in (
        "backend_image_digest",
        "ai_review_image_digest",
        "receipt_intelligence_image_digest",
        "policy_assistant_image_digest",
    ):
        require(f'variable "{variable}"' in root_variables, f"missing immutable image variable {variable}")
    require('backend "azurerm" {}' in versions, "Terraform must declare an AzureRM remote-state backend")
    require(
        "schema-gate:" in deploy_workflow
        and "009_tenant_workflows_outbox" in deploy_workflow
        and "alembic current" in deploy_workflow
        and "alembic upgrade head" not in deploy_workflow,
        "normal deploy workflow must verify the approved Supabase schema without applying migrations",
    )
    require(not (ROOT / "receipt_intelligence_service" / "requirements.txt").exists(), "floating receipt requirements.txt must remain removed")

    for ignore in (
        ROOT / "backend" / ".dockerignore",
        ROOT / "ai_review_service" / ".dockerignore",
        ROOT / "receipt_intelligence_service" / ".dockerignore",
        ROOT / "policy_assistant_service" / ".dockerignore",
    ):
        text = ignore.read_text()
        require(".env*" in text, f"{ignore.relative_to(ROOT)} must exclude environment files")

    compose_images = re.findall(
        r"^\s*image:\s*([^\s#]+)",
        (ROOT / "backend" / "docker-compose.yml").read_text(),
        flags=re.MULTILINE,
    )
    require(compose_images, "local Compose must declare its dependency images")
    for image in compose_images:
        require("@sha256:" in image, f"local Compose image must be digest-pinned: {image}")
        require(":latest@" not in image, f"local Compose image must not use a latest tag: {image}")

    for workflow in (ROOT / ".github" / "workflows").glob("*.yml"):
        for line in workflow.read_text().splitlines():
            if line.lstrip().startswith("#") or "uses:" not in line:
                continue
            match = re.search(r"uses:\s+[^@\s]+@([0-9a-f]{40})(?:\s|$)", line)
            require(match is not None, f"{workflow.relative_to(ROOT)} has an unpinned action: {line.strip()}")

    print("deployment contract: valid")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"deployment contract: {exc}", file=sys.stderr)
        raise SystemExit(1)
