from bfl.types.inputs.flux_dev import FluxDevInputs
from bfl.types.inputs.flux_kontext_pro import FluxKontextProInputs
from bfl.types.inputs.flux_pro import FluxProInputs
from bfl.types.inputs.flux_pro_1_1 import FluxPro11Inputs
from bfl.types.inputs.flux_ultra import FluxUltraInputs

MODEL_INPUT_REGISTRY = {
    "flux-dev": FluxDevInputs,
    "flux-pro": FluxProInputs,
    "flux-pro-1.1": FluxPro11Inputs,
    "flux-pro-1.1-ultra": FluxUltraInputs,
    "flux-kontext-pro": FluxKontextProInputs,
    "flux-kontext-max": FluxKontextProInputs,
}
