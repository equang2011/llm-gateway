import httpx
from fastapi import FastAPI, HTTPException

from app.models import InvokeRequest, InvokeResponse
from app.providers.openrouter import invoke_openrouter, normalize_openrouter_response

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(request: InvokeRequest) -> InvokeResponse:

    try:
        provider_result = invoke_openrouter(request)

    except httpx.TimeoutException as err:
        raise HTTPException(
            status_code=504,
            detail={
                "error": {
                    "code": "provider_timeout",
                    "message": "The upstream model provider timed out.",
                }
            },
        ) from err
    except httpx.HTTPStatusError as err:
        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "code": "provider_error",
                    "message": "The upstream model provider returned an error.",
                }
            },
        ) from err

    return normalize_openrouter_response(
        provider_result,
        requested_model=request.model,
    )
