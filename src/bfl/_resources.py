"""Resource namespaces — the typed, discoverable surface of the client.

``client.flux2.pro``, ``client.flux1.ultra``, ``client.tools.fill``,
``client.kontext.pro`` and friends are all :class:`ImageModel` (or
:class:`AsyncImageModel`) instances. Each exposes two methods:

* :meth:`submit` — fire the request, get a :class:`~bfl._jobs.Job` back
  immediately (non-blocking).
* :meth:`generate` — submit *and* wait, returning a
  :class:`~bfl._jobs.Result`.

The methods take explicit, model-appropriate keyword arguments; ``prompt`` is
accepted positionally and ``images=[...]`` is spread across the reference-image
slots for convenience.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Generic, Iterator, TypeVar

from ._catalog import ModelSpec
from ._jobs import ProgressCallback
from ._params import GenerateParams
from ._requests import build_payload, spread_images

if sys.version_info >= (3, 11):  # pragma: no cover - version branch
    from typing import Unpack
else:  # pragma: no cover - version branch
    from typing_extensions import Unpack

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ._client import BFL, AsyncBFL
    from ._jobs import AsyncJob, Job, Result

#: Either kind of model accessor; namespaces are generic over it so a sync
#: client yields ImageModel members and an async client AsyncImageModel.
M = TypeVar("M", "ImageModel", "AsyncImageModel")


def _build_request_payload(
    spec: ModelSpec,
    prompt: str | None,
    images: list[Any] | None,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Merge prompt + spread images into params and build the request body.

    Shared by the sync and async accessors so the two paths can't drift.
    """
    if prompt is not None:
        params.setdefault("prompt", prompt)
    params.update(spread_images(images))
    return build_payload(spec, params)


class ImageModel:
    """Synchronous accessor for a single generation model."""

    def __init__(self, client: "BFL", spec: ModelSpec) -> None:
        self._client = client
        self.spec = spec

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def label(self) -> str:
        return self.spec.label

    def submit(
        self,
        prompt: str | None = None,
        *,
        images: list[Any] | None = None,
        **params: Unpack[GenerateParams],
    ) -> "Job":
        """Submit a generation task and return a :class:`Job` without waiting."""
        payload = _build_request_payload(self.spec, prompt, images, dict(params))
        return self._client._submit(self.spec, payload)

    def generate(
        self,
        prompt: str | None = None,
        *,
        images: list[Any] | None = None,
        timeout: float | None = 300.0,
        poll_interval: float = 1.0,
        on_progress: ProgressCallback | None = None,
        **params: Unpack[GenerateParams],
    ) -> "Result":
        """Submit a task, wait for it to finish, and return its :class:`Result`."""
        job = self.submit(prompt, images=images, **params)
        return job.wait(
            timeout=timeout, poll_interval=poll_interval, on_progress=on_progress
        )

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<ImageModel {self.spec.id!r}>"


class AsyncImageModel:
    """Asynchronous accessor for a single generation model."""

    def __init__(self, client: "AsyncBFL", spec: ModelSpec) -> None:
        self._client = client
        self.spec = spec

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def label(self) -> str:
        return self.spec.label

    async def submit(
        self,
        prompt: str | None = None,
        *,
        images: list[Any] | None = None,
        **params: Unpack[GenerateParams],
    ) -> "AsyncJob":
        """Submit a generation task and return an :class:`AsyncJob`."""
        payload = _build_request_payload(self.spec, prompt, images, dict(params))
        return await self._client._submit(self.spec, payload)

    async def generate(
        self,
        prompt: str | None = None,
        *,
        images: list[Any] | None = None,
        timeout: float | None = 300.0,
        poll_interval: float = 1.0,
        on_progress: ProgressCallback | None = None,
        **params: Unpack[GenerateParams],
    ) -> "Result":
        """Submit, await completion, and return the :class:`Result`."""
        job = await self.submit(prompt, images=images, **params)
        return await job.wait(
            timeout=timeout, poll_interval=poll_interval, on_progress=on_progress
        )

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<AsyncImageModel {self.spec.id!r}>"


class _Namespace(Generic[M]):
    """Base for a dotted group of model accessors (e.g. ``client.flux2``).

    Subclasses declare their members as typed attributes so IDEs offer
    autocomplete and type checkers verify access. The base stores the members
    for iteration and ``__contains__``.
    """

    _members: dict[str, M]

    def __init__(self, members: dict[str, M]) -> None:
        self._members = members

    def __iter__(self) -> "Iterator[M]":
        return iter(self._members.values())

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} {sorted(self._members)}>"


class Flux2Namespace(_Namespace[M]):
    """The FLUX.2 family: ``pro``, ``max``, ``flex``, ``klein_4b``/``klein_9b``."""

    def __init__(self, members: dict[str, M]) -> None:
        super().__init__(members)
        self.pro: M = members["pro"]
        self.max: M = members["max"]
        self.flex: M = members["flex"]
        self.klein_4b: M = members["klein_4b"]
        self.klein_9b: M = members["klein_9b"]
        self.klein: M = members["klein"]


class Flux1Namespace(_Namespace[M]):
    """The legacy FLUX.1 generation models."""

    def __init__(self, members: dict[str, M]) -> None:
        super().__init__(members)
        self.pro_1_1: M = members["pro_1_1"]
        self.ultra: M = members["ultra"]
        self.pro: M = members["pro"]
        self.dev: M = members["dev"]


class ToolsNamespace(_Namespace[M]):
    """The FLUX Tools: outpainting, erase, deblur, and virtual try-on."""

    def __init__(self, members: dict[str, M]) -> None:
        super().__init__(members)
        self.outpaint: M = members["outpaint"]
        self.erase: M = members["erase"]
        self.deblur: M = members["deblur"]
        self.vto: M = members["vto"]


class KontextNamespace(_Namespace[M]):
    """The FLUX.1 Kontext reference-guided editing models."""

    def __init__(self, members: dict[str, M]) -> None:
        super().__init__(members)
        self.pro: M = members["pro"]
        self.max: M = members["max"]


# Attribute name each model id is exposed under within its family namespace,
# paired with the namespace class that wraps it.
NAMESPACE_LAYOUT: dict[str, dict[str, str]] = {
    "flux2": {
        "pro": "flux-2-pro",
        "max": "flux-2-max",
        "flex": "flux-2-flex",
        "klein_4b": "flux-2-klein-4b",
        "klein_9b": "flux-2-klein-9b",
        "klein": "flux-2-klein-9b",
    },
    "flux1": {
        "pro_1_1": "flux-pro-1.1",
        "ultra": "flux-pro-1.1-ultra",
        "pro": "flux-pro",
        "dev": "flux-dev",
    },
    "tools": {
        "outpaint": "flux-tools-outpaint",
        "erase": "flux-tools-erase",
        "deblur": "flux-tools-deblur",
        "vto": "flux-tools-vto",
    },
    "kontext": {
        "pro": "flux-kontext-pro",
        "max": "flux-kontext-max",
    },
}

NAMESPACE_CLASSES: dict[str, type[_Namespace]] = {
    "flux2": Flux2Namespace,
    "flux1": Flux1Namespace,
    "tools": ToolsNamespace,
    "kontext": KontextNamespace,
}
