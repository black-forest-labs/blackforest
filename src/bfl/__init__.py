"""Black Forest Labs — the official Python SDK for the FLUX image models.

Quick start::

    from bfl import BFL

    client = BFL()                              # reads $BFL_API_KEY
    image = client.generate("a red fox in the snow")
    image.save("fox.png")

Pick a specific model and control its parameters::

    job = client.flux2.max.submit(
        prompt="a neon-lit alley, rain, cinematic",
        width=1536, height=1024, seed=7,
    )
    image = job.wait()
    print(image.url)

Edit with reference images (any mix of paths, URLs, bytes, or PIL images)::

    edited = client.flux2.pro.generate(
        "place the product on a marble countertop",
        images=["product.png", "https://example.com/scene.jpg"],
    )

Async mirrors the sync API one-to-one::

    import asyncio
    from bfl import AsyncBFL

    async def main():
        async with AsyncBFL() as client:
            image = await client.generate("a misty forest at dawn")
            await image.asave("forest.png")

    asyncio.run(main())
"""

from ._catalog import DEFAULT_MODEL, ModelSpec, all_models, model_ids
from ._client import BFL, AsyncBFL
from ._exceptions import (
    BFLAPIError,
    BFLAuthError,
    BFLConfigError,
    BFLConnectionError,
    BFLContentModerated,
    BFLError,
    BFLInsufficientCreditsError,
    BFLNotFoundError,
    BFLRateLimitError,
    BFLServerError,
    BFLTaskError,
    BFLTimeoutError,
    BFLValidationError,
)
from ._images import ImageInput, to_image_payload
from ._jobs import AsyncJob, Job, ProgressCallback, Result
from ._models import (
    DeblurParams,
    EraseParams,
    Flux2FlexParams,
    Flux2KleinParams,
    Flux2Params,
    OutpaintMode,
    OutpaintParams,
    OutputFormat,
    VtoParams,
)
from ._transport import RetryConfig
from ._version import __version__
from ._webhooks import WEBHOOK_SECRET_HEADER, verify_webhook
from .client import BFLClient  # legacy compatibility shim

__all__ = [
    # Modern clients
    "BFL",
    "AsyncBFL",
    # Handles
    "Job",
    "AsyncJob",
    "Result",
    "ProgressCallback",
    # Config / catalog
    "RetryConfig",
    "ModelSpec",
    "DEFAULT_MODEL",
    "all_models",
    "model_ids",
    # Typed params
    "Flux2Params",
    "Flux2FlexParams",
    "Flux2KleinParams",
    "OutputFormat",
    # FLUX Tools params
    "OutpaintParams",
    "OutpaintMode",
    "EraseParams",
    "DeblurParams",
    "VtoParams",
    # Image helpers
    "to_image_payload",
    "ImageInput",
    # Webhooks
    "verify_webhook",
    "WEBHOOK_SECRET_HEADER",
    # Exceptions
    "BFLError",
    "BFLConfigError",
    "BFLValidationError",
    "BFLAPIError",
    "BFLAuthError",
    "BFLNotFoundError",
    "BFLRateLimitError",
    "BFLInsufficientCreditsError",
    "BFLServerError",
    "BFLConnectionError",
    "BFLTaskError",
    "BFLContentModerated",
    "BFLTimeoutError",
    # Legacy
    "BFLClient",
    "__version__",
]
