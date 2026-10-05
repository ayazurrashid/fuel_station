import numpy as np
from dataclasses import dataclass
from dataclasses import field
from django.core.cache import cache
from routes.constants import EARTH_RADIUS_MILES
from routes.constants import ROUTE_CACHE_SECONDS


@dataclass
class Route:
    coordinates: list  # [[lng, lat], ...]
    miles: float
    hours: float
    lats: np.ndarray = field(init=False, repr=False)
    lngs: np.ndarray = field(init=False, repr=False)
    mile_markers: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        self.lngs, self.lats = np.array(self.coordinates, dtype=float).T
        markers = self._cumulative_miles(self.lats, self.lngs)
        # align the haversine distances with the routing API's road distance
        self.mile_markers = markers * (self.miles / markers[-1]) if markers[-1] > 0 else markers

    def to_geojson(self):
        return {"type": "LineString", "coordinates": self.coordinates}

    @staticmethod
    def _cumulative_miles(lats, lngs):
        lat, lng = np.radians(lats), np.radians(lngs)
        a = np.sin(np.diff(lat) / 2) ** 2 + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin(np.diff(lng) / 2) ** 2
        return np.concatenate(([0.0], np.cumsum(2 * EARTH_RADIUS_MILES * np.arcsin(np.sqrt(a)))))


class DirectionsService:
    """Gets a Route between two Locations. One API call per new trip, cached afterwards."""

    def __init__(self, client, cache_seconds=ROUTE_CACHE_SECONDS):
        self.client = client
        self.cache_seconds = cache_seconds

    def get_route(self, start, finish):
        cache_key = "route:{:.5f},{:.5f}:{:.5f},{:.5f}".format(*start.coords, *finish.coords)
        data = cache.get(cache_key)
        if data is None:
            data = self.client.directions(start.coords, finish.coords)
            cache.set(cache_key, data, self.cache_seconds)
        return Route(**data)