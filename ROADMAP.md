LLM Gateway Roadmap — deployment-first credible prototype

Rewritten 2026-08-09 from the existing prototype → credible prototype roadmap.

Guiding objective

The next milestone is not “finish the gateway.” It is:

Get a small, safe, understandable version of the gateway running remotely,then improve it while using it as real infrastructure.

The roadmap therefore prioritizes:

deployment blockers,

minimum protection for provider credits,

first hosted deployment,

gateway-owned model abstraction,

request correlation and usage visibility,

one genuine downstream consumer.

Internal refactoring should follow concrete pressure from those milestones ratherthan lead them.

1. Current state

Implemented and working:

POST /invoke with gateway-owned InvokeRequest / InvokeResponse

GET /health

OpenRouter provider module

provider payload construction

authenticated outbound HTTP request using httpx

OpenRouter response normalization

timeout → 504 provider_timeout

provider HTTP error → 502 provider_error

exception chaining using raise ... from err

latency + outcome logging via app/observability.py

static frontend served by FastAPI

external smoke client under scripts/

tests covering health, success, provider payload construction,response normalization, 502, and 504 paths

pydantic-settings configuration with local .env

Ruff + pytest + Makefile checks

Current value proposition:

A single-provider LLM proxy with a stable request/response contract,normalized provider errors, and basic observability.

Current limitations:

The gateway does not yet fully own the model namespace.app/model_catalog.py exists, but clients still know provider-specificmodel identifiers or un-resolved aliases.

There is no downstream-client authentication.Anyone who can reach /invoke can potentially spend provider credits.

There is no client-visible request identity.Logs cannot yet be correlated with a request ID returned to a caller.

No genuine downstream application has yet proven the gateway as independentinfrastructure.

Repository housekeeping remains:

stale make run target

untracked frontend/scripts if still uncommitted

raw provider error-body printing if still present

duplicate test if still duplicated

no minimal CI workflow

Architectural constraint:

Sync httpx inside a sync FastAPI route is acceptable at this scale.

Async conversion is not a deployment blocker and should not jump the queue.

2. What “deployment-ready prototype” means

For the first hosted milestone, the gateway does NOT need to be productiongrade.

It should demonstrate:

the service starts reliably on a remote host

/health is reachable remotely

/invoke is protected from anonymous use

provider credentials exist only in server-side environment configuration

a real authenticated remote /invoke call succeeds

provider failures remain normalized

logs are visible in the host console

local checks remain green

This first deployment does NOT require:

Kubernetes

Redis

a database

distributed tracing

autoscaling

high availability

persistent log infrastructure

advanced rate limiting

OpenAI compatibility

multiple providers

streaming

tool calling

user signup

OAuth

a public browser-safe authentication scheme

The first hosted gateway may be used primarily by trusted server-side clients.

Phase A — Get safely hosted

Slice A0 — Deployment-critical housekeeping

Goal: remove obvious problems that could break or embarrass the firstdeployment.

Estimated size: ~30–60 minutes.

Work

Fix the Makefile run target to use the canonical app entry point:

uvicorn app.app:app --reload

Confirm frontend/ and scripts/ are committed if they are intended to ship.

Remove raw provider-response-body printing fromapp/providers/openrouter.py.Log only safe metadata such as provider status code.

Confirm/remove the duplicate test if it is still actually duplicated.

Run:

ruff format .

ruff check .

make check

Confirm secrets remain in environment configuration and are not committed.

Minimal CI

Add one GitHub Actions workflow if no equivalent workflow exists.

It should only run the existing checks on push / pull request:

Ruff format check

Ruff lint

pytest

Do not add matrices, caching optimization, deployment automation, or multiplejobs yet.

Definition of done

make run works locally

make check is green

no raw provider body is printed

intended files are committed

git status is clean

simple CI runs successfully

Concepts to focus on

application entry points

environment-vs-source configuration

CI as automated verification, not deployment

safe logging boundaries

Do not build

deployment automation

Docker optimization unless the chosen host actually requires it

broader test refactoring

async conversion

Slice A1 — Minimal gateway authentication

Goal: prevent a hosted /invoke endpoint from becoming an open proxy tothe OpenRouter account.

Estimated size: ~60–90 minutes.

First version

Use one server-side gateway API key if there is only one trusted consumer.

Conceptually:

GATEWAY_API_KEY=<secret>

