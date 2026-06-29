"""Typed request models for the FLUX.2 family.

These mirror the real public API contract (read from the generation service):
output dimensions go up to 4 megapixels with no multiple-of-32 constraint, and
``transparent_bg`` requires a PNG/WebP container. Validation runs locally so a
bad argument fails at the call site — instantly and for free — instead of as a
``422`` after a round trip.

The legacy FLUX.1 / tools / Kontext models live under ``types/inputs`` and are
reused as-is; only the FLUX.2 surface is defined here.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

_MAX_PIXELS = 2048 * 2048  # 4 MP, the FLUX.2 output ceiling.


class OutputFormat(str, Enum):
    """Container for the returned image."""

    jpeg = "jpeg"
    png = "png"
    webp = "webp"


class Flux2Params(BaseModel):
    """Shared parameters for FLUX.2 [pro] and [max].

    Image inputs are accepted by the resource methods in any form (path, URL,
    bytes, PIL, base64) and are encoded before they reach this model, so the
    ``input_image*`` fields here are always strings.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    prompt: str = Field(description="Text prompt describing the image to generate.")
    input_image: str | None = Field(
        default=None,
        description="Primary reference image (base64 or URL) for editing.",
    )
    input_image_2: str | None = None
    input_image_3: str | None = None
    input_image_4: str | None = None
    input_image_5: str | None = None
    input_image_6: str | None = None
    input_image_7: str | None = None
    input_image_8: str | None = None
    seed: int | None = Field(default=None, description="Seed for reproducible output.")
    width: int | None = Field(
        default=None,
        ge=64,
        description="Output width in pixels. Omit to let the model choose.",
    )
    height: int | None = Field(
        default=None,
        ge=64,
        description="Output height in pixels. Omit to let the model choose.",
    )
    safety_tolerance: int = Field(
        default=2,
        ge=0,
        le=7,
        description=(
            "Moderation strictness, 0 (strictest) to 5 (most lenient) for public "
            "use. Values 6-7 require an allowlisted organization."
        ),
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.jpeg,
        description="Image container: jpeg, png, or webp.",
    )
    prompt_upsampling: bool | None = Field(
        default=None,
        description=(
            "Expand the prompt for more creative results. Leave unset to use "
            "the model's default. (Sent to the API as the appropriate per-model "
            "field; FLUX.2 [klein] has no upsampling control.)"
        ),
    )
    transparent_bg: bool = Field(
        default=False,
        description=(
            "Return a transparent background (RGBA). Requires png or webp output."
        ),
    )
    webhook_url: str | None = Field(
        default=None, description="URL to receive a completion webhook."
    )
    webhook_secret: str | None = Field(
        default=None,
        description=(
            "Secret echoed back verbatim in the X-Webhook-Secret header so you "
            "can verify the callback came from BFL."
        ),
    )

    @model_validator(mode="after")
    def _check_dimensions(self) -> "Flux2Params":
        if self.width and self.height and self.width * self.height > _MAX_PIXELS:
            raise ValueError(
                f"width*height ({self.width * self.height}) exceeds the 4MP limit "
                f"({_MAX_PIXELS}). Reduce the dimensions."
            )
        return self

    @model_validator(mode="after")
    def _check_transparency(self) -> "Flux2Params":
        if self.transparent_bg and self.output_format not in (
            OutputFormat.png.value,
            OutputFormat.webp.value,
            OutputFormat.png,
            OutputFormat.webp,
        ):
            raise ValueError(
                "transparent_bg requires output_format 'png' or 'webp' "
                "(JPEG has no alpha channel)."
            )
        return self


class Flux2FlexParams(Flux2Params):
    """FLUX.2 [flex] adds explicit control over guidance and step count."""

    prompt_upsampling: bool | None = Field(
        default=None,
        description=(
            "Expand the prompt for more creative results. Flex upsamples by "
            "default; pass False to disable."
        ),
    )
    guidance: float = Field(
        default=5.0,
        ge=1.5,
        le=10.0,
        description="Prompt adherence vs. realism. Higher follows the prompt more.",
    )
    steps: int = Field(
        default=50,
        ge=1,
        le=50,
        description="Denoising steps. More steps trade speed for detail.",
    )


class Flux2KleinParams(Flux2Params):
    """FLUX.2 [klein] — the fast, open-weight tier.

    Behaves like [pro] but accepts fewer reference images; the exact ceiling
    (4 for 4B, 5 for 9B) is enforced by the resource based on the chosen model.
    """


# --------------------------------------------------------------------------- #
# FLUX Tools — the dedicated editing endpoints under /v1/flux-tools/*.
# These have their own request shapes (no shared prompt/dimension base), so
# they are modeled separately from the FLUX.2 generation params above. Field
# names and bounds mirror the server contract exactly; the server forbids
# unknown fields on outpainting, so we only declare what each endpoint accepts.
# --------------------------------------------------------------------------- #


