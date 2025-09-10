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
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Content-Type"] == "application/json"
