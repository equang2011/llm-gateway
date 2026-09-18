import hashlib
import secrets


API_KEY_PREFIX = "gw_"

def generate_api_key() -> str:
    random_part = secrets.token_urlsafe(32)
    return f"{API_KEY_PREFIX}{random_part}"

def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

