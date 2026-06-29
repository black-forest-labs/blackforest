"""The model catalog: one declarative table describing every model.

Each :class:`ModelSpec` ties a friendly, stable model id (the string a caller
passes, e.g. ``"flux-2-pro"``) to the API path it POSTs to, the family it
belongs to, and how many reference images it accepts. This is the single source
of truth the resource namespaces and the top-level ``generate`` read from, so
adding a model is a one-line change here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The default model for the zero-config happy path. Matches the API's own
#: "recommended default" decision for FLUX.2.
DEFAULT_MODEL = "flux-2-pro"


@dataclass(frozen=True)
class ModelSpec:
    """Static description of a single generation model.

    Attributes:
        id: Stable public identifier callers pass to ``generate``.
        path: API path (under the versioned prefix) the request POSTs to.
        family: Coarse grouping — ``"flux2"``, ``"flux1"``, ``"tools"``,
            or ``"kontext"``.
        label: Human-facing marketing name, e.g. ``"FLUX.2 [pro]"``.
        max_reference_images: How many ``input_image*`` slots the model
            accepts (0 = text-to-image only).
        supports_pricing: Whether ``/v1/pricing`` can quote this model.
        aliases: Alternative ids that resolve to this spec.
    """

    id: str
    path: str
    family: str
    label: str
    max_reference_images: int = 0
    supports_pricing: bool = False
    aliases: tuple[str, ...] = field(default_factory=tuple)


_SPECS: tuple[ModelSpec, ...] = (
    # ---- FLUX.2 ---------------------------------------------------------
    ModelSpec(
        id="flux-2-pro",
        path="/v1/flux-2-pro",
        family="flux2",
        label="FLUX.2 [pro]",
        max_reference_images=8,
        supports_pricing=True,
        aliases=("flux2-pro", "flux.2-pro"),
    ),
    ModelSpec(
        id="flux-2-max",
        path="/v1/flux-2-max",
        family="flux2",
        label="FLUX.2 [max]",
        max_reference_images=8,
        supports_pricing=True,
        aliases=("flux2-max", "flux.2-max"),
    ),
    ModelSpec(
        id="flux-2-flex",
        path="/v1/flux-2-flex",
        family="flux2",
        label="FLUX.2 [flex]",
        max_reference_images=8,
        supports_pricing=True,
        aliases=("flux2-flex", "flux.2-flex"),
    ),
    ModelSpec(
        id="flux-2-klein-4b",
        path="/v1/flux-2-klein-4b",
        family="flux2",
        label="FLUX.2 [klein] 4B",
        max_reference_images=4,
        supports_pricing=True,
        aliases=("flux2-klein-4b", "klein-4b"),
    ),
    ModelSpec(
        id="flux-2-klein-9b",
        path="/v1/flux-2-klein-9b",
        family="flux2",
        label="FLUX.2 [klein] 9B",
        max_reference_images=5,
        supports_pricing=True,
        aliases=("flux2-klein-9b", "klein-9b", "flux-2-klein"),
    ),
    # ---- FLUX.1 ---------------------------------------------------------
    ModelSpec(
        id="flux-pro-1.1",
        path="/v1/flux-pro-1.1",
        family="flux1",
        label="FLUX 1.1 [pro]",
        max_reference_images=0,
        aliases=("flux-1.1-pro",),
    ),
    ModelSpec(
        id="flux-pro-1.1-ultra",
        path="/v1/flux-pro-1.1-ultra",
        family="flux1",
        label="FLUX 1.1 [pro] ultra",
        max_reference_images=0,
        aliases=("flux-1.1-ultra", "flux-ultra"),
    ),
    ModelSpec(
        id="flux-pro",
        path="/v1/flux-pro",
        family="flux1",
        label="FLUX.1 [pro]",
        max_reference_images=0,
    ),
    ModelSpec(
        id="flux-dev",
        path="/v1/flux-dev",
        family="flux1",
        label="FLUX.1 [dev]",
        max_reference_images=0,
    ),
    # ---- FLUX Tools (dedicated editing endpoints) -----------------------
    ModelSpec(
        id="flux-tools-outpaint",
        path="/v1/flux-tools/outpainting-v1",
        family="tools",
        label="FLUX Outpainting",
        aliases=("outpaint", "outpainting"),
    ),
    ModelSpec(
        id="flux-tools-erase",
        path="/v1/flux-tools/erase-v1",
        family="tools",
        label="FLUX Erase",
        aliases=("erase",),
    ),
    ModelSpec(
        id="flux-tools-deblur",
        path="/v1/flux-tools/deblur-v1",
        family="tools",
        label="FLUX Deblur",
        aliases=("deblur",),
    ),
    ModelSpec(
        id="flux-tools-vto",
        path="/v1/flux-tools/vto-v1",
        family="tools",
        label="FLUX Virtual Try-On",
        aliases=("vto", "virtual-try-on", "try-on"),
    ),
    # ---- Kontext --------------------------------------------------------
    ModelSpec(
        id="flux-kontext-pro",
        path="/v1/flux-kontext-pro",
        family="kontext",
        label="FLUX.1 Kontext [pro]",
        max_reference_images=4,
    ),
    ModelSpec(
        id="flux-kontext-max",
        path="/v1/flux-kontext-max",
        family="kontext",
        label="FLUX.1 Kontext [max]",
        max_reference_images=4,
    ),
)


_BY_ID: dict[str, ModelSpec] = {}
for _spec in _SPECS:
    _BY_ID[_spec.id] = _spec
    for _alias in _spec.aliases:
        _BY_ID[_alias] = _spec


def resolve(model: str) -> ModelSpec:
    """Look up a :class:`ModelSpec` by id or alias.

    Raises:
        KeyError: If the model id is unknown. Callers convert this into a
            :class:`~bfl._exceptions.BFLValidationError` with the list
            of supported ids.
    """
    try:
        return _BY_ID[model]
    except KeyError as exc:
        raise KeyError(model) from exc


def all_models() -> tuple[ModelSpec, ...]:
    """Every canonical model spec (no alias duplicates), in catalog order."""
    return _SPECS


def model_ids() -> list[str]:
    """All canonical, user-facing model ids."""
    return [spec.id for spec in _SPECS]
