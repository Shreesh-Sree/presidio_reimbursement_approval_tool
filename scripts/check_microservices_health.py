"""Health checker for core backend and advisory microservices."""

from __future__ import annotations

import sys
import urllib.request
import urllib.error
import json

SERVICES = [
    {"name": "Core Backend API", "port": 8000, "url": "http://127.0.0.1:8000/api/auth/health"},
    {"name": "AI Review Microservice", "port": 8011, "url": "http://127.0.0.1:8011/health"},
    {"name": "Receipt Intelligence Microservice", "port": 8012, "url": "http://127.0.0.1:8012/health"},
    {"name": "Policy Assistant Microservice", "port": 8013, "url": "http://127.0.0.1:8013/health"},
]


def check_service_health(service: dict[str, str | int]) -> bool:
    name = service["name"]
    url = service["url"]
    print(f"Checking {name} at {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            if status_code in (200, 204):
                print(f"  🟢 {name}: LIVE (Status {status_code}) - {body[:100]}")
                return True
            else:
                print(f"  🔴 {name}: UNHEALTHY (Status {status_code})")
                return False
    except urllib.error.URLError as err:
        print(f"  🟡 {name}: Offline or not listening on port {service['port']} ({err.reason})")
        return False
    except Exception as err:
        print(f"  🔴 {name}: Error ({err})")
        return False


def main():
    print("==================================================")
    print("   PRESIDIO REIMBURSEMENT TOOL - SERVICE HEALTH   ")
    print("==================================================")
    results = [check_service_health(srv) for srv in SERVICES]
    live_count = sum(1 for r in results if r)
    print("\n--------------------------------------------------")
    print(f"Summary: {live_count}/{len(SERVICES)} microservices currently active.")
    print("--------------------------------------------------")
    return 0


if __name__ == "__main__":
    sys.exit(main())
