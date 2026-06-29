"""HTTP transport: connection management, retries, and error mapping.

Two thin wrappers around ``httpx`` — :class:`Transport` (sync) and
:class:`AsyncTransport` (async) — share one set of pure helpers for deciding
*whether* to retry, *how long* to back off, and *which* typed exception a
failed response maps to. Keeping that logic in module-level functions means the
sync and async paths can never drift apart.

Retries cover the genuinely transient cases with exponential backoff, full
jitter, and respect for a server-sent ``Retry-After``. Retry safety is
idempotency-aware so a paid, non-idempotent ``POST`` submission is never
silently sent twice:

* ``429`` (rate limited) is always retryable — the request was rejected, not
  processed, so replaying it cannot double-charge.
* ``5xx`` is retried only for idempotent methods (``GET``/``HEAD``). A ``5xx``
  on a ``POST`` submit might mean the server already created (and billed) the
  job before the response was lost, so we surface it instead of resubmitting.
* Connection/timeout errors raised *before* a response are retried for
  idempotent methods (``GET``/``HEAD``); for a ``POST`` only the failures that
  prove the request never left the client (connect/pool errors) are retried,
  while a read/write timeout — where the submit may already have reached the
  server — is surfaced rather than replayed.

``4xx`` client errors (other than ``429``) are never retried; they map straight
to a precise exception.
"""

from __future__ import annotations

import random
import time
from typing import Any, Mapping

import httpx

from ._exceptions import (
    BFLAPIError,
    BFLAuthError,
    BFLConnectionError,
    BFLInsufficientCreditsError,
    BFLNotFoundError,
    BFLRateLimitError,
    BFLServerError,
)
from ._version import __version__

DEFAULT_BASE_URL = "https://api.bfl.ai"
_USER_AGENT = f"bfl-python/{__version__}"
# 429 is safe to retry for any method (request was rejected, not executed).
_ALWAYS_RETRY_STATUSES = frozenset({429})
# 5xx is only safe to retry when the method is idempotent (see _should_retry).
_SERVER_ERROR_STATUSES = frozenset({500, 502, 503, 504})
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_REQUEST_ID_HEADERS = ("x-request-id", "x-trace-id", "cf-ray")


class RetryConfig:
    """How the transport retries transient failures.

    Args:
        max_retries: Maximum number of *additional* attempts after the first.
            ``0`` disables retries.
        backoff_factor: Base for exponential backoff; sleep is
            ``backoff_factor * 2**(attempt-1)`` seconds, plus jitter.
        max_backoff: Upper bound on any single backoff sleep, in seconds.
        respect_retry_after: When ``True``, a server ``Retry-After`` header
            overrides the computed backoff.
    """

    __slots__ = ("max_retries", "backoff_factor", "max_backoff", "respect_retry_after")

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        max_backoff: float = 30.0,
        respect_retry_after: bool = True,
    ) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}.")
        if backoff_factor < 0:
            raise ValueError(f"backoff_factor must be >= 0, got {backoff_factor}.")
        if max_backoff < 0:
            raise ValueError(f"max_backoff must be >= 0, got {max_backoff}.")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.respect_retry_after = respect_retry_after


def _parse_retry_after(headers: Mapping[str, str]) -> float | None:
    """Return the ``Retry-After`` delay in seconds, if the header is present.

    Handles both forms the HTTP spec allows: a number of seconds
    (``Retry-After: 5``) and an HTTP-date (``Retry-After: Wed, 21 Oct 2026
    07:28:00 GMT``), which is converted to a delay relative to now.
    """
    value = headers.get("retry-after")
    if not value:
        return None
    value = value.strip()
    try:
        return float(value)
    except ValueError:
        pass
    # HTTP-date form: compute seconds until that instant.
    try:
        from email.utils import parsedate_to_datetime

        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    import datetime as _dt

    now = _dt.datetime.now(when.tzinfo or _dt.timezone.utc)
    delay = (when - now).total_seconds()
    return max(delay, 0.0)


def _request_id(headers: Mapping[str, str]) -> str | None:
    for name in _REQUEST_ID_HEADERS:
        if name in headers:
            return headers[name]
    return None


def _backoff_seconds(
    attempt: int, config: RetryConfig, retry_after: float | None
) -> float:
    """Compute how long to sleep before ``attempt`` (1-indexed)."""
    if retry_after is not None and config.respect_retry_after:
        return min(retry_after, config.max_backoff)
    raw = config.backoff_factor * (2 ** (attempt - 1))
    capped = min(raw, config.max_backoff)
    # Full jitter avoids thundering-herd retries across many clients.
    return random.uniform(0, capped)


def _extract_body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text or None