The client sends the credential to /invoke.

Keep /health public.

If multiple consumers appear later, evolve this into:

key A → lesson app

key B → precedent app

key C → other trusted client

Do not build multi-client identity before it is useful.

Boundary to understand

There are two separate authentication relationships:

downstream client → gateway

gateway → OpenRouter

The downstream client should never receive or know OPENROUTER_API_KEY.

Likely files

app/settings.py

app/app.py or a small app/dependencies.py

scripts/gateway_smoke_client.py

tests

Definition of done

/health works without authentication

/invoke rejects missing/invalid gateway credentials

valid gateway credential succeeds

gateway credential comes from environment configuration

OpenRouter credential remains server-only

smoke client can authenticate

tests cover missing, invalid, and valid credentials

authentication failures use the existing normalized gateway error convention

Important browser caveat

Do NOT put GATEWAY_API_KEY into public browser JavaScript.

Anything shipped to the browser should be considered visible to users.

Therefore:

hosted API for trusted backend/downstream clients: okay

public browser demo with embedded secret: not okay

Treat “hosted gateway API” and “public browser demo” as separate milestones.

Concepts to focus on

authentication boundaries

401 behavior

server-side secrets

FastAPI dependencies

why browser JavaScript cannot safely hold a shared secret

Do not build

OAuth

user accounts

DB-backed keys

key rotation UI

rate limits

API-key management UI



NEXT: A1 AUTH TESTS

Manual behavior is already verified:
- no Authorization header -> 401
- wrong Bearer token -> 401
- correct Bearer token -> 200 and real OpenRouter response

Next task:
Add automated tests so CI verifies the same contract.

Tests to write:
1. test_invoke_rejects_missing_gateway_key
   - POST /invoke without Authorization header
   - assert 401
   - assert error code == "unauthorized"

2. test_invoke_rejects_invalid_gateway_key
   - POST /invoke with:
     Authorization: Bearer definitely-wrong
   - assert 401
   - assert error code == "unauthorized"

3. Update/verify the existing successful /invoke test
   - it now needs a valid Authorization header
   - provider should remain monkeypatched so the test does NOT call OpenRouter
   - assert 200 and normal normalized response

Important question to resolve:
The auth dependency currently constructs Settings(), which reads the gateway
key from environment/.env. Avoid making CI depend on my real local .env or
real secret.

Preferred approach:
First inspect the current tests and decide the smallest clean way to supply a
fake GATEWAY_API_KEY during tests. Do not introduce a large Settings/DI
refactor unless it materially simplifies testing.

After tests:
- pytest
- ruff format .
- ruff check .
- make check
- push and confirm GitHub CI is green

A1 is done when missing/wrong/valid credential behavior is protected by
automated tests and the smoke client can authenticate.


Slice A2 — First hosted deployment

Goal: get the actual backend service running remotely as soon as possible.

Estimated size: ~60–120 minutes, depending on host/setup friction.

Deployment contract

The remote environment must provide:

OPENROUTER_API_KEY

GATEWAY_API_KEY

any other currently required settings

The deployed process must start the canonical FastAPI app.

The exact hosting provider and start-command syntax should be verified whenthis slice begins rather than assumed in advance.

Definition of done

Remote URL:

GET /health → 200

unauthenticated POST /invoke → normalized 401

authenticated POST /invoke → real OpenRouter call → normalized success

known provider timeout/error behavior still maps correctly

logs are visible in the hosting platform console

provider secrets do not appear in source or client output

local make check remains green

Manual verification sequence

Deploy.

Hit /health.

Call /invoke without gateway credentials.

Confirm 401.

Call /invoke with a valid gateway credential.

Confirm a real model response.

Inspect host logs.

Confirm no prompt/provider body/secret leakage.

Record the hosted base URL for downstream clients.

What this slice teaches

remote process startup

environment-variable configuration

ports and server binding

build/start commands

host logs

health checks

differences between local and remote execution

the real meaning of “service boundary”

Do not build

custom domain

deployment pipeline

autoscaling

managed database

persistent logging

observability vendor integration

production SLOs

public-browser credential design

Clean stopping point

At the end of this slice, the key milestone is:

I have an authenticated LLM gateway running on the internet that can make areal provider call.

Stop and commit/document that milestone before adding more features.

Phase B — Make the hosted gateway more gateway-like

Slice B1 — Gateway model aliases + GET /models + unified errors

