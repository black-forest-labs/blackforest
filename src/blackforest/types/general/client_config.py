import os
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# Determine default sync behavior based on environment
def _get_default_sync() -> bool:
    """Get default sync behavior based on environment variables"""
    env = os.environ.get("BFL_ENV", "").lower()
    return env == "dev" or env == "development"


class ClientConfig(BaseModel):
    """Base configuration class for BFL client operations."""
    sync: bool = Field(
        default_factory=_get_default_sync,
        description="Whether to wait for the operation to complete before returning \
            (synchronous mode)."
    )
    timeout: Optional[int] = Field(
        default=None,
        description="Timeout in seconds for synchronous operations. \
            Only used when sync=True."
    )
    polling_interval: float = Field(
        default=1.0,
        ge=0.1,
        description="Time in seconds to wait between polling attempts for \
              synchronous operations."
    )
    max_retries: int = Field(
        default=60,
        ge=1,
        description="Maximum number of polling attempts for synchronous operations."
    )

    @model_validator(mode='after')
    def log_sync_mode(self):
        """Log debug information about sync mode when in development"""
        if os.environ.get("BFL_DEBUG", "").lower() in ("1", "true", "yes"):
            env = os.environ.get("BFL_ENV", "production")
            print(f"[BFL_DEBUG] Environment: {env}, \
                  Sync mode: {'enabled' if self.sync else 'disabled'}")
        return self
