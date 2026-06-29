# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the official Python SDK for the Black Forest Labs API — the FLUX family
of image generation and editing models. The package is distributed as
`black-forest-labs` on PyPI, imported as `bfl` (with `blackforestlabs` kept as
a quiet back-compat re-export alias, and `blackforest` kept as a deprecated
alias that warns and will be removed). It exposes a modern, layered client with
a sync and async mirror, typed per-model namespaces, retries, universal image
handling, pricing, and webhook verification.

**Requirements:** Python 3.10+. Runtime deps: `httpx`, `pydantic`. Pillow is an
optional extra (`black-forest-labs[images]`) used only for `Result.image` and
passing `PIL.Image` inputs.

## Basic Usage

```python
from bfl import BFL

client = BFL()                          # reads $BFL_API_KEY
image = client.generate("a red fox in the snow")   # FLUX.2 [pro], blocks
image.save("fox.png")

# Typed per-model access; submit() returns a Job, generate() submits + waits
job = client.flux2.max.submit(prompt="...", width=1536, height=1024, seed=7)
image = job.wait(on_progress=lambda p: print(p["status"]))

# Editing: images=[...] accepts paths, URLs, bytes, PIL, or base64
edited = client.flux2.pro.generate("...", images=["a.png", "https://.../b.jpg"])
```

Async mirrors the sync API one-to-one via `AsyncBFL` (use as an async context
manager; `await client.generate(...)`, then `await image.asave(...)`).

## Development Commands

```bash
# Tests (offline, network-free — uses a FakeTransport)
python -m pytest tests/ -q

# Lint + format
ruff check src/ tests/ examples/
ruff format src/ tests/ examples/

# Install in dev mode
pip install -e .
```

The unit tests do **not** hit the network. There are throwaway live E2E scripts
written to `/tmp` during development; a real `BFL_API_KEY` lives in `.env`
(loaded via python-dotenv). Don't burn credits casually — the offline suite is
the inner loop.

## Architecture

The SDK is layered. Internal modules are underscore-prefixed; the public surface
is re-exported from `__init__.py`.

- **`_client.py`** — `BFL` and `AsyncBFL` facades. Resolve the API key
  (`$BFL_API_KEY`), build the typed namespaces from the catalog, and expose
  `generate`/`submit`, `credits()`, `estimate_cost()`, `get_result()`. The
  zero-config happy path and the `model(id)` escape hatch live here.
- **`_transport.py`** — `Transport` (sync) and `AsyncTransport` (async) wrap
  `httpx`. Shared module-level helpers decide retry/backoff/error-mapping so the
  two paths never drift. **Retries are idempotency-aware**: `429` always
  retries; `5xx` retries only for idempotent methods (GET/HEAD) — a `POST`
  submit is never replayed on a server error (double-charge guard);
  connection/timeout errors before a response retry for any method.
  `Retry-After` is honored (seconds or HTTP-date).
