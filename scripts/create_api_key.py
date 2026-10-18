"""
take app name + rate limit
→ generate raw key
→ hash raw key
→ create GatewayApiKey ORM object
→ open DB session
→ add + commit
→ print raw key once

"""

import argparse

from app.database import SessionLocal
from app.db.models import GatewayApiKey
from app.model_catalog import SUPPORTED_MODELS
from app.security.api_keys import generate_api_key, hash_api_key


def parse_args():
    parser = argparse.ArgumentParser(description="Create a gateway API key.")

    parser.add_argument(
        "--app-name",
        required=True,
        help="Application that will own this API key.",
    )

    parser.add_argument(
        "--allowed-models",
        nargs="+",
        default=None,
        help="Gateway model aliases permitted for this key.",
    )

    parser.add_argument(
        "--requests-per-minute",
        type=int,
        default=30,
    )

    return parser.parse_args()


def validate_allowed_models(allowed_models: list[str] | None) -> None:
    if allowed_models is None:
        return
    unknown = set(allowed_models) - set(SUPPORTED_MODELS)

    if unknown:
        raise ValueError(f"Unsupported model aliases: {sorted(unknown)}")


def main():
    args = parse_args()

    validate_allowed_models(args.allowed_models)
    if args.requests_per_minute <= 0:
        raise ValueError("requests_per_minute must be positive")

    db = SessionLocal()

    try:
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)

        record = GatewayApiKey(
            app_name=args.app_name,
            key_hash=key_hash,
            key_prefix=raw_key[:12],
            requests_per_minute=args.requests_per_minute,
            allowed_models=args.allowed_models,
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
