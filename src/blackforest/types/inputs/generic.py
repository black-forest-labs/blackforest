import base64
import io
from typing import Optional

from PIL import Image
from pydantic import BaseModel, Field, model_validator

from blackforest.types.base.output_format import OutputFormat


class ImageInput(BaseModel):
    image_path: Optional[str] = Field(None, description="Path to a single image file")
    folder_path: Optional[str] = Field(None, description="Path to a folder \
                                       containing images")
    zip_path: Optional[str] = Field(None, description="Path to a zip file \
                                    containing images")
    image_data: Optional[str] = Field(None, description="Base64 encoded image data")


class GenericAspectRatioInput(BaseModel):
    aspect_ratio: str = Field(
        default="16:9", description="Aspect ratio of the image between 21:9 and 9:21"
    )
class GenericDimensionInput(BaseModel):
    width: int = Field(
        default=1024,
        ge=256,
        le=1440,
        multiple_of=32,
        description="Width of the generated image in pixels. \
            Must be a multiple of 32.",
    )
    height: int = Field(
        default=768,
        ge=256,
        le=1440,
        multiple_of=32,
        description="Height of the generated image in pixels. \
            Must be a multiple of 32.",
    )

class GenericImagePromptInput(BaseModel):
    image_prompt: Optional[str] = Field(
        default=None,
        description="Optional base64 encoded image to use with image models.",
    )

    @model_validator(mode="after")
    def validate_images(self):
        if self.image_prompt is not None:
            # Basic base64 validation
            try:
                import base64
                base64.b64decode(self.image_prompt)
            except Exception:
                raise ValueError("image_prompt must be a valid base64 encoded image")
        return self

class GenericImageValidation:
    @classmethod
    def _validate_image(cls, image: str, field_name: str = "image"):
        if not image:
            raise ValueError(f"{field_name.capitalize()} is required")

        try:
            if len(image) > 20 * 1024 * 1024:
                raise ValueError(
                    f"{field_name.capitalize()} file size exceeds 20MB limit"
                )

            b64_data = base64.b64decode(image)
            img = Image.open(io.BytesIO(b64_data))

            if img.width * img.height > 20 * 10**6:
                raise ValueError(
                    f"{field_name.capitalize()} dimensions exceed 20 megapixels"
                )

            # No side smaller than 256
            if img.width < 256 or img.height < 256:
                raise ValueError(
                    f"{field_name.capitalize()} dimensions \
                        must be at least 256x256 pixels"
                )

            return img.size, img.mode

        except base64.binascii.Error:
            raise ValueError(f"Invalid base64 encoding for {field_name}")
        except ValueError as e:
            raise e
        except Exception:
            raise ValueError(f"Error processing {field_name}")
class GenericImageInput(BaseModel):
    """Base class for image generation inputs."""
    prompt: Optional[str] = Field(
        default="",
        example="ein fantastisches bild",
        description="Text prompt for image generation.",
    )
    seed: Optional[int] = Field(
        default=None,
        description="Optional seed for reproducibility.",
        example=42,
    )
    safety_tolerance: int = Field(
        default=2,
        ge=0,
        le=6,
        description="Tolerance level for input and output moderation. \
            Between 0 and 6, 0 being most strict, 6 being least strict.",
        example=2,
    )
    output_format: Optional[OutputFormat] = Field(
        default=OutputFormat.jpeg,
        description="Output format for the generated image. Can be 'jpeg' or 'png'.",
    )
    prompt_upsampling: bool = Field(
        default=False,
        description="Whether to perform upsampling on the prompt. \
            If active, automatically modifies the prompt for more creative generation.",
    )
    # webhook_url: Optional[HttpUrl] = Field(
    #     default=None, description="URL to receive webhook notifications"
    # )
    # webhook_secret: Optional[str] = Field(
    #     default=None, description="Optional secret for webhook signature verification"
    # )


