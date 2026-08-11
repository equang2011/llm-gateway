import httpx
from fastapi.testclient import TestClient

import app.app as app_module
from app.models import InvokeRequest, Message
from app.providers.openrouter import (
    build_openrouter_payload,
    normalize_openrouter_response,
)

client = TestClient(app_module.app)


def test_build_openrouter_payload():
    request = InvokeRequest(
        model="mock-1",
        messages=[
            Message(role="system", content="Answer concisely."),
            Message(role="user", content="What is indemnification?"),
        ],
    )

    payload = build_openrouter_payload(request)

    assert payload == {
        "model": "mock-1",
        "messages": [
            {"role": "system", "content": "Answer concisely."},
            {"role": "user", "content": "What is indemnification?"},
        ],
    }


def test_normalize_openrouter_response():
    provider_result = {
        "choices": [
            {
                "message": {
                    "content": "Honey never spoils.",
                },
                "finish_reason": "stop",
            }
        ]
    }

    response = normalize_openrouter_response(
        provider_result,
        requested_model="qwen/qwen3.7-flash",
    )

    assert response.model == "qwen/qwen3.7-flash"
    assert response.content == "Honey never spoils."
    assert response.finish_reason == "stop"


def test_invoke(monkeypatch):
    def fake_invoke_openrouter(request):
        return {
            "choices": [
                {
                    "message": {"content": "Fake response"},
                    "finish_reason": "stop",
                }
            ]
        }

    monkeypatch.setattr(app_module, "invoke_openrouter", fake_invoke_openrouter)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key")
    monkeypatch.setenv("GATEWAY_API_KEY", "test-gateway-key")

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
        headers={
            "Authorization": "Bearer test-gateway-key",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "model": "mock-1",
        "content": "Fake response",
        "finish_reason": "stop",
    }


def test_invoke_returns_502_when_provider_errors(monkeypatch):
    def fake_openrouter_provider(request):
        raise httpx.HTTPStatusError(
            "simulated provider error",
            request=httpx.Request("POST", "https://example.com"),
            response=httpx.Response(
                500, request=httpx.Request("POST", "https://example.com")
            ),
        )

    monkeypatch.setattr(app_module, "invoke_openrouter", fake_openrouter_provider)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key")
    monkeypatch.setenv("GATEWAY_API_KEY", "test-gateway-key")

    response = client.post(
        "/invoke",
        json={
            "model": "fake-provider",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                }
            ],
        },
        headers={
            "Authorization": "Bearer test-gateway-key",
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": {
            "error": {
                "code": "provider_error",
                "message": "The upstream model provider returned an error.",
            }
        }
    }


def test_invoke_returns_504_when_provider_times_out(monkeypatch):
    def fake_openrouter_timeout(request):
        raise httpx.TimeoutException(
            "simulated provider timeout",
        )

    monkeypatch.setattr(app_module, "invoke_openrouter", fake_openrouter_timeout)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key")
    monkeypatch.setenv("GATEWAY_API_KEY", "test-gateway-key")

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
        headers={
            "Authorization": "Bearer test-gateway-key",
        },
    )

    assert response.status_code == 504
    assert response.json() == {
        "detail": {
            "error": {
                "code": "provider_timeout",
                "message": "The upstream model provider timed out.",
            }
        }
    }


def test_invoke_with_missing_authorization_header(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key")
    monkeypatch.setenv("GATEWAY_API_KEY", "test-gateway-key")

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

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "error": {
                "code": "unauthorized",
                "message": "Missing gateway credentials.",
            }
        }
    }


def test_invoke_with_wrong_bearer_token(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key")
    monkeypatch.setenv("GATEWAY_API_KEY", "test-gateway-key")

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
        headers={
            "Authorization": "Bearer wrong-gateway-key",
        },
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "error": {
                "code": "unauthorized",
                "message": "Invalid gateway credentials.",
            }
        }
    }
