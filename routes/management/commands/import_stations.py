import csv
import os
import time
from decimal import Decimal

from decouple import config
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from fuel_station.components.common import BASE_DIR
from routes.constants import STATE_CODES
from routes.models import Station
from routes.api import PeliasClient
from routes.services import StationLocator

CSV_PATH = BASE_DIR / "data_files" / "fuel-prices-for-be-assessment.csv"


def city_key(city, state):
    """'  Fort   Wayne ', 'in' -> ('fort wayne', 'IN')"""
    return " ".join(city.split()).casefold(), state.strip().upper()


class Command(BaseCommand):
    help = "Load fuel stations from the CSV, geocoding only cities without known coordinates."

    def handle(self, *args, **options):
        api_key = config('ORS_API_KEY')
        if not api_key:
            raise CommandError("ORS_API_KEY environment variable is not set.")
        self.pelias = PeliasClient(api_key, timeout=30)

        coords = self.known_coords()
        stations = self.read_csv()

        for station in stations:
            key = city_key(station["city"], station["state"])
            print(key)
            if key not in coords:
                coords[key] = self.geocode(*key)  # None = not found; still cached so it isn't retried
            if coords[key]:
                station["lat"], station["lng"] = coords[key]
                Station.objects.create(**station)

        StationLocator.reset()
        self.stdout.write(self.style.SUCCESS(f"Saved stations."))

    def known_coords(self):
        """Coordinates already in the database, keyed by city."""
        return {
            city_key(city, state): (lat, lng)
            for city, state, lat, lng in Station.objects.filter(lat__isnull=False, lng__isnull=False)
            .values_list("city", "state", "lat", "lng")
        }

    def read_csv(self):
        """US stations only, one per OPIS ID, keeping the lowest price."""
        stations = {}
        opis_id_list = list(Station.objects.all().values_list("opis_id", flat=True))
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                state = row["State"].strip().upper()
                if state not in STATE_CODES:
                    continue
                opis_id = int(row["OPIS Truckstop ID"])
                price = Decimal(row["Retail Price"])
                if opis_id in stations and stations[opis_id]["price"] <= price:
                    continue
                if opis_id in opis_id_list:
                    print('Skipping', opis_id)
                    continue
                stations[opis_id] = {
                    "opis_id": opis_id,
                    "name": row["Truckstop Name"].strip(),
                    "address": row["Address"].strip(),
                    "city": " ".join(row["City"].split()),
                    "state": state,
                    "rack_id": int(row["Rack ID"]),
                    "price": price,
                }
        return list(stations.values())

    def geocode(self, city, state):
        coords = self.pelias.search_structured(city, state)
        if coords is None:
            self.stdout.write(self.style.WARNING(f"Not found: {city}, {state}"))
        return coords