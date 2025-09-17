# Import dotenv, pathlib and os to load environment variables from a file
from dotenv import load_dotenv
from database import *
from opensky import *
from utils import *
import typing as t
import time

def get_closest_flight_to_position(
    client_id: str,
    client_secret: str,
    latitude: float,
    longitude: float,
    box: float,
    buffer: int,
    delay: int = 5,
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

        flights_or_error = get_aircraft_flights(token, s.icao24, begin, end)
        print(flights_or_error)
        if isinstance(flights_or_error, ErrorResponse):
            # try next state
            continue

        flights = flights_or_error
        # prefer flight that has both departure and arrival airports
        for f in flights:
            if f.estDepartureAirport and f.estArrivalAirport:
                # return both Flight and the State we queried
                return (f, s)

    # fallback: return the closest available Flight from the nearest state
    nearest_state = find_closest_state(states, latitude, longitude, 0)
    if nearest_state:
        last = nearest_state.last_contact or nearest_state.time_position
        if last:
            flights_or_error = get_aircraft_flights(token, nearest_state.icao24, int(max(0, last - (buffer*1000))), int(last + (buffer*1000)))
            if not isinstance(flights_or_error, ErrorResponse) and flights_or_error:
                return (flights_or_error[0], nearest_state)

    return ErrorResponse(message="no flight found matching criteria", code=None)

# Run project

# get_closest_flight_to_position(
#   OPENSKY_CLIENT_ID,
#   OPENSKY_CLIENT_SECRET,
#   LATITUDE,
#   LONGITUDE,
#   BOX,
#   BUFFER,
# )