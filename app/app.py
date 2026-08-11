import logging
import time

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.dependencies import require_gateway_key
from app.models import InvokeRequest, InvokeResponse
from app.observability import log_invocation
from app.providers.openrouter import invoke_openrouter, normalize_openrouter_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(
    request: InvokeRequest,
    _: None = Depends(require_gateway_key),
) -> InvokeResponse:

    start = time.perf_counter()
    outcome = "unexpected_error"
    gateway_status = 500

    try:
        provider_result = invoke_openrouter(request)

        outcome = "success"
        gateway_status = 200

    except httpx.TimeoutException as err:
        outcome = "timeout"
        gateway_status = 504
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
        outcome = "status_error"
        gateway_status = 502
        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "code": "provider_error",
                    "message": "The upstream model provider returned an error.",
                }
            },
        ) from err

    finally:
        elapsed_time = (time.perf_counter() - start) * 1000

        log_invocation(
            model=request.model,
            outcome=outcome,
            gateway_status=gateway_status,
            elapsed_ms=elapsed_time,
        )

    return normalize_openrouter_response(
        provider_result,
        requested_model=request.model,
    )


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
