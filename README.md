# Black Forest Labs — Python SDK

The official Python library for the [Black Forest Labs API](https://docs.bfl.ai) —
the FLUX family of image generation and editing models.

It is designed to make the simple things one line and the powerful things
obvious: a zero-config happy path, typed access to every model, full async
support, automatic image handling, retries, and precise errors.

```bash
pip install black-forest-labs            # core
pip install 'black-forest-labs[images]'  # + Pillow for .image and PIL inputs
```

Requires Python 3.10+.

## Quick start

```python
from bfl import BFL

client = BFL()                      # reads $BFL_API_KEY
image = client.generate("a red fox curled up in fresh snow, soft morning light")
image.save("fox.png")
```

> Import as `bfl` (canonical). `from blackforestlabs import ...` also works as
> an alias. `from blackforest import ...` still works for now but is deprecated
> (it warns) and will be removed in a future release — switch to `bfl`.

That's it. `generate` uses **FLUX.2 [pro]** by default, blocks until the image
is ready, and hands back a `Result` you can `.save()`, read as `.bytes()`, open
as a Pillow `.image`, or grab the signed `.url` from.

## Choosing a model

Pass `model=` to pick any model by id — the same flat style as the OpenAI and
Anthropic SDKs. This is the quickest way when you already know the id:

```python
image = client.generate("a neon-lit alley in the rain, cinematic", model="flux-2-max")
```

For autocomplete on parameters, discoverable model names, and non-blocking
jobs, reach into the typed namespaces. Each model exposes `submit` (returns a
`Job` immediately) and `generate` (submits and waits):

```python
# Highest quality, blocking
image = client.flux2.max.generate("a neon-lit alley in the rain, cinematic", width=1536, height=1024)

# Fire-and-forget: get a job handle, do other work, wait later
job = client.flux2.pro.submit("a serene mountain lake at dawn", seed=7)
print(job.id, job.cost)
image = job.wait(on_progress=lambda p: print(p["status"]))

# Flex adds guidance + steps
image = client.flux2.flex.generate("an intricate art-nouveau poster", guidance=6.0, steps=40)

# Klein — fast, open-weight
image = client.flux2.klein_4b.generate("a pixel-art cat")
```

Keyword parameters are typed (via `TypedDict` + `Unpack`), so editors
autocomplete them and a type checker flags a misspelled keyword. The exact set a
given model accepts is enforced at submit time — pass `guidance` to a model that
doesn't support it and you get a clear `BFLValidationError` rather than a silently
ignored field.

Both styles hit the same models; use `model=` for a quick one-liner and the
namespaces when you want discoverability and typed params. Every namespaced
model id below also works as a `model=` string.

| Namespace | `model=` id | Notes |
|-----------|-------------|-------|
| `client.flux2.pro` | `flux-2-pro` | Recommended default. Generation + editing. |
| `client.flux2.max` | `flux-2-max` | Highest quality, strongest editing. |
| `client.flux2.flex` | `flux-2-flex` | Exposes `guidance` and `steps`. |
| `client.flux2.klein_4b` / `klein_9b` | `flux-2-klein-4b` / `flux-2-klein-9b` | Fast, open-weight. |
| `client.flux1.pro_1_1` / `ultra` / `pro` / `dev` | `flux-pro-1.1` / `flux-pro-1.1-ultra` / `flux-pro` / `flux-dev` | Legacy generation. |
| `client.tools.outpaint` / `erase` / `deblur` / `vto` | `flux-tools-outpaint` / `-erase` / `-deblur` / `-vto` | Outpaint, object erase, deblur, virtual try-on. |
| `client.kontext.pro` / `max` | `flux-kontext-pro` / `flux-kontext-max` | Reference-guided editing. |

For a model id held in a variable, `client.model("flux-2-flex").submit(...)`
returns the same typed accessor as the namespaces.

## Editing with reference images

For FLUX.2 and Kontext, pass `images=[...]` — any mix of file paths, URLs,
`bytes`, base64, or Pillow images. The SDK encodes them and spreads them across
the model's reference-image slots:

```python
from pathlib import Path

edited = client.flux2.pro.generate(
    "place the product on a marble countertop, studio lighting",
    images=[Path("product.png"), "https://example.com/scene.jpg"],
)
edited.save("composite.png")
```

The FLUX Tools take named image arguments instead of `images=[...]`, matching
each endpoint's contract:

```python
# Outpaint: extend an image onto a larger canvas
bigger = client.tools.outpaint.generate(
    input_image="photo.png", width=1920, height=1080,
)

# Erase: remove a masked object (white = remove, black = keep)
cleaned = client.tools.erase.generate(image="room.png", mask="object_mask.png")

# Deblur: sharpen a whole image (no prompt or mask)
sharp = client.tools.deblur.generate(image="blurry.png")

# Virtual try-on: dress a person in a garment
look = client.tools.vto.generate(
    prompt="The person of image 1, maintaining exactly their face and pose, "
           "wearing the olive bomber jacket of image 2.",
    person="me.jpg", garment="jacket.jpg",
)
```

## Async

`AsyncBFL` mirrors the sync client one-to-one. Use it as an async context
manager so connections are cleaned up:

```python
import asyncio
from bfl import AsyncBFL

async def main():
    async with AsyncBFL() as client:
        image = await client.flux2.flex.generate("a misty pine forest at dawn", steps=30)
        await image.asave("forest.png")

asyncio.run(main())
```

## Estimating cost

Quote a FLUX.2 generation before you run it (no credits spent, no task started):

```python
quote = client.estimate_cost("flux-2-pro", width=1024, height=1024)
print(quote["cost"], "credits ≈ $", quote["cost_usd"])

balance = client.credits()
```

## Errors

Every failure maps to a precise, catchable type. Catch `BFLError` for
everything, or narrow to the case you care about:

```python
from bfl import (
    BFLError, BFLAuthError, BFLRateLimitError,
    BFLContentModerated, BFLValidationError, BFLTimeoutError,
)

try:
    image = client.generate("...")
except BFLContentModerated as e:
    print("Blocked at the", e.stage, "stage")   # "request" or "content"
except BFLRateLimitError as e:
    print("Slow down; retry after", e.retry_after, "s")
except BFLAuthError:
    print("Check your API key / deployment")
```

Transient failures are retried automatically with exponential backoff, full
jitter, and `Retry-After` support. Retries are idempotency-aware: a `429` is
always replayed, but a `5xx` on a generation **POST** is surfaced rather than
resubmitted — so a lost response can never silently bill you for a second
image. Invalid inputs are caught **locally**, before any network call, so a
typo costs you nothing.

## Webhooks

Pass `webhook_url` (and an optional `webhook_secret`) to any `submit`/`generate`
call — the one exception is `tools.outpaint`, which the API does not accept
webhook fields for. When the task finishes, the API POSTs the result to your URL
and, if you set a secret, echoes it back in the `X-Webhook-Secret` header. Verify
it in your handler with a constant-time check:

```python
from bfl import verify_webhook, WEBHOOK_SECRET_HEADER

def handle(request):                      # any framework
    received = request.headers.get(WEBHOOK_SECRET_HEADER)
    if not verify_webhook(my_secret, received):
        abort(401)
    payload = request.json()              # trusted: task id, status, result
```

## Configuration

```python
client = BFL(
    api_key="...",          # or $BFL_API_KEY
    base_url="...",         # or $BFL_BASE_URL; defaults to production
    timeout=60.0,           # per-request HTTP timeout (seconds)
    max_retries=3,          # transient-failure retry budget
)
```

For full control over backoff, pass a `RetryConfig` (it takes precedence over
`max_retries`):

```python
from bfl import BFL, RetryConfig

client = BFL(retry=RetryConfig(
    max_retries=5,
    backoff_factor=0.5,     # sleep ≈ backoff_factor * 2**(attempt-1) + jitter
    max_backoff=30.0,       # cap on any single sleep, seconds
    respect_retry_after=True,
))
```

## Examples

Runnable scripts live in [`examples/`](examples/):

- `quickstart.py` — the one-liner happy path.
- `models_and_editing.py` — model selection, jobs, progress, reference images.
- `async_and_webhooks.py` — the async client and webhook verification.
- `tools_tour.py` — every FLUX Tool; run as-is to inspect each request body
  without spending credits, or `LIVE=1 python examples/tools_tour.py` to execute.

## Migrating from 0.1.x

The original `BFLClient(api_key).generate(model, inputs, config)` interface
still works (it now runs on the new transport, with the polling-bug fix and
retries), but it is deprecated. Move to `BFL`:

```python
# Old
from bfl import BFLClient
client = BFLClient(api_key="...")
resp = client.generate("flux-pro-1.1", {"prompt": "..."}, ClientConfig(sync=True))
url = resp.result.sample

# New
from bfl import BFL
client = BFL(api_key="...")
image = client.generate("...", model="flux-pro-1.1")
url = image.url
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
