import httpx
from fastapi.testclient import TestClient

import app.app as app_module
from app.database import get_db
from app.db.models import GatewayApiKey
from app.models import InvokeRequest, Message
from app.providers.openrouter import (
    build_openrouter_payload,
    normalize_openrouter_response,
)
from app.security.api_keys import generate_api_key, get_key_prefix, hash_api_key

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


def test_invoke(test_db, monkeypatch):
    raw_key = generate_api_key()

    record = GatewayApiKey(
        app_name="test-app",
        key_hash=hash_api_key(raw_key),
        key_prefix=get_key_prefix(raw_key),
        is_active=True,
        requests_per_minute=30,
    )

    test_db.add(record)
    test_db.commit()

    def override_get_db():
        yield test_db

    app_module.app.dependency_overrides[get_db] = override_get_db

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

    try:
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
                "Authorization": f"Bearer {raw_key}",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "model": "mock-1",
            "content": "Fake response",
            "finish_reason": "stop",
        }
    finally:
        app_module.app.dependency_overrides.clear()


def test_invoke_returns_502_when_provider_errors(test_db, monkeypatch):
    raw_key = generate_api_key()
    
    record = GatewayApiKey(
        app_name="test-app",
        key_hash=hash_api_key(raw_key),
        key_prefix=get_key_prefix(raw_key),
        is_active=True,
        requests_per_minute=30,
    )

    test_db.add(record)
    test_db.commit()

    def override_get_db():
        yield test_db

    app_module.app.dependency_overrides[get_db] = override_get_db
    

    def fake_openrouter_provider(request):
        raise httpx.HTTPStatusError(
            "simulated provider error",
            request=httpx.Request("POST", "https://example.com"),
            response=httpx.Response(
                500, request=httpx.Request("POST", "https://example.com")
            ),
        )

    monkeypatch.setattr(app_module, "invoke_openrouter", fake_openrouter_provider)

    try:
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
                "Authorization": f"Bearer {raw_key}",
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
    finally:
        app_module.app.dependency_overrides.clear()

def test_invoke_returns_504_when_provider_times_out(test_db, monkeypatch):
    raw_key = generate_api_key()
    
    record = GatewayApiKey(
        app_name="test-app",
        key_hash=hash_api_key(raw_key),
        key_prefix=get_key_prefix(raw_key),
        is_active=True,
        requests_per_minute=30,
    )

    test_db.add(record)
    test_db.commit()

    def override_get_db():
        yield test_db

    app_module.app.dependency_overrides[get_db] = override_get_db


    def fake_openrouter_timeout(request):
        raise httpx.TimeoutException(
            "simulated provider timeout",
        )

    monkeypatch.setattr(app_module, "invoke_openrouter", fake_openrouter_timeout)

    try:
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
                "Authorization": f"Bearer {raw_key}",
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
    finally:
        app_module.app.dependency_overrides.clear()


def test_invoke_with_missing_authorization_header(test_db):
    def override_get_db():
        yield test_db

    app_module.app.dependency_overrides[get_db] = override_get_db

    try:
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

    finally:
        app_module.app.dependency_overrides.clear()


def test_invoke_with_wrong_bearer_token(test_db):
    def override_get_db():
        yield test_db

    app_module.app.dependency_overrides[get_db] = override_get_db

    try:
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

    finally:
        app_module.app.dependency_overrides.clear()