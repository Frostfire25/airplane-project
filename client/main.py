from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time
import math
import time
from pathlib import Path
import os
from dotenv import load_dotenv
from database import *
from opensky import *
from utils import *

# === Matrix setup ===
options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'regular'
options.pwm_lsb_nanoseconds = 130

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

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
ensure_nearestplane_table()

# Determine if a NearestPlane record exists for the given identifier
ID = create_position_identifier(LATITUDE, LONGITUDE)
existing_record = get_nearestplane_by_id(ID)

def hsv_to_rgb(h, s, v):
    """Convert HSV color values to RGB."""
    h = float(h)
    s = float(s)
    v = float(v)
    h60 = h / 60.0
    h60f = math.floor(h60)
    hi = int(h60f) % 6
    f = h60 - h60f
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r, g, b = 0, 0, 0
    if hi == 0: r, g, b = v, t, p
    elif hi == 1: r, g, b = q, v, p
    elif hi == 2: r, g, b = p, v, t
    elif hi == 3: r, g, b = p, q, v
    elif hi == 4: r, g, b = t, p, v
    elif hi == 5: r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


def clear() -> None:
    """Clear the physical matrix display."""
    matrix.Clear()


def swap() -> None:
    """Swap the current canvas onto the display using VSync."""
    matrix.SwapOnVSync(canvas)


def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
    """Set a pixel on the current canvas (does not swap)."""
    canvas.SetPixel(x, y, r, g, b)


def get_canvas():
    """Return the active canvas object for direct drawing if needed."""
    return canvas

