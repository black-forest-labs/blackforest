"""Shared pytest fixtures and a fake transport for offline tests.

Nothing here touches the network. :class:`FakeTransport` records the requests a
client makes and returns scripted responses, so the full submit/poll/result
lifecycle can be exercised deterministically.
"""

from __future__ import annotations

from typing import Any

import pytest

from bfl._client import BFL


class FakeTransport:
    """A stand-in for the HTTP transport that returns scripted responses."""

    def __init__(self, responses: list[Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses = list(responses or [])

    def queue(self, *responses: Any) -> "FakeTransport":
        self._responses.extend(responses)
        return self

    def request(
        self, method: str, url: str, *, json: Any = None, params: Any = None
    ) -> Any:
        self.calls.append(
            {"method": method, "url": url, "json": json, "params": params}
        )
        if not self._responses:
            raise AssertionError(f"No scripted response for {method} {url}")
        nxt = self._responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    def close(self) -> None:  # pragma: no cover - trivial
        pass


@pytest.fixture
def fake_transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def client(fake_transport: FakeTransport) -> BFL:
    """A BFL client whose transport is the fake (no network)."""
    c = BFL(api_key="bfl_" + "x" * 32)
    c._transport = fake_transport
    c._build_namespaces()
    return c
