import re
from typing import Optional

from pydantic import Field, HttpUrl, model_validator

from blackforest.types.base.output_format import OutputFormat
from blackforest.types.inputs.generic import GenericImageInput


class FluxKontextProInputs(GenericImageInput):
    """Inputs for the Flux Kontext Pro model."""
    
    # Override prompt to make it required
    prompt: str = Field(
        example="ein fantastisches bild",
        description="Text prompt for image generation.",
    )

    # Override output_format default to png
    output_format: Optional[OutputFormat] = Field(
        default=OutputFormat.png,
        description="Output format for the generated image. Can be 'jpeg' or 'png'.",
    )

    # Kontext-specific input image fields
    input_image: Optional[str] = Field(
        default=None,
        description="Base64 encoded image or URL to use with Kontext.",
    )
    input_image_2: Optional[str] = Field(
        default=None,
        description="Base64 encoded image or URL to use with Kontext. *Experimental Multiref*",
    )
    input_image_3: Optional[str] = Field(
        default=None,
        description="Base64 encoded image or URL to use with Kontext. *Experimental Multiref*",
    )
    input_image_4: Optional[str] = Field(
        default=None,
        description="Base64 encoded image or URL to use with Kontext. *Experimental Multiref*",
    )

    # Custom aspect ratio field with specific validation
    aspect_ratio: Optional[str] = Field(
        default=None, description="Aspect ratio of the image between 21:9 and 9:21"
    )

    @model_validator(mode="after")
    def validate_aspect_ratio(self):
        try:
            if self.aspect_ratio is not None:
                # ensure proper format (1:1) and ratio is between 21:9 and 9:21
                if not re.match(r"^\d+:\d+$", self.aspect_ratio):
                    raise ValueError(
                        "Aspect ratio must be in the format of 'width:height'"
                    )
                width, height = map(int, self.aspect_ratio.split(":"))
                ratio = width / height
                min_ratio = 1 / 4
                max_ratio = 4 / 1
                if not (min_ratio <= ratio <= max_ratio):
                    raise ValueError(
                        f"Aspect ratio {self.aspect_ratio} ({ratio:.3f}) must be between 1:4 and 4:1"
                    )
        except Exception as e:
            raise ValueError(f"Invalid aspect ratio: {e}")
        return self
