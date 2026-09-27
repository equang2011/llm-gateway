from fastapi.testclient import TestClient

import app.app as app_module
from app.app import app
from app.database import get_db
from app.db.models import GatewayApiKey
from app.security.api_keys import generate_api_key, get_key_prefix, hash_api_key

DATABASE_URL = "sqlite://"

client = TestClient(app_module.app)


def test_db_can_store_api_key(test_db):
    record = GatewayApiKey(
        app_name="test-app",
        key_hash="abc123",
        key_prefix="gw_test",
        requests_per_minute=30,
    )

    test_db.add(record)
    test_db.commit()

    assert record.id is not None


def test_unknown_api_key_returns_401(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.post(
            "/invoke",
            headers={
                "Authorization": "Bearer gw_not-a-real-key",
            },
            json={
                "model": "deepseek-v4-flash",
                "prompt": "hello",
            },
        )

        assert response.status_code == 401

    finally:
        app.dependency_overrides.clear()

def test_valid_active_api_key(test_db, monkeypatch):
    """
    generate raw key
→ hash raw key
→ insert GatewayApiKey(is_active=True)
→ commit

override get_db
→ FastAPI now sees that row

monkeypatch provider
→ successful auth doesn't hit OpenRouter

POST /invoke with raw key
→ expect 200"""
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
                "message": {
                    "content": "Fake response",
                },
                "finish_reason": "stop",
            }
        ]
    }

    monkeypatch.setattr( 
        app_module,
        "invoke_openrouter",
        fake_invoke_openrouter,
    )
    headers={
        "Authorization": f"Bearer {raw_key}",
    }

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
            headers=headers,
        )
        assert response.status_code==200
        assert response.json() == {
            "model": "mock-1",
            "content": "Fake response",
            "finish_reason": "stop",
        }
    finally:
        app_module.app.dependency_overrides.clear()


def test_inactive_api_key_returns_401(test_db):
    raw_key = generate_api_key()
    record = GatewayApiKey(
        app_name="test-app",
        key_hash=hash_api_key(raw_key),
        key_prefix=get_key_prefix(raw_key),
        is_active=False,
        requests_per_minute=30,
    )

    test_db.add(record)
    test_db.commit()

    def override_get_db():
        yield test_db

    app_module.app.dependency_overrides[get_db] = override_get_db
    headers={
            "Authorization": f"Bearer {raw_key}",
        }
    try:
        response=client.post(
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
            headers=headers,
        )

        assert response.status_code==401
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


def test_successful_auth_updates_last_used_at(test_db, monkeypatch):
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

    assert record.last_used_at is None

    def override_get_db():
        yield test_db

    app_module.app.dependency_overrides[get_db] = override_get_db

    def fake_invoke_openrouter(request):
        return {
        "choices": [
            {
                "message": {
                    "content": "Fake response",
                },
                "finish_reason": "stop",
            }
        ]
    }
    
    monkeypatch.setattr( 
        app_module,
        "invoke_openrouter",
        fake_invoke_openrouter,
    )

    headers={
        "Authorization": f"Bearer {raw_key}",
    }

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
            headers=headers,
        )

        assert response.status_code == 200

        test_db.refresh(record)

        assert record.last_used_at is not None
    finally:
        app_module.app.dependency_overrides.clear()

def test_inactive_key_does_not_change_last_used_at(test_db):
    raw_key = generate_api_key()

    record = GatewayApiKey(
        app_name="test-app",
        key_hash=hash_api_key(raw_key),
        key_prefix=get_key_prefix(raw_key),
        is_active=False,
        requests_per_minute=30,
        last_used_at=None,
    )

    test_db.add(record)
    test_db.commit()

    def override_get_db():
        yield test_db

    app_module.app.dependency_overrides[get_db] = override_get_db

    headers={
        "Authorization": f"Bearer {raw_key}",
    }

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
            headers=headers,
        )

        assert response.status_code ==401
        test_db.refresh(record)
        assert record.last_used_at is None
    finally:
        app_module.app.dependency_overrides.clear()
