from blackforest.types.inputs.flux_dev import FluxDevInputs
from blackforest.types.inputs.flux_kontext_pro import FluxKontextProInputs
from blackforest.types.inputs.flux_pro import FluxProInputs
from blackforest.types.inputs.flux_pro_1_1 import FluxPro11Inputs
from blackforest.types.inputs.flux_pro_canny import FluxProCannyInputs
from blackforest.types.inputs.flux_pro_depth import FluxProDepthInputs
from blackforest.types.inputs.flux_pro_expand import FluxProExpandInputs
from blackforest.types.inputs.flux_pro_fill import FluxProFillInputs
from blackforest.types.inputs.flux_ultra import FluxUltraInputs

MODEL_INPUT_REGISTRY = {
    "flux-dev": FluxDevInputs,
    "flux-pro": FluxProInputs,
    "flux-pro-1.1": FluxPro11Inputs,
    "flux-pro-1.1-ultra": FluxUltraInputs,
    "flux-pro-1.0-fill": FluxProFillInputs,
    "flux-pro-1.0-expand": FluxProExpandInputs,
    "flux-pro-1.0-canny": FluxProCannyInputs,
    "flux-pro-1.0-depth": FluxProDepthInputs,
    "flux-kontext-pro": FluxKontextProInputs,
}
