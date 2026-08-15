# llm-gateway

An authenticated HTTP gateway that fronts an LLM provider (OpenRouter) behind a
stable request/response contract, so client applications depend on this
service's schema rather than provider-specific payloads and error shapes.

Deployed on Railway and currently used by two in-development applications.

## Why

Applications that call an LLM provider directly end up coupled to that
provider's payload format, error semantics, and credentials. This service owns
that boundary instead:

- clients authenticate to the gateway; only the gateway holds provider credentials
- provider responses are normalized to a fixed response model
- provider failures are mapped to a consistent error envelope
- each invocation is logged with model, outcome, status, and latency

## API

### `GET /health`

Public. Returns `{"status": "ok"}`.

### `POST /invoke`

Requires `Authorization: Bearer <GATEWAY_API_KEY>`.

```json
{
  "model": "deepseek/deepseek-v4-flash",
  "messages": [
    { "role": "system", "content": "Reply in one word." },
    { "role": "user", "content": "Say hi" }
  ]
}
```

`role` is one of `system`, `user`, or `assistant`. Response:

```json
{
  "model": "deepseek/deepseek-v4-flash",
  "content": "Hi",
  "finish_reason": "stop"
}
```

### Error contract

Failures return a consistent envelope rather than leaking provider internals:

```json
{ "detail": { "error": { "code": "provider_timeout", "message": "..." } } }
```

| Status | Code                | Cause                                          |
| ------ | ------------------- | ---------------------------------------------- |
| 401    | `unauthorized`      | Missing or invalid gateway credentials          |
| 502    | `provider_error`    | Provider returned an error or an unusable body  |
| 504    | `provider_timeout`  | Provider did not respond within the timeout     |

Prompts, credentials, and raw provider bodies are never logged.

## Running locally

```bash
python -m venv .venv && .venv/Scripts/activate   # or: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                             # then fill in both keys
make run                                         # uvicorn app.app:app --reload
```

`GET /health` and the static frontend are then served at `http://127.0.0.1:8000`.

## Development

```bash
make check    # ruff format --check, ruff check, pytest
```

GitHub Actions runs the same checks on every push.

`scripts/gateway_smoke_client.py` exercises a deployed instance over HTTP.
`/sandbox.html` is a local browser tool for iterating on prompts against a
running gateway.

## Layout

```
app/
  app.py              FastAPI routes, error mapping, invocation logging
  dependencies.py     gateway API-key authentication
  models.py           InvokeRequest / InvokeResponse contract
  observability.py    per-invocation logging
  settings.py         environment configuration (pydantic-settings)
  providers/
    openrouter.py     payload construction, HTTP call, response normalization
  model_catalog.py    gateway model aliases (not yet wired into the request path)
```

## Current scope

Built: authentication, normalized request/response contract, provider error and
timeout mapping, per-invocation logging, test coverage of success and failure
paths, CI, hosted deployment.

Not yet built: gateway-owned model aliases (`model_catalog.py` exists but client
requests still carry provider model IDs), generation parameters such as
temperature and max_tokens, per-request correlation IDs, token usage accounting,
multi-client API keys, and a second provider. See `ROADMAP.md` for the current
sequencing and rationale.
