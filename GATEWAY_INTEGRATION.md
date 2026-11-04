# LLM Gateway — Integration Guide for Consuming Applications

This document is for an engineer or coding agent building a **separate
application** that calls this gateway over HTTP. It describes the contract as
it exists today. The gateway is under active development — capabilities will
be added over time — so treat this as a snapshot, not a permanent spec. If
this document and the running gateway's actual behavior ever disagree, the
running gateway wins; when in doubt, check `README.md` and `ROADMAP.md` in
this repo for the current state before assuming a capability exists.

_Last verified against the code: 2026-11-03 (commit `b267ac9`)._

## What this service is

A single HTTP gateway that fronts an LLM provider (currently OpenRouter). Your
application should never call OpenRouter directly and should never hold an
OpenRouter API key. You call this gateway; it holds the provider credential
server-side and returns a normalized response.

## Base URL

- Local development: `http://127.0.0.1:8000`
- Deployed (Railway): confirm the current URL with the project owner before
  hardcoding it — Railway URLs can change on redeploy.

## Authentication

Every request to `POST /invoke` requires:

```
Authorization: Bearer <GATEWAY_API_KEY>
```

Each consuming application gets **its own gateway API key** (prefix `gw_`),
issued by the gateway owner. Keys are not interchangeable between apps: each
key is tied to an app name, may be restricted to a subset of models, and can be
revoked individually. The raw key is shown only once at creation, so store it
as a secret on your server. It is **not** an OpenRouter key, and your
application should never need one.

Keep the key server-side. Do not embed it in browser code or a mobile app.

`GET /health` requires no authentication and returns `{"status": "ok"}` — use
it as a liveness check, not a capability check.

Missing, malformed, unknown, or revoked credentials all return `401` in the
error envelope described below, before any provider call is made.

## The only endpoint that matters: `POST /invoke`

### Request body

```json
{
  "model": "deepseek-v4.1-flash",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "Summarize this text: ..." }
  ]
}
```

- `model` — **required.** A **gateway model alias** (e.g. `deepseek-v4.1-flash`),
  not a raw provider ID. The gateway maps the alias to the provider model
  internally. Raw provider IDs such as `deepseek/deepseek-v4.1-flash` are
  rejected with `400 unsupported_model`. The set of aliases is defined in
  `app/model_catalog.py` and **will change over time** — ask the gateway owner
  which aliases your key may use rather than hardcoding the full list.
- `messages` — **required.** Ordered list of `{role, content}`. `role` is one
  of `"system"`, `"user"`, `"assistant"`.
- **No other fields are currently accepted.** There is no `temperature`,
  `max_tokens`, `response_format`, or streaming support yet. If your prompt
  needs deterministic output or structured JSON, do it via prompt instructions
  for now, not request parameters.

### Model access is per key

A key may be restricted to an allowlist of aliases. If the alias exists but
your key is not permitted to use it, you get `403 model_forbidden`. A key with
no allowlist can use every supported model. If you need a model your key can't
use, ask the gateway owner to update the key — don't work around it.

### Success response — `200`

```json
{
  "model": "deepseek-v4.1-flash",
  "content": "...",
  "finish_reason": "stop"
}
```

`model` echoes back the alias you sent. `content` is the model's text output.
`finish_reason` is passed through from the provider (e.g. `"stop"`,
`"length"`).

### Error responses

Failures raised by the gateway use one consistent envelope:

```json
{ "detail": { "error": { "code": "provider_timeout", "message": "..." } } }
```

| HTTP status | `code`              | Meaning                                                          |
| ----------- | ------------------- | ---------------------------------------------------------------- |
| 400         | `unsupported_model` | The `model` alias is not one this gateway supports               |
| 401         | `unauthorized`      | Missing, invalid, or revoked gateway credentials                 |
| 403         | `model_forbidden`   | Your key exists but is not allowed to use the requested model    |
| 502         | `provider_error`    | Provider returned an HTTP error, or an unusable body             |
| 504         | `provider_timeout`  | Provider did not respond in time                                 |

A malformed request body (missing field, bad `role`, wrong types) returns `422`
in FastAPI's **standard validation format**, which is *not* the envelope above
— `detail` is a list of validation errors. Handle `422` separately; it means a
bug in your client, not a gateway or provider problem.

Your integration should branch on the top-level HTTP status first, and use
`code` for logging/telemetry — don't parse `message` programmatically, it's
meant for humans and may change wording.

Retry guidance: `400`, `401`, `403`, and `422` are not retryable — fix the
request or the key. `502` and `504` may be transient; retry with backoff and a
low retry cap, because every attempt can spend real provider credits.

**Known gap — timeouts:** the gateway's call to the provider uses a 30-second
`httpx` timeout, but that is not a hard cap on total duration, and a single
call has been observed taking several minutes before completing. Enforce your
own total timeout client-side; do not assume the gateway will fail fast.

## Minimal example (Python)

```python
import os
import httpx

GATEWAY_URL = os.environ["GATEWAY_URL"]  # e.g. http://127.0.0.1:8000/invoke
GATEWAY_API_KEY = os.environ["GATEWAY_API_KEY"]  # your app's own gw_... key


def invoke(model: str, messages: list[dict]) -> dict:
    response = httpx.post(
        GATEWAY_URL,
        headers={"Authorization": f"Bearer {GATEWAY_API_KEY}"},
        json={"model": model, "messages": messages},
        # Hard client-side cap: connect/read/write/pool each bounded.
        timeout=httpx.Timeout(60.0),
    )
    response.raise_for_status()  # on failure, inspect response.json()["detail"]
    return response.json()
```

## What NOT to assume

- **No rate limiting is enforced yet.** Each key stores a
  `requests_per_minute` value (default 30), but the gateway does not check it.
  Until the limiter lands, you are responsible for not flooding the gateway —
  every call spends real money. A `429` response is planned but does not exist
  today; don't write logic that depends on it.
- No streaming responses.
- No usage/token-count fields in the response.
- No request ID returned for correlation yet. The gateway logs your app name
  and key ID per call, but you can't yet match a specific request to a log line.
- No guarantee that the model catalog is stable. Aliases can be added or
  removed.

## Where to look for the current, authoritative state

This gateway's own repo — not this document — is the source of truth once
capabilities change:

- `app/models.py` — the actual `InvokeRequest`/`InvokeResponse` schema.
- `app/model_catalog.py` — the supported model aliases.
- `README.md` — current API surface and setup.
- `ROADMAP.md` — what's planned next, and what's explicitly deferred.
