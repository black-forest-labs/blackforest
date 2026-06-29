"""Tests for transport retry logic and error mapping (no real network)."""

from __future__ import annotations

import httpx
import pytest

from bfl._exceptions import (
    BFLAuthError,
    BFLConnectionError,
    BFLInsufficientCreditsError,
    BFLNotFoundError,
    BFLRateLimitError,
    BFLServerError,
)
from bfl._transport import (
    RetryConfig,
    Transport,
    _backoff_seconds,
    _parse_retry_after,
    _should_retry,
    _should_retry_exception,
    map_response_error,
)


def _response(status: int, json=None, headers=None):
    return httpx.Response(status, json=json or {}, headers=headers or {})


def test_map_auth_error():
    err = map_response_error(_response(403, {"detail": "nope"}))
    assert isinstance(err, BFLAuthError)
    assert err.status_code == 403


def test_map_rate_limit_with_retry_after():
    err = map_response_error(
        _response(429, {"detail": "slow down"}, {"retry-after": "2.5"})
    )
    assert isinstance(err, BFLRateLimitError)
    assert err.retry_after == 2.5


def test_map_payment_required():
    assert isinstance(map_response_error(_response(402)), BFLInsufficientCreditsError)


def test_map_not_found():
    assert isinstance(map_response_error(_response(404)), BFLNotFoundError)


def test_map_server_error():
    assert isinstance(map_response_error(_response(503)), BFLServerError)


def test_parse_retry_after_invalid():
    assert _parse_retry_after({"retry-after": "soon"}) is None
    assert _parse_retry_after({}) is None


def test_backoff_respects_retry_after():
    cfg = RetryConfig(max_backoff=30)
    assert _backoff_seconds(1, cfg, retry_after=5.0) == 5.0
    # capped at max_backoff
    assert _backoff_seconds(1, cfg, retry_after=100.0) == 30.0


def test_backoff_jitter_bounded():
    cfg = RetryConfig(backoff_factor=1.0, max_backoff=8)
    for attempt in range(1, 5):
        val = _backoff_seconds(attempt, cfg, retry_after=None)
        assert 0 <= val <= 8


class _MockHTTPClient:
    """Minimal httpx.Client stand-in that yields scripted responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = 0

    def request(self, method, url, **kwargs):
        self.requests += 1
        nxt = self._responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    def close(self):
        pass


def _transport_with(responses, max_retries=3):
    t = Transport(
        "bfl_" + "x" * 32, retry=RetryConfig(max_retries=max_retries, backoff_factor=0)
    )
    t._client = _MockHTTPClient(responses)
    return t


def test_transport_retries_500_then_succeeds():
    t = _transport_with([_response(500), _response(200, {"ok": True})])
    assert t.request("GET", "/v1/credits") == {"ok": True}
    assert t._client.requests == 2


def test_transport_gives_up_after_retries():
    t = _transport_with([_response(500)] * 10, max_retries=2)
    with pytest.raises(BFLServerError):
        t.request("GET", "/v1/credits")
    assert t._client.requests == 3  # 1 + 2 retries


def test_transport_does_not_retry_4xx():
    t = _transport_with([_response(403)])
    with pytest.raises(BFLAuthError):
        t.request("GET", "/v1/credits")
    assert t._client.requests == 1


def test_transport_retries_connection_error():
    t = _transport_with([httpx.ConnectError("boom"), _response(200, {"ok": 1})])
    assert t.request("GET", "/v1/credits") == {"ok": 1}


def test_transport_connection_error_exhausted():
    t = _transport_with([httpx.ConnectError("boom")] * 5, max_retries=1)
    with pytest.raises(BFLConnectionError):
        t.request("GET", "/v1/credits")


# --- idempotency-aware retry (the double-charge guard) -----------------------


def test_should_retry_429_for_any_method():
    assert _should_retry("POST", 429) is True
    assert _should_retry("GET", 429) is True


def test_should_retry_5xx_only_for_idempotent_methods():
    assert _should_retry("GET", 503) is True
    assert _should_retry("HEAD", 500) is True
    # POST submits must NOT be replayed on a server error — risks double-charge.
    assert _should_retry("POST", 503) is False
    assert _should_retry("POST", 500) is False


def test_should_not_retry_4xx():
    assert _should_retry("GET", 404) is False
    assert _should_retry("POST", 400) is False


def test_post_5xx_is_not_retried_end_to_end():
    """A 5xx on a POST submit surfaces immediately, never resubmitted."""
    t = _transport_with([_response(503), _response(200, {"id": "should-not-reach"})])
    with pytest.raises(BFLServerError):
        t.request("POST", "/v1/flux-2-pro", json={"prompt": "x"})
    assert t._client.requests == 1  # no second submit


def test_post_429_is_retried():
    """Rate limiting is safe to replay even for POST."""
    t = _transport_with([_response(429), _response(200, {"id": "ok"})])
    assert t.request("POST", "/v1/flux-2-pro", json={"prompt": "x"}) == {"id": "ok"}
    assert t._client.requests == 2


def test_post_connection_error_is_retried():
    """A pre-response connection failure never reached the server, so replay."""
    t = _transport_with([httpx.ConnectError("boom"), _response(200, {"id": "ok"})])
    assert t.request("POST", "/v1/flux-2-pro", json={"prompt": "x"}) == {"id": "ok"}


def test_post_read_timeout_is_not_retried():
    """A read timeout can fire AFTER the server accepted+billed a POST submit.

    Replaying would double-charge, so it must surface, not retry.
    """
    t = _transport_with(
        [httpx.ReadTimeout("slow"), _response(200, {"id": "should-not-reach"})]
    )
    with pytest.raises(BFLConnectionError):
        t.request("POST", "/v1/flux-2-pro", json={"prompt": "x"})
    assert t._client.requests == 1  # no replay


def test_get_read_timeout_is_retried():
    """A read timeout on an idempotent GET is safe to replay."""
    t = _transport_with([httpx.ReadTimeout("slow"), _response(200, {"ok": 1})])
    assert t.request("GET", "/v1/credits") == {"ok": 1}


def test_should_retry_exception_idempotency():
    assert _should_retry_exception("GET", httpx.ReadTimeout("x")) is True
    assert _should_retry_exception("POST", httpx.ReadTimeout("x")) is False
    assert _should_retry_exception("POST", httpx.ConnectError("x")) is True
    assert _should_retry_exception("POST", httpx.ConnectTimeout("x")) is True
    assert _should_retry_exception("POST", httpx.PoolTimeout("x")) is True


# --- Retry-After parsing -----------------------------------------------------


def test_retry_after_http_date():
    import datetime as dt
    from email.utils import format_datetime

    future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=30)
    delay = _parse_retry_after({"retry-after": format_datetime(future)})
    assert delay is not None
    assert 20 <= delay <= 31  # ~30s, allowing for clock/parsing slack


def test_retry_after_past_date_clamped_to_zero():
    delay = _parse_retry_after({"retry-after": "Wed, 21 Oct 2015 07:28:00 GMT"})
    assert delay == 0.0
