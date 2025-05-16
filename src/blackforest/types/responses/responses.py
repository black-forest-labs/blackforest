from typing import Dict, Optional

from pydantic import BaseModel


class AsyncResponse(BaseModel):
    id: str
    polling_url: str

class SyncResponse(BaseModel):
    id: str
    result: dict
    error: Optional[str] = None

class ImageProcessingResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict] = None
    error: Optional[str] = None