def _error_message(body: Any, default: str) -> str:
    if isinstance(body, dict):
        for key in ("detail", "message", "error"):
            val = body.get(key)
            if isinstance(val, str) and val:
                return val
            if val:  # e.g. a list of pydantic errors
                return str(val)
    return default


def map_response_error(response: httpx.Response) -> BFLAPIError:
    """Translate a non-2xx response into the right typed exception."""
    status = response.status_code
    body = _extract_body(response)
    request_id = _request_id(response.headers)
    message = _error_message(body, f"API request failed with status {status}")
    common = {"status_code": status, "body": body, "request_id": request_id}

    if status in (401, 403):
        return BFLAuthError(message, **common)
    if status == 402:
        return BFLInsufficientCreditsError(message, **common)
    if status == 404:
        return BFLNotFoundError(message, **common)
    if status == 429:
        return BFLRateLimitError(
            message, retry_after=_parse_retry_after(response.headers), **common
        )
    if status >= 500:
        return BFLServerError(message, **common)
    return BFLAPIError(message, **common)


def _should_retry(method: str, status: int) -> bool:
    """Whether a response with ``status`` to ``method`` is safe to retry.

    ``429`` is always retryable. ``5xx`` is retryable only for idempotent
    methods — replaying a ``POST`` submit after a server error risks creating
    (and billing) a second generation.
    """
    if status in _ALWAYS_RETRY_STATUSES:
        return True
    if status in _SERVER_ERROR_STATUSES:
        return method.upper() in _IDEMPOTENT_METHODS
    return False


def _should_retry_exception(method: str, exc: Exception) -> bool:
    """Whether a transport exception (no response received) is safe to retry.

    Idempotent methods retry any connection/timeout error. A non-idempotent
    method (``POST`` submit) retries ONLY when the failure proves the request
    never reached the server — a connect/pool failure. A read/write timeout or
    read error can fire *after* the server accepted (and billed) the job, so we
    must not replay it: that would double-charge.
    """
    if method.upper() in _IDEMPOTENT_METHODS:
        return True
    return isinstance(
        exc,
        (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout),
    )


def build_headers(
    api_key: str, extra: Mapping[str, str] | None = None
) -> dict[str, str]:
    headers = {
        "x-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": _USER_AGENT,
    }
    if extra:
        headers.update(extra)
    return headers


class Transport:
    """Synchronous HTTP transport with retries and typed errors."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        retry: RetryConfig | None = None,
        client: httpx.Client | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._retry = retry or RetryConfig()
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout,
            headers=build_headers(api_key, default_headers),
            follow_redirects=True,
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        """Send a request, retrying transient failures. Returns parsed JSON."""
        target = (
            url if url.startswith(("http://", "https://")) else f"{self._base_url}{url}"
        )
        attempt = 0
        while True:
            try:
                response = self._client.request(
                    method, target, json=json, params=params
                )
            except httpx.RequestError as exc:
                if _should_retry_exception(method, exc) and (
                    attempt < self._retry.max_retries
                ):
                    attempt += 1
                    time.sleep(_backoff_seconds(attempt, self._retry, None))
                    continue
                raise BFLConnectionError(f"Could not reach BFL API: {exc}") from exc

            if response.is_success:
                return _extract_body(response)

            if (
                _should_retry(method, response.status_code)
                and attempt < self._retry.max_retries
            ):
                attempt += 1
                retry_after = _parse_retry_after(response.headers)
                time.sleep(_backoff_seconds(attempt, self._retry, retry_after))
                continue

            raise map_response_error(response)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "Transport":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncTransport:
    """Asynchronous HTTP transport with retries and typed errors."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        retry: RetryConfig | None = None,
        client: httpx.AsyncClient | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._retry = retry or RetryConfig()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout,
            headers=build_headers(api_key, default_headers),
            follow_redirects=True,
        )

    async def request(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        import asyncio

        target = (
            url if url.startswith(("http://", "https://")) else f"{self._base_url}{url}"
        )
        attempt = 0
        while True:
            try:
                response = await self._client.request(
                    method, target, json=json, params=params
                )
            except httpx.RequestError as exc:
                if _should_retry_exception(method, exc) and (
                    attempt < self._retry.max_retries
                ):
                    attempt += 1
                    await asyncio.sleep(_backoff_seconds(attempt, self._retry, None))
                    continue
                raise BFLConnectionError(f"Could not reach BFL API: {exc}") from exc

            if response.is_success:
                return _extract_body(response)

            if (
                _should_retry(method, response.status_code)
                and attempt < self._retry.max_retries
            ):
                attempt += 1
                retry_after = _parse_retry_after(response.headers)
                await asyncio.sleep(_backoff_seconds(attempt, self._retry, retry_after))
                continue

            raise map_response_error(response)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncTransport":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
