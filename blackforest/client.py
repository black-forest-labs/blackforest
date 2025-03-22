"""
Main client implementation for the BFL API.
"""

import base64
import os
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from urllib.parse import urljoin

import requests
from .router_types.api_types import ImageInput, ImageProcessingResponse

class BFLError(Exception):
    """Base exception for BFL API errors."""
    pass

class BFLClient:
    """
    Main client class for interacting with the Black Forest Labs API.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.us1.bfl.ai",  # Update this
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
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

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
            endpoint: API endpoint
            params: URL parameters
            data: Form data
            json: JSON data

        Returns:
            API response as dictionary

        Raises:
            BFLError: If the API request fails
        """
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
                        raise BFLError(f"Error processing image {file_name} from zip: {str(e)}")
        
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
        
        return ImageProcessingResponse(
            task_id=response.get("id"),
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
        response = self._request("GET", f"/v1/get_result?id={task_id}")
        
        return ImageProcessingResponse(
            task_id=task_id,
            status=response.get("status", "unknown"),
            result=response.get("result"),
            error=response.get("error")
        )

    # Add your API endpoint methods here
    # For example:
    # def get_user(self, user_id: str) -> Dict[str, Any]:
    #     return self._request("GET", f"/users/{user_id}") 