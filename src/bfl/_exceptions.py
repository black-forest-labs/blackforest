"""Typed exception hierarchy for the Black Forest Labs SDK.

Every failure mode the API can hand back maps to a precise, catchable type.
Catch :class:`BFLError` to handle everything, or narrow to the case you care
about (auth, rate limit, moderation, ...). All request-level errors carry the
raw status code and parsed response body so nothing is lost.
"""

from __future__ import annotations

from typing import Any


class BFLError(Exception):
    """Base class for every error raised by this SDK.

    Catch this to handle any SDK failure in one place.
    """


class BFLConfigError(BFLError):
    """Client was constructed wrong (e.g. missing API key, bad base URL)."""


class BFLValidationError(BFLError):
    """Inputs failed local validation before a request was ever sent.

    Raised by the typed input models, image loaders, and argument checks so a
    mistake costs you nothing and surfaces at the call site instead of as a
    far-away ``422``.
    """


class BFLAPIError(BFLError):
    """An HTTP request to the API failed.

    Attributes:
        status_code: HTTP status code, when a response was received.
        body: Parsed JSON body (or raw text) returned by the API, if any.
        request_id: The ``x-request-id`` / trace id, when present, for support.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: Any = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.request_id = request_id

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        base = super().__str__()
        bits = []
        if self.status_code is not None:
            bits.append(f"status={self.status_code}")
        if self.request_id:
            bits.append(f"request_id={self.request_id}")
        return f"{base} ({', '.join(bits)})" if bits else base


class BFLAuthError(BFLAPIError):
    """The API key is missing, malformed, or not valid for this deployment.

    Corresponds to ``401``/``403``. A common cause is using a production key
    against a staging/review deployment (or vice versa) — the key is real but
    lives in a different database.
    """


class BFLNotFoundError(BFLAPIError):
    """The requested resource or task does not exist (``404``)."""


class BFLRateLimitError(BFLAPIError):
    """Too many requests (``429``).

    Attributes:
        retry_after: Seconds to wait before retrying, parsed from the
            ``Retry-After`` header when the server provides it.
    """

    def __init__(
        self, *args: Any, retry_after: float | None = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class BFLInsufficientCreditsError(BFLAPIError):
    """The account is out of credits for this request (``402``)."""


class BFLServerError(BFLAPIError):
    """The API returned a ``5xx``. Usually transient; the SDK retries these."""


class BFLConnectionError(BFLError):
    """The request never reached the API (DNS, TCP, TLS, or read timeout)."""


class BFLTaskError(BFLError):
    """A submitted task finished in a non-success terminal state.

    Attributes:
        task_id: The id of the task that failed.
        status: The terminal status reported by the API (e.g. ``"Error"``).
        details: Any structured detail the API attached to the failure.
    """

    def __init__(
        self,
        message: str,
        *,
        task_id: str | None = None,
        status: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.task_id = task_id
        self.status = status
        self.details = details


class BFLContentModerated(BFLTaskError):
    """The request or the generated output was blocked by moderation.

    This is a *terminal* outcome, not an error to retry. ``stage`` tells you
    whether the prompt/inputs were rejected (``"request"``) or the produced
    image was rejected (``"content"``).
    """

    def __init__(self, *args: Any, stage: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.stage = stage


class BFLTimeoutError(BFLTaskError):
    """A task did not reach a terminal state within the allotted wait time."""
