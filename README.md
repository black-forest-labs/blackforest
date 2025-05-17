# BFL Client - Black Forest Labs API Client

A Python client for interacting with the Black Forest Labs API.

## Installation

You can install the package using either name:

```bash
pip install blackforest
```

## Quick Start

```python
# You can import using either name
from blackforest import BFLClient
# or
from blackforestlabs import BFLClient

# Initialize the client
client = BFLClient(api_key="your-api-key")

# Use the client to make API calls
inputs = {
        "prompt": "a beautiful sunset over mountains, digital art style",
        "width": 1024,
        "height": 768,
        "output_format": "jpeg"
    }
response = client.generate("flux-pro-1.1", inputs)
```

## Features

- Official Python interface for Black Forest Labs API
- Automatic request handling and response parsing
- Type hints for better IDE support

## Requirements

- Python 3.7+
- requests>=2.31.0
- pydantic>=2.0.0,
- pillow==10.4.0,


## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 