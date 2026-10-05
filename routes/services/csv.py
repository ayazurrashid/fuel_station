import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from routes.constants import STATE_CODES


class StationCSVService:
    """Read, validate, clean, and deduplicate fuel station CSV data."""

    def __init__(self, csv_path: Path):
        self.csv_path = csv_path

    def read(self):
        """
        Read stations from CSV.

        Returns:
            tuple[list[dict], int, int]:
                cleaned station rows, skipped non-US rows, bad rows.
        """
        by_id = {}
        skipped_non_us = 0
        bad_rows = 0

        with self.csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)

            for raw_row in reader:
                row = self._clean_row(raw_row)

                state = row["State"].upper()

                if state not in STATE_CODES:
                    skipped_non_us += 1
                    continue

                station = self._build_station(row)

                if station is None:
                    bad_rows += 1
                    continue

                opis_id = station["opis_id"]
                current = by_id.get(opis_id)

                # Keep the lowest retail price for a station.
                if current is None or station["price"] < current["price"]:
                    by_id[opis_id] = station

        return list(by_id.values()), skipped_non_us, bad_rows

    @staticmethod
    def _clean_row(raw_row):
        """Normalize CSV column names and values."""
        return {
            key.strip(): (value or "").strip()
            for key, value in raw_row.items()
        }

    @staticmethod
    def _build_station(row):
        """Validate and convert a CSV row into a Station-compatible dict."""
        try:
            opis_id = int(row["OPIS Truckstop ID"])
            price = Decimal(row["Retail Price"])
        except (ValueError, InvalidOperation):
            return None

        if price < 0:
            return None

        rack_id = (
            int(row["Rack ID"])
            if row["Rack ID"].isdigit()
            else None
        )

        return {
            "opis_id": opis_id,
            "name": row["Truckstop Name"],
            "address": row["Address"],
            "city": row["City"],
            "state": row["State"].upper(),
            "rack_id": rack_id,
            "price": price,
        }