"""
take app name + rate limit
→ generate raw key
→ hash raw key
→ create GatewayApiKey ORM object
→ open DB session
→ add + commit
→ print raw key once

"""
from app.database import SessionLocal
from app.db.models import GatewayApiKey
from app.security.api_keys import generate_api_key, hash_api_key


def main():
    db = SessionLocal()

    try:
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)


        record = GatewayApiKey(
            app_name="adaptive-learning-app",
            key_hash=key_hash,
            key_prefix=raw_key[:12],
            requests_per_minute=30,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        print("Created API key")
        print(f"id: {record.id}")
        print(f"app: {record.app_name}")
        print(f"key: {raw_key}")

    finally:
        db.close()

if __name__ == "__main__":
    main()