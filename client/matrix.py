from __future__ import annotations

from typing import Optional, Tuple
import os
import threading
import datetime

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    _HAVE_RGB = True
except Exception as e:
    _HAVE_RGB = False

# --- Common static colors (20) ---
# Define as RGB tuples so they are safe even if rgbmatrix/graphics isn't available.
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
LIME = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
SILVER = (192, 192, 192)
GRAY = (128, 128, 128)
MAROON = (128, 0, 0)
OLIVE = (128, 128, 0)
GREEN = (0, 128, 0)
PURPLE = (128, 0, 128)
TEAL = (0, 128, 128)
NAVY = (0, 0, 128)
ORANGE = (255, 165, 0)
PINK = (255, 192, 203)
BROWN = (165, 42, 42)
GOLD = (255, 215, 0)

# Convenient mapping by name
COLORS = {
    'WHITE': WHITE,
    'BLACK': BLACK,
    'RED': RED,
    'LIME': LIME,
    'BLUE': BLUE,
    'YELLOW': YELLOW,
    'CYAN': CYAN,
    'MAGENTA': MAGENTA,
    'SILVER': SILVER,
    'GRAY': GRAY,
    'MAROON': MAROON,
    'OLIVE': OLIVE,
    'GREEN': GREEN,
    'PURPLE': PURPLE,
    'TEAL': TEAL,
    'NAVY': NAVY,
    'ORANGE': ORANGE,
    'PINK': PINK, 
    'BROWN': BROWN,
    'GOLD': GOLD,
}

# If graphics is available, build graphics.Color versions for direct use
GRAPHICS_COLORS = {}
# Opacity multiplier (0.0 - 1.0) to darken colors; 1.0 = full brightness.
OPACITY = 1.0

# --- New: environment-configurable values ---
# MATRIX_BORDER_COLOR and MATRIX_TEXT_COLOR may be a named color (from COLORS),
# a hex string like #RRGGBB, or a CSV 'r,g,b'. Default to WHITE and BLUE.
ENV_BORDER_COLOR = os.getenv('MATRIX_BORDER_COLOR', 'WHITE')
ENV_TEXT_COLOR = os.getenv('MATRIX_TEXT_COLOR', 'BLUE')
# Optional override to the time-based opacity (percent 1-100). If not set, opacity
# is computed from local time (midnight->1, noon->100).
ENV_OPACITY_PERCENT = os.getenv('MATRIX_OPACITY_PERCENT')
# Optional matrix brightness (0-100) applied to RGBMatrixOptions.brightness
ENV_MATRIX_BRIGHTNESS = os.getenv('MATRIX_BRIGHTNESS')


def _parse_color(value: str) -> tuple:
    """Return an (r,g,b) tuple for a named color, hex (#RRGGBB), or CSV 'r,g,b'."""
    if not value:
        return WHITE
    v = value.strip()
    # Named color (case-insensitive)
    name = v.upper()
    if name in COLORS:
        return COLORS[name]
    # Hex #RRGGBB
    if v.startswith('#') and len(v) == 7:
        try:
            r = int(v[1:3], 16)
            g = int(v[3:5], 16)
            b = int(v[5:7], 16)
            return (r, g, b)
        except Exception:
            pass
    # CSV r,g,b
    parts = v.split(',')
    if len(parts) == 3:
        try:
            r = int(parts[0])
            g = int(parts[1])
            b = int(parts[2])
            return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
        except Exception:
            pass
    # Fallback
    return WHITE

# Pre-parse env colors for speed
PARSED_BORDER_RGB = _parse_color(ENV_BORDER_COLOR)
PARSED_TEXT_RGB = _parse_color(ENV_TEXT_COLOR)


def _apply_opacity(rgb: tuple, opacity: float) -> tuple:
    """Return an (r,g,b) tuple scaled by opacity and clamped to 0-255."""
    try:
        o = max(0.0, min(1.0, float(opacity)))
    except Exception:
        o = 1.0
    r, g, b = rgb
    return (max(0, min(255, int(r * o))), max(0, min(255, int(g * o))), max(0, min(255, int(b * o))))

