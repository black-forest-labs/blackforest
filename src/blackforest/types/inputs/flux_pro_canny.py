from typing import Optional

from pydantic import Field, model_validator

from blackforest.types.inputs.generic import GenericImageInput, GenericImageValidation


class FluxProCannyInputs(GenericImageInput, GenericImageValidation):
    control_image: Optional[str] = Field(
        default=None,
        description="Base64 encoded image to use as control input \
            if no preprocessed image is provided",
    )

    preprocessed_image: Optional[str] = Field(
        default=None,
        description="Optional pre-processed image that will bypass \
            the control preprocessing step",
    )

    canny_low_threshold: Optional[int] = Field(
        default=50, ge=0, le=500, description="Low threshold for Canny edge detection"
    )

    canny_high_threshold: Optional[int] = Field(
        default=200, ge=0, le=500, description="High threshold for Canny edge detection"
    )

    steps: Optional[int] = Field(
        default=50,
        ge=15,
        le=50,
        description="Number of steps for the image generation process",
    )

    guidance: Optional[float] = Field(
        default=30,
        ge=1,
        le=100,
        description="Guidance strength for the image generation process",
    )


    @model_validator(mode="after")
    def validate_control_image(self):
        if not self.control_image and not self.preprocessed_image:
            raise ValueError(
                "Either control_image or preprocessed_image must be provided"
            )

        if self.control_image:
            self._validate_image(self.control_image, field_name="control_image")
        if self.preprocessed_image:
            self._validate_image(
                self.preprocessed_image, field_name="preprocessed_image"
            )
        return self
