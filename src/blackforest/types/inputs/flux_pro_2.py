from typing import Optional

from pydantic import Field

from blackforest.types.inputs.generic import GenericImageInput


class FluxPro2Inputs(GenericImageInput):
    """Inputs for the Flux Pro 2.0 model.

    Supports multiple input images (up to 8) and flexible dimensions.
    """

    # Multiple input image support
    input_image: Optional[str] = Field(
        default=None,
        description="Base64 encoded input image",
    )
    input_image_2: Optional[str] = Field(
        default=None,
        description="Base64 encoded second input image",
    )
    input_image_3: Optional[str] = Field(
        default=None,
        description="Base64 encoded third input image",
    )
    input_image_4: Optional[str] = Field(
        default=None,
        description="Base64 encoded fourth input image",
    )
    input_image_5: Optional[str] = Field(
        default=None,
        description="Base64 encoded fifth input image",
    )
    input_image_6: Optional[str] = Field(
        default=None,
        description="Base64 encoded sixth input image",
    )
    input_image_7: Optional[str] = Field(
        default=None,
        description="Base64 encoded seventh input image",
    )
    input_image_8: Optional[str] = Field(
        default=None,
        description="Base64 encoded eighth input image",
    )

    # Dimension parameters with FLUX2 Pro constraints
    width: Optional[int] = Field(
        default=None,
        ge=64,
        multiple_of=16,
        description="Width of the generated image in pixels. Must be at least 64 and a multiple of 16.",
    )
    height: Optional[int] = Field(
        default=None,
        ge=64,
        multiple_of=16,
        description="Height of the generated image in pixels. Must be at least 64 and a multiple of 16.",
    )

    # Override safety_tolerance range for FLUX2 Pro (0-5 instead of 0-6)
    safety_tolerance: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Tolerance level for input and output moderation. "
        "Between 0 and 5, 0 being most strict, 5 being least strict.",
        example=2,
    )
