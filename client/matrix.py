from typing import Optional, Tuple
import os
import threading

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    _HAVE_RGB = True
except Exception:
    _HAVE_RGB = False


def _available_font_paths() -> list:
    base = os.path.dirname(__file__)
    candidates = [
        os.path.join(base, "fonts", "7x13.bdf"),
        os.path.join(base, "fonts", "6x9.bdf"),
        os.path.join(base, "fonts", "5x8.bdf"),
    ]
    # Add some common system locations (may not be BDFs, but harmless to try)
    candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    return [p for p in candidates if os.path.isfile(p)]


def init_matrix() -> Optional[Tuple[RGBMatrix, object, object]]:
    """Initialize and return (matrix, canvas, font) or None on failure."""
    if not _HAVE_RGB:
        return None
    try:
        options = RGBMatrixOptions()
        # Adjust these to match your panel/HAT
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = 'regular'
        # Some Pi HATs and panels need tuning; these are safe defaults
        options.pwm_lsb_nanoseconds = 130
        options.disable_hardware_pulsing = True

        matrix = RGBMatrix(options=options)
        canvas = matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("fonts/6x9.bdf")

        # If font.LoadFont never succeeded, keep font as None to trigger fallback
        if not hasattr(font, 'LoadFont'):
            font = None

        return (matrix, canvas, font)
    except Exception:
        return None


# Module-level state and lock to allow safe reuse across threads
_state_lock = threading.Lock()
_state = {"matrix": None, "canvas": None, "font": None}


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
    line3 = f"{icao}"
    line4 = f"{distance_mi}mi"

    if not _HAVE_RGB:
        # No hardware — fallback to console output
        print(line1)
        print(line2)
        print(line3)
        print(line4)
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
                return
            m, c, f = init_res
            _state["matrix"] = m
            _state["canvas"] = c
            _state["font"] = f

        try:
            canvas = _state["canvas"]
            font = _state["font"]
            canvas.Clear()

            # Draw a white border around the frame. Prefer DrawLine (fast) and
            # fall back to SetPixel loops if DrawLine isn't available on this
            # graphics binding. Determine width/height from canvas or matrix if
            # possible, otherwise fall back to common defaults.
            border_color = graphics.Color(255, 255, 255)
            # sensible defaults matching the init options
            w, h = 64, 32
            try:
                w = int(getattr(canvas, 'width', None) or getattr(_state['matrix'], 'width', None) or w)
                h = int(getattr(canvas, 'height', None) or getattr(_state['matrix'], 'height', None) or h)
            except Exception:
                # keep defaults
                pass

            try:
                # Draw the four edge lines
                graphics.DrawLine(canvas, 0, 0, w - 1, 0, border_color)
                graphics.DrawLine(canvas, 0, h - 1, w - 1, h - 1, border_color)
                graphics.DrawLine(canvas, 0, 0, 0, h - 1, border_color)
                graphics.DrawLine(canvas, w - 1, 0, w - 1, h - 1, border_color)
            except Exception:
                # Fallback: set individual edge pixels
                try:
                    for x in range(w):
                        try:
                            canvas.SetPixel(x, 0, 255, 255, 255)
                        except Exception:
                            pass
                        try:
                            canvas.SetPixel(x, h - 1, 255, 255, 255)
                        except Exception:
                            pass
                    for y in range(h):
                        try:
                            canvas.SetPixel(0, y, 255, 255, 255)
                        except Exception:
                            pass
                        try:
                            canvas.SetPixel(w - 1, y, 255, 255, 255)
                        except Exception:
                            pass
                except Exception:
                    # If all drawing fails, ignore and continue; text fallback will print to console
                    pass

            color = graphics.Color(255, 255, 0)

            if font is not None:
                graphics.DrawText(canvas, font, 4, 10, color, line1)
                graphics.DrawText(canvas, font, 4, 20, color, line2)
                graphics.DrawText(canvas, font, 4, 30, color, line3)
                graphics.DrawText(canvas, font, 4, 40, color, line4)
            else:
                fallback_font = graphics.Font()
                try:
                    graphics.DrawText(canvas, fallback_font, 1, 10, color, f"{line1} {line2} {line3}")
                except Exception:
                    print(line1)
                    print(line2)
                    print(line3)
                    return

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
                _state["font"] = None
        except Exception:
            pass

