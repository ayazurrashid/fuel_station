# Fuel Station Route Planner

A Django REST API that plans the cheapest fuel stops for a road trip within the USA.

Given a start and finish location, it:

1. geocodes both locations,
2. fetches the driving route from [openrouteservice](https://openrouteservice.org/),
3. finds the fuel stations within 10 miles of the route,
4. chooses where to refuel and how many gallons to buy at each stop,

and returns the route geometry, the fuel stops and the total fuel cost.

## Vehicle assumptions

| Setting | Value |
|---|---|
| Maximum range on a full tank | 500 miles |
| Fuel efficiency | 10 miles per gallon |
| Starting fuel | Empty: the first stop must be within 50 miles of the start |

These values, and the other planner settings, are in [`routes/constants.py`](routes/constants.py).

## Tech stack

- Python, Django, Django REST Framework
- drf-spectacular for OpenAPI and Swagger docs
- NumPy and SciPy (KD-tree) for the station search and the fuel planner
- openrouteservice for directions and HeiGIT Pelias for geocoding
- SQLite

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```dotenv
PROJECT_ENV=local
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
ORS_API_KEY=your-openrouteservice-api-key
```

`ORS_API_KEY` is used for both the openrouteservice directions API and the Pelias geocoding API. You can get a free key at [openrouteservice.org](https://openrouteservice.org/dev/#/signup).

`PROJECT_ENV` selects a settings file from `fuel_station/environments/` (`local`, `development`, `staging`, `uat`, `dryrun` or `production`).

Create the database:

```bash
python manage.py migrate
```

## Loading fuel stations

The station prices are in `data_files/fuel-prices-for-be-assessment.csv`. Import them with:

```bash
python manage.py import_stations
```

The command:

- keeps US stations only,
- keeps the lowest price when an OPIS ID appears more than once,
- skips stations already in the database,
- geocodes each city once with Pelias, reusing coordinates already stored for that city.

Stations whose city can't be geocoded are skipped. Running the command again retries them.

## Running the server

```bash
python manage.py runserver
```

| URL | Description |
|---|---|
| `/` | Swagger UI |
| `/api/schema/` | OpenAPI schema |
| `/api/routes/route/` | Trip planner endpoint |
| `/admin/` | Django admin (stations can be browsed and filtered by state) |

## API

### `GET /api/routes/route/`

| Query parameter | Required | Example |
|---|---|---|
| `start` | Yes | `New York, NY` |
| `finish` | Yes | `Los Angeles, CA` |

Locations in `City, ST` form are matched against station cities in the database first. Anything else is sent to Pelias as a free-text search within the USA.

Example:

```bash
curl "http://localhost:8000/api/routes/route/?start=New%20York,%20NY&finish=Los%20Angeles,%20CA"
```

Response:

```json
{
  "start": {"query": "New York, NY", "lat": 40.71, "lng": -74.0},
  "finish": {"query": "Los Angeles, CA", "lat": 34.05, "lng": -118.24},
  "distance_miles": 2789.4,
  "duration_hours": 41.2,
  "total_gallons": 278.94,
  "total_fuel_cost": 921.37,
  "fuel_stops": [
    {
      "opis_id": 123,
      "name": "EXAMPLE TRUCK STOP",
      "address": "I-80, EXIT 1",
      "city": "Newark",
      "state": "NJ",
      "lat": 40.73,
      "lng": -74.17,
      "mile": 12.3,
      "price_per_gallon": 3.199,
      "gallons": 48.5,
      "cost": 155.15
    }
  ],
  "route": {"type": "LineString", "coordinates": [[-74.0, 40.71], "..."]}
}
```

The values above are illustrative. `route` is a GeoJSON LineString with `[lng, lat]` coordinates, and `mile` is each stop's distance along the route.

Errors are returned as `{"error": "..."}`:

| Status | Cause |
|---|---|
| 400 | `start` or `finish` is missing, or a location can't be found |
| 422 | No fuel plan is possible, for example no station within range somewhere on the route |
| 502 | The routing or geocoding service failed |

## How the fuel planner works

The planner is in [`routes/services/fuel.py`](routes/services/fuel.py) and has two strategies, chosen by `USE_STOP_PENALTY` in `routes/constants.py`.

**Stop penalty (default).** A dynamic program over the stations in route order. It minimizes fuel cost plus `STOP_PENALTY_USD` ($10) for each stop, so it won't stop just to save a few cents. The penalty only steers the choice: the reported cost is fuel only. Tank levels are tracked in 0.1-mile steps.

**Greedy.** At each station:

- if a cheaper station is within range, buy just enough to reach it;
- otherwise, if the destination is within range, buy just enough to finish;
- otherwise, fill the tank and go to the cheapest station within range.

This gives the cheapest fuel but may stop often.

In both strategies the tank starts empty. The fuel used to reach the first stop is bought at that stop, so the total cost covers the whole trip.

Routes are cached for 24 hours, so a repeated trip makes no routing API call.

## Project structure

```
fuel_station/            Django project
  components/            Settings split by concern (apps, database, REST, ...)
  environments/          Per-environment settings overrides
routes/                  Main app
  api/                   HTTP clients for openrouteservice and Pelias
  management/commands/   import_stations command
  rest/                  REST API view and URLs
  services/              Geocoding, directions, station lookup, fuel and trip planning
  constants.py           Vehicle, search and planner settings
  models.py              Station model
data_files/              Fuel price CSV
```
