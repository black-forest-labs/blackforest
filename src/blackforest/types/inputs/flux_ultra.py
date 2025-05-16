
from pydantic import Field

from blackforest.types.inputs.generic import GenericAspectRatioInput, GenericImageInput


class FluxUltraInputs(GenericImageInput, GenericAspectRatioInput):
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
