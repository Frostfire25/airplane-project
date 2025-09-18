from typing import Optional, Tuple
import os
import threading

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    _HAVE_RGB = True
except Exception:
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
OPACITY = 0.7

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
        options.parallel = 1
        options.hardware_mapping = 'regular'
        # Some Pi HATs and panels need tuning; these are safe defaults
        options.pwm_lsb_nanoseconds = 130
        options.disable_hardware_pulsing = True

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
        font_small = _try_load('4x6.bdf')     # small

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
    distance_mi: float) -> None:
    """Draw the supplied information to the RGB matrix (if available) and return
    the (matrix, canvas, font) triple to reuse on subsequent calls.

    Returns the (matrix, canvas, font) tuple which the caller should pass back
    to avoid re-initializing hardware on every call.
    """
    line1 = f"{timestr}"
    line2 = f"{arrival} {departure}".strip() or "-"
    line3 = f"{icao} {distance_mi:0.2f} mi"

    if not _HAVE_RGB:
        # No hardware — fallback to console output
        print(line1)
        print(line2)
        print(line3)
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

            # Draw a white border around the frame. Prefer DrawLine (fast) and
            # fall back to SetPixel loops if DrawLine isn't available on this
            # graphics binding. Determine width/height from canvas or matrix if
            # possible, otherwise fall back to common defaults.
            # Use opacity-adjusted white
            border_color = GRAPHICS_COLORS['WHITE']
            # sensible defaults matching the init options
            w, h = 64, 64

            # Draw the four edge lines (use DrawLine if available)
            graphics.DrawLine(canvas, 0, 0, w - 1, 0, border_color)
            graphics.DrawLine(canvas, 0, h - 1, w - 1, h - 1, border_color)
            graphics.DrawLine(canvas, 0, 0, 0, h - 1, border_color)
            graphics.DrawLine(canvas, w - 1, 0, w - 1, h - 1, border_color)

            color = GRAPHICS_COLORS['BLUE']

            # Draw using large/medium/small fonts with graceful fallbacks
            # Line positions chosen to avoid the 1px border:
            graphics.DrawText(canvas, f_large, 4, 12, color, line1)
            graphics.DrawText(canvas, f_med, 4, 24, color, line2)
            graphics.DrawText(canvas, f_small or graphics.Font(), 4, 36, color, line3)
            
            # Swap to show the frame
            _state["canvas"] = _state["matrix"].SwapOnVSync(canvas)
        except Exception as e:
            print(f"Matrix error: {e}")
            print(line1)
            print(line2)
            print(line3)
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

