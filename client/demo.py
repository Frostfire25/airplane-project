from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time
import math

# === Matrix setup ===
options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'regular'
options.pwm_lsb_nanoseconds = 130
options.disable_hardware_pulsing = True  # Add this line

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

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

try:
    offset = 0
    brightness_offset = 0
    while True:
        canvas.Clear()
        
        # Calculate the current brightness wave (0.3 to 1.0)
        brightness = 0.65 + 0.35 * math.sin(brightness_offset)
        
        for y in range(64):
            for x in range(64):
                # Calculate hue based on position and time
                hue = (offset + (x + y) * 5.625) % 360
                
                # Add position-based brightness variation
                local_brightness = brightness * (0.5 + 0.2 * math.sin((x + y) * 0.1 + brightness_offset))
                
                # Convert HSV to RGB with varying brightness
                r, g, b = hsv_to_rgb(hue, 1.0, local_brightness)
                canvas.SetPixel(x, y, r, g, b)
        
        matrix.SwapOnVSync(canvas)
        
        # Update animation parameters
        offset = (offset + 2) % 360  # Color rotation
        brightness_offset += 0.05     # Brightness wave speed
        
        time.sleep(0.5)

except KeyboardInterrupt:
    matrix.Clear()
