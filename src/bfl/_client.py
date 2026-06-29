"""The client facades: :class:`BFL` (sync) and :class:`AsyncBFL` (async).

The zero-config happy path is one line::

    from bfl import BFL
    img = BFL().generate("a red fox in the snow")
    img.save("fox.png")

``BFL()`` reads ``BFL_API_KEY`` from the environment. ``generate`` defaults to
FLUX.2 [pro] and blocks until the image is ready. For control, reach into the
typed namespaces — ``client.flux2.max``, ``client.tools.fill``,
``client.kontext.pro`` — which return :class:`~bfl._jobs.Job` /
:class:`~bfl._jobs.Result` handles.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from . import _catalog
from ._catalog import DEFAULT_MODEL, ModelSpec
from ._exceptions import (
    BFLConfigError,
    BFLError,
    BFLNotFoundError,
    BFLValidationError,
)
from ._jobs import AsyncJob, Job, ProgressCallback, Result
from ._params import GenerateParams
from ._resources import (
    NAMESPACE_CLASSES,
    NAMESPACE_LAYOUT,
    AsyncImageModel,
    Flux1Namespace,
    Flux2Namespace,
    ImageModel,
    KontextNamespace,
    ToolsNamespace,
)
from ._transport import DEFAULT_BASE_URL, AsyncTransport, RetryConfig, Transport

if sys.version_info >= (3, 11):  # pragma: no cover - version branch
    from typing import Unpack
else:  # pragma: no cover - version branch
    from typing_extensions import Unpack

_API_KEY_ENV = "BFL_API_KEY"
_BASE_URL_ENV = "BFL_BASE_URL"


def _resolve_api_key(api_key: str | None) -> str:
    key = api_key or os.environ.get(_API_KEY_ENV)
    if not key:
        raise BFLConfigError(
            f"No API key provided. Pass api_key=... or set the {_API_KEY_ENV} "
            "environment variable. Get a key at https://dashboard.bfl.ai."
        )
    return key


def _resolve_spec(model: str) -> ModelSpec:
    try:
        return _catalog.resolve(model)
    except KeyError:
        raise BFLValidationError(
            f"Unknown model {model!r}. Supported models: "
            f"{', '.join(_catalog.model_ids())}."
        ) from None


def _require(response: Any, key: str, endpoint: str) -> Any:
    """Pull a required field from an API response, or raise a protocol error.

    A 200 response that's missing an expected field means the API contract was
    violated (or we hit the wrong endpoint). Surface that as a typed
    :class:`BFLError` rather than letting a raw ``KeyError``/``TypeError`` leak.
    """
    if not isinstance(response, dict) or key not in response:
        raise BFLError(
            f"Unexpected response from {endpoint}: expected a JSON object with "
            f"a {key!r} field, got {response!r}."
        )
    return response[key]


def _build_job_kwargs(response: Any) -> dict[str, Any]:
    """Shared, validated Job/AsyncJob construction args from a submit response."""
    task_id = _require(response, "id", "submit")
    return {
        "id": task_id,
        "polling_url": response.get("polling_url") or f"/v1/get_result?id={task_id}",
        "cost": response.get("cost"),
        "raw": response,
    }


def _pricing_body(
    model: str,
    width: int,
    height: int,
    input_images: list[tuple[int, int]] | None,
) -> dict[str, Any]:
    """Validate the model and build the ``/v1/pricing`` request body."""
    spec = _resolve_spec(model)
    if not spec.supports_pricing:
        raise BFLValidationError(
            f"{spec.label} does not support price estimation; only FLUX.2 " "models do."
        )
    body: dict[str, Any] = {"model": spec.id, "width": width, "height": height}
    if input_images:
        body["input_images"] = [{"width": w, "height": h} for w, h in input_images]
    return body


def _pricing_unavailable(exc: BFLNotFoundError) -> BFLError:
    """Turn a bare 404 from /v1/pricing into an actionable message."""
    return BFLError(
        "Price estimation is not available on this deployment yet "
        "(/v1/pricing returned 404). Submit the generation to learn its cost "
        "from the response instead."
    )


def _resolve_retry(retry: "RetryConfig | None", max_retries: int) -> "RetryConfig":
    """Pick the explicit RetryConfig if given, else build one from max_retries."""
    return retry if retry is not None else RetryConfig(max_retries=max_retries)


class BFL:
    """Synchronous client for the Black Forest Labs API.

    Args:
        api_key: Your API key. Falls back to ``$BFL_API_KEY``.
        base_url: API base URL. Falls back to ``$BFL_BASE_URL`` then the
            production endpoint.
        timeout: Per-request HTTP timeout in seconds.
        max_retries: Transient-failure retry budget (convenience shortcut).
        retry: Full :class:`RetryConfig` for fine control (backoff, max_backoff,
            Retry-After). Takes precedence over ``max_retries`` when provided.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry: RetryConfig | None = None,
    ) -> None:
        self._transport = Transport(
            _resolve_api_key(api_key),
            base_url=base_url or os.environ.get(_BASE_URL_ENV, DEFAULT_BASE_URL),
            timeout=timeout,
            retry=_resolve_retry(retry, max_retries),
        )
        self._build_namespaces()

    # -- namespaces -------------------------------------------------------

    #: FLUX.2 family — ``client.flux2.pro`` / ``.max`` / ``.flex`` / ``.klein_4b``.
    flux2: Flux2Namespace[ImageModel]
    #: Legacy FLUX.1 generation models.
    flux1: Flux1Namespace[ImageModel]
    #: FLUX.1 Tools — fill (inpaint) and expand (outpaint).
    tools: ToolsNamespace[ImageModel]
    #: FLUX.1 Kontext reference-guided editing.
    kontext: KontextNamespace[ImageModel]

    def _build_namespaces(self) -> None:
        self._models: dict[str, ImageModel] = {
            spec.id: ImageModel(self, spec) for spec in _catalog.all_models()
        }
        for family, layout in NAMESPACE_LAYOUT.items():
            members = {attr: self._models[mid] for attr, mid in layout.items()}
            setattr(self, family, NAMESPACE_CLASSES[family](members))

    def model(self, model: str) -> ImageModel:
        """Get the :class:`ImageModel` accessor for any model id or alias."""
        return self._models[_resolve_spec(model).id]

    # -- high-level convenience ------------------------------------------

    def generate(
        self,
        prompt: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        images: list[Any] | None = None,
        timeout: float | None = 300.0,
        poll_interval: float = 1.0,
        on_progress: ProgressCallback | None = None,
        **params: Unpack[GenerateParams],
    ) -> Result:
        """Generate an image and block until it's ready. The happy path.

        Defaults to FLUX.2 [pro]. Pass ``model=`` to pick another, ``images=``
        to supply reference images for editing, and any model-specific keyword
        (``width``, ``seed``, ``guidance``, ...) as needed.
        """
        return self.model(model).generate(
            prompt,
            images=images,
            timeout=timeout,
            poll_interval=poll_interval,
            on_progress=on_progress,
            **params,
        )

    def submit(
        self,
        prompt: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        images: list[Any] | None = None,
        **params: Unpack[GenerateParams],
    ) -> Job:
        """Submit a task and return immediately with a :class:`Job`."""
        return self.model(model).submit(prompt, images=images, **params)

    # -- internals used by resources -------------------------------------

    def _submit(self, spec: ModelSpec, payload: dict[str, Any]) -> Job:
        response = self._transport.request("POST", spec.path, json=payload)
        return Job(transport=self._transport, **_build_job_kwargs(response))

    # -- account / utility endpoints -------------------------------------

    def credits(self) -> float:
        """Return the account's current credit balance."""
        data = self._transport.request("GET", "/v1/credits")
        return _require(data, "credits", "/v1/credits")

    def estimate_cost(
        self,
        model: str = DEFAULT_MODEL,
        *,
        width: int = 0,
        height: int = 0,
        input_images: list[tuple[int, int]] | None = None,
    ) -> dict[str, Any]:
        """Quote the cost of a FLUX.2 generation before submitting it.

        Args:
            model: A FLUX.2 model id. Only FLUX.2 supports quoting.
            width / height: Intended output dimensions (0 = let the model infer).
            input_images: ``(width, height)`` of each reference image for edits.

        Returns:
            The pricing payload: ``cost`` (credits), ``cost_usd``, and the
            megapixel breakdown.

        Raises:
            BFLValidationError: If the model can't be priced.
            BFLError: If the deployment has no pricing endpoint yet.
        """
        body = _pricing_body(model, width, height, input_images)
        try:
            return self._transport.request("POST", "/v1/pricing", json=body)
        except BFLNotFoundError as exc:
            raise _pricing_unavailable(exc) from exc

    def get_result(self, task_id: str) -> dict[str, Any]:
        """Fetch the raw status/result payload for a task id."""
        return self._transport.request("GET", f"/v1/get_result?id={task_id}")

    # -- lifecycle --------------------------------------------------------

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "BFL":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncBFL:
    """Asynchronous client for the Black Forest Labs API.

    Mirrors :class:`BFL`. Use as an async context manager so connections are
    cleaned up::

        async with AsyncBFL() as client:
            img = await client.generate("a misty forest at dawn")
            await img.asave("forest.png")
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry: RetryConfig | None = None,
    ) -> None:
        self._transport = AsyncTransport(
            _resolve_api_key(api_key),
            base_url=base_url or os.environ.get(_BASE_URL_ENV, DEFAULT_BASE_URL),
            timeout=timeout,
            retry=_resolve_retry(retry, max_retries),
        )
        self._build_namespaces()

    #: FLUX.2 family — ``client.flux2.pro`` / ``.max`` / ``.flex`` / ``.klein_4b``.
    flux2: Flux2Namespace[AsyncImageModel]
    #: Legacy FLUX.1 generation models.
    flux1: Flux1Namespace[AsyncImageModel]
    #: FLUX.1 Tools — fill (inpaint) and expand (outpaint).
    tools: ToolsNamespace[AsyncImageModel]
    #: FLUX.1 Kontext reference-guided editing.
    kontext: KontextNamespace[AsyncImageModel]

    def _build_namespaces(self) -> None:
        self._models: dict[str, AsyncImageModel] = {
            spec.id: AsyncImageModel(self, spec) for spec in _catalog.all_models()
        }
        for family, layout in NAMESPACE_LAYOUT.items():
            members = {attr: self._models[mid] for attr, mid in layout.items()}
            setattr(self, family, NAMESPACE_CLASSES[family](members))

    def model(self, model: str) -> AsyncImageModel:
        """Get the :class:`AsyncImageModel` accessor for any model id or alias."""
        return self._models[_resolve_spec(model).id]

    async def generate(
        self,
        prompt: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        images: list[Any] | None = None,
        timeout: float | None = 300.0,
        poll_interval: float = 1.0,
        on_progress: ProgressCallback | None = None,
        **params: Unpack[GenerateParams],
    ) -> Result:
        """Generate an image and await its completion. Defaults to FLUX.2 [pro]."""
        return await self.model(model).generate(
            prompt,
            images=images,
            timeout=timeout,
            poll_interval=poll_interval,
            on_progress=on_progress,
            **params,
        )

    async def submit(
        self,
        prompt: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        images: list[Any] | None = None,
        **params: Unpack[GenerateParams],
    ) -> AsyncJob:
        """Submit a task and return immediately with an :class:`AsyncJob`."""
        return await self.model(model).submit(prompt, images=images, **params)

    async def _submit(self, spec: ModelSpec, payload: dict[str, Any]) -> AsyncJob:
        response = await self._transport.request("POST", spec.path, json=payload)
        return AsyncJob(transport=self._transport, **_build_job_kwargs(response))

    async def credits(self) -> float:
        """Return the account's current credit balance."""
        data = await self._transport.request("GET", "/v1/credits")
        return _require(data, "credits", "/v1/credits")

    async def estimate_cost(
        self,
        model: str = DEFAULT_MODEL,
        *,
        width: int = 0,
        height: int = 0,
        input_images: list[tuple[int, int]] | None = None,
    ) -> dict[str, Any]:
        """Async variant of :meth:`BFL.estimate_cost`."""
        body = _pricing_body(model, width, height, input_images)
        try:
            return await self._transport.request("POST", "/v1/pricing", json=body)
        except BFLNotFoundError as exc:
            raise _pricing_unavailable(exc) from exc

    async def get_result(self, task_id: str) -> dict[str, Any]:
        """Fetch the raw status/result payload for a task id."""
        return await self._transport.request("GET", f"/v1/get_result?id={task_id}")

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> "AsyncBFL":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