Goal: make clients depend on the gateway namespace instead of OpenRouter'snamespace.

Estimated size: ~2–2.5 hours.

Problem

The gateway currently does not fully enforce this promise:

Clients should know gateway model aliases, not provider-specific model IDs.

app/model_catalog.py already contains the seed of this feature.

Desired flow

Client sends:

model="deepseek-v4-flash"

Gateway resolves internally:

deepseek/deepseek-v4-flash

OpenRouter sees only the provider ID.

Required capability

GET /models should expose the aliases supported by the gateway.

The frontend and smoke client should use gateway aliases rather than rawprovider IDs.

Unknown aliases should be rejected before any provider call.

Error-contract hardening

Use one public gateway error convention for:

unknown model

authentication failure

provider timeout

provider HTTP error

Do not introduce separate response shapes per feature.

If the current FastAPI behavior wraps error data under detail, preserve oneconsistent convention and update tests accordingly.

Likely files

app/model_catalog.py

app/app.py

possibly a tiny model-resolution helper

app/providers/openrouter.py

frontend files

smoke client

tests

Definition of done

GET /models works locally and remotely

clients use gateway aliases

known alias resolves internally

unknown alias produces local 4xx error

unknown alias does not contact OpenRouter

public error envelope is consistent

tests cover alias resolution, /models, unknown model, and error shape

Concepts to focus on

public API contracts

canonical internal identifiers

validation beyond Pydantic type checking

anti-corruption boundaries

client/provider decoupling

Do not build

DB-backed model catalog

dynamic catalog updates

pricing metadata unless clearly needed

model routing

provider failover

Slice B2 — Request IDs + usage/accounting visibility

Goal: make hosted requests operationally traceable.

Estimated size: ~2–2.5 hours.

Operational question

For a gateway invocation, be able to answer:

Which request was this, which client called, which model was requested andresolved, how long did it take, did it succeed, and what supported usageinformation was returned?

Target metadata

When supported by the actual provider response:

request_id

client_id or current gateway caller identity

requested gateway alias

resolved provider model

outcome

gateway status

elapsed_ms

prompt/input tokens

completion/output tokens

total tokens

Never log:

prompt text

document text

API keys

auth headers

raw provider bodies

Request correlation

Return an X-Request-ID header on success and normalized failures wherepractical.

The caller can then report a request ID that can be found in the logs.

Provider usage caveat

Do not assume OpenRouter usage fields.

Before implementing token accounting:

inspect a real provider response

verify field names and presence

only log fields the current response actually supports

Definition of done

request ID exists per invocation

request ID is returned to client

invocation log includes request ID

logs include client identity when available

logs include requested alias and resolved provider ID

supported token usage is included only if verified

safe log still emitted on error

tests cover request ID on success and one failure

Concepts to focus on

correlation IDs

response headers

operational accounting vs debugging

provider-response metadata

safe observability

Do not build

OpenTelemetry

distributed traces

external metrics stack

log aggregation service

JSON logging framework

contextvars unless a concrete need appears

Phase C — Prove the gateway is useful infrastructure

Slice C1 — One real downstream consumer

Goal: prove that a separate application can use the hosted gateway withoutknowing anything about OpenRouter.

Estimated size: one focused vertical slice; likely 1.5–3+ hours dependingon the downstream library/application.

Preferred first slice

Keep it tiny:

one document or text input→ application-specific prompt / extraction rule→ gateway HTTP client→ hosted POST /invoke→ normalized response→ one useful printed or displayed result

The consumer can be:

ContextGem-backed

a small legal/document analysis app

another real project that naturally needs an LLM

The important condition is architectural independence, not library choice.

Consumer owns

domain logic

prompt construction

document parsing

application persistence

UI/output formatting

Gateway owns

downstream-client authentication

model alias resolution

provider communication

OpenRouter authentication

response normalization

normalized gateway errors

request/usage logging

Consumer must contain zero

OPENROUTER_API_KEY

OpenRouter URL

OpenRouter headers

OpenRouter raw response parsing

Definition of done

separate application calls the hosted gateway over HTTP

it authenticates with the gateway

it uses a gateway model alias

it produces one actually useful result

no OpenRouter-specific code exists in the consumer

any awkwardness in the gateway API is written down before changing thegateway

Concepts to focus on

service boundaries

HTTP client design

dependency on contracts rather than implementations