if _HAVE_RGB:
    try:
        for name, (r, g, b) in COLORS.items():
            rr, gg, bb = _apply_opacity((r, g, b), OPACITY)
            GRAPHICS_COLORS[name] = graphics.Color(rr, gg, bb)
    except Exception:
        # Ignore if graphics.Color isn't behaving as expected; callers can fall back
        GRAPHICS_COLORS = {}

def _get_local_now():
    """Return timezone-aware local datetime using TIMEZONE env or UTC as fallback."""
    tz_name = os.getenv('TIMEZONE') or os.getenv('TZ') or 'UTC'
    try:
        if ZoneInfo:
            return datetime.datetime.now(ZoneInfo(tz_name))
    except Exception:
        pass
    return datetime.datetime.now(datetime.timezone.utc)

# Map local time to opacity percent (1..100)
# - midnight (00:00) -> 1
# - noon (12:00) -> 100
# linear ramp from 00:00->12:00 up, 12:00->24:00 down
def current_opacity_percent() -> float:
    now = _get_local_now()
    hour = now.hour + now.minute / 60.0 + now.second / 3600.0  # 0..24
    if hour <= 12.0:
        percent = 1.0 + (100.0 - 1.0) * (hour / 12.0)
    else:
        percent = 100.0 - (100.0 - 1.0) * ((hour - 12.0) / 12.0)
    return max(1.0, min(100.0, percent))

def current_opacity_multiplier() -> float:
    # If ENV_OPACITY_PERCENT is set and valid, use it as override
    try:
        if ENV_OPACITY_PERCENT is not None:
            p = float(ENV_OPACITY_PERCENT)
            return max(1.0, min(100.0, p)) / 100.0
    except Exception:
        pass
    return current_opacity_percent() / 100.0

def init_matrix() -> Optional[Tuple[RGBMatrix, object, object, object, object]]:
    """Initialize and return (matrix, canvas, font_large, font_medium, font_small) or None on failure."""
    if not _HAVE_RGB:
        return None
    try:
        options = RGBMatrixOptions()
        # Adjust these to match your panel/HAT
        options.rows = 64
        options.cols = 64
        options.chain_length = 1
        options.brightness = 50  # 0-100
        # allow env override of brightness
        try:
            if ENV_MATRIX_BRIGHTNESS is not None:
                options.brightness = int(max(0, min(100, int(ENV_MATRIX_BRIGHTNESS))))
        except Exception:
            pass
        options.parallel = 1
        options.hardware_mapping = 'regular'
        # Some Pi HATs and panels need tuning; these are safe defaults
        options.pwm_lsb_nanoseconds = 130
        options.disable_hardware_pulsing = True
        options.gpio_slowdown=3

        matrix = RGBMatrix(options=options)
        canvas = matrix.CreateFrameCanvas()

        base = os.path.dirname(__file__)
        def _try_load(filename: str):
            path = os.path.join(base, 'fonts', filename)
            try:
                f = graphics.Font()
                f.LoadFont(path)
                return f
            except Exception:
                return None

        # Medium is required per request: fonts/6x9.bdf
        font_large = _try_load('7x13.bdf')    # large (best-effort)
        font_medium = _try_load('6x9.bdf')    # medium (requested)
        font_small = _try_load('5x7.bdf')     # small

        return (matrix, canvas, font_large, font_medium, font_small)
    except Exception:
        return None


# Module-level state and lock to allow safe reuse across threads
_state_lock = threading.Lock()
_state = {"matrix": None, "canvas": None, "font_large": None, "font_medium": None, "font_small": None}


