from pydantic import Field

from blackforest.types.inputs.generic import GenericImageInput


class FluxPro11Inputs(GenericImageInput):
    """Inputs for the Flux Pro 1.1 model."""
    prompt_upsampling: bool = Field(
        default=False,
        description="Whether to perform upsampling on the prompt.\
            If active, automatically modifies the prompt for more creative generation",
    )
