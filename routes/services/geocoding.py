import re
from dataclasses import dataclass

from ..models import Station
from .exceptions import TripException


@dataclass(frozen=True)
class Location:
    query: str
    lat: float
    lng: float

    @property
    def coords(self):
        return self.lat, self.lng

    def to_dict(self):
        return {"query": self.query, "lat": self.lat, "lng": self.lng}


class Geocoder:
    """Turns 'City, ST' into a Location. Uses station coordinates in the DB first, Pelias only if missing."""

    CITY_STATE = re.compile(r"\s*(.+?)\s*,\s*([A-Za-z]{2})\s*")

    def __init__(self, pelias):
        self.pelias = pelias

    def geocode(self, query):
        coords = self._from_stations(query) or self.pelias.search(query)
        if coords is None:
            raise TripException(f"Location not found in the USA: {query}")
        return Location(query, *coords)

    def _from_stations(self, query):
        match = self.CITY_STATE.fullmatch(query)
        if not match:
            return None
        city, state = " ".join(match.group(1).split()), match.group(2).upper()
        return (Station.objects.filter(city__iexact=city, state=state, lat__isnull=False)
                .values_list("lat", "lng").first())