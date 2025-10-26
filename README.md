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

import os

# For synchronous API call (great for testing, but please use "production" for async calls, for faster throughput)
os.environ["BFL_ENV"] = "dev"  

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

# For Flux Kontext Pro with reference images
kontext_inputs = {
        "prompt": "A beautiful landscape in the style of the reference image",
        "input_image": "path/to/reference/image.jpg",  # File path (auto-encoded) or base64
        "input_image_2": "path/to/another/image.png",  # Optional multiref (experimental)
        "aspect_ratio": "16:9",  # Between 1:4 and 4:1
        "output_format": "png",
        "seed": 42,  # Optional for reproducibility
        "safety_tolerance": 2,  # 0-6, higher = less strict
        "prompt_upsampling": True  # Enhanced prompt processing
    }
response = client.generate("flux-kontext-pro", kontext_inputs)
```

## Features

- Official Python interface for Black Forest Labs API
- Automatic request handling and response parsing
- Type hints for better IDE support
- Support for all Flux models including Flux Kontext Pro with multi-reference capabilities

## Supported Models

- `flux-dev` - Development model
- `flux-pro` - Professional model 
- `flux-pro-1.1` - Enhanced professional model
- `flux-pro-1.1-ultra` - Ultra high-quality model
- `flux-kontext-pro` - Context-aware model with reference image support and experimental multi-reference capabilities
- `flux-pro-1.0-fill` - Image inpainting model
- `flux-pro-1.0-expand` - Image expansion model
- `flux-pro-1.0-canny` - Canny edge-guided model
- `flux-pro-1.0-depth` - Depth-guided model

## Requirements

- Python 3.10+
- requests>=2.31.0
- pydantic>=2.0.0
- pillow>=10.0.0
- python-dotenv>=0.21.1


## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 