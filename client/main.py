# rgbmatrix is optional for headless environments. Commented out to allow
# importing this module without the hardware library installed.
# from rgbmatrix import RGBMatrix, RGBMatrixOptions
import os
import time as _time
from pathlib import Path
from dotenv import load_dotenv as _load_dotenv

# Load .env early and set TZ before importing other modules that might
# import tzlocal. This helps avoid tzlocal's offset-mismatch UserWarning.
try:
	_base_dir = Path(__file__).resolve().parent
	_env_file = _base_dir / '.env'
	_load_dotenv(dotenv_path=_env_file)
	_env_tz = os.getenv('TZ') or os.getenv('TIMEZONE')
	if _env_tz:
		os.environ['TZ'] = _env_tz
		try:
			if hasattr(_time, 'tzset'):
				_time.tzset()
		except Exception:
			pass
except Exception:
	# If early dotenv load fails for any reason, continue; later code will
	# still attempt to load .env again.
	pass

import datetime
from pathlib import Path
import os
from dotenv import load_dotenv
from database import ensure_database, ensure_nearestplane_table, get_nearestplane_by_id, upsert_nearestplane
from opensky import *
from utils import create_position_identifier
import typing as t
from airplane import *
from matrix import *
from dateutil.tz import gettz
from atexit import register as atexit_register
import signal
import sys
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor


# Load .env located next to this module
base_dir = Path(__file__).resolve().parent
env_path = base_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Basic network connectivity check. Attempts a short TCP connect to a well-known
# public DNS server (8.8.8.8:53). If this check fails the process exits with
# a clear message so the operator knows networking is required for OpenSky calls.
def _network_available(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
	import socket
	try:
		with socket.create_connection((host, port), timeout=timeout):
			return True
	except Exception:
		return False

if not _network_available():
	print("Network check failed: no network connectivity detected (tried 8.8.8.8:53).\nPlease ensure the machine has network access before starting this program.")
	# Use a clean exit code to indicate failure to start due to missing network
	import sys as _sys
	_sys.exit(1)

# Matrix timezone: read from .env (TIMEZONE or TZ) or default to America/New_York
MATRIX_TIMEZONE = os.getenv('TIMEZONE') or os.getenv('TZ') or 'America/New_York'
MATRIX_ZONE = gettz(MATRIX_TIMEZONE) or gettz('UTC')
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
GET_FLIGHT_CACHE_TTL_MILLIS = int(os.getenv('GET_FLIGHT_CACHE_TTL_MILLIS', 86400000))

# Initialize or get the path to the sqlite database
AIRPLANE_DB = ensure_database()
ensure_nearestplane_table()

# Determine if a NearestPlane record exists for the given identifier
ID = create_position_identifier(LATITUDE, LONGITUDE)

# Scheduler configuration from env
OPENSKY_POLL_SCHEDULE_MINUTES = int(os.getenv('OPENSKY_POLL_SCHEDULE_MINUTES', '5'))

# Initialize the 64x64 RGB MAtrix
matrix, canvas, font = init_matrix()

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

# Event to block main thread; set on shutdown to exit cleanly
stop_event = threading.Event()

def _closest_flight_run():
	"""Perform one OpenSky poll and persist the nearest plane to the DB."""
	print("Starting to find the closest flight.")
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
			GET_FLIGHT_CACHE_TTL_MILLIS
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
    global matrix, canvas, font
    nearest_plane = get_nearestplane_by_id(ID)

    # Use Python conditional expression and guard for None
    icao = nearest_plane.icao24 if nearest_plane and nearest_plane.icao24 else ""
    distance_mi = distance_miles(nearest_plane.latitude, nearest_plane.longitude, LATITUDE, LONGITUDE) if nearest_plane and nearest_plane.latitude and nearest_plane.longitude else ""
    arrivalAirport = nearest_plane.arrivalAirport if nearest_plane and nearest_plane.arrivalAirport else ""
    departureAirport = nearest_plane.departureAirport if nearest_plane and nearest_plane.departureAirport else ""

    now_local = datetime.datetime.now(MATRIX_ZONE)
    ts = now_local.strftime("%H:%M:%S")
    # Delegate display to matrix helper which will fallback to console if no hardware
    result = cal(ts, arrivalAirport, departureAirport, icao, distance_mi, matrix, canvas, font)
    if result:
        matrix, canvas, font = result

def shutdown_scheduler(signum=None, frame=None):
	# Idempotent shutdown handler invoked by signals or manually.
	try:
		if stop_event.is_set():
			return
		print("Shutting down...")
		# Don't block waiting for currently running jobs; prefer prompt exit.
		try:
			sched.shutdown(wait=False)
		except Exception:
			pass
		# Try to remove any pending jobs to avoid new runs
		try:
			sched.remove_all_jobs()
		except Exception:
			pass
		# signal the main thread to exit
		try:
			stop_event.set()
		except Exception:
			pass
		# Exit the process; if called from a signal handler this will raise SystemExit.
		try:
			sys.exit(0)
		except Exception:
			pass
	except Exception as e:
		print(f"Error shutting down scheduler: {e}")


# Ensure scheduler shuts down cleanly on exit or signals
atexit_register(shutdown_scheduler)
signal.signal(signal.SIGINT, shutdown_scheduler)
signal.signal(signal.SIGTERM, shutdown_scheduler)

if __name__ == "__main__":
	"""Start APScheduler with two interval jobs: OpenSky polling and matrix time."""
	# Schedule the OpenSky poll to run immediately and then every N minutes.
	# Use a timezone-aware next_run_time matching the scheduler timezone so
	# APScheduler interprets the timestamp correctly on start.
	now = datetime.datetime.now(tz=sched.timezone)
	sched.add_job(
		_closest_flight_run,
		"interval",
		minutes=OPENSKY_POLL_SCHEDULE_MINUTES,
		id="opensky_poll",
		max_instances=1,
		coalesce=True,
		replace_existing=True,
		next_run_time=now,
	)
	sched.add_job(_matrix_clock_run, "interval", seconds=MATRIX_SCHEDULE_SECONDS, id="matrix_time", max_instances=1, coalesce=True)
	sched.start()	
	print("Scheduler started (APScheduler). Ctrl-C to exit.")
	#_closest_flight_run()
	try:
		# Use a short sleep loop instead of a single blocking wait so that
		# KeyboardInterrupt is raised promptly on Windows/PowerShell when
		# the user presses Ctrl-C. stop_event will be set by signal handlers.
		while not stop_event.is_set():
			_time.sleep(0.5)
	except (KeyboardInterrupt, SystemExit):
		print("Shutting down...")
		shutdown_scheduler()
		sys.exit(0)

