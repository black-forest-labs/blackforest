import pytest
from blackforest import BFLClient, BFLError

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

# Add test for alternative import
def test_alternative_import():
    from blackforestlabs import BFLClient
    client = BFLClient(api_key="test-key")
    assert client.api_key == "test-key"
