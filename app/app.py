from fastapi import FastAPI

from app.models import InvokeRequest, InvokeResponse

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(request: InvokeRequest) -> InvokeResponse:
    # provider_result = mock_provider.invoke(request)

    return InvokeResponse(
        model=request.model,
        content=f"Gateway received: {request.messages[-1].content}",
        finish_reason="stop",
    )
