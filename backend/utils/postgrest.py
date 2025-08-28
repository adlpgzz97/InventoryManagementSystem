"""
PostgREST utilities for Inventory Management System
Handles API requests to PostgREST with error handling and retry logic
"""

import requests
import json
import logging
from typing import Dict, Any, Optional, Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_config

# Configure logging
logger = logging.getLogger(__name__)


class PostgRESTClient:
    """PostgREST API client with retry logic and error handling"""
    
    def __init__(self, base_url: str = None):
        self.config = get_config()
        self.base_url = base_url or self.config.POSTGREST_URL
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, 
                     headers: Dict = None) -> Optional[Dict]:
        """Make HTTP request to PostgREST API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Default headers
        default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, headers=default_headers)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=default_headers, json=data)
            elif method.upper() == 'PATCH':
                response = self.session.patch(url, headers=default_headers, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=default_headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Handle response
            response.raise_for_status()
            
            # Return JSON if content exists
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"PostgREST request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in PostgREST request: {e}")
            return None
    
    def get(self, endpoint: str, headers: Dict = None) -> Optional[Dict]:
        """Make GET request"""
        return self._make_request('GET', endpoint, headers=headers)
    
    def post(self, endpoint: str, data: Dict = None, headers: Dict = None) -> Optional[Dict]:
        """Make POST request"""
        return self._make_request('POST', endpoint, data=data, headers=headers)
    
    def patch(self, endpoint: str, data: Dict = None, headers: Dict = None) -> Optional[Dict]:
        """Make PATCH request"""
        return self._make_request('PATCH', endpoint, data=data, headers=headers)
    
    def delete(self, endpoint: str, headers: Dict = None) -> Optional[Dict]:
        """Make DELETE request"""
        return self._make_request('DELETE', endpoint, headers=headers)


# Global PostgREST client instance
_postgrest_client = None


def get_postgrest_client() -> PostgRESTClient:
    """Get or create PostgREST client instance"""
    global _postgrest_client
    
    if _postgrest_client is None:
        _postgrest_client = PostgRESTClient()
    
    return _postgrest_client


def postgrest_request(endpoint: str, method: str = 'GET', data: Dict = None) -> Optional[Dict]:
    """
    Make request to PostgREST API (backward compatibility function)
    
    Args:
        endpoint: API endpoint
        method: HTTP method (GET, POST, PATCH, DELETE)
        data: Request data for POST/PATCH requests
    
    Returns:
        Response data as dictionary or None if request failed
    """
    client = get_postgrest_client()
    
    if method.upper() == 'GET':
        return client.get(endpoint)
    elif method.upper() == 'POST':
        return client.post(endpoint, data)
    elif method.upper() == 'PATCH':
        return client.patch(endpoint, data)
    elif method.upper() == 'DELETE':
        return client.delete(endpoint)
    else:
        logger.error(f"Unsupported HTTP method: {method}")
        return None


def test_postgrest_connection() -> bool:
    """Test PostgREST connection"""
    try:
        client = get_postgrest_client()
        response = client.get('')
        return response is not None
    except Exception as e:
        logger.error(f"PostgREST connection test failed: {e}")
        return False
