from typing import Optional

from pydantic import Field, model_validator

from blackforest.types.inputs.generic import (
    GenericDimensionInput,
    GenericImageInput,
    GenericImagePromptInput,
)


class FluxProInputs(GenericImageInput,
                    GenericImagePromptInput,
                    GenericDimensionInput):
    steps: Optional[int] = Field(
        default=40,
        ge=1,
        le=50,
        description="Number of steps for the image generation process.",
        example=40,
    )
    guidance: Optional[float] = Field(
        default=2.5,
        ge=1.5,
        le=5.0,
        description="Guidance scale for image generation. \
            High guidance scales improve prompt adherence \
                at the cost of reduced realism.",
        example=2.5,
    )
    interval: Optional[float] = Field(
        default=2.0,
        ge=1.0,
        le=4.0,
        description="Interval parameter for guidance control.",
        example=2.0,
    )

    @model_validator(mode="after")
    def validate_prompt_or_image(self):
        if not self.prompt and not self.image_prompt:
            raise ValueError("Either prompt or image_prompt must be provided")
        return self
