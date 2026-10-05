STATE_MAPPING = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}
STATE_CODES = set(STATE_MAPPING.keys())
STATE_NAMES = set(STATE_MAPPING.values())

COUNTRY_SUFFIXES = {"usa", "us", "united states", "united states of america"}



"""
Constants for trip planning.

Vehicle limits come from the assignment. Search and caching values are design
choices that trade accuracy against speed and API usage. The last two values
are unit conversions.
"""

# External APIs
PELIAS_BASE_URL = "https://api.heigit.org/pelias/v1"
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"

# Vehicle (from the assignment)
MAX_RANGE_MILES = 500
"""Maximum distance on a full tank. Also sets the tank size: 500 / MPG = 50 gallons."""

MPG = 10
"""Fuel efficiency. gallons = miles / MPG; cost = gallons * station price."""

# Station search
CORRIDOR_MILES = 10
"""
Maximum distance from the route for a station to count as on the way.
Stations are geocoded to their city's center, so this buffer covers
highway-exit truck stops a few miles from that point.
"""

START_WINDOW_MILES = 50
"""
The trip starts with an empty tank, so the first fill-up must be at a
station within this many miles of the start. Fuel for the miles driven to
reach it is bought there, so total cost covers the whole trip.
"""

USE_STOP_PENALTY = True
"""
Fuel planner strategy. True: cheapest fuel plus STOP_PENALTY_USD per stop, so
it avoids stopping to save a few cents. False: greedy cheapest fuel, however
many stops.
"""

STOP_PENALTY_USD = 10
"""
Cost of one extra fuel stop (time and detour), used only to choose stops; the
reported total is fuel only. A stop is made only if it saves more than this.
"""

FUEL_STEP_MILES = 0.1
"""Resolution of the fuel planner: tank levels are tracked in 0.1-mile (0.01 gallon) steps."""

# Caching
ROUTE_CACHE_SECONDS = 24 * 3600
"""How long a route is cached. A repeated trip within 24 hours makes no routing API call."""

# Unit conversions
EARTH_RADIUS_MILES = 3958.8
"""Mean Earth radius, used by the haversine and KD-tree distance calculations."""

METERS_PER_MILE = 1609.344
"""openrouteservice returns distance in meters; divide by this to get miles."""