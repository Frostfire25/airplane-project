from typing import Optional, Tuple

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    _HAVE_RGB = True
except Exception:
    _HAVE_RGB = False

def init_matrix():
    if not _HAVE_RGB:
        return None
    try:
        options = RGBMatrixOptions()
        options.rows = 64
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = 'regular'
        options.pwm_lsb_nanoseconds = 130
        options.disable_hardware_pulsing = True
        matrix = RGBMatrix(options=options)
        canvas = matrix.CreateFrameCanvas()
        font = graphics.Font()
        # Try to load a font shipped with the project if available, otherwise skip
        try:
            font.LoadFont("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        except Exception:
            try:
                # fallback to bundled font path used in many demos
                font.LoadFont("./fonts/7x13.bdf")
            except Exception:
                # If font loading fails, set to None and use graphics default behaviour
                font = None
        return (matrix, canvas, font)
    except Exception:
        # If any matrix init fails, mark as unavailable
        return None


def cal(timestr: str, arrival: str, departure: str, icao: str, distance_mi: float, matrix, canvas, font):
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
    if matrix is None:
        init_res = init_matrix()
        if not init_res:
            print(text)
            return
        matrix, canvas, font = init_res

    try:
        # Clear canvas and draw text
        canvas.Clear()
        if font is not None:
            color = graphics.Color(255, 255, 0)
            # Simple multi-line layout if text is long
            graphics.DrawText(canvas, font, 1, 10, color, timestr)
            graphics.DrawText(canvas, font, 1, 20, color, f"{arrival} {departure}")
            graphics.DrawText(canvas, font, 1, 30, color, f"{icao} {distance_mi:.2f}mi" if isinstance(distance_mi, (int, float)) else f"{icao} {distance_mi}")
        else:
            # No font loaded — just try drawing raw text at a single position
            graphics.DrawText(canvas, graphics.Font(), 1, 10, graphics.Color(255, 255, 0), text)
        
        # Swap and update the display buffer
        matrix.SwapOnVSync(canvas)
        # Create a new canvas for the next frame
        return matrix, matrix.CreateFrameCanvas(), font
    except Exception as e:
        # If anything goes wrong with hardware drawing, fallback to console
        print(f"Matrix error: {str(e)}")
        print(text)
        return matrix, canvas, font
