"""Typed keyword-argument specs for the generation methods.

``submit`` / ``generate`` accept model parameters as keyword arguments. To give
editors real autocomplete and let type checkers catch typos — instead of an
opaque ``**params: Any`` — those keywords are described here as a
:class:`~typing.TypedDict` and surfaced via :data:`typing.Unpack` on the method
signatures.

This is intentionally a single ``total=False`` union of every parameter the
generation models accept, rather than one TypedDict per model. It gives the
full vocabulary to autocomplete everywhere while staying lean (no per-model
accessor subclasses); the per-model *runtime* contract is still enforced by the
pydantic models in :mod:`bfl._models` and the legacy input models, all of which
now forbid unknown fields. So a wrong combination (e.g. ``guidance`` on a model
that doesn't support it) is reported as a clear ``BFLValidationError`` at call
time.
"""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):  # pragma: no cover - version branch
    from typing import TypedDict
else:  # pragma: no cover - version branch
    from typing_extensions import TypedDict


class GenerateParams(TypedDict, total=False):
    """Keyword parameters accepted across the generation models.

    Not every field applies to every model; the model's own schema validates
    the combination at submit time. ``total=False`` means all are optional.
    """

    # Common across FLUX.2 / FLUX.1 / Kontext generation.
    width: int
    height: int
    seed: int
    output_format: str
    safety_tolerance: int
    prompt_upsampling: bool

    # FLUX.2 [flex] only.
    guidance: float
    steps: int

    # FLUX.2 transparency (png/webp only).
    transparent_bg: bool

    # Kontext aspect-ratio control.
    aspect_ratio: str

    # Reference images for editing models, when passed by explicit slot rather
    # than the ``images=[...]`` convenience list.
    input_image: str
    input_image_2: str
    input_image_3: str
    input_image_4: str
    input_image_5: str
    input_image_6: str
    input_image_7: str
    input_image_8: str

    # FLUX Tools (client.tools.*) — endpoint-specific image and control fields.
    image: str  # erase / deblur source
    mask: str  # erase mask
    dilate_pixels: int  # erase
    person: str  # virtual try-on
    garment: str  # virtual try-on
    reference_offset_x: int  # outpaint
    reference_offset_y: int  # outpaint
    auto_crop: bool  # outpaint
    mode: str  # outpaint: "high" | "fast"

    # Async delivery (accepted by every generation model except outpainting).
    webhook_url: str
    webhook_secret: str
