from fastapi.testclient import TestClient

import app.app as app_module

client = TestClient(app_module.app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_invoke_returns_gateway_response(monkeypatch):
    def fake_invoke_openrouter(request):
        return {
            "choices": [
                {
                    "message": {"content": "Mock provider response"},
                    "finish_reason": "stop",
                }
            ]
        }

    monkeypatch.setattr(
        app_module,
        "invoke_openrouter",
        fake_invoke_openrouter,
    )

    response = client.post(
        "/invoke",
        json={
            "model": "mock-1",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "model": "mock-1",
        "content": "Mock provider response",
        "finish_reason": "stop",
    }
