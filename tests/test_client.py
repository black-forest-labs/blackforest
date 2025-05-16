import os

import pytest

from blackforest import BFLClient
from blackforest.types.general.client_config import ClientConfig

BFL_API_KEY = os.getenv("BFL_API_KEY", "test-key")
os.environ["BFL_ENV"] = "dev"  # Set environment to dev mode for testing

def test_client_initialization():
    client = BFLClient(api_key="test-key")
    assert client.api_key == "test-key"
    assert client.base_url == "https://api.us1.bfl.ai"
    assert client.timeout == 30

def test_client_custom_base_url():
    client = BFLClient(api_key="test-key", base_url="https://api.us1.bfl.ai")
    assert client.base_url == "https://api.us1.bfl.ai"

def test_client_headers():
    client = BFLClient(api_key="test-key")
    headers = client.session.headers
    assert headers["X-Key"] == "test-key"
    assert headers["Content-Type"] == "application/json"

def test_generate_flux_pro_1_1_no_config():
    print(f"Using API key: {BFL_API_KEY}")
    client = BFLClient(api_key=BFL_API_KEY)

    # Create input as dictionary instead of model instance
    inputs = {
        "prompt": "a beautiful sunset over mountains, digital art style",
        "width": 1024,
        "height": 768,
        "output_format": "jpeg"
    }

    config = ClientConfig()

    # Call generate with dictionary and config
    response = client.generate("flux-pro-1.1", inputs)
    print(f"Response: {response}")

    if config.sync:
        assert response.id is not None
        assert response.result is not None
    else:
        assert response.id is not None
        assert response.polling_url is not None

@pytest.mark.parametrize("model", ["flux-pro-1.1", "flux-pro", "flux-dev"])
@pytest.mark.parametrize("sync", [False, True])
def test_generate_flux_model(model, sync):
    print(f"Using API key: {BFL_API_KEY}")
    client = BFLClient(api_key=BFL_API_KEY)

    # Create input as dictionary instead of model instance
    inputs = {
        "prompt": "a beautiful sunset over mountains, digital art style",
        "width": 1024,
        "height": 768,
        "output_format": "jpeg"
    }

    config = ClientConfig(sync=sync)

    # Call generate with dictionary and config
    response = client.generate(model, inputs, config)
    print(f"Response: {response}")

    if sync:
        assert response.id is not None
        assert response.result is not None
    else:
        assert response.id is not None
        assert response.polling_url is not None

@pytest.mark.parametrize("model", ["flux-pro-1.1-ultra"])
@pytest.mark.parametrize("raw", [True, False])
@pytest.mark.parametrize("aspect_ratio", ["16:9", "9:16"])
@pytest.mark.parametrize("sync", [False, True])
def test_generate_ultra_model(model, raw, aspect_ratio, sync):
    print(f"Using API key: {BFL_API_KEY}")
    client = BFLClient(api_key=BFL_API_KEY)

    # Create input as dictionary instead of model instance
    inputs = {
        "prompt": "a beautiful sunset over mountains, digital art style",
        "width": 1024,
        "height": 768,
        "output_format": "jpeg",
        "raw": raw,
        "aspect_ratio": aspect_ratio,
    }

    config = ClientConfig(sync=sync)

    # Call generate with dictionary and config
    response = client.generate(model, inputs, config)
    print(f"Response: {response}")

    if sync:
        assert response.id is not None
        assert response.result is not None
    else:
        assert response.id is not None
        assert response.polling_url is not None
