# Import dotenv, pathlib and os to load environment variables from a file
from dotenv import load_dotenv
from database import *
from opensky import *
from utils import *
import typing as t
import time

# Simple in-memory cache mapping icao24 -> last-fetch-timestamp-ms
# Used to avoid calling get_aircraft_flights too frequently for the same aircraft
_flight_fetch_cache: dict[str, int] = {}


def _should_fetch_icao(icao24: str, cache_ttl_ms: int) -> bool:
        """Return True if we should call get_aircraft_flights for this icao24.

        Behavior:
            - If icao24 not in cache -> True (we should fetch and cache timestamp)
            - If cached and age < cache_ttl_ms -> False (skip fetch)
            - If cached and age >= cache_ttl_ms -> True (re-fetch and update timestamp)
        """
        now_ms = int(time.time() * 1000)
        ts = _flight_fetch_cache.get(icao24)
        if ts is None:
                return True
        return (now_ms - ts) >= cache_ttl_ms

def get_closest_flight_to_position(
    client_id: str,
    client_secret: str,
    latitude: float,
    longitude: float,
    box: float,
    buffer: int,
    delay: int = 5,
    cache_ttl_ms: int = 86400000,
) -> t.Union[tuple["Flight", "State"], "ErrorResponse"]:
    """Find the closest Flight to a position.

    Procedure:
    - compute bbox from latitude/longitude +/- box
    - fetch states via get_opensky_states
    - iterate states ordered by proximity to (latitude, longitude)
      and call get_aircraft_flights for each state's icao24 with begin/end
      = last_contact +/- buffer
    - return the first Flight found that has both estDepartureAirport and
      estArrivalAirport present. If none is found, return the closest Flight
      available. On network/validation errors return an ErrorResponse.

    NOTE: Assumes `buffer` is provided in seconds.
    """
    # compute bbox
    lat_min = latitude - box
    lat_max = latitude + box
    lon_min = longitude - box
    lon_max = longitude + box

    token = get_opensky_token(client_id, client_secret)
    if not token:
        return ErrorResponse(message="failed to obtain token", code=None)
    
    print(token)

    states_resp = get_opensky_states(token, lat_min, lat_max, lon_min, lon_max)
    if isinstance(states_resp, ErrorResponse):
        return states_resp

    states = states_resp.states
    if not states:
        return ErrorResponse(message="no states in bounding box", code=None)

    # Iterate by increasing distance using rank via find_closest_state
    checked_icao = set()
    for rank in range(len(states)):
        # Wait for the buffer period
        time.sleep(delay)

        s = find_closest_state(states, latitude, longitude, rank)
        if s is None:
            continue
        if s.icao24 in checked_icao:
            continue
        checked_icao.add(s.icao24)

        last = s.last_contact
        if not last:
            # no time info, skip
            continue

        begin = last - (buffer*1000)
        end = last

        # Check cache to avoid calling flights endpoint too often
        if not _should_fetch_icao(s.icao24, cache_ttl_ms):
            # Skip calling flights API for this icao24 because cache is fresh
            continue

        flights_or_error = get_aircraft_flights(token, s.icao24, begin, end)

        print(flights_or_error)

        # If API returned an error, cache the failure and try next state
        if isinstance(flights_or_error, ErrorResponse):
            _flight_fetch_cache[s.icao24] = int(time.time() * 1000)
            continue

        flights = flights_or_error
        # prefer flight that has both departure and arrival airports
        valid_flight = None
        for f in flights:
            if f.estDepartureAirport and f.estArrivalAirport:
                valid_flight = f
                break

        if valid_flight:
            # return both Flight and the State we queried
            return (valid_flight, s)

        # No valid flight found in this response: cache this icao and try next state
        _flight_fetch_cache[s.icao24] = int(time.time() * 1000)

    # fallback: return the closest available Flight from the nearest state
    nearest_state = find_closest_state(states, latitude, longitude, 0)
    if nearest_state:
        last = nearest_state.last_contact or nearest_state.time_position
        if last:
            # Check cache for fallback fetch as well
            if _should_fetch_icao(nearest_state.icao24, cache_ttl_ms):
                flights_or_error = get_aircraft_flights(
                    token,
                    nearest_state.icao24,
                    int(max(0, last - (buffer * 1000))),
                    int(last + (buffer * 1000)),
                )
                if isinstance(flights_or_error, ErrorResponse):
                    _flight_fetch_cache[nearest_state.icao24] = int(time.time() * 1000)
                elif flights_or_error:
                    # find a flight that has both departure and arrival
                    f = next((x for x in flights_or_error if x.estDepartureAirport and x.estArrivalAirport), None)
                    if f:
                        return (f, nearest_state)
                    # otherwise cache and fall through
                    _flight_fetch_cache[nearest_state.icao24] = int(time.time() * 1000)
            else:
                # cache is fresh for this icao24; cannot fetch now
                return ErrorResponse(message="no flight found matching criteria (cached)", code=None)

    return ErrorResponse(message="no flight found matching criteria", code=None)