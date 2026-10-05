from routes.models import Station


class StationService:
    """Handle persistence of fuel station records."""

    def create_stations(self, station_rows, coordinates, batch_size=100):
        """
        Create Station objects using bulk_create.

        Coordinates are expected in the format:
            {(city, state): (latitude, longitude)}
        """
        station_objects = [
            self._build_station(row, coordinates)
            for row in station_rows
        ]

        return Station.objects.bulk_create(
            station_objects,
            batch_size=batch_size,
        )

    @staticmethod
    def _build_station(row, coordinates):
        """Convert a cleaned station row into a Station model instance."""
        latitude, longitude = coordinates.get(
            (row["city"], row["state"]),
            (None, None),
        )

        return Station(
            **row,
            lat=latitude,
            lng=longitude,
        )