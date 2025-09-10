import base64
import os

import pytest

from blackforest import BFLClient
from blackforest.types.general.client_config import ClientConfig

BFL_API_KEY = os.getenv("BFL_API_KEY", "test-key")
os.environ["BFL_ENV"] = "dev"  # Set environment to dev mode for testing

def test_client_initialization():
    client = BFLClient(api_key="test-key")
    assert client.api_key == "test-key"
    assert client.base_url == "https://api.bfl.ai"
    assert client.timeout == 30

def test_client_custom_base_url():
    client = BFLClient(api_key="test-key", base_url="https://api.bfl.ai")
    assert client.base_url == "https://api.bfl.ai"

def test_client_headers():
    client = BFLClient(api_key="test-key")
    headers = client.session.headers
    assert headers["X-Key"] == "test-key"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"

def test_polling_url_mapping():
    """Test that polling URLs are properly stored and retrieved."""
    client = BFLClient(api_key=BFL_API_KEY)
    
    # Test that mapping starts empty
    assert len(client._task_polling_urls) == 0
    
    # Create a test task
    inputs = {
        "prompt": "test prompt",
        "width": 512,
        "height": 512,
        "output_format": "jpeg"
    }
    
    config = ClientConfig(sync=False)  # Use async to avoid polling
    response = client.generate("flux-pro-1.1", inputs, config)
    
    # Verify that polling URL was stored
    assert response.id in client._task_polling_urls
    stored_url, timestamp = client._task_polling_urls[response.id]
    assert stored_url == response.polling_url
    assert timestamp > 0
    
    # Test that the correct polling endpoint is returned
    endpoint = client._get_polling_endpoint(response.id)
    assert endpoint == response.polling_url
    
    # Test manual cleanup
    client.clear_polling_urls()
    assert len(client._task_polling_urls) == 0

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

@pytest.mark.parametrize("model", ["flux-pro-1.0-fill"])
@pytest.mark.parametrize("sync", [False, True])
def test_generate_flux_pro_fill_model(model, sync):
    print(f"Using API key: {BFL_API_KEY}")
    client = BFLClient(api_key=BFL_API_KEY)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "test_images", "image.png")
    mask_path = os.path.join(current_dir, "test_images", "mask.png")

    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    with open(mask_path, "rb") as image_file:
        mask_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # Create input as dictionary instead of model instance
    inputs = {
        "image": image_base64,
        "mask": mask_base64,
        "prompt": "A beautiful landscape with mountains and a lake",
        "prompt_upsampling": True,
        "seed": 42,
        "safety_tolerance": 2,
    }
    if model == "flux-pro-1.0-fill":
        inputs.update({"guidance": 30.0, "steps": 30})

    config = ClientConfig(sync=sync)

    # Call generate with dictionary and config
    response = client.generate(model, inputs, config)
    print(f"Response: {response}")

    if sync:
        assert response.id is not None
        assert response.result is not None
    else:
        assert response.id is not None

@pytest.mark.parametrize("model", ["flux-pro-1.0-expand"])
@pytest.mark.parametrize("sync", [False, True])
def test_generate_flux_pro_expand_model(model, sync):
    print(f"Using API key: {BFL_API_KEY}")
    client = BFLClient(api_key=BFL_API_KEY)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "test_images", "image.png")

    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # Create input as dictionary instead of model instance
    inputs = {
        "image": image_base64,
        "top": 10,
        "bottom": 0,
        "left": 0,
        "right": 0,
        "prompt": "A beautiful landscape with mountains and a lake",
        "prompt_upsampling": True,
        "seed": 42,
        "safety_tolerance": 2,
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

@pytest.mark.parametrize("model", ["flux-pro-1.0-canny"])
@pytest.mark.parametrize("sync", [False, True])
def test_generate_flux_pro_canny_model(model, sync):
    print(f"Using API key: {BFL_API_KEY}")
    client = BFLClient(api_key=BFL_API_KEY)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "test_images", "image.png")

    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # Create input as dictionary instead of model instance
    inputs = {
        "control_image": image_base64,
        "prompt": "A beautiful landscape with mountains and a lake",
        "steps": 30,
        "prompt_upsampling": True,
        "seed": 42,
        "guidance": 30.0,
        "safety_tolerance": 2,
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


@pytest.mark.parametrize("model", ["flux-pro-1.0-depth"])
@pytest.mark.parametrize("sync", [False, True])
def test_generate_flux_pro_depth_model(model, sync):
    print(f"Using API key: {BFL_API_KEY}")
    client = BFLClient(api_key=BFL_API_KEY)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "test_images", "image.png")

    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # Create input as dictionary instead of model instance
    inputs =  {
            "control_image": image_base64,
            "prompt": "A beautiful landscape with mountains and a lake",
            "steps": 30,
            "prompt_upsampling": True,
            "seed": 42,
            "guidance": 15.0,
            "safety_tolerance": 2,
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


@pytest.mark.parametrize("model", ["flux-kontext-pro"])
@pytest.mark.parametrize("sync", [False, True])
def test_generate_flux_kontext_pro_model(model, sync):
    print(f"Using API key: {BFL_API_KEY}")
    client = BFLClient(api_key=BFL_API_KEY)

    inputs = {
        "prompt": "Make the 2 animals in a scene having breakfast together",
        "input_image": "tests/inputs/test_image_1.jpeg",
        "input_image_2": "tests/inputs/test_image_2.jpeg",
        "aspect_ratio": "16:9",
        "output_format": "png",
        "seed": 42,
        "safety_tolerance": 2,
        "prompt_upsampling": True,
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