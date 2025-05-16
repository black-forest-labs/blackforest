from typing import Optional

from pydantic import BaseModel


class AsyncResponse(BaseModel):
    id: str
    polling_url: str

class SyncResponse(BaseModel):
    id: str
    result: dict
    error: Optional[str] = None
