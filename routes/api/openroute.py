import requests
from routes.constants import METERS_PER_MILE
from routes.constants import ORS_DIRECTIONS_URL
from routes.services import TripException


class OpenRouteClient:
    """HTTP client for openrouteservice driving directions."""

    def __init__(self, api_key, url=ORS_DIRECTIONS_URL, timeout=30):
        self.api_key = api_key
        self.url = url
        self.timeout = timeout

    def directions(self, start, finish):
        """
        start/finish are (lat, lng).
        Returns {"coordinates": [[lng, lat], ...], "miles": float, "hours": float}.
        """
        try:
            response = requests.post(
                self.url,
                json={
                    "coordinates": [[start[1], start[0]], [finish[1], finish[0]]],
                    "radiuses": [-1, -1],  # snap to the nearest road however far; city centers can be off-road
                },
                headers={"Authorization": self.api_key},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TripException("Routing service is unavailable.", status=502) from exc

        if response.status_code != 200:
            raise TripException(f"Routing failed: {response.text[:200]}", status=502)

        feature = response.json()["features"][0]
        summary = feature["properties"]["summary"]
        return {
            "coordinates": feature["geometry"]["coordinates"],
            "miles": summary["distance"] / METERS_PER_MILE,
            "hours": summary["duration"] / 3600,
        }