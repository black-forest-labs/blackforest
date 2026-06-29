"""Turn friendly keyword arguments into a validated JSON request body.

One place owns the two cross-cutting concerns shared by every model:

* **Image coercion** — any field that carries an image (``input_image``,
  ``image``, ``mask``, ``control_image``, ...) accepts a path, URL, bytes, a
  Pillow image, or base64, and is encoded to what the API expects.
* **Validation** — FLUX.2 requests are checked against the typed params in
  :mod:`._models`; the legacy FLUX.1 / tools / Kontext requests reuse the
  existing pydantic input classes so their established constraints still apply.

Validation runs locally, so a malformed request fails at the call site instead
of as a ``422`` after a network round trip.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ._catalog import ModelSpec
from ._exceptions import BFLValidationError
from ._images import to_image_payload
from ._models import (
    DeblurParams,
    EraseParams,
    Flux2FlexParams,
    Flux2KleinParams,
    Flux2Params,
    OutpaintParams,
    VtoParams,
)
from .resources.mapping.model_input_registry import MODEL_INPUT_REGISTRY

# Every field name, across all models, whose value is an image. Anything listed
# here is run through ``to_image_payload`` before validation.
_IMAGE_FIELDS = frozenset(
    {
        "image",
        "mask",
        "control_image",
        "preprocessed_image",
        "image_prompt",
        "person",
        "garment",
        *(f"input_image_{n}" for n in range(2, 11)),
        "input_image",
    }
)

# FLUX.2 model id -> its typed params class.
_FLUX2_PARAMS: dict[str, type[Flux2Params]] = {
    "flux-2-pro": Flux2Params,
    "flux-2-max": Flux2Params,
    "flux-2-flex": Flux2FlexParams,
    "flux-2-klein-4b": Flux2KleinParams,
    "flux-2-klein-9b": Flux2KleinParams,
}

# FLUX Tools model id -> its typed params class.
_FLUX_TOOLS_PARAMS: dict[str, type[BaseModel]] = {
    "flux-tools-outpaint": OutpaintParams,
    "flux-tools-erase": EraseParams,
    "flux-tools-deblur": DeblurParams,
    "flux-tools-vto": VtoParams,
}


def spread_images(images: list[Any] | None) -> dict[str, Any]:
    """Map a list of references to ``input_image``, ``input_image_2``, ... slots.

    Lets callers write ``images=[a, b, c]`` instead of three positional
    ``input_image*`` keyword arguments. Encoding happens later in
    :func:`build_payload`.
    """
    if not images:
        return {}
    slots: dict[str, Any] = {}
    for index, image in enumerate(images):
        key = "input_image" if index == 0 else f"input_image_{index + 1}"
        slots[key] = image
    return slots


def _encode_image_fields(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Encode any image-bearing field in ``kwargs`` in place-safe fashion."""
    encoded = dict(kwargs)
    for field, value in kwargs.items():
        if field in _IMAGE_FIELDS and value is not None:
            encoded[field] = to_image_payload(value, field=field)
    return encoded


def build_payload(spec: ModelSpec, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Validate and serialize a request for ``spec`` from raw ``kwargs``.

    Args:
        spec: The resolved model specification.
        kwargs: Caller-supplied parameters (already merged with any spread
            ``images`` list). ``None`` values are dropped.

    Returns:
        A JSON-ready dict with images encoded and fields validated.

    Raises:
        BFLValidationError: If the inputs fail the model's validation rules.
    """
    cleaned = {k: v for k, v in kwargs.items() if v is not None}
    _enforce_reference_limit(spec, cleaned)
    encoded = _encode_image_fields(cleaned)

    params_cls = _FLUX2_PARAMS.get(spec.id)
    if params_cls is None:
        params_cls = _FLUX_TOOLS_PARAMS.get(spec.id)
    if params_cls is None:
        params_cls = MODEL_INPUT_REGISTRY.get(spec.id)
    if params_cls is None:  # pragma: no cover - guarded by the catalog
        raise BFLValidationError(f"No request schema registered for model {spec.id!r}.")

    try:
        model = params_cls(**encoded)
    except Exception as exc:  # pydantic ValidationError or ValueError
        raise BFLValidationError(f"Invalid inputs for {spec.label}: {exc}") from exc

    # Send only what the caller actually set; the server applies its own
    # defaults for everything else. This keeps requests minimal and avoids
    # tripping any model that forbids unknown/extra fields.
    payload = model.model_dump(exclude_none=True, exclude_unset=True, mode="json")

    if spec.id in _FLUX2_PARAMS:
        _translate_flux2_upsampling(spec.id, payload)
    return payload


def _translate_flux2_upsampling(model_id: str, payload: dict[str, Any]) -> None:
    """Map the SDK's uniform ``prompt_upsampling`` knob to each model's real field.

    The FLUX.2 endpoints disagree on how upsampling is controlled:

    * ``[pro]`` / ``[max]`` accept ``disable_pup`` (the inverse), not
      ``prompt_upsampling``. We translate so ``prompt_upsampling=False`` is
      honored as ``disable_pup=True`` instead of being silently ignored.
    * ``[flex]`` has a native ``prompt_upsampling`` field — pass it through.
    * ``[klein]`` has no upsampling control at all — drop it so we don't send a
      field the model neither documents nor uses.

    Mutates ``payload`` in place. Only runs when the caller set the knob.
    """
    if "prompt_upsampling" not in payload:
        return
    value = payload.pop("prompt_upsampling")
    if model_id in ("flux-2-pro", "flux-2-max"):
        payload["disable_pup"] = not value
    elif model_id == "flux-2-flex":
        payload["prompt_upsampling"] = value
    # klein: no upsampling control — intentionally dropped.


def _enforce_reference_limit(spec: ModelSpec, kwargs: dict[str, Any]) -> None:
    """Reject reference images the model can't accept, with a clear message.

    Applies to the generation families whose ``images=[...]`` list is spread
    into ``input_image*`` slots (FLUX.2, FLUX.1, Kontext). Tools declare their
    own image fields (``input_image``, ``image``, ``person``…) and validate
    them via their typed models, so they're exempt here.
    """
    if spec.family == "tools":
        return
    provided = [f for f in kwargs if f == "input_image" or f.startswith("input_image_")]
    if not provided:
        return
    if spec.max_reference_images <= 0:
        raise BFLValidationError(
            f"{spec.label} does not accept reference images, but "
            f"{len(provided)} was/were provided."
        )
    if len(provided) > spec.max_reference_images:
        raise BFLValidationError(
            f"{spec.label} accepts at most {spec.max_reference_images} reference "
            f"image(s); got {len(provided)}."
        )
