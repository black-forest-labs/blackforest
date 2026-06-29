"""Tests for the A+ hardening pass: async parity, input validation, error
wrapping, retry-config validation, and response-protocol errors.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from bfl import AsyncBFL
from bfl._catalog import resolve
from bfl._client import _require
from bfl._exceptions import BFLConnectionError, BFLError, BFLValidationError
from bfl._jobs import Result
from bfl._requests import build_payload
from bfl._transport import RetryConfig


class FakeAsyncTransport:
    """Async stand-in mirroring conftest.FakeTransport."""

    def __init__(self, responses: list | None = None) -> None:
        self.calls: list[dict] = []
        self._responses = list(responses or [])

    def queue(self, *responses) -> "FakeAsyncTransport":
        self._responses.extend(responses)
        return self

    async def request(self, method, url, *, json=None, params=None):
        self.calls.append({"method": method, "url": url, "json": json})
        if not self._responses:
            raise AssertionError(f"No scripted response for {method} {url}")
        nxt = self._responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    async def aclose(self) -> None:  # pragma: no cover - trivial
        pass


def _async_client() -> AsyncBFL:
    c = AsyncBFL(api_key="bfl_" + "x" * 32)
    c._transport = FakeAsyncTransport()
    c._build_namespaces()
    return c


# --- Async lifecycle parity -------------------------------------------------


@pytest.mark.asyncio
async def test_async_submit_returns_job_with_id():
    c = _async_client()
    c._transport.queue({"id": "task-123", "polling_url": "/v1/get_result?id=task-123"})
    job = await c.flux2.pro.submit("a fox")
    assert job.id == "task-123"
    assert c._transport.calls[0]["method"] == "POST"
    await c.aclose()


@pytest.mark.asyncio
async def test_async_generate_polls_to_ready():
    c = _async_client()
    c._transport.queue(
        {"id": "t1", "polling_url": "/v1/get_result?id=t1"},
        {"id": "t1", "status": "Pending"},
        {"id": "t1", "status": "Ready", "result": {"sample": "https://d/x.png"}},
    )
    result = await c.flux2.pro.generate("a fox", poll_interval=0.0)
    assert isinstance(result, Result)
    assert result.url == "https://d/x.png"
    await c.aclose()


@pytest.mark.asyncio
async def test_async_result_blocks_sync_accessors():
    """A result from the async client must refuse blocking sync I/O."""
    c = _async_client()
    c._transport.queue(
        {"id": "t1", "polling_url": "/v1/get_result?id=t1"},
        {"id": "t1", "status": "Ready", "result": {"sample": "https://d/x.png"}},
    )
    result = await c.flux2.pro.generate("a fox", poll_interval=0.0)
    with pytest.raises(BFLError):
        result.bytes()
    await c.aclose()


# --- Input validation -------------------------------------------------------


def test_text_only_model_rejects_images():
    spec = resolve("flux-pro-1.1")
    with pytest.raises(BFLValidationError):
        build_payload(spec, {"prompt": "x", "input_image": "https://e/a.png"})


def test_legacy_model_rejects_unknown_kwarg():
    spec = resolve("flux-pro-1.1")
    with pytest.raises(BFLValidationError):
        build_payload(spec, {"prompt": "x", "definitely_not_a_field": 1})


def test_kontext_accepts_its_input_images():
    spec = resolve("flux-kontext-pro")
    payload = build_payload(spec, {"prompt": "x", "input_image": "https://e/a.png"})
    assert payload["input_image"] == "https://e/a.png"


# --- RetryConfig validation -------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_retries": -1},
        {"backoff_factor": -0.5},
        {"max_backoff": -1.0},
    ],
)
def test_retry_config_rejects_negative(kwargs):
    with pytest.raises(ValueError):
        RetryConfig(**kwargs)


def test_retry_config_accepts_valid():
    rc = RetryConfig(max_retries=0, backoff_factor=0.0, max_backoff=0.0)
    assert rc.max_retries == 0


# --- Response protocol errors -----------------------------------------------


def test_require_raises_on_missing_key():
    with pytest.raises(BFLError):
        _require({"unexpected": 1}, "id", "submit")


def test_require_raises_on_non_dict():
    with pytest.raises(BFLError):
        _require("not a dict", "id", "submit")


def test_require_returns_value():
    assert _require({"id": "abc"}, "id", "submit") == "abc"


# --- Download error wrapping ------------------------------------------------


def test_result_bytes_wraps_http_errors(monkeypatch):
    result = Result(id="t1", raw={"sample": "https://d/expired.png"})

    def boom(*args, **kwargs):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "get", boom)
    with pytest.raises(BFLConnectionError):
        result.bytes()


def test_result_abytes_wraps_http_errors(monkeypatch):
    result = Result(id="t1", raw={"sample": "https://d/expired.png"}, _async=True)

    class BoomClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: BoomClient())

    async def run():
        with pytest.raises(BFLConnectionError):
            await result.abytes()

    asyncio.run(run())
