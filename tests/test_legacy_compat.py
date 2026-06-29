"""Tests that the legacy BFLClient shim still works over the modern stack."""

from __future__ import annotations

import warnings

from bfl import BFLClient
from bfl.types.general.client_config import ClientConfig
from bfl.types.responses.responses import AsyncResponse, SyncResponse
from tests.conftest import FakeTransport


def _legacy_client():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        c = BFLClient(api_key="bfl_" + "x" * 32)
    c._client._transport = FakeTransport()
    c._client._build_namespaces()
    return c


def test_legacy_emits_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        BFLClient(api_key="bfl_" + "x" * 32)
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_legacy_async_generate():
    c = _legacy_client()
    c._client._transport.queue({"id": "abc", "polling_url": "/v1/get_result?id=abc"})
    resp = c.generate("flux-pro-1.1", {"prompt": "a fox"}, ClientConfig(sync=False))
    assert isinstance(resp, AsyncResponse)
    assert resp.id == "abc"
    assert resp.polling_url == "/v1/get_result?id=abc"


def test_legacy_sync_generate():
    c = _legacy_client()
    c._client._transport.queue(
        {"id": "abc", "polling_url": "/v1/get_result?id=abc"},
        {"id": "abc", "status": "Ready", "result": {"sample": "https://img/x.png"}},
    )
    resp = c.generate(
        "flux-pro-1.1",
        {"prompt": "a fox"},
        ClientConfig(sync=True, polling_interval=0.1),
    )
    assert isinstance(resp, SyncResponse)
    assert resp.result.sample == "https://img/x.png"
