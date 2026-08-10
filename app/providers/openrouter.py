import logging

import httpx

from app.models import InvokeRequest, InvokeResponse
from app.settings import Settings

logger = logging.getLogger(__name__)


def build_openrouter_payload(request: InvokeRequest) -> dict:

    messages = []

    for message in request.messages:
        messages.append(
            {
                "role": message.role,
                "content": message.content,
            }
        )

    return {"model": request.model, "messages": messages}


def invoke_openrouter(request: InvokeRequest) -> dict:

    settings = Settings()
    payload = build_openrouter_payload(request)

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key.get_secret_value()}",
        "Content-Type": "application/json",
    }

    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30.0,
    )

    if response.status_code >= 400:
        logger.warning(
            "openrouter_request_failed status_code=%s",
            response.status_code,
        )

    response.raise_for_status()
    return response.json()


def normalize_openrouter_response(
    result: dict,
    requested_model: str,
) -> InvokeResponse:
    choice = result["choices"][0]

    return InvokeResponse(
        model=requested_model,
        content=choice["message"]["content"],
        finish_reason=choice["finish_reason"],
    )
