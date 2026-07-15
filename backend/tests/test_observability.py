"""Small reliability surface: liveness, readiness, and correlation IDs."""


def test_health_and_readiness_return_a_safe_request_id(client):
    request_id = "local-check-123"
    health = client.get("/api/health", headers={"X-Request-ID": request_id})

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert health.headers["x-request-id"] == request_id

    ready = client.get("/api/ready", headers={"X-Request-ID": request_id})
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}
    assert ready.headers["x-request-id"] == request_id
