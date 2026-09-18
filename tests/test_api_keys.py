from app.security.api_keys import generate_api_key, hash_api_key



def test_api_key_hashing():
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    assert raw_key.startswith("gw_")
    assert raw_key != key_hash
    assert hash_api_key(raw_key) == key_hash

    