class OutpaintMode(str, Enum):
    """Quality/speed trade-off for outpainting."""

    high = "high"
    fast = "fast"


class OutpaintParams(BaseModel):
    """Parameters for ``/v1/flux-tools/outpainting-v1``.

    Extends an image onto a larger canvas. The model fills the new region from
    the source on its own; ``prompt`` is optional and only loosely followed.
    Note this endpoint does **not** accept webhook fields.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    input_image: str = Field(description="Reference image to expand (base64 or URL).")
    width: int = Field(
        ge=64, description="Target canvas width. width*height must be <= 4MP."
    )
    height: int = Field(
        ge=64, description="Target canvas height. width*height must be <= 4MP."
    )
    reference_offset_x: int | None = Field(
        default=None,
        description=(
            "Left offset (px) of the reference's top-left corner on the canvas. "
            "Negative allowed; omit to center horizontally."
        ),
    )
    reference_offset_y: int | None = Field(
        default=None,
        description=(
            "Top offset (px) of the reference's top-left corner on the canvas. "
            "Negative allowed; omit to center vertically."
        ),
    )
    auto_crop: bool = Field(
        default=False,
        description="Crop the reference to canvas bounds if it overflows the edges.",
    )
    mode: OutpaintMode = Field(
        default=OutpaintMode.high,
        description="'high' (default, best fidelity) or 'fast' (quicker, cheaper).",
    )
    prompt: str | None = Field(
        default=None,
        description="Optional, loosely-followed text guidance for the new region.",
    )
    safety_tolerance: int = Field(
        default=2,
        ge=0,
        le=7,
        description="Moderation strictness, 0 (strictest) to 5 (public max).",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.png, description="Image container: png (default) or jpeg."
    )

    @model_validator(mode="after")
    def _check_canvas(self) -> "OutpaintParams":
        if self.width * self.height > _MAX_PIXELS:
            raise ValueError(
                f"width*height ({self.width * self.height}) exceeds the 4MP limit "
                f"({_MAX_PIXELS}). Reduce the canvas size."
            )
        return self


class EraseParams(BaseModel):
    """Parameters for ``/v1/flux-tools/erase-v1`` — mask-driven object removal."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    image: str = Field(description="Input image (base64 or URL).")
    mask: str = Field(
        description=(
            "Black/white mask (base64 or URL), same dimensions as the image. "
            "White (255) = remove, black (0) = keep."
        )
    )
    dilate_pixels: int = Field(
        default=10,
        ge=0,
        le=25,
        description="Pixels to dilate the mask before removal (helps cover edges).",
    )
    seed: int | None = Field(default=None, description="Seed for reproducible output.")
    safety_tolerance: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Moderation strictness, 0 (strictest) to 5 (most lenient).",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.png, description="Image container: png (default) or jpeg."
    )
    webhook_url: str | None = Field(
        default=None, description="URL to receive a completion webhook."
    )
    webhook_secret: str | None = Field(
        default=None,
        description=(
            "Secret echoed back in the X-Webhook-Secret header for verification."
        ),
    )


class DeblurParams(BaseModel):
    """Parameters for ``/v1/flux-tools/deblur-v1`` — whole-image sharpening.

    No prompt or mask: the server sharpens the entire image with a fixed
    instruction.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    image: str = Field(description="Blurry input image (base64 or URL). Max 4MP.")
    seed: int | None = Field(default=None, description="Seed for reproducible output.")
    safety_tolerance: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Moderation strictness, 0 (strictest) to 5 (most lenient).",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.png, description="Image container: png (default) or jpeg."
    )
    webhook_url: str | None = Field(
        default=None, description="URL to receive a completion webhook."
    )
    webhook_secret: str | None = Field(
        default=None,
        description=(
            "Secret echoed back in the X-Webhook-Secret header for verification."
        ),
    )


class VtoParams(BaseModel):
    """Parameters for ``/v1/flux-tools/vto-v1`` — virtual try-on.

    Dresses the ``person`` in the ``garment``. The server maps ``person`` to
    ``input_image`` and ``garment`` to ``input_image_2`` internally.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    prompt: str = Field(
        description=(
            "Styling instruction, e.g. 'The person of image 1, maintaining "
            "exactly their face and pose, wearing the <garment> of image 2.'"
        )
    )
    person: str = Field(description="Person image (base64 or URL).")
    garment: str = Field(description="Garment reference image (base64 or URL).")
    seed: int | None = Field(default=None, description="Seed for reproducible output.")
    safety_tolerance: int = Field(
        default=2,
        ge=0,
        le=7,
        description="Moderation strictness, 0 (strictest) to 5 (public max).",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.jpeg,
        description="Image container: jpeg (default), png, or webp.",
    )
    webhook_url: str | None = Field(
        default=None, description="URL to receive a completion webhook."
    )
    webhook_secret: str | None = Field(
        default=None,
        description=(
            "Secret echoed back in the X-Webhook-Secret header for verification."
        ),
    )
