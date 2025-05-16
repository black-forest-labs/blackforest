from typing import Optional

from pydantic import Field

from blackforest.types.inputs.generic import GenericImageInput


class FluxDevInputs(GenericImageInput):\

    steps: Optional[int] = Field(
        default=28,
        ge=1,
        le=50,
        description="Number of steps for the image generation process.",
        example=28,
    )

    guidance: Optional[float] = Field(
        default=3.0,
        ge=1.5,
        le=5.0,
        description="Guidance scale for image generation. \
            High guidance scales improve prompt adherence \
                at the cost of reduced realism.",
        example=3.0,
    )
    safety_tolerance: int = Field(
        default=2,
        ge=0,
        le=6,
        description="Tolerance level for input and output moderation. \
            Between 0 and 6, 0 being most strict, 6 being least strict.",
        example=2,
    )