integration testing

discovering abstractions through real consumers

Do not build

polished downstream UI

large database

multi-step agent architecture

multiple document formats

several extraction workflows at once

Phase D — Choose the next gateway expansion

After the hosted gateway has at least one real consumer, pick one direction.

Option D1 — OpenAI-compatible endpoint

Best if the goal is:

Make the gateway itself a more credible standalone infrastructure projectthat third-party SDKs/tools can consume.

Possible endpoint:

POST /v1/chat/completions

Before implementation:

capture/inspect a real request from the chosen SDK or tool

do not implement the protocol from memory

Keep compatibility mapping separate from provider code.

Preserve /invoke.

Defer:

streaming

tool calls

n > 1

logprobs

broad structured-output compatibility

Approximate size: ~3–4 hours.

Option D2 — Second real provider

Best if the goal is:

Prove that the gateway genuinely abstracts providers.

Choose a provider with meaningful differences in auth, payload, response, orerror behavior.

This is the point where provider dependency injection, provider interfaces,and registry design become justified.

Derive the abstraction from two concrete providers rather than guessing aheadof time.

Where dependency injection belongs

Provider DI is a legitimate improvement, but it is not currently a deploymentmilestone.

The existing monkeypatch-based tests are acceptable while there is oneprovider and one main endpoint.

Introduce DI when:

a second provider exists

another endpoint needs the same provider dependency

monkeypatch tests become materially difficult to maintain

Do not implement DI only because it sounds more professional.

Do not create:

provider base classes

provider registries

generic provider interfaces

before a real second provider creates the need.

Suggested next 5–8 hours

Fastest path to hosted milestone

Deployment-critical housekeeping — ~30–60 min

Minimal gateway authentication — ~60–90 min

First hosted deployment — ~60–120 min

Expected result after roughly 2.5–4.5 hours:

A protected FastAPI LLM gateway is running remotely and successfully makingreal provider calls.

That is the first major milestone.

Then improve the live service

Model aliases + /models + unified error contract — ~2–2.5 h

Request ID + usage visibility — ~2–2.5 h

Real downstream consumer — next focused block

The roadmap is deliberately not:

finish every gateway feature → finally deploy

It is:

make it safe enough → deploy → improve the real hosted service → consume it

Session guide

For each slice, use the same learning process.

1. Orient — 5–10 minutes

Before changing code, answer:

What user/system problem does this slice solve?

Which boundary is changing?

What should remain unchanged?

What is the smallest definition of done?

2. Trace — 5–10 minutes

Write the request/control flow in plain text.

Example:

client→ gateway auth→ /invoke→ model resolution→ provider→ normalized response

Identify:

object types

exceptions

environment values

response status codes

3. Implement — 20–60+ minutes

Make the smallest working change.

Avoid opportunistic refactoring unless it is necessary for the slice.

4. Verify

Run:

ruff format .

ruff check .

make check

Then manually exercise the changed behavior.

For deployment slices, manually test the remote URL as well.

5. Close

Before switching tasks:

update the project roadmap/next-session note

record anything surprising

commit a coherent slice

leave the next task explicit

Open questions

Which hosting platform best fits this small FastAPI service?Verify current deployment requirements/pricing when the deployment slicebegins rather than relying on stale assumptions.

What exact production start command/environment does that host require?

Should the first deployment ship the static frontend, or should it initiallyexpose only the API plus /docs?

If the frontend is public, what browser-safe access model should eventuallyreplace a shared server-side gateway key?

Does OpenRouter reliably include usage metadata for the currently supportedmodels?

Should aliases stay flat until a second provider exists?

Should /models eventually expose lightweight metadata?

When the first real consumer exposes API awkwardness, is the problem trulyin the gateway contract or should the consumer adapt?

Is a second provider or OpenAI compatibility the stronger next demonstrationafter the first consumer?

Rabbit holes to avoid

Do not delay first deployment for model aliases.

Do not expose /invoke publicly before minimal authentication exists.

Do not embed a shared gateway secret in public browser JavaScript.

Do not convert the provider call to async merely for sophistication.

Do not build a provider registry before a second provider exists.

Do not add OpenTelemetry or distributed tracing yet.

Do not build DB-backed auth/key management.

Do not add OAuth/user accounts.

Do not optimize CI beyond one simple check workflow.

Do not build a custom domain before the hosted service itself works.