def cal(timestr: str,
    arrival: str,
    departure: str,
    icao: str,
    distance_mi: float,
    callsign: str,
    airline: str) -> None:
    """Draw the supplied information to the RGB matrix (if available) and return
    the (matrix, canvas, font) triple to reuse on subsequent calls.

    Returns the (matrix, canvas, font) tuple which the caller should pass back
    to avoid re-initializing hardware on every call.
    """
    line1 = f"{timestr}"
    line2 = f"{arrival} {departure}".strip() or "-"
    line3 = f"{callsign or '-'}"
    line4 = f"{distance_mi:0.2f} mi"
    line5 = f"{airline}"

    if not _HAVE_RGB:
        # No hardware — fallback to console output
        print(line1)
        print(line2)
        print(line3)
        print(line4)
        print(line5)
        return

    # Use a lock for init/draw so concurrent scheduler threads don't race
    with _state_lock:
        if _state["matrix"] is None or _state["canvas"] is None:
            init_res = init_matrix()
            if not init_res:
                print("Matrix init failed; printing to console:")
                print(line1)
                print(line2)
                print(line3)
                print(line4)
                print(line5)
                return
            m, c, fl, fm, fs = init_res
            _state["matrix"] = m
            _state["canvas"] = c
            _state["font_large"] = fl
            _state["font_medium"] = fm
            _state["font_small"] = fs

        try:
            canvas = _state["canvas"]
            f_large = _state.get("font_large")
            f_med = _state.get("font_medium")
            f_small = _state.get("font_small")
            canvas.Clear()

            # Compute opacity for this draw and build graphics.Color instances on-the-fly
            mult = current_opacity_multiplier()
            border_rgb = _apply_opacity(PARSED_BORDER_RGB, mult)
            text_rgb = _apply_opacity(PARSED_TEXT_RGB, mult)
            try:
                border_color = graphics.Color(*border_rgb)
                text_color = graphics.Color(*text_rgb)
            except Exception:
                # fall back to any precomputed graphics colors if available
                border_color = GRAPHICS_COLORS.get('WHITE') if GRAPHICS_COLORS else None
                text_color = GRAPHICS_COLORS.get('BLUE') if GRAPHICS_COLORS else None
                if border_color is None:
                    border_color = graphics.Color(*_apply_opacity(COLORS['WHITE'], 1.0))
                if text_color is None:
                    text_color = graphics.Color(*_apply_opacity(COLORS['BLUE'], 1.0))

            # sensible defaults matching the init options
            w, h = 64, 64

            # Draw the four edge lines (use DrawLine if available)
            graphics.DrawLine(canvas, 0, 0, w - 1, 0, border_color)
            graphics.DrawLine(canvas, 0, h - 1, w - 1, h - 1, border_color)
            graphics.DrawLine(canvas, 0, 0, 0, h - 1, border_color)
            graphics.DrawLine(canvas, w - 1, 0, w - 1, h - 1, border_color)

            # Draw using large/medium/small fonts with graceful fallbacks
            graphics.DrawText(canvas, f_large, 4, 12, text_color, line1)
            graphics.DrawText(canvas, f_med, 4, 24, text_color, line2)
            graphics.DrawText(canvas, f_med, 4, 36, text_color, line3)
            graphics.DrawText(canvas, f_small, 4, 48, text_color, line4)
            graphics.DrawText(canvas, f_small, 4, 60, text_color, line5)

            # Swap to show the frame
            _state["canvas"] = _state["matrix"].SwapOnVSync(canvas)
        except Exception as e:
            print(f"Matrix error: {e}")
            print(line1)
            print(line2)
            print(line3)
            print(line4)
            print(line5)
            return


def shutdown() -> None:
    """Shutdown the matrix hardware if it was initialized."""
    with _state_lock:
        try:
            if _state["matrix"] is not None:
                # Best-effort: clear display
                try:
                    _state["canvas"].Clear()
                except Exception:
                    pass
                # There is no explicit close API on the python binding; drop refs
                _state["matrix"] = None
                _state["canvas"] = None
                _state["font_large"] = None
                _state["font_medium"] = None
                _state["font_small"] = None
        except Exception:
            pass

