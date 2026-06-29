"""Task lifecycle: :class:`Job` (a submitted task) and :class:`Result` (its output).

``submit`` returns a :class:`Job` immediately. Call :meth:`Job.wait` to block
until the task reaches a terminal state — ``Ready`` yields a :class:`Result`,
while moderation/error states raise the matching typed exception *right away*
instead of polling uselessly to the retry ceiling (the bug in the old client).

A :class:`Result` is the payload you actually want: ``.url`` is the signed
image link, ``.bytes`` downloads it, ``.image`` opens it as a Pillow image, and
``.save(path)`` writes it to disk in one call.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from ._exceptions import (
    BFLConnectionError,
    BFLContentModerated,
    BFLError,
    BFLTaskError,
    BFLTimeoutError,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from PIL.Image import Image as PILImage

    from ._transport import AsyncTransport, Transport

# Terminal task states reported by GET /v1/get_result (StatusResponse enum).
_READY = "Ready"
_PENDING = "Pending"
_TERMINAL_OK = {_READY}
_TERMINAL_MODERATED = {"Content Moderated": "content", "Request Moderated": "request"}
_TERMINAL_ERROR = {"Error", "Task not found"}
# The only status that means "not finished yet". Anything else unrecognized is
# surfaced rather than polled forever.
_IN_PROGRESS = {_PENDING}


def _interpret(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Inspect a poll response. Returns ``(is_ready, payload)`` or raises.

    ``Ready`` returns ``(True, payload)``. ``Pending`` returns ``(False,
    payload)`` so the caller keeps polling. Moderation and error states raise
    the matching typed exception immediately. Any *unrecognized* status is
    treated as a failure and raised — never polled to the timeout — so a new or
    malformed status surfaces loudly instead of hanging.
    """
    status = payload.get("status")
    task_id = payload.get("id")

    if status in _TERMINAL_OK:
        return True, payload
    if status in _IN_PROGRESS:
        return False, payload
    if status in _TERMINAL_MODERATED:
        raise BFLContentModerated(
            f"Task {task_id} was blocked by moderation ({status}).",
            task_id=task_id,
            status=status,
            stage=_TERMINAL_MODERATED[status],
            details=payload.get("details"),
        )
    if status in _TERMINAL_ERROR:
        raise BFLTaskError(
            f"Task {task_id} failed with status {status!r}.",
            task_id=task_id,
            status=status,
            details=payload.get("details"),
        )
    # Unknown / missing status: do not poll forever — surface it.
    raise BFLTaskError(
        f"Task {task_id} returned an unrecognized status {status!r}. "
        "This may indicate an API change; inspect `.details` and the raw payload.",
        task_id=task_id,
        status=status,
        details=payload.get("details") or payload,
    )


@dataclass
class Result:
    """The output of a completed generation task.

    Use the sync accessors (:meth:`save`, :meth:`bytes`, :attr:`image`) from
    sync code, and the async ones (:meth:`asave`, :meth:`abytes`) from async
    code. A result produced by :class:`AsyncJob` refuses the blocking sync
    accessors so you can't accidentally stall the event loop.
    """

    id: str
    raw: dict[str, Any]
    _async: bool = False

    def _forbid_sync(self, method: str, alt: str) -> None:
        if self._async:
            raise BFLError(
                f"{method} runs blocking I/O and this result came from an async "
                f"client — it would stall the event loop. Use `await result.{alt}` "
                "instead."
            )

    @property
    def url(self) -> str:
        """Signed URL to the generated image (typically valid ~10 minutes)."""
        sample = self.raw.get("sample")
        if not sample:
            raise BFLError(
                f"Result {self.id} has no image URL in payload {self.raw!r}."
            )
        return sample

    @property
    def seed(self) -> int | None:
        """Seed used for the generation, when the API reports it."""
        return self.raw.get("seed")

    @property
    def prompt(self) -> str | None:
        """Prompt used for the generation, when the API reports it."""
        return self.raw.get("prompt")

    def bytes(self) -> bytes:
        """Download the generated image and return its raw bytes (sync)."""
        self._forbid_sync(".bytes()", "abytes()")
        import httpx

        try:
            resp = httpx.get(self.url, follow_redirects=True, timeout=120.0)
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPStatusError as exc:
            raise BFLConnectionError(
                f"Failed to download result image ({exc.response.status_code}) "
                f"from {self.url}: the signed URL may have expired (they last "
                "~10 minutes)."
            ) from exc
        except httpx.HTTPError as exc:
            raise BFLConnectionError(
                f"Failed to download result image from {self.url}: {exc}"
            ) from exc

    async def abytes(self) -> bytes:
        """Download the generated image and return its raw bytes (async)."""
        import httpx

        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=120.0
            ) as client:
                resp = await client.get(self.url)
                resp.raise_for_status()
                return resp.content
        except httpx.HTTPStatusError as exc:
            raise BFLConnectionError(
                f"Failed to download result image ({exc.response.status_code}) "
                f"from {self.url}: the signed URL may have expired (they last "
                "~10 minutes)."
            ) from exc
        except httpx.HTTPError as exc:
            raise BFLConnectionError(
                f"Failed to download result image from {self.url}: {exc}"
            ) from exc

    @property
    def image(self) -> "PILImage":
        """Open the generated image as a Pillow ``Image`` (requires Pillow)."""
        self._forbid_sync(".image", "abytes() then PIL.Image.open(io.BytesIO(...))")
        try:
            import io

            from PIL import Image
        except ImportError as exc:  # pragma: no cover - depends on env
            raise BFLError(
                "Pillow is required for .image. Install with `pip install "
                "'black-forest-labs[images]'`."
            ) from exc
        return Image.open(io.BytesIO(self.bytes()))

    def save(self, path: str | Path) -> Path:
        """Download and write the image to ``path``. Returns the path written."""
        self._forbid_sync(".save()", "asave(path)")
        destination = Path(path)
        if destination.parent and not destination.parent.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.bytes())
        return destination

    async def asave(self, path: str | Path) -> Path:
        """Async variant of :meth:`save`. Runs disk I/O off the event loop."""
        import asyncio

        data = await self.abytes()
        destination = Path(path)

        def _write() -> None:
            if destination.parent and not destination.parent.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)

        await asyncio.to_thread(_write)
        return destination


ProgressCallback = Callable[[dict[str, Any]], None]


class _BaseJob:
    """Shared state for sync and async jobs."""

    def __init__(
        self,
        *,
        id: str,
        polling_url: str,
        cost: float | None = None,
        raw: dict[str, Any] | None = None,
    ) -> None:
        self.id = id
        self.polling_url = polling_url
        self.cost = cost
        self.raw_submit = raw or {}

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} id={self.id!r} cost={self.cost}>"


class Job(_BaseJob):
    """A submitted task you can poll for its result (synchronous)."""

    def __init__(self, *, transport: "Transport", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._transport = transport

    def status(self) -> dict[str, Any]:
        """Fetch the current raw status payload without blocking."""
        return self._transport.request("GET", self.polling_url)

    def wait(
        self,
        *,
        timeout: float | None = 300.0,
        poll_interval: float = 1.0,
        on_progress: ProgressCallback | None = None,
    ) -> Result:
        """Block until the task is ``Ready`` and return its :class:`Result`.

        Args:
            timeout: Max seconds to wait. ``None`` waits indefinitely.
            poll_interval: Seconds between polls.
            on_progress: Optional callback invoked with each raw poll payload
                (carries ``status`` and a ``progress`` float when available).

        Raises:
            BFLContentModerated / BFLTaskError: On a terminal failure state.
            BFLTimeoutError: If ``timeout`` elapses before completion.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            payload = self._transport.request("GET", self.polling_url)
            if on_progress is not None:
                on_progress(payload)
            ready, data = _interpret(payload)
            if ready:
                return Result(id=self.id, raw=data.get("result") or {})
            if deadline is not None and time.monotonic() >= deadline:
                raise BFLTimeoutError(
                    f"Task {self.id} did not finish within {timeout}s "
                    f"(last status: {payload.get('status')!r}).",
                    task_id=self.id,
                    status=payload.get("status"),
                )
            time.sleep(poll_interval)


class AsyncJob(_BaseJob):
    """A submitted task you can poll for its result (asynchronous)."""

    def __init__(self, *, transport: "AsyncTransport", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._transport = transport

    async def status(self) -> dict[str, Any]:
        """Fetch the current raw status payload without blocking."""
        return await self._transport.request("GET", self.polling_url)

    async def wait(
        self,
        *,
        timeout: float | None = 300.0,
        poll_interval: float = 1.0,
        on_progress: ProgressCallback | None = None,
    ) -> Result:
        """Async variant of :meth:`Job.wait`."""
        import asyncio

        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            payload = await self._transport.request("GET", self.polling_url)
            if on_progress is not None:
                on_progress(payload)
            ready, data = _interpret(payload)
            if ready:
                return Result(id=self.id, raw=data.get("result") or {}, _async=True)
            if deadline is not None and time.monotonic() >= deadline:
                raise BFLTimeoutError(
                    f"Task {self.id} did not finish within {timeout}s "
                    f"(last status: {payload.get('status')!r}).",
                    task_id=self.id,
                    status=payload.get("status"),
                )
            await asyncio.sleep(poll_interval)
