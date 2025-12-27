#!/usr/bin/env python3
"""
Simple demo for LED matrix using rgbmatrix library.
Displays test patterns and text to verify matrix functionality.
"""
import time
import sys
import os

SIMULATE = bool(int(os.environ.get('SIMULATE_MATRIX', '0')))

if not SIMULATE:
    try:
        from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    except Exception as e:
        print("Missing dependency: rgbmatrix library not found")
        print("See https://github.com/hzeller/rpi-rgb-led-matrix/tree/master/bindings/python")
        print("")
        print("If you'd like to run this script without hardware, set SIMULATE_MATRIX=1 and re-run:")
        print("  SIMULATE_MATRIX=1 python3 demo.py")
        raise


WIDTH = 64
HEIGHT = 64


def create_color_wheel(angle):
    """Create RGB color based on angle (0-360)."""
    if angle < 120:
        r = int((120 - angle) / 120.0 * 255)
        g = int(angle / 120.0 * 255)
        b = 0
    elif angle < 240:
        r = 0
        g = int((240 - angle) / 120.0 * 255)
        b = int((angle - 120) / 120.0 * 255)
    else:
        r = int((angle - 240) / 120.0 * 255)
        g = 0
        b = int((360 - angle) / 120.0 * 255)
    return (r, g, b)


def run_demo():
    """Run the demo display."""
    if SIMULATE:
        print("Demo running in SIMULATION mode")
        print("=" * 40)
        for i in range(5):
            print(f"Frame {i+1}/5: Drawing colorful patterns...")
            time.sleep(1)
        print("=" * 40)
        print("Demo complete!")
        return
    
    # Initialize matrix
    options = RGBMatrixOptions()
    options.rows = HEIGHT
    options.cols = WIDTH
    options.chain_length = 1
    options.brightness = 50
    options.parallel = 1
    options.hardware_mapping = 'regular'
    options.pwm_lsb_nanoseconds = 150
    options.disable_hardware_pulsing = True
    options.gpio_slowdown = 3
    
    matrix = RGBMatrix(options=options)
    canvas = matrix.CreateFrameCanvas()
    
    # Load a font
    font = graphics.Font()
    font_path = os.path.join(os.path.dirname(__file__), 'fonts', '7x13.bdf')
    try:
        font.LoadFont(font_path)
    except:
        print("Warning: Could not load font")
    
    print("Starting demo... (Press Ctrl+C to exit)")
    
    try:
        angle = 0
        frame = 0
        
        while True:
            canvas.Clear()
            
            # Draw border
            border_color = graphics.Color(100, 100, 100)
            graphics.DrawLine(canvas, 0, 0, WIDTH - 1, 0, border_color)
            graphics.DrawLine(canvas, 0, HEIGHT - 1, WIDTH - 1, HEIGHT - 1, border_color)
            graphics.DrawLine(canvas, 0, 0, 0, HEIGHT - 1, border_color)
            graphics.DrawLine(canvas, WIDTH - 1, 0, WIDTH - 1, HEIGHT - 1, border_color)
            
            # Draw animated text
            text = "RGB TEST"
            r, g, b = create_color_wheel(angle)
            text_color = graphics.Color(r, g, b)
            graphics.DrawText(canvas, font, 6, 20, text_color, text)
            
            # Draw a small moving circle
            circle_x = int(WIDTH / 2 + 15 * (frame % 60 - 30) / 30.0)
            circle_y = int(HEIGHT / 2 + 10)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx*dx + dy*dy <= 4:
                        x, y = circle_x + dx, circle_y + dy
                        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                            canvas.SetPixel(x, y, r, g, b)
            
            # Draw frame counter
            frame_text = f"F:{frame:04d}"
            graphics.DrawText(canvas, font, 6, 45, graphics.Color(255, 255, 255), frame_text)
            
            # Swap buffers
            canvas = matrix.SwapOnVSync(canvas)
            
            # Update animation
            angle = (angle + 5) % 360
            frame += 1
            
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\nDemo stopped")
        canvas.Clear()
        matrix.SwapOnVSync(canvas)


if __name__ == '__main__':
    run_demo()
