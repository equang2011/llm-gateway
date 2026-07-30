from fastapi.testclient import TestClient

from app.app import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_invoke_returns_gateway_response():
    payload = {
        "model": "mock-1",
        "messages": [
            {
                "role": "user",
                "content": "Explain indemnification",
            }
        ],
    }

    response = client.post("/invoke", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "model": "mock-1",
        "content": "Gateway received: Explain indemnification",
        "finish_reason": "stop",
    }
