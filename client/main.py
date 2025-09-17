# rgbmatrix is optional for headless environments. Commented out to allow
# importing this module without the hardware library installed.
# from rgbmatrix import RGBMatrix, RGBMatrixOptions
import datetime
from pathlib import Path
import os
from dotenv import load_dotenv
from database import ensure_database, ensure_nearestplane_table, get_nearestplane_by_id, upsert_nearestplane
from opensky import *
from utils import create_position_identifier
import typing as t
from airplane import *
from zoneinfo import ZoneInfo
from atexit import register as atexit_register
import signal
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor


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
MATRIX_SCHEDULE_SECONDS = int(os.getenv('MATRIX_SCHEDULE_SECONDS', '60'))

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


# Create APScheduler with a thread pool executor
executors = {"default": ThreadPoolExecutor(max_workers=4)}
sched = BackgroundScheduler(executors=executors)


def _closest_flight_run():
	"""Perform one OpenSky poll and persist the nearest plane to the DB."""
	try:
		# Call the orchestrator which returns either (Flight, State) or ErrorResponse
		res = get_closest_flight_to_position(
			OPENSKY_CLIENT_ID,
			OPENSKY_CLIENT_SECRET,
			LATITUDE,
			LONGITUDE,
			BOX,
			BUFFER,
			DELAY_FLIGHTS_API_SECONDS,
		)
		if isinstance(res, ErrorResponse):
			print(f"OpenSky orchestrator returned error: {res}")
			return
		flight, state = res
		data = _map_flight_to_nearestplane(flight, state)
		# Persist (INSERT OR REPLACE)
		np = upsert_nearestplane(**data)
		print(f"Nearest plane upserted: icao24={np.icao24} id={np.id} distance={np.distance}")
	except Exception as exc:
		print(f"Exception in _perform_run: {exc}")

def _matrix_clock_run():
    now_est = datetime.datetime.now(ZoneInfo("America/New_York"))
    ts = now_est.strftime("%H:%M:%S")
    print(f"MATRIX time (EST): {ts}")

def shutdown_scheduler(signum=None, frame=None):
	try:
		sched.shutdown(wait=True)
	except Exception as e:
		print(f"Error shutting down scheduler: {e}")


# Ensure scheduler shuts down cleanly on exit or signals
atexit_register(shutdown_scheduler)
signal.signal(signal.SIGINT, shutdown_scheduler)
signal.signal(signal.SIGTERM, shutdown_scheduler)

if __name__ == "__main__":
	"""Start APScheduler with two interval jobs: OpenSky polling and matrix time."""
	sched.add_job(_closest_flight_run, "interval", minutes=OPENSKY_POLL_SCHEDULE_MINUTES, id="opensky_poll", max_instances=1, coalesce=True)
	sched.add_job(_matrix_clock_run, "interval", seconds=MATRIX_SCHEDULE_SECONDS, id="matrix_time", max_instances=1, coalesce=True)
	sched.start()	
	print("Scheduler started (APScheduler). Ctrl-C to exit.")

