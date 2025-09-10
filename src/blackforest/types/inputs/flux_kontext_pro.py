import re
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator

from blackforest.types.base.output_format import OutputFormat


class FluxKontextProInputs(BaseModel):
    """Inputs for the Flux Kontext Pro model."""
    
    prompt: str = Field(
        example="ein fantastisches bild",
        description="Text prompt for image generation.",
    )

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
    seed: Optional[int] = Field(
        default=None,
        description="Optional seed for reproducibility.",
        example=42,
    )
    aspect_ratio: Optional[str] = Field(
        default=None, description="Aspect ratio of the image between 21:9 and 9:21"
    )
    output_format: Optional[OutputFormat] = Field(
        default=OutputFormat.png,
        description="Output format for the generated image. Can be 'jpeg' or 'png'.",
    )
    webhook_url: Optional[HttpUrl] = Field(
        default=None, description="URL to receive webhook notifications"
    )
    webhook_secret: Optional[str] = Field(
        default=None, description="Optional secret for webhook signature verification"
    )
    prompt_upsampling: bool = Field(
        default=False,
        description="Whether to perform upsampling on the prompt. If active, automatically modifies the prompt for more creative generation.",
    )
    safety_tolerance: int = Field(
        default=2,
        ge=0,
        le=6,
        description="Tolerance level for input and output moderation. Between 0 and 6, 0 being most strict, 6 being least strict.",
        example=2,
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
