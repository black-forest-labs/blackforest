"""Backwards-compatible shim for the pre-0.2 ``BFLClient`` API.

The original client shipped a single ``BFLClient(api_key).generate(model, inputs,
config)`` surface. That contract is preserved here so code written against
``black-forest-labs<0.2`` keeps working, while new code uses :class:`BFL`.

Internally this delegates to the modern client, so the polling bug fix, retry
logic, and typed errors all apply to legacy callers too.
"""

from __future__ import annotations

import os
import warnings
from typing import Any

from ._client import BFL
from ._exceptions import BFLError
from ._jobs import Result
from .types.general.client_config import ClientConfig
from .types.responses.responses import AsyncResponse, SyncResponse

_DEPRECATION = (
    "BFLClient is the legacy interface. Prefer `from bfl import BFL` "
    "for the modern client (typed models, async, retries, result.save())."
)


class BFLClient:
    """Legacy client. Thin compatibility wrapper over :class:`BFL`."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.bfl.ai",
        timeout: int = 30,
    ) -> None:
        warnings.warn(_DEPRECATION, DeprecationWarning, stacklevel=2)
        # Preserve the original env fallback behavior documented in the README.
        resolved = api_key or os.environ.get("BFL_API_KEY")
        self.api_key = resolved
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = BFL(resolved, base_url=self.base_url, timeout=float(timeout))

    def generate(
        self,
        model: str,
        inputs: dict[str, Any],
        config: ClientConfig | None = None,
        track_usage: bool = False,
    ) -> AsyncResponse | SyncResponse:
        """Generate using the legacy ``(model, inputs, config)`` signature."""
        config = config or ClientConfig()
        accessor = self._client.model(model)
        job = accessor.submit(**inputs)

        if not config.sync:
            return AsyncResponse(id=job.id, polling_url=job.polling_url)

        result: Result = job.wait(
            timeout=config.timeout,
            poll_interval=config.polling_interval,
        )
        return SyncResponse(id=job.id, result=result.raw)

    def get_polling_result(
        self, task_id: str, config: ClientConfig | None = None
    ) -> dict[str, Any]:
        """Poll a task to completion and return the raw result dict."""
        config = config or ClientConfig()
        # Reconstruct a job handle from the task id and poll it.
        from ._jobs import Job

        job = Job(
            transport=self._client._transport,
            id=task_id,
            polling_url=f"/v1/get_result?id={task_id}",
        )
        result = job.wait(timeout=config.timeout, poll_interval=config.polling_interval)
        return result.raw

    def close(self) -> None:
        self._client.close()


__all__ = ["BFLClient", "BFLError"]
