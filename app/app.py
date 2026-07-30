from fastapi import FastAPI

from app.models import InvokeRequest, InvokeResponse
from app.providers.openrouter import invoke_openrouter, normalize_openrouter_response

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(request: InvokeRequest) -> InvokeResponse:
    provider_result = invoke_openrouter(request)

    return normalize_openrouter_response(
        provider_result,
        requested_model=request.model,
    )
