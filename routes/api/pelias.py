import time

import requests
from routes.constants import PELIAS_BASE_URL
from routes.services import TripException
REQUEST_INTERVAL = 0.7  # seconds; stays under the 100 requests/minute limit


class PeliasClient:
    """HTTP client for the HeiGIT Pelias geocoding API. Returns (lat, lng) or None."""

    def __init__(self, api_key, base_url=PELIAS_BASE_URL, timeout=10):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(self, text):
        """Free-text search, e.g. 'Times Square, New York'."""
        return self._first_match(
            "search",
            {"text": text, "boundary.country": "USA", "size": 1},
        )

    def search_structured(self, city, state):
        """City/state search. Only accepts a result in the requested state."""
        return self._first_match(
            "search/structured",
            {"locality": city, "region": state, "country": "USA", "size": 1},
            expected_state=state,
        )

    def _first_match(self, endpoint, params, expected_state=None):
        features = self._get(endpoint, params).get("features", [])
        if not features:
            return None

        feature = features[0]
        if expected_state and feature["properties"].get("region_a") != expected_state:
            return None

        lng, lat = feature["geometry"]["coordinates"]
        return lat, lng

    def _get(self, endpoint, params):
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                headers={"Authorization": self.api_key},
                timeout=self.timeout,
            )
            print("status", response.status_code)
            if response.status_code == 429:
                time.sleep(REQUEST_INTERVAL)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise TripException("Geocoding service is unavailable.", status=502)