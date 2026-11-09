import pytest
from fastapi.testclient import TestClient

import app.app as app_module
from app.database import get_db
from app.db.models import GatewayApiKey
from app.model_catalog import SUPPORTED_MODELS
from app.providers.openrouter import normalize_openrouter_response
from app.security.api_keys import generate_api_key, get_key_prefix, hash_api_key

client = TestClient(app_module.app)


@pytest.fixture
def auth_headers(test_db):
    def override_get_db():
        yield test_db

    def make_headers(allowed_models):
        raw_key = generate_api_key()
        test_db.add(
            GatewayApiKey(
                app_name="test-app",
                key_hash=hash_api_key(raw_key),
                key_prefix=get_key_prefix(raw_key),
                is_active=True,
                requests_per_minute=30,
                allowed_models=allowed_models,
            )
        )
        test_db.commit()
        return {"Authorization": f"Bearer {raw_key}"}

    app_module.app.dependency_overrides[get_db] = override_get_db
    try:
        yield make_headers
    finally:
        app_module.app.dependency_overrides.clear()


def test_models_requires_auth(auth_headers):
    response = client.get("/models")

    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "unauthorized"


def test_models_unrestricted_key_sees_whole_catalog(auth_headers):
    response = client.get("/models", headers=auth_headers(None))

    assert response.status_code == 200
    assert {m["alias"]: m["provider_model"] for m in response.json()["models"]} == (
        SUPPORTED_MODELS
    )


def test_models_filters_to_allowlist(auth_headers):
    response = client.get("/models", headers=auth_headers(["qwen-3.7-flash"]))

    assert response.json() == {
        "models": [
            {"alias": "qwen-3.7-flash", "provider_model": "qwen/qwen3.7-flash"},
        ]
    }


def test_models_omits_stale_allowlist_entries(auth_headers):
    headers = auth_headers(["qwen-3.7-flash", "removed-from-catalog"])

    response = client.get("/models", headers=headers)

    assert [m["alias"] for m in response.json()["models"]] == ["qwen-3.7-flash"]


def test_provider_model_prefers_what_the_provider_reported():
    result = {
        "model": "qwen/qwen3.7-flash-20261101",
        "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
    }

    response = normalize_openrouter_response(result, requested_model="qwen-3.7-flash")

    assert response.model == "qwen-3.7-flash"
    assert response.provider_model == "qwen/qwen3.7-flash-20261101"
