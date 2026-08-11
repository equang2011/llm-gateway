import secrets

from fastapi import Header, HTTPException, status

from app.settings import Settings


def require_gateway_key(
    authorization: str | None = Header(default=None),
) -> None:
    settings = Settings()

    expected = settings.gateway_api_key.get_secret_value()

    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "unauthorized",
                    "message": "Missing gateway credentials.",
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

    provided = authorization[len(prefix) :]

    if not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "unauthorized",
                    "message": "Invalid gateway credentials.",
                }
            },
        )
