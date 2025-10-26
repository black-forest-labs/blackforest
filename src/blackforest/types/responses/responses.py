from pydantic import BaseModel, ConfigDict, Field


class GenerationResult(BaseModel):
    """Result from a completed image generation task.

    """
    model_config = ConfigDict(extra="allow")

    sample: str = Field(..., description="Signed URL to the generated image (valid for 10 minutes)")
    prompt: str | None = Field(None, description="The prompt used for generation")
    seed: int | None = Field(None, description="The seed used for generation")


class AsyncResponse(BaseModel):
    id: str
    polling_url: str


class SyncResponse(BaseModel):
    id: str
    result: GenerationResult


class ImageProcessingResponse(BaseModel):
    """Response for image processing tasks.

    Used for tracking the status of async image processing operations.
    """
    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None