Do not add persistent logs/metrics infrastructure before basic host logs areinsufficient.

Do not implement OpenAI compatibility from memory.

Do not pursue OpenAI compatibility and a second provider simultaneously.

Do not let the downstream consumer absorb OpenRouter-specific code.

Do not turn the first consumer into a polished product before the one usefulend-to-end flow works.

Milestone summary

Milestone 1 — Local gateway is clean

green checks

safe logging

clean repo

working start command

Milestone 2 — Hosted gateway exists

remote /health

authenticated remote /invoke

real provider response

server-side secrets

visible host logs

Milestone 3 — Gateway owns its public abstraction

model aliases

/models

consistent errors

Milestone 4 — Hosted gateway is operationally traceable

request IDs

caller identity

model resolution

latency

supported usage metadata

Milestone 5 — Gateway has a real consumer

separate downstream app

no OpenRouter-specific code in consumer

hosted gateway used as infrastructure

Milestone 6 — Choose deeper gateway capability

OpenAI-compatible protocol surfaceOR

second provider + provider abstraction
---

# Appendix — 2026-08-14 status and next slices

Supersedes the phase/milestone plan above where they conflict. Phase A is
complete; the mid-document "NEXT: A1 AUTH TESTS" note is done and stale.

## Shipped since the original draft

- Gateway API key authentication on /invoke (/health remains public)
- Deployed and running on Railway with server-side secrets
- CI workflow running ruff format, ruff lint, and pytest on push
- Prompt sandbox at /sandbox.html: model selection, ordered
  system/user/assistant messages, run history with copy/export, client-side
  latency display
- Error-contract fix: normalize_openrouter_response() now runs inside the
  try block, and a provider response with content=None maps to a normalized
  502 provider_error instead of an unhandled 500

## Current gaps

- app/model_catalog.py is still unused. Provider model IDs pass through
  /invoke unchanged, and frontend/sandbox.js now hardcodes a provider ID
  with a comment asking for manual sync with the catalog.
- InvokeRequest exposes no generation parameters (temperature, max_tokens,
  response_format). Prompts currently ask for JSON in prose instead of
  using structured-output support.
- Logging records model, outcome, gateway status, and latency, but there is
  no request ID returned to callers, no caller identity, and no token usage.
- One shared gateway key, so all callers are anonymous and
  indistinguishable.
- The ValidationError path added on 2026-08-13 has no test.

## Next slices, in recommended order

### 1. Model aliases + GET /models + unified errors (~2-2.5h)

Wire SUPPORTED_MODELS into the request path so clients send gateway
aliases and the gateway resolves them to provider IDs. Reject unknown
aliases locally with a 4xx before any provider call. Expose GET /models.
Point the frontend and sandbox at aliases so no client hardcodes a
provider ID.

Rationale: this is the boundary that makes the service a gateway rather
than a proxy, and it is a prerequisite for provider routing or a second
provider. The leak is currently spreading rather than shrinking.

### 2. Generation parameters on InvokeRequest (~1-1.5h)

Add optional temperature, max_tokens, and response_format (or equivalent
structured-output support), validated at the gateway and passed through in
build_openrouter_payload. Verify the parameter names against a real
OpenRouter request before implementing.

Rationale: the most direct unblock for downstream apps. Prompt-level
instructions like "return JSON only" are unreliable compared to provider
structured-output support.

### 3. Request IDs, caller identity, and usage (~2-2.5h)

Generate a request ID per invocation, return it as X-Request-ID on success
and normalized failures, and include it in the invocation log. Move from
one shared key to a mapping of key to client_id (env-var JSON, SHA-256
hashes rather than plaintext, lookup by hash rather than a comparison
loop). Add token usage to logs only after verifying the fields exist in a
real provider response.

Rationale: makes hosted requests traceable and makes provider spend
attributable per consuming app. More valuable once multiple clients exist,
which is why it follows the slices above.

### 4. Test the provider-response failure path (~20-30 min)

Cover the ValidationError to 502 mapping with a test, and check whether
non-timeout network failures (for example httpx.ConnectError) are still
uncaught.

Rationale: smallest item on the list, and it closes a gap found through
real use rather than speculation.

## Housekeeping

- Trim the tutoring-oriented framing from the sections above ("What this
  slice teaches", "Concepts to focus on", "Session guide") so the document
  reads as an engineering plan.
- Confirm scripts/ is committed.
