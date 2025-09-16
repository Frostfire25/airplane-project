# rgbmatrix is optional for headless environments. Commented out to allow
# importing this module without the hardware library installed.
# from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time
import datetime
import math
import time
from pathlib import Path
import os
from dotenv import load_dotenv
from database import ensure_database, ensure_nearestplane_table, get_nearestplane_by_id, upsert_nearestplane
from opensky import *
from utils import create_position_identifier
import typing as t
import threading
from  airplane import * 

# === Matrix setup ===
# The physical RGB matrix initialization is disabled to allow running on
# machines without the `rgbmatrix` package or attached hardware. If you
# want to enable the matrix, uncomment the import at the top and the
# block below.
# options = RGBMatrixOptions()
# options.rows = 64
# options.cols = 64
# options.chain_length = 1
# options.parallel = 1
# options.hardware_mapping = 'regular'
# options.pwm_lsb_nanoseconds = 130
#
# matrix = RGBMatrix(options=options)
# canvas = matrix.CreateFrameCanvas()

# Load .env located next to this module
base_dir = Path(__file__).resolve().parent
env_path = base_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Get OpenSky credentials from environment (do not log secrets)
OPENSKY_CLIENT_ID = os.getenv('OPENSKY_CLIENT_ID')
OPENSKY_CLIENT_SECRET = os.getenv('OPENSKY_CLIENT_SECRET')

# Load LATITUDE and LONGITUDE from environment, with defaults if not set
LATITUDE = float(os.getenv('LATITUDE', '0.0'))
LONGITUDE = float(os.getenv('LONGITUDE', '0.0'))
BOX = float(os.getenv('BOX', '0'))  # Box size in degrees
BUFFER = int(os.getenv('BUFFER', '5'))  # Buffer time in seconds
DELAY_FLIGHTS_API_SECONDS = int(os.getenv('DELAY_FLIGHTS_API_SECONDS', '5'))

# Initialize or get the path to the sqlite database
AIRPLANE_DB = ensure_database()
ensure_nearestplane_table()

# Determine if a NearestPlane record exists for the given identifier
ID = create_position_identifier(LATITUDE, LONGITUDE)

# Scheduler configuration from env
OPENSKY_POLL_SCHEDULE_MINUTES = int(os.getenv('OPENSKY_POLL_SCHEDULE_MINUTES', '5'))

def _map_flight_to_nearestplane(flight, state=None) -> dict:
	"""Map a Flight object to the NearestPlane fields.

	Uses getattr to defensively extract fields.
	"""
	lat = None
	lon = None
	if state is not None:
		lat = getattr(state, "latitude", None)
		lon = getattr(state, "longitude", None)
	# Fallback to using provided env coordinates if State coords unavailable
	return {
		"id": ID,
		"latitude": float(lat) if lat is not None else 0.0,
		"longitude": float(lon) if lon is not None else 0.0,
		"icao24": getattr(flight, "icao24", ""),
		"callsign": getattr(flight, "callsign", None),
		"velocity": getattr(flight, "velocity", None),
		"last_conact": float(getattr(flight, "lastSeen", 0) or 0),
		"updateRow": float(datetime.datetime.now(datetime.timezone.utc).timestamp()),
		"arrivalAirport": getattr(flight, "estArrivalAirport", None),
		"departureAirport": getattr(flight, "estDepartureAirport", None),
		"distance": getattr(flight, "distance", None),
	}


def run_once_and_store():
	result = get_closest_flight_to_position(
		OPENSKY_CLIENT_ID,
		OPENSKY_CLIENT_SECRET,
		LATITUDE,
		LONGITUDE,
		BOX,
		BUFFER,
		DELAY_FLIGHTS_API_SECONDS
	)

	if isinstance(result, ErrorResponse):
		print(f"Scheduler: error finding flight: {result.message}")
		return

	# result is expected to be (Flight, State)
	flight = None
	state = None
	if isinstance(result, tuple) and len(result) == 2:
		flight, state = result
	else:
		flight = result

	row = _map_flight_to_nearestplane(flight, state)
	upsert_nearestplane(**row)
	print(f"Scheduler: updated nearest plane row id={ID}")


def _scheduler_loop():
	interval = max(1, OPENSKY_POLL_SCHEDULE_MINUTES) * 60
	while True:
		try:
			run_once_and_store()
		except Exception as e:
			print(f"Scheduler error: {e}")
		time.sleep(interval)


def start_scheduler(background: bool = True) -> threading.Thread | None:
	if background:
		t = threading.Thread(target=_scheduler_loop, daemon=True)
		t.start()
		return t
	else:
		_scheduler_loop()
		return None

if __name__ == "__main__":
	start_scheduler(background=True)

