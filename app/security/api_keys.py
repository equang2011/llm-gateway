import hashlib
import secrets

API_KEY_PREFIX = "gw_"
KEY_DISPLAY_PREFIX_LENGTH = 12


def generate_api_key() -> str:
    random_part = secrets.token_urlsafe(32)
    return f"{API_KEY_PREFIX}{random_part}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_key_prefix(raw_key: str) -> str:
    return raw_key[:KEY_DISPLAY_PREFIX_LENGTH]