- **`_jobs.py`** — `Job`/`AsyncJob` (poll lifecycle, `wait` with progress
  callbacks) and `Result` (`.url`, `.seed`, `.prompt`, `.save`/`.bytes`/`.image`
  sync, `.asave`/`.abytes` async). `_interpret` maps the API status enum:
  `Ready`→done, `Pending`→keep polling, moderation/error/**unknown**→raise a
  typed exception immediately (never poll to timeout). A `Result` from an async
  job sets `_async=True` and refuses the blocking sync accessors.
- **`_models.py`** — fresh, correct typed params for FLUX.2 (`Flux2Params`,
  `Flux2FlexParams`, `Flux2KleinParams`, `OutputFormat`). FLUX.2 rules: up to
  4MP (2048×2048), min side 64, NO multiple-of-32; `transparent_bg` requires
  png/webp. `extra="forbid"`.
- **`_params.py`** — `GenerateParams`, a single ``total=False`` `TypedDict` of
  every keyword the generation/tool methods accept. Surfaced via
  `typing.Unpack` on `submit`/`generate` so editors autocomplete params and
  type checkers flag typos. It's the full vocabulary (not per-model); the exact
  per-model contract is enforced at runtime by the pydantic models below, which
  all `extra="forbid"`, so a wrong-for-this-model field raises a clear
  `BFLValidationError`.
- **`_catalog.py`** — `ModelSpec` registry mapping public model id/alias →
  API path, family, reference-image limit, pricing support. Single source of
  truth; adding a model is one entry. `DEFAULT_MODEL = "flux-2-pro"`.
- **`_requests.py`** — `build_payload` validates + serializes a request:
  encodes every image-bearing field, enforces per-model reference-image limits,
  routes FLUX.2 through `_models.py` and legacy models through the reused
  pydantic input classes. `spread_images` maps `images=[...]` to
  `input_image`/`input_image_2`/…
- **`_images.py`** — `to_image_payload` coerces path/Path/bytes/PIL/base64/
  data-URI/URL into what the API wants (base64 string or URL passthrough).
  Path-vs-base64 disambiguation guards against ENAMETOOLONG.
- **`_exceptions.py`** — typed hierarchy under `BFLError`
  (Auth/RateLimit/Validation/NotFound/InsufficientCredits/Server/Connection/
  Task/ContentModerated/Timeout). Request errors carry `status_code`, `body`,
  `request_id`.
- **`_webhooks.py`** — `verify_webhook(secret, received_secret)` constant-time
  compares the incoming `X-Webhook-Secret` header (exported as
  `WEBHOOK_SECRET_HEADER`) to your secret. **This is a shared-secret header
  check, not a body HMAC** — that is exactly how the API delivers
  (`task_management.py` sets `headers["X-Webhook-Secret"] = webhook_secret`).
- **`_resources.py`** — typed namespaces (`flux2`/`flux1`/`tools`/`kontext`),
  statically declared so `client.flux2.pro` autocompletes and type-checks.
- **`client.py`** — deprecated `BFLClient` compat shim over the modern client,
  preserving the pre-0.2 `(model, inputs, config)` surface.
- **`types/inputs/*.py`, `resources/mapping/`** — the legacy FLUX.1 / tools /
  Kontext pydantic input models, reused as-is for those endpoints.

## API ground truth

The live API contract is in the hoellental monorepo
(`~/Documents/bfl/hoellental`). When in doubt about request/response shape,
**read the source, don't guess**. Key facts the SDK depends on:
- Public routes under `/v1` (`/v1/flux-2-pro`, `/v1/flux-2-max`,
  `/v1/flux-2-flex`, `/v1/flux-2-klein-4b`, `/v1/flux-2-klein-9b`,
  `/v1/get_result`, `/v1/credits`, `/v1/pricing`).
- FLUX Tools routes under `/v1/flux-tools/*-v1`
  (`/v1/flux-tools/outpainting-v1`, `/erase-v1`, `/deblur-v1`, `/vto-v1`),
  defined in `routers/flux_tools.py`; request models `FluxOutpaintingInputs`,
  `Flux2EraseInputs`, `Flux2DeblurInputs`, `Flux2KleinTryonInputs` in
  `flux_types.py`. Outpainting is `extra="forbid"` and does NOT accept webhook
  fields; erase/deblur/vto do. VTO takes literal `person`/`garment` fields
  (server maps them to `input_image`/`input_image_2`). The old
  `/v1/flux-pro-1.0-fill|expand|canny|depth` tools are NOT surfaced by this SDK.
- Auth header is `x-key` (lowercase).
- `get_result` status enum: `Pending`, `Ready`, `Error`, `Content Moderated`,
  `Request Moderated`, `Task not found`.
- Reference-image limits: klein 4B = 4, klein 9B = 5, pro/max/flex = 8.
- `/v1/pricing` may 404 in production (not yet deployed); `estimate_cost`
  degrades to a clear message.

## Adding a New Model

1. Add a `ModelSpec` entry to `_SPECS` in `_catalog.py` (id, path, family,
   limits, pricing).
2. For a FLUX.2 variant, point it at the right params class in `_requests.py`'s
   `_FLUX2_PARAMS`; for a FLUX Tool, add a typed params model in `_models.py`
   and register it in `_requests.py`'s `_FLUX_TOOLS_PARAMS`; for a legacy
   model, register the pydantic input class in
   `resources/mapping/model_input_registry.py`.
3. Expose it under the right namespace in `NAMESPACE_LAYOUT` (`_resources.py`)
   and add the typed attribute to the namespace class.
4. Add offline tests in `tests/`.

## Testing Notes

- The suite is fully offline. `tests/conftest.py` provides a `FakeTransport`
  that returns scripted responses and records calls.
- Cover the real risk surface: retry idempotency (POST not replayed on 5xx),
  status interpretation (including unknown→raise), image coercion, dimension/
  reference validation, webhook verify, the async-result guard, and the legacy
  shim.

## Package Structure

`black-forest-labs` ships three import names: `bfl` (canonical — the real
package under `src/bfl/`), `blackforestlabs` (a quiet back-compat shim that
does `from bfl import *`), and `blackforest` (the same shim but emits a
`DeprecationWarning` on import; slated for removal). All three carry a
`py.typed` marker. Configured via `pyproject.toml` `package-dir = {"" = "src"}`
and `packages.find include = ["bfl*", "blackforestlabs*", "blackforest*"]`. The
dynamic version reads `bfl._version.__version__`.
