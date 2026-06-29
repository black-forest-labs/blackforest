"""Tests for image input coercion (bfl._images)."""

from __future__ import annotations

import base64

import pytest

from bfl._exceptions import BFLValidationError
from bfl._images import to_image_payload


def test_url_passthrough():
    url = "https://example.com/cat.png"
    assert to_image_payload(url) == url


def test_data_uri_extracts_payload():
    raw = base64.b64encode(b"hello-world-image-bytes").decode()
    assert to_image_payload(f"data:image/png;base64,{raw}") == raw


def test_bytes_encoded():
    assert to_image_payload(b"\x89PNG\r\n") == base64.b64encode(b"\x89PNG\r\n").decode()


def test_bytearray_encoded():
    data = bytearray(b"abc123")
    assert to_image_payload(data) == base64.b64encode(b"abc123").decode()


def test_path_read_and_encoded(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"PNGDATA")
    assert to_image_payload(f) == base64.b64encode(b"PNGDATA").decode()


def test_str_path_read_and_encoded(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"PNGDATA")
    assert to_image_payload(str(f)) == base64.b64encode(b"PNGDATA").decode()


def test_long_base64_passthrough():
    raw = base64.b64encode(b"x" * 200).decode()
    assert to_image_payload(raw) == raw


def test_base64_jpeg_passthrough():
    """A base64 JPEG starts with '/9j/' — the '/' must not get it rejected."""
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 256  # JFIF magic + padding
    raw = base64.b64encode(jpeg_bytes).decode()
    assert raw.startswith("/9j/")
    assert to_image_payload(raw) == raw


def test_missing_file_raises():
    with pytest.raises(BFLValidationError):
        to_image_payload("/nope/does/not/exist.png", field="input_image")


def test_unsupported_type_raises():
    with pytest.raises(BFLValidationError):
        to_image_payload(12345)  # type: ignore[arg-type]


def test_malformed_data_uri_raises():
    with pytest.raises(BFLValidationError):
        to_image_payload("data:image/png;base64,")
