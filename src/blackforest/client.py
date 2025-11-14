"""
Main client implementation for the BFL API.
"""

import base64
import os
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import requests

from blackforest.resources.mapping.model_input_registry import MODEL_INPUT_REGISTRY
from blackforest.types.general.client_config import ClientConfig
from blackforest.types.inputs.generic import ImageInput
from blackforest.types.responses.responses import (
    AsyncResponse,
    ImageProcessingResponse,
    SyncResponse,
)


class BFLError(Exception):
    """Base exception for BFL API errors."""
    pass

class BFLClient:
    """
    Main client class for interacting with the Black Forest Labs API.
    """

    # Model to input type mapping registry
    model_input_registry = MODEL_INPUT_REGISTRY
    api_version = "v1"
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.bfl.ai",
        timeout: int = 30,
    ):
        """
        Initialize the BFL client.

        Args:
            api_key: Your BFL API key
            base_url: Base URL for the API (optional)
            timeout: Request timeout in seconds (optional)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'X-Key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        # Map to store task_id -> (polling_url, timestamp)
        self._task_polling_urls = {}

    def _cleanup_expired_polling_urls(self) -> None:
        """
        Remove polling URL entries that are older than 30 minutes.
        """
        current_time = time.time()
        expired_keys = []
        
        for task_id, (polling_url, timestamp) in self._task_polling_urls.items():
            # Remove entries older than 30 minutes (1800 seconds)
            if current_time - timestamp > 1800:
                expired_keys.append(task_id)
        
        for key in expired_keys:
            del self._task_polling_urls[key]

    def clear_polling_urls(self) -> None:
        """
        Manually clear all stored polling URLs.
        """
        self._task_polling_urls.clear()

    def _get_polling_endpoint(self, task_id: str) -> str:
        """
        Get the appropriate polling endpoint for a task.
        
        Args:
            task_id: The task ID to get the endpoint for
            
        Returns:
            The endpoint (relative path or full URL) to use for polling
        """
        # Clean up expired entries
        self._cleanup_expired_polling_urls()
        
        if task_id in self._task_polling_urls:
            polling_url, _ = self._task_polling_urls[task_id]  # Extract URL from tuple
            # Return the full polling URL as-is since _request() now handles full URLs
            return polling_url
        else:
            # Fallback to constructed URL
            return f"/v1/get_result?id={task_id}"

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a request to the API.

        Args:
            method: HTTP method
            endpoint: API endpoint (can be a relative path or full URL)
            params: URL parameters
            data: Form data
            json: JSON data

        Returns:
            API response as dictionary

        Raises:
            BFLError: If the API request fails
        """
        # If endpoint is already a full URL, use it directly
        if endpoint.startswith(('http://', 'https://')):
            url = endpoint
        else:
            url = urljoin(self.base_url, endpoint)

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if response is not None:
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', str(e))
                except ValueError:
                    error_message = response.text or str(e)
            else:
                error_message = str(e)

            raise BFLError(f"API request failed: {error_message}") from e

    def _encode_image(self, image_path: str) -> str:
        """Encode image file to base64 string."""
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _is_file_path(self, value: str) -> bool:
        """Check if a string is a file path (not base64 or URL)."""
        if value.startswith(('http://', 'https://')):
            return False
        # Check if it looks like base64 (no path separators, mostly alphanumeric with +/=)
        if '/' not in value and '\\' not in value and len(value) > 100:
            try:
                base64.b64decode(value)
                return False  # It's valid base64
            except Exception:
                pass
        # Check if file exists
        return os.path.exists(value)

    def _process_kontext_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process flux-kontext-pro inputs to automatically encode image paths."""
        processed_inputs = inputs.copy()
        
        # Image fields that might need encoding
        image_fields = ['input_image', 'input_image_2', 'input_image_3', 'input_image_4']
        
        for field in image_fields:
            if field in processed_inputs and processed_inputs[field]:
                value = processed_inputs[field]
                if isinstance(value, str) and self._is_file_path(value):
                    try:
                        processed_inputs[field] = self._encode_image(value)
                    except Exception as e:
                        raise BFLError(f"Error encoding image file '{value}' for field '{field}': {str(e)}")
        
        return processed_inputs

    def _process_folder(self, folder_path: str) -> List[str]:
        """Process all images in a folder and return list of base64 encoded images."""
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise BFLError(f"Invalid folder path: {folder_path}")

        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        encoded_images = []

        for file_path in folder.glob('*'):
            if file_path.suffix.lower() in image_extensions:
                try:
                    encoded_images.append(self._encode_image(str(file_path)))
                except Exception as e:
                    raise BFLError(f"Error processing image {file_path}: {str(e)}")

        return encoded_images

    def _process_zip(self, zip_path: str) -> List[str]:
        """Process all images in a zip file and return list of base64 encoded images."""
        if not os.path.exists(zip_path):
            raise BFLError(f"Invalid zip file path: {zip_path}")

        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        encoded_images = []

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_name in zip_ref.namelist():
                if Path(file_name).suffix.lower() in image_extensions:
                    try:
                        with zip_ref.open(file_name) as image_file:
                            encoded_images.append(base64.b64encode(image_file.read()).decode('utf-8'))
                    except Exception as e:
                        raise BFLError(f"Error processing image {file_name} \
                                        from zip: {str(e)}")

        return encoded_images

    def process_image(
        self,
        input_data: Union[str, ImageInput],
        endpoint: str = "/v1/image",
        **kwargs
    ) -> ImageProcessingResponse:
        """
        Process an image or multiple images using the specified endpoint.

        Args:
            input_data: Either a path to an image file or an ImageInput object
            endpoint: The API endpoint to use for processing
            **kwargs: Additional parameters to pass to the API

        Returns:
            ImageProcessingResponse containing task ID and status

        Raises:
            BFLError: If there's an error processing the images
        """
        if isinstance(input_data, str):
            # If input_data is a string, assume it's a path to an image
            input_data = ImageInput(image_path=input_data)

        if not isinstance(input_data, ImageInput):
            raise BFLError("input_data must be either a string or an ImageInput object")

        # Process the input based on the provided type
        if input_data.image_path:
            image_data = self._encode_image(input_data.image_path)
        elif input_data.folder_path:
            image_data = self._process_folder(input_data.folder_path)
        elif input_data.zip_path:
            image_data = self._process_zip(input_data.zip_path)
        elif input_data.image_data:
            image_data = input_data.image_data
        else:
            raise BFLError("No valid image input provided")

        # Prepare the request payload
        payload = {
            "image": image_data,
            **kwargs
        }

        # Make the API request
        response = self._request("POST", endpoint, json=payload)

        # Store the polling URL for this task if available
        task_id = response.get("id")
        if task_id and "polling_url" in response:
            # Clean up expired entries before adding new one
            self._cleanup_expired_polling_urls()
            self._task_polling_urls[task_id] = (response["polling_url"], time.time())

        return ImageProcessingResponse(
            task_id=task_id,
            status="submitted",
            result=response
        )

    def get_task_status(self, task_id: str) -> ImageProcessingResponse:
        """
        Get the status of a processing task.

        Args:
            task_id: The ID of the task to check

        Returns:
            ImageProcessingResponse containing current status and result if available
        """
        endpoint = self._get_polling_endpoint(task_id)
        response = self._request("GET", endpoint)

        return ImageProcessingResponse(
            task_id=task_id,
            status=response.get("status", "unknown"),
            result=response.get("result"),
            error=response.get("error")
        )

    def get_polling_result(
        self,
        task_id: str,
        config: Optional[ClientConfig] = None,
    ) -> Dict[str, Any]:
        """
        Poll for results until they are ready or until timeout.

        Args:
            task_id: The ID of the task to poll for
            config: Optional configuration for polling behavior

        Returns:
            The final result from the API

        Raises:
            BFLError: If polling times out or the API request fails
        """
        if config is None:
            config = ClientConfig()

        start_time = time.time()
        attempts = 0

        while attempts < config.max_retries:
            print(f"Polling task {task_id} for result. \
                  Attempt {attempts + 1} of {config.max_retries}")
            
            endpoint = self._get_polling_endpoint(task_id)
            response = self._request("GET", endpoint)

            # Check if the task is complete
            if response.get("status") in ["Ready", "completed", "failed"]:
                if response.get("status") == "failed":
                    error_msg = response.get('error', 'Unknown error')
                    raise BFLError(f"Task failed: {error_msg}")
                return response.get("result", {})

            # Check for timeout
            if config.timeout and (time.time() - start_time > config.timeout):
                raise BFLError(f"Polling timed out after {config.timeout} seconds")

            # Sleep before next attempt
            time.sleep(config.polling_interval)
            attempts += 1

        raise BFLError(f"Polling exceeded maximum retries ({config.max_retries})")

    def generate(
        self,
        model: str,
        inputs: Dict[str, Any],
        config: Optional[ClientConfig] = None,
        track_usage: bool = False,
    ) -> Union[AsyncResponse, SyncResponse, Dict[str, Any]]:
        """
        Generate an image using model

        Args:
            model: The model to use for generation, eg "flux-pro-1.1"
            inputs: Dictionary containing generation parameters
            config: Optional configuration for client behavior
            track_usage: Whether to track usage for licensed models (default: False)

        Returns:
            AsyncResponse containing task ID and polling URL
            OR
            SyncResponse containing actual results

        Raises:
            BFLError: If the API request fails

        Examples:
            >>> from blackforest import BFLClient
            >>> from blackforest.types.general.client_config import ClientConfig
            >>> client = BFLClient(api_key="your-api-key")
            >>>
            >>> # Asynchronous request (default)
            >>> response = client.generate("flux-pro-1.1", \
                                            {"prompt": "a beautiful forest"})
            >>> print(f"Task ID: {response.id}")
            >>>
            >>> # Synchronous request with polling
            >>> config = ClientConfig(sync=True, timeout=120)
            >>> response = client.generate("flux-pro-1.1", \
                                        {"prompt": "a beautiful forest"},
                                        config)
            >>> print(f"Image URL: {response.result['sample']}")
        """
        if config is None:
            config = ClientConfig()

        # Get the appropriate input type from the registry
        input_cls = self.model_input_registry.get(model)
        if not input_cls:
            raise BFLError(f"Model {model} not supported. \
                           Supported models: {list(self.model_input_registry.keys())}")

        # Process inputs for automatic image encoding if using flux-kontext-pro
        processed_inputs = inputs
        if model == "flux-kontext-pro":
            processed_inputs = self._process_kontext_inputs(inputs)

        # Convert the inputs to the appropriate type
        typed_inputs = input_cls(**processed_inputs)

        response = self._request("POST", f"{self.api_version}/{model}",
                                  json=typed_inputs.model_dump(exclude_none=True))

        # Store the polling URL for this task
        task_id = response["id"]
        if "polling_url" in response:
            # Clean up expired entries before adding new one
            self._cleanup_expired_polling_urls()
            self._task_polling_urls[task_id] = (response["polling_url"], time.time())

        # Track usage if requested
        if track_usage:
            self.track_usage_via_api(model, 1)

        # If sync is True, poll for results
        if config.sync:
            try:
                result = self.get_polling_result(task_id, config)
                return SyncResponse(
                    id=task_id,
                    result=result
                )
            except Exception as e:
                raise BFLError(f"Error getting synchronous result: {str(e)}")

        else:
            return AsyncResponse(
                id=task_id,
                polling_url=response["polling_url"]
            )

    def track_usage_via_api(self, name: str, n: int = 1) -> None:
        """
        Track usage of licensed models via the BFL API for commercial licensing compliance.

        Args:
            name: The model name to track usage for
            n: Number of generations to track (default: 1)

        Raises:
            BFLError: If the API request fails or model is not trackable

        For more information on licensing BFL's models for commercial use and usage reporting,
        see the README.md or visit: https://dashboard.bfl.ai/licensing/subscriptions?showInstructions=true
        """
        model_slug_map = {
            "flux-dev": "flux-1-dev",
            "flux-dev-kontext": "flux-1-kontext-dev",
            "flux-dev-fill": "flux-tools",
            "flux-dev-depth": "flux-tools",
            "flux-dev-canny": "flux-tools",
            "flux-dev-canny-lora": "flux-tools",
            "flux-dev-depth-lora": "flux-tools",
            "flux-dev-redux": "flux-tools",
        }

        if name not in model_slug_map:
            raise BFLError(f"Cannot track usage for model '{name}'. Model not trackable or name incorrect. "
                          f"Trackable models: {list(model_slug_map.keys())}")

        model_slug = model_slug_map[name]
        endpoint = f"/v1/licenses/models/{model_slug}/usage"
        payload = {"number_of_generations": n}

        try:
            self._request("POST", endpoint, json=payload)
            print(f"Successfully tracked usage for {name} with {n} generations")
        except BFLError as e:
            raise BFLError(f"Failed to track usage for {name}: {str(e)}")