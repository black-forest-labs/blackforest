import os

from blackforest import BFLClient
from blackforest.router_types.api_types import FluxPro11Inputs, OutputFormat

BFL_API_KEY = os.getenv("BFL_API_KEY", "test-key")
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
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Content-Type"] == "application/json"



def test_generate_flux_pro_1_1():
    print(BFL_API_KEY)
    client = BFLClient(api_key=BFL_API_KEY)
    inputs = FluxPro11Inputs(
        prompt="a beautiful sunset over mountains, digital art style",
        width=1024,
        height=768,
        output_format=OutputFormat.jpeg
    )
    print(inputs)
    response = client.generate("flux-pro-1.1", inputs)
    print(response)
    assert response.id is not None
    assert response.polling_url is not None
    assert "poll" in response.polling_url
