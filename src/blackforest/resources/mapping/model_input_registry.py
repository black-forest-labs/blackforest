from blackforest.types.inputs.flux_dev import FluxDevInputs
from blackforest.types.inputs.flux_pro import FluxProInputs
from blackforest.types.inputs.flux_pro_1_1 import FluxPro11Inputs
from blackforest.types.inputs.flux_pro_fill import FluxProFillInputs
from blackforest.types.inputs.flux_ultra import FluxUltraInputs

MODEL_INPUT_REGISTRY = {
    "flux-dev": FluxDevInputs,
    "flux-pro": FluxProInputs,
    "flux-pro-1.1": FluxPro11Inputs,
    "flux-pro-1.1-ultra": FluxUltraInputs,
    "flux-pro-1.0-fill": FluxProFillInputs
}
