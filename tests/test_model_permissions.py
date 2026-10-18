from app.security.model_permissions import is_model_allowed


def test_unrestricted_key_allows_model():
    assert is_model_allowed("deepseek-v4-flash", None)


def test_empty_allowlist_denies_model():
    assert not is_model_allowed("deepseek-v4-flash", [])


def test_allowlist_permits_listed_model():
    assert is_model_allowed(
        "deepseek-v4-flash",
        ["deepseek-v4-flash"],
    )


def test_allowlist_denies_unlisted_model():
    assert not is_model_allowed(
        "qwen-3.7-flash",
        ["deepseek-v4-flash"],
    )
