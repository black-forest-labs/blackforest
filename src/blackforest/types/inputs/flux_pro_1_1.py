from pydantic import model_validator

from blackforest.types.inputs.generic import (
    GenericDimensionInput,
    GenericImageInput,
    GenericImagePromptInput,
)


class FluxPro11Inputs(GenericImageInput,
                      GenericImagePromptInput,
                      GenericDimensionInput):
    """Inputs for the Flux Pro 1.1 model."""

    @model_validator(mode="after")
    def validate_prompt_or_image(self):
        if not self.prompt and not self.image_prompt:
            raise ValueError("Either prompt or image_prompt must be provided")
        return self
