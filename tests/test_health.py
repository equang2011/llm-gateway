from fastapi.testclient import TestClient

import app.app as app_module

client = TestClient(app_module.app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
