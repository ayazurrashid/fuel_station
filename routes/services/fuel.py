from dataclasses import dataclass
from itertools import takewhile

import numpy as np

from routes.constants import FUEL_STEP_MILES
from routes.constants import MAX_RANGE_MILES
from routes.constants import MPG
from routes.constants import START_WINDOW_MILES
from routes.constants import STOP_PENALTY_USD
from routes.constants import USE_STOP_PENALTY
from routes.services import TripException


@dataclass(frozen=True)
class FuelStop:
    station: object  # RouteStation
    gallons: float
    cost: float

    def to_dict(self):
        s = self.station
        return {
            "opis_id": s.opis_id,
            "name": s.name,
            "address": s.address,
            "city": s.city,
            "state": s.state,
            "lat": s.lat,
            "lng": s.lng,
            "mile": round(s.mile, 1),
            "price_per_gallon": round(s.price, 3),
            "gallons": round(self.gallons, 2),
            "cost": round(self.cost, 2),
        }


class FuelPlanner:
    """
    Chooses where to refuel and how much to buy. Two strategies, picked by
    `use_stop_penalty` (default: USE_STOP_PENALTY):

    True - stop penalty: minimizes fuel cost + stop_penalty * number of stops.
        The penalty stands for the time and detour of leaving the highway. It
        only steers the choice; the reported cost is fuel only. Dynamic
        programming over the stations in route order; the state is the fuel in
        the tank, tracked in steps of `step` miles of range. At each station the
        vehicle either drives past or stops and buys any amount.

    False - greedy: cheapest fuel, however many stops.
        - if a cheaper station is within range, buy just enough to reach it;
        - else if the destination is within range, buy just enough to finish;
        - else fill the tank and go to the cheapest station within range.
        Tends to stop for a gallon whenever a station a few miles ahead is a
        cent cheaper.

    In both, the tank starts empty: the first stop must be within start_window
    miles, and the fuel used to reach it is bought there too, so the total
    covers the whole trip.
    """

    def __init__(self, max_range=MAX_RANGE_MILES, mpg=MPG, start_window=START_WINDOW_MILES,
                 stop_penalty=STOP_PENALTY_USD, step=FUEL_STEP_MILES, use_stop_penalty=USE_STOP_PENALTY):
        self.max_range = max_range
        self.mpg = mpg
        self.start_window = start_window
        self.stop_penalty = stop_penalty
        self.step = step
        self.use_stop_penalty = use_stop_penalty
        self.levels = np.arange(round(max_range / step) + 1)  # tank levels, 0 = empty

    def plan(self, stations, total_miles):
        if self.use_stop_penalty:
            return self._plan_with_stop_penalty(stations, total_miles)
        return self._plan_greedy(stations, total_miles)

    # ---------- greedy: cheapest fuel ----------

    def _plan_greedy(self, stations, total_miles):
        i = self._first_stop(stations)
        fuel = 0.0  # miles of range in the tank on arrival
        already_driven = stations[i].mile
        stops = []

        while True:
            here = stations[i]
            next_i, target = self._next_move(stations, i, total_miles)

            needed = target - here.mile
            miles_bought = max(0.0, needed - fuel) + already_driven
            already_driven = 0.0
            if miles_bought > 0:
                stops.append(self._stop(here, miles_bought))

            if next_i is None:
                return stops

            fuel = max(fuel, needed) - (stations[next_i].mile - here.mile)
            i = next_i

    def _first_stop(self, stations):
        near_start = [i for i, s in enumerate(stations) if s.mile <= self.start_window]
        if not near_start:
            raise TripException(f"No fuel station within {self.start_window} miles of the start.", status=422)
        return min(near_start, key=lambda i: stations[i].price)

    def _next_move(self, stations, i, total_miles):
        """Returns (next station index or None for destination, mile to fuel up to)."""
        here = stations[i]
        reach = here.mile + self.max_range
        ahead = list(takewhile(lambda k: stations[k].mile <= reach, range(i + 1, len(stations))))

        cheaper = next((k for k in ahead if stations[k].price < here.price), None)
        if cheaper is not None:
            return cheaper, stations[cheaper].mile
        if total_miles <= reach:
            return None, total_miles
        if ahead:
            return min(ahead, key=lambda k: stations[k].price), reach

        raise TripException(f"No fuel station within {self.max_range} miles after mile {here.mile:.0f}.", status=422)

    # ---------- stop penalty: cheapest fuel + fewer stops ----------

    def _plan_with_stop_penalty(self, stations, total_miles):
        stations = sorted((s for s in stations if 0 <= s.mile <= total_miles), key=lambda s: (s.mile, s.price))
        self._check_coverage(stations, total_miles)

        positions = [round(s.mile / self.step) for s in stations]
        end = round(total_miles / self.step)

        departure = np.full(len(self.levels), np.inf)  # cheapest cost of leaving with each fuel level
        decisions = []
        previous = 0
        for station, position in zip(stations, positions):
            arrival = self._drive(departure, position - previous)
            departure, decision = self._visit(station, position, arrival)
            decisions.append(decision)
            previous = position

        at_finish = self._drive(departure, end - previous)
        if not np.isfinite(at_finish).any():
            raise TripException("No fuel plan reaches the destination.", status=422)

        level = int(np.argmin(at_finish)) + end - previous  # fuel when leaving the last station
        return self._backtrack(stations, positions, decisions, level)

    def _check_coverage(self, stations, total_miles):
        if not any(s.mile <= self.start_window for s in stations):
            raise TripException(f"No fuel station within {self.start_window} miles of the start.", status=422)

        miles = [s.mile for s in stations] + [total_miles]
        for here, after in zip(miles, miles[1:]):
            if after - here > self.max_range:
                raise TripException(f"No fuel station within {self.max_range} miles after mile {here:.0f}.",
                                    status=422)

    def _drive(self, departure, distance):
        """Cost per fuel level after driving `distance` steps; levels that run dry become impossible."""
        arrival = np.full(len(self.levels), np.inf)
        if distance < len(self.levels):
            arrival[:len(self.levels) - distance] = departure[distance:]
        return arrival

    def _visit(self, station, position, arrival):
        """Best cost per departure level: drive past, or stop and top up from any arrival level."""
        step_price = station.price * self.step / self.mpg
        base = arrival.copy()

        # First stop: arrive empty and also pay here for the miles driven from the start.
        first_stop_cost = position * step_price if station.mile <= self.start_window else np.inf
        first_stop = first_stop_cost < base[0]
        if first_stop:
            base[0] = first_stop_cost

        # Topping up from level f to g costs base[f] + (g - f) * step_price; take the best f <= g.
        values = base - self.levels * step_price
        best = np.minimum.accumulate(values)
        source = np.maximum.accumulate(np.where(values <= best, self.levels, 0)).astype(np.int32)
        stop_cost = best + self.levels * step_price + self.stop_penalty

        stopped = stop_cost < arrival
        return np.where(stopped, stop_cost, arrival), (stopped, source, first_stop)

    def _backtrack(self, stations, positions, decisions, level):
        stops = []
        for i in range(len(stations) - 1, -1, -1):
            stopped, source, first_stop = decisions[i]
            if stopped[level]:
                start = int(source[level])
                bought = level - start
                is_first = first_stop and start == 0
                if is_first:
                    bought += positions[i]
                stops.append(self._stop(stations[i], bought * self.step))
                if is_first:
                    break
                level = start
            if i > 0:
                level += positions[i] - positions[i - 1]
        return stops[::-1]

    # ---------- shared ----------

    def _stop(self, station, miles):
        gallons = miles / self.mpg
        return FuelStop(station, gallons, gallons * station.price)
