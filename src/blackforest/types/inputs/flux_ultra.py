from pydantic import Field, model_validator

from blackforest.types.inputs.generic import (
    GenericAspectRatioInput,
    GenericImageInput,
    GenericImagePromptInput,
)


class FluxUltraInputs(GenericImageInput,
                      GenericImagePromptInput,
                      GenericAspectRatioInput):
    raw: bool = Field(
        default=False,
        description="Generate less processed, more natural-looking images",
        example=False,
    )

    image_prompt_strength: float = Field(
        default=0.1,
        ge=0,
        le=1,
        description="Blend between the prompt and the image prompt",
    )

    @model_validator(mode="after")
    def validate_prompt_or_image(self):
        if not self.prompt and not self.image_prompt:
            raise ValueError("Either prompt or image_prompt must be provided")
        return self
