import os
from dataclasses import dataclass
from decouple import config

from routes.services import DirectionsService
from routes.services import FuelPlanner
from routes.services import Geocoder
from routes.services import StationLocator


@dataclass
class TripPlan:
    start: object   # Location
    finish: object  # Location
    route: object   # Route
    stops: list     # [FuelStop]
    mpg: float

    @property
    def total_cost(self):
        return sum(s.cost for s in self.stops)

    def to_dict(self):
        return {
            "start": self.start.to_dict(),
            "finish": self.finish.to_dict(),
            "distance_miles": round(self.route.miles, 1),
            "duration_hours": round(self.route.hours, 1),
            "total_gallons": round(self.route.miles / self.mpg, 2),
            "total_fuel_cost": round(self.total_cost, 2),
            "fuel_stops": [s.to_dict() for s in self.stops],
            "route": self.route.to_geojson(),
        }


class TripPlanner:
    """Geocode → route → stations along the route → cheapest fuel stops."""

    def __init__(self, geocoder=None, directions=None, locator=None, fuel_planner=None):
        from routes.api import OpenRouteClient
        from routes.api import PeliasClient
        api_key = config("ORS_API_KEY", "")
        self.geocoder = geocoder or Geocoder(PeliasClient(api_key))
        self.directions = directions or DirectionsService(OpenRouteClient(api_key))
        self.locator = locator or StationLocator.shared()
        self.fuel_planner = fuel_planner or FuelPlanner()

    def plan(self, start, finish):
        start_loc = self.geocoder.geocode(start)
        finish_loc = self.geocoder.geocode(finish)
        route = self.directions.get_route(start_loc, finish_loc)
        stations = self.locator.along(route)
        stops = self.fuel_planner.plan(stations, route.miles)
        return TripPlan(start_loc, finish_loc, route, stops, self.fuel_planner.mpg)