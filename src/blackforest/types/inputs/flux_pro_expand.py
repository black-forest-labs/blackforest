from typing import Optional

from pydantic import Field, model_validator

from blackforest.types.inputs.generic import GenericImageInput, GenericImageValidation


class FluxProExpandInputs(GenericImageInput, GenericImageValidation):
    image: str = Field(
        description="A Base64-encoded string representing \
            the image you wish to expand.",
    )
    top: Optional[int] = Field(
        default=0,
        ge=0,
        le=2048,
        description="Number of pixels to expand at the top of the image",
    )
    bottom: Optional[int] = Field(
        default=0,
        ge=0,
        le=2048,
        description="Number of pixels to expand at the bottom of the image",
    )
    left: Optional[int] = Field(
        default=0,
        ge=0,
        le=2048,
        description="Number of pixels to expand on the left side of the image",
    )
    right: Optional[int] = Field(
        default=0,
        ge=0,
        le=2048,
        description="Number of pixels to expand on the right side of the image",
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


    @model_validator(mode="after")
    def validate_images(self):
        # Only validate the input image exists and is valid
        image_size, _ = self._validate_image(self.image, field_name="image")

        # Ensure at least one side is being expanded
        if not any([self.top, self.bottom, self.left, self.right]):
            raise ValueError(
                "At least one side must be expanded (top, bottom, left, or right)"
            )

        return self
