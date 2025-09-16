from __future__ import annotations

import math
from typing import List, Optional

# Import the State model from the opensky module
from opensky import State


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
	"""Return great-circle distance between two points in kilometers.

	Uses the haversine formula. Inputs are in decimal degrees.
	"""
	# convert decimal degrees to radians
	rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
	dlat = rlat2 - rlat1
	dlon = rlon2 - rlon1
	a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
	c = 2 * math.asin(min(1, math.sqrt(a)))
	earth_km = 6371.0
	return earth_km * c


def find_closest_state(
	states: List[State], latitude: float, longitude: float, rank: int = 0
) -> Optional[State]:
	"""Return the nth-closest State from `states` to (`latitude`, `longitude`).

	Parameters:
	- states: list of `State` objects
	- latitude, longitude: target position
	- rank: zero-based index into the sorted-by-distance list (0 => closest)

	Behavior:
	- Skips any State that has missing `latitude` or `longitude`.
	- If no state has valid coordinates, returns None.
	- If rank < 0, treated as 0. If rank >= number of valid states, the last
	  (farthest) valid state is returned.
	"""
	distances: List[tuple[float, State]] = []

	for s in states:
		if s.latitude is None or s.longitude is None:
			continue
		try:
			d = _haversine_km(latitude, longitude, float(s.latitude), float(s.longitude))
		except Exception:
			# skip any state with non-numeric coords
			continue
		distances.append((d, s))

	if not distances:
		return None

	# Sort ascending by distance
	distances.sort(key=lambda x: x[0])

	# Clamp rank
	if rank < 0:
		rank = 0
	if rank >= len(distances):
		rank = len(distances) - 1

	return distances[rank][1]

# Utility function to create identifier from a Longitude and Latitude position
def create_position_identifier(lat: float, lon: float) -> str:
    return f"{lat}_{lon}"


__all__ = ["find_closest_state", "create_position_identifier"]

