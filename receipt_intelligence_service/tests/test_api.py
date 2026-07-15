from __future__ import annotations

from copy import deepcopy

from .conftest import authorization_headers


def test_private_analyze_endpoint_rejects_missing_or_bad_service_token(
    client, service_token: str, valid_payload: dict[str, object]
):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200

    denied = client.post("/v1/analyze", json=valid_payload)
    assert denied.status_code == 401
    assert denied.headers["www-authenticate"] == "Bearer"

    bad_token = client.post(
        "/v1/analyze",
        json=valid_payload,
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert bad_token.status_code == 401

    accepted = client.post(
        "/v1/analyze",
        json=valid_payload,
        headers={**authorization_headers(service_token), "X-Request-ID": "receipt-event-123"},
    )
    assert accepted.status_code == 200
    assert accepted.headers["x-request-id"] == "receipt-event-123"
    assert accepted.json()["correlation_id"] == "receipt-event-123"


def test_digest_deduplication_is_scoped_to_organization(
    client, service_token: str, valid_payload: dict[str, object]
):
    headers = authorization_headers(service_token)

    first = client.post("/v1/analyze", json=valid_payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["deduplication"] == {
        "duplicate_within_organization": False,
        "prior_seen_count": 0,
        "total_seen_count": 1,
    }

    duplicate = client.post("/v1/analyze", json=valid_payload, headers=headers)
    assert duplicate.status_code == 200
    assert duplicate.json()["deduplication"] == {
        "duplicate_within_organization": True,
        "prior_seen_count": 1,
        "total_seen_count": 2,
    }
    assert "duplicate_receipt_digest" in {
        finding["code"] for finding in duplicate.json()["findings"]
    }

    other_organization = deepcopy(valid_payload)
    other_organization["organization_scope"] = "org:opaque-999"
    isolated = client.post("/v1/analyze", json=other_organization, headers=headers)
    assert isolated.status_code == 200
    assert isolated.json()["deduplication"]["duplicate_within_organization"] is False
