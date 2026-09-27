from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import GatewayApiKey
from app.security.api_keys import hash_api_key


def require_gateway_key(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> GatewayApiKey:    
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail ={
                "error": {
                    "code": "unauthorized",
                    "message": "Missing gateway credentials."
                }
            },
        )
    prefix = "Bearer "

    if not authorization.startswith(prefix):
        raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": {
                            "code": "unauthorized",
                            "message": "Invalid gateway credentials.",
                        }
                    },
                )

    provided = authorization[len(prefix):]
    key_hash = hash_api_key(provided)

    statement = select(GatewayApiKey).where(
        GatewayApiKey.key_hash == key_hash
    )

    record = db.scalar(statement)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error":{
                "code": "unauthorized",
                "message": "Invalid gateway credentials.",
                }
            },
        )

    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "unauthorized",
                    "message": "Invalid gateway credentials.",
                }
            },
        )

    record.last_used_at = datetime.now(timezone.utc)
    db.commit()

    
    return record
