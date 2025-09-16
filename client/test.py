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
from database import ensure_database, ensure_nearestplane_table, get_nearestplane_by_id, upsert_nearestplane, create_nearestplane, drop_nearestplane_table
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

# Initialize or get the path to the sqlite database
AIRPLANE_DB = ensure_database()
# Start with a clean table for the test
drop_nearestplane_table()
ensure_nearestplane_table()

# Determine identifier and insert a realistic sample row
ID = create_position_identifier(LATITUDE, LONGITUDE)
created = create_nearestplane(
	id=ID,
	latitude=LATITUDE,
	longitude=LONGITUDE,
	icao24="a1b2c3",
	callsign="TEST123",
	velocity=250.5,
	last_conact=time.time(),
	updateRow=datetime.datetime.now(datetime.timezone.utc).timestamp(),
	arrivalAirport="SEA",
	departureAirport="LAX",
	distance=185.4,
)
print("created:", created)

# Fetch back from DB and print
nearest_plane = get_nearestplane_by_id(ID)
print("fetched:", nearest_plane)
