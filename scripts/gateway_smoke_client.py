"""
define gateway URL
construct request payload
send POST request using httpx
check response status
read JSON response
print normalized fields

"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

gateway_api_key = os.getenv("GATEWAY_API_KEY")
if not gateway_api_key:
    raise RuntimeError("Missing LLM gateway API key")

headers = {
    "Authorization": f"Bearer {gateway_api_key}",
}

GATEWAY_URL = "http://127.0.0.1:8000/invoke"


def main():
    payload = {
        # Provider model ID. Becomes the gateway alias "deepseek-v4-flash"
        # once model_catalog.py is wired into the request path.
        "model": "deepseek/deepseek-v4-flash",
        "messages": [
            {
                "role": "user",
                "content": "Give me 2-3 sentences about an interesting fact.",
            }
        ],
    }

    try:
        response = httpx.post(GATEWAY_URL, json=payload, timeout=42.0, headers=headers)

    except httpx.RequestError as err:
        print(f"request failed: {err}")
        return

    if response.status_code != 200:
        print(f"gateway returned {response.status_code}: {response.text}")
        return
    data = response.json()

    print(f"model used: {data['model']}")
    print(f"content: {data['content']}")
    print(f"finish reason: {data['finish_reason']}")


if __name__ == "__main__":
    main()
