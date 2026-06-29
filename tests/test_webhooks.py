"""Tests for webhook verification and async client wiring."""

from __future__ import annotations

import pytest

from bfl import WEBHOOK_SECRET_HEADER, verify_webhook
from bfl._exceptions import BFLValidationError


def test_header_constant():
    assert WEBHOOK_SECRET_HEADER == "X-Webhook-Secret"


def test_verify_matching_secret():
    assert verify_webhook("s3cret", "s3cret") is True


def test_verify_mismatched_secret():
    assert verify_webhook("s3cret", "nope") is False


def test_verify_missing_header_returns_false():
    assert verify_webhook("s3cret", None) is False
    assert verify_webhook("s3cret", "") is False


def test_verify_empty_secret_raises():
    with pytest.raises(BFLValidationError):
        verify_webhook("", "anything")


@pytest.mark.asyncio
async def test_async_client_builds_namespaces():
    from bfl import AsyncBFL

    client = AsyncBFL(api_key="bfl_" + "x" * 32)
    assert client.flux2.pro.id == "flux-2-pro"
    assert client.flux1.ultra.id == "flux-pro-1.1-ultra"
    # FLUX Tools namespace exposes the current editing endpoints.
    assert client.tools.outpaint.id == "flux-tools-outpaint"
    assert client.tools.erase.id == "flux-tools-erase"
    assert client.tools.deblur.id == "flux-tools-deblur"
    assert client.tools.vto.id == "flux-tools-vto"
    await client.aclose()
