import math
from dataclasses import dataclass
import numpy as np
from scipy.spatial import cKDTree
from routes.models import Station
from routes.constants import CORRIDOR_MILES
from routes.constants import EARTH_RADIUS_MILES


@dataclass(frozen=True)
class RouteStation:
    opis_id: int
    name: str
    address: str
    city: str
    state: str
    price: float
    lat: float
    lng: float
    mile: float  # position along the route


class StationLocator:
    """Holds all stations in memory and finds the ones along a route."""

    _shared = None

    def __init__(self, stations, corridor_miles=CORRIDOR_MILES):
        self.stations = stations
        self.corridor_miles = corridor_miles
        self.points = self._to_xyz([s["lat"] for s in stations], [s["lng"] for s in stations])

    @classmethod
    def from_db(cls):
        rows = list(Station.objects.filter(lat__isnull=False, lng__isnull=False)
                    .values("opis_id", "name", "address", "city", "state", "price", "lat", "lng"))
        for row in rows:
            row["price"] = float(row["price"])
        return cls(rows)

    @classmethod
    def shared(cls):
        """One instance per server process, built on first use."""
        if cls._shared is None:
            cls._shared = cls.from_db()
        return cls._shared

    @classmethod
    def reset(cls):
        """Call after reloading stations so the next request rebuilds the index."""
        cls._shared = None

    def along(self, route):
        """Stations within corridor_miles of the route, sorted by mile."""
        tree = cKDTree(self._to_xyz(route.lats, route.lngs))
        distances, nearest = tree.query(self.points, distance_upper_bound=self._miles_to_chord(self.corridor_miles))

        found = [RouteStation(**self.stations[i], mile=float(route.mile_markers[nearest[i]]))
                 for i in np.flatnonzero(np.isfinite(distances))]
        return sorted(found, key=lambda s: (s.mile, s.price))

    @staticmethod
    def _to_xyz(lats, lngs):
        """Lat/lng → points on a unit sphere, so the KD-tree measures true distance."""
        lat, lng = np.radians(lats), np.radians(lngs)
        return np.column_stack((np.cos(lat) * np.cos(lng), np.cos(lat) * np.sin(lng), np.sin(lat)))

    @staticmethod
    def _miles_to_chord(miles):
        return 2 * math.sin(miles / (2 * EARTH_RADIUS_MILES))