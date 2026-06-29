"""Universal image input handling.

The BFL API accepts a reference image as either a base64-encoded string or a
public ``http(s)`` URL. Developers, though, have images in many shapes: a path
on disk, raw ``bytes``, a Pillow ``Image``, an already-encoded base64 string,
or a URL. :func:`to_image_payload` accepts all of them and returns exactly what
the API expects — so callers never hand-roll ``base64.b64encode`` again.

Pillow is optional: passing a ``PIL.Image.Image`` works only if Pillow is
installed, but every other input type works with the standard library alone.
"""

from __future__ import annotations

import base64
import binascii
import os
from pathlib import Path
from typing import TYPE_CHECKING, Union

from ._exceptions import BFLValidationError

if TYPE_CHECKING:  # pragma: no cover - typing only
    from PIL.Image import Image as PILImage

# What a caller may pass anywhere an image is accepted.
ImageInput = Union[str, Path, bytes, bytearray, "PILImage"]

_URL_PREFIXES = ("http://", "https://")
_DATA_URI_PREFIX = "data:"


def _looks_like_base64(value: str) -> bool:
    """Heuristic: is this string already base64 image data (not a path/URL)?

    A real filesystem path is handled earlier (we try ``Path.exists`` first), so
    by the time we get here the string is either base64 or junk. We rely on a
    strict base64 decode rather than character heuristics — note the base64
    alphabet includes ``/``, so a JPEG (which encodes to ``/9j/...``) must NOT be
    rejected just because it starts with a slash.
    """
    stripped = value.strip()
    if len(stripped) < 16 or "\n" in stripped or "\r" in stripped:
        return False
    try:
        base64.b64decode(stripped, validate=True)
    except (binascii.Error, ValueError):
        return False
    return True


def _encode_bytes(raw: bytes) -> str:
    return base64.b64encode(raw).decode("utf-8")


def _encode_pil(image: PILImage) -> str:
    import io

    buffer = io.BytesIO()
    fmt = image.format or "PNG"
    image.save(buffer, format=fmt)
    return _encode_bytes(buffer.getvalue())


def to_image_payload(value: ImageInput, *, field: str = "image") -> str:
    """Coerce any supported image input into an API-ready string.

    Accepts:
        * ``str`` / ``Path`` pointing at a file on disk -> base64 of its bytes
        * ``str`` that is an ``http(s)`` URL -> returned unchanged (the API
          fetches it server-side)
        * ``str`` that is a ``data:`` URI -> the base64 payload is extracted
        * ``str`` that is already base64 image data -> returned unchanged
        * ``bytes`` / ``bytearray`` -> base64
        * ``PIL.Image.Image`` -> base64 (requires Pillow)

    Args:
        value: The image in any supported form.
        field: Name used in error messages so failures point at the right arg.

    Returns:
        Either a base64-encoded image string or an ``http(s)`` URL.

    Raises:
        BFLValidationError: If the value cannot be interpreted as an image.
    """
    if isinstance(value, (bytes, bytearray)):
        return _encode_bytes(bytes(value))

    if isinstance(value, Path):
        return _path_to_payload(value, field=field)

    if isinstance(value, str):
        if value.startswith(_URL_PREFIXES):
            return value
        if value.startswith(_DATA_URI_PREFIX):
            # data:image/png;base64,XXXX -> XXXX
            _, _, payload = value.partition(",")
            if not payload:
                raise BFLValidationError(f"{field}: malformed data URI")
            return payload
        # Disambiguate path vs raw base64. Prefer an existing file, but a long
        # base64 blob can trip the filesystem (ENAMETOOLONG when a path
        # component exceeds the OS limit) — treat any such error as "not a
        # path" and fall through to the base64 check.
        if len(value) <= 1024:
            try:
                candidate = Path(os.path.expanduser(value))
                if candidate.exists():
                    return _path_to_payload(candidate, field=field)
            except OSError:
                pass
        if _looks_like_base64(value):
            return value
        raise BFLValidationError(
            f"{field}: {value!r} is not an existing file, URL, data URI, or "
            "valid base64 image data."
        )

    # Pillow image (checked last to avoid importing PIL unless needed).
    try:
        from PIL.Image import Image as PILImage
    except ImportError:  # pragma: no cover - exercised only without Pillow
        PILImage = None  # type: ignore[assignment]

    if PILImage is not None and isinstance(value, PILImage):
        return _encode_pil(value)

    raise BFLValidationError(
        f"{field}: unsupported image type {type(value).__name__}. Pass a path, "
        "URL, bytes, base64 string, or PIL.Image."
    )


def _path_to_payload(path: Path, *, field: str) -> str:
    if not path.exists():
        raise BFLValidationError(f"{field}: file does not exist: {path}")
    if not path.is_file():
        raise BFLValidationError(f"{field}: not a file: {path}")
    try:
        return _encode_bytes(path.read_bytes())
    except OSError as exc:
        raise BFLValidationError(f"{field}: could not read {path}: {exc}") from exc
