# Lightweight matrix helper: expose `cal(timestr, arrival, departure, icao, distance_mi)`
# Tries to use rpi-rgb-led-matrix if available. Falls back to console output.
from typing import Optional

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    _HAVE_RGB = True
except Exception:
    _HAVE_RGB = False

_matrix = None
_canvas = None
_font = None


def _init_matrix() -> Optional[tuple]:
    global _matrix, _canvas, _font
    if not _HAVE_RGB:
        return None
    try:
        options = RGBMatrixOptions()
        # sensible defaults; adjust in your environment if needed
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = 'adafruit-hat'  # common mapping; change if needed
        _matrix = RGBMatrix(options=options)
        _canvas = _matrix.CreateFrameCanvas()
        _font = graphics.Font()
        # Try to load a font shipped with the project if available, otherwise skip
        try:
            _font.LoadFont("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        except Exception:
            try:
                # fallback to bundled font path used in many demos
                _font.LoadFont("./fonts/7x13.bdf")
            except Exception:
                # If font loading fails, set to None and use graphics default behaviour
                _font = None
        return (_matrix, _canvas, _font)
    except Exception:
        # If any matrix init fails, mark as unavailable
        return None


def cal(timestr: str, arrival: str, departure: str, icao: str, distance_mi: float) -> None:
    """Display the supplied information on the RGB matrix or print to console.

    Args:
        timestr: formatted time string (e.g. HH:MM:SS)
        arrival: arrival airport string or empty
        departure: departure airport string or empty
        icao: aircraft icao24 code or empty
        distance_mi: numeric distance in miles (may be float or empty-string)
    """
    text = f"{timestr} {arrival} {departure} {icao} {distance_mi:.2f}mi" if isinstance(distance_mi, (int, float)) else f"{timestr} {arrival} {departure} {icao} {distance_mi}"

    if not _HAVE_RGB:
        # No hardware lib present — fallback to console
        print(text)
        return

    # Lazy init
    if _matrix is None:
        init_res = _init_matrix()
        if not init_res:
            print(text)
            return

    try:
        # Clear canvas and draw text
        _canvas.Clear()
        if _font is not None:
            color = graphics.Color(255, 255, 0)
            # Simple multi-line layout if text is long
            graphics.DrawText(_canvas, _font, 1, 10, color, timestr)
            graphics.DrawText(_canvas, _font, 1, 20, color, f"{arrival} {departure}")
            graphics.DrawText(_canvas, _font, 1, 30, color, f"{icao} {distance_mi:.2f}mi")
        else:
            # No font loaded — just try drawing raw text at a single position
            graphics.DrawText(_canvas, graphics.Font(), 1, 10, graphics.Color(255, 255, 0), text)
        _canvas = _matrix.SwapOnVSync(_canvas)
    except Exception:
        # If anything goes wrong with hardware drawing, fallback to console
        print(text)
