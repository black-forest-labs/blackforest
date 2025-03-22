from typing import Optional, Union
from pydantic import BaseModel, Field

class AsyncResponse(BaseModel):
    id: str
    polling_url: str

class AsyncWebhookResponse(BaseModel):
    id: str
    webhook_url: str

class ImageInput(BaseModel):
    image_path: Optional[str] = Field(None, description="Path to a single image file")
    folder_path: Optional[str] = Field(None, description="Path to a folder containing images")
    zip_path: Optional[str] = Field(None, description="Path to a zip file containing images")
    image_data: Optional[str] = Field(None, description="Base64 encoded image data")

class ImageProcessingResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None 