# Changelog

All notable changes to `black-forest-labs` are documented here. This project
adheres to [Semantic Versioning](https://semver.org/).

## 0.2.0 (unreleased)

A ground-up rework of the client. The 0.1.x `BFLClient` interface still works
(deprecated) so existing code keeps running, but new code should use the
`BFL` / `AsyncBFL` clients.

### Added
- **Layered `BFL` and `AsyncBFL` clients** with a zero-config happy path
  (`client.generate("...")` reads `$BFL_API_KEY` and blocks until ready).
- **Typed per-model namespaces**: `client.flux2.pro/max/flex/klein_4b/klein_9b`,
  `client.flux1.*`, `client.tools.*`, `client.kontext.*`. Each exposes
  `submit()` (returns a `Job`) and `generate()` (submits and waits).
- **Flat `model=` selection** — `client.generate("...", model="flux-2-max")` —
  matching the OpenAI/Anthropic idiom, alongside the typed namespaces.
- **Typed keyword parameters** via `TypedDict` + `typing.Unpack`: editors
  autocomplete generation params and type checkers flag misspelled keywords.
- **FLUX Tools**: `tools.outpaint`, `tools.erase`, `tools.deblur`, `tools.vto`
  (virtual try-on), mapped to the `/v1/flux-tools/*-v1` endpoints.
- **Universal image inputs** — paths, URLs, `bytes`, base64, data-URIs, and
  `PIL.Image` are all accepted and encoded automatically.
- **`Job` / `Result` handles**: `Result.save()`, `.bytes()`, `.image`, `.url`,
  `.seed`, plus async `.asave()` / `.abytes()`.
- **Idempotency-aware retries** with exponential backoff, full jitter, and
  `Retry-After` support; injectable `RetryConfig` for full control.
- **Typed exception hierarchy** under `BFLError` (auth, rate-limit, validation,
  moderation, timeout, connection, …) carrying `status_code`, `body`,
  `request_id`.
- **Webhook verification** via `verify_webhook()` and `WEBHOOK_SECRET_HEADER`.
- **Cost estimation** with `client.estimate_cost(...)` and `client.credits()`.
- `py.typed` marker — the package ships as fully typed.
- Runnable `examples/` including `tools_tour.py` (inspect tool request bodies
  with no credits, or run live).

### Changed
- **Canonical import is now `bfl`** (`from bfl import BFL`). `blackforestlabs`
  remains a quiet alias. `blackforest` still works but emits a
  `DeprecationWarning` and will be removed in a future release.
- Package version is single-sourced from `bfl._version.__version__` via the
  build backend.
- Unknown/unsupported keyword arguments and reference images now raise a clear
  `BFLValidationError` instead of being silently dropped.
- Result-download failures raise `BFLConnectionError` (with an expiry hint)
  instead of leaking raw `httpx` exceptions.

### Fixed
- Terminal task states (moderation/error) raise immediately instead of polling
  to the timeout (the 0.1.x hang).
- `prompt_upsampling` is correctly translated per FLUX.2 model (`disable_pup`
  for pro/max, native for flex, dropped for klein) instead of being ignored.
- `import bfl` no longer requires Pillow; it is an optional extra
  (`black-forest-labs[images]`) used only for `Result.image` and PIL inputs.
- Base64-encoded JPEG inputs are no longer rejected by the input heuristic.

### Removed
- The unsupported `flux-pro-1.0-canny` / `-depth` and the legacy
  `flux-pro-1.0-fill` / `-expand` tool endpoints (replaced by the FLUX Tools).
