from app.models import InvokeRequest, Message
from app.providers.openrouter import build_openrouter_payload


def test_build_openrouter_payload():
    request = InvokeRequest(
        model="mock-1",
        messages=[
            Message(role="system", content="Answer concisely."),
            Message(role="user", content="What is indemnification?"),
        ],
    )

    payload = build_openrouter_payload(request)

    assert payload == {
        "model": "mock-1",
        "messages": [
            {"role": "system", "content": "Answer concisely."},
            {"role": "user", "content": "What is indemnification?"},
        ],
    }
