from typing import Optional

from pydantic import Field

from blackforest.types.inputs.generic import GenericImageInput


class FluxProFillInputs(GenericImageInput):
    image: str = Field(
        description="A Base64-encoded string representing the image \
            you wish to modify. Can contain alpha mask if desired.",
    )

    mask: Optional[str] = Field(
        default=None,
        description=(
            "A Base64-encoded string representing a mask for the areas you want to \
                modify in the image. "
            "The mask should be the same dimensions as the image \
                and in black and white. Black areas (0%) "
            "indicate no modification, while white areas (100%) \
                specify areas for inpainting. "
            "Optional if you provide an alpha mask in the original image. "
            "Validation: The endpoint verifies that \
                the dimensions of the mask match the original image."
        ),
    )

    steps: Optional[int] = Field(
        default=50,
        ge=15,
        le=50,
        description="Number of steps for the image generation process",
        example=50,
    )

    guidance: Optional[float] = Field(
        default=60,
        ge=1.5,
        le=100,
        description="Guidance strength for the image generation process",
    )
