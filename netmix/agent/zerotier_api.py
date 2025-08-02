import logging
import requests
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class ZeroTierAPIError(Exception):
    """Custom exception for ZeroTier API errors."""
    pass

class ZeroTierAPI:
    """A client for the ZeroTier One local JSON API."""

    def __init__(self, api_url=None, auth_token=None):
        """
        Initializes the API client.

        Pulls configuration from environment variables by default, but can be
        overridden with direct arguments.
        """
        import os # Local import for debugging
        self.api_url = api_url or os.getenv('ZT_API', 'http://127.0.0.1:9993')
        self._auth_token = auth_token or os.getenv('ZT_TOKEN')

        if not self._auth_token:
            self._auth_token = self._load_token_from_file()

        if not self._auth_token:
            raise ZeroTierAPIError("ZeroTier auth token not found. Please set ZT_TOKEN or ensure authtoken.secret exists.")

        self.session = requests.Session()
        self.session.headers.update({'X-ZT1-Auth': self._auth_token})
        logging.info(f"ZeroTier API client initialized for endpoint: {self.api_url}")

    def _load_token_from_file(self):
        """Loads the auth token from the default location on Windows."""
        import os # Local import for debugging
        if os.name != 'nt':
            return None # This path is specific to Windows

        token_path = r"C:\ProgramData\ZeroTier\One\authtoken.secret"
        try:
            with open(token_path, 'r') as f:
                token = f.read().strip()
                logging.info(f"Loaded ZeroTier auth token from {token_path}")
                return token
        except FileNotFoundError:
            logging.warning(f"Could not find ZeroTier auth token at {token_path}")
            return None
        except Exception as e:
            logging.error(f"Error reading ZeroTier auth token file: {e}")
            return None

    def _request(self, method, endpoint, **kwargs):
        """Makes a request to the ZeroTier API and handles errors."""
        url = f"{self.api_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=5, **kwargs)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP Error for {method} {url}: {e.response.status_code} {e.response.text}")
            raise ZeroTierAPIError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for {method} {url}: {e}")
            raise ZeroTierAPIError(f"Request failed: {e}") from e

    def get_status(self):
        """Gets the status of the local ZeroTier node."""
        return self._request('GET', '/status')

    def list_networks(self):
        """Lists all networks the local node has joined."""
        return self._request('GET', '/network')

    def get_network(self, network_id):
        """Gets detailed information for a specific joined network."""
        return self._request('GET', f'/network/{network_id}')

    def join_network(self, network_id):
        """Joins a network."""
        return self._request('POST', f'/network/{network_id}', json={})

    def leave_network(self, network_id):
        """Leaves a network."""
        return self._request('DELETE', f'/network/{network_id}')

    def get_virtual_ip(self, network_id):
        """
        Helper method to get the first assigned virtual IPv4 address for a network.

        Returns:
            str or None: The IPv4 address if found, otherwise None.
        """
        try:
            network_info = self.get_network(network_id)
            if network_info and network_info.get('assignedAddresses'):
                for addr in network_info['assignedAddresses']:
                    # Simple check for IPv4
                    if '.' in addr:
                        return addr.split('/')[0] # Remove CIDR suffix
            return None
        except ZeroTierAPIError:
            return None
