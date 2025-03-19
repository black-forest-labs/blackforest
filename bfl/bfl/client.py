"""
Main client implementation for the BFL API.
"""

import requests
from typing import Optional, Dict, Any, Union
from urllib.parse import urljoin

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

    # Add your API endpoint methods here
    # For example:
    # def get_user(self, user_id: str) -> Dict[str, Any]:
    #     return self._request("GET", f"/users/{user_id}") 