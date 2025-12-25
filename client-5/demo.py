#!/usr/bin/env python3
"""
Simple demo for a 64x64 HUB75 RGB matrix using
Adafruit_Blinka_Raspberry_Pi5_Piomatter (PioMatter) on Raspberry Pi 5.

This script draws a moving rainbow and a pulsing circle to demonstrate
basic drawing primitives. It's intentionally small and dependency-light;
follow the README instructions to install the library and enable the
piomatter device node (/dev/pio0) on Raspberry Pi 5.

Tested conceptually against the PioMatter API provided by the Adafruit
project; adjust pin mappings or timing parameters for your hardware.
"""
import time
import math
import sys
import numpy as np
from PIL import Image, ImageDraw

SIMULATE = bool(int(__import__('os').environ.get('SIMULATE_MATRIX', '0')))

if not SIMULATE:
    try:
        from adafruit_blinka_raspberry_pi5_piomatter import PioMatter, Geometry, Orientation, Pinout, Colorspace
    except Exception as e:
        print("Missing dependency: install Adafruit-Blinka-Raspberry-Pi5-Piomatter")
        print("See README in this folder for installation steps.")
        print("")
        print("Installation: pip install Adafruit-Blinka-Raspberry-Pi5-Piomatter")
        print("")
        print("If you'd like to run this script without hardware, set SIMULATE_MATRIX=1 and re-run:")
        print("  SIMULATE_MATRIX=1 python3 demo.py")
        raise


WIDTH = 64
HEIGHT = 64
N_ADDR_LINES = 5  # Try 5 for 1/64 scan panels


def hsv_to_rgb(h, s, v):
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
    if hi == 0:
        r, g, b = v, t, p
    elif hi == 1:
        r, g, b = q, v, p
    elif hi == 2:
        r, g, b = p, v, t
    elif hi == 3:
        r, g, b = p, q, v
    elif hi == 4:
        r, g, b = t, p, v
    elif hi == 5:
        r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


def draw_frame(canvas, draw, t0: float):
    # Fill canvas with a rainbow background that shifts with time
    for y in range(HEIGHT):
        for x in range(WIDTH):
            hue = (t0 * 30 + (x + y) * 360.0 / (WIDTH + HEIGHT)) % 360
            r, g, b = hsv_to_rgb(hue, 1.0, 0.6)
            canvas.putpixel((x, y), (r, g, b))

    # Draw a pulsing circle moving horizontally
    cx = (WIDTH // 2) + int(math.sin(t0) * (WIDTH // 4))
    cy = HEIGHT // 2
    radius = 6 + int((math.sin(t0 * 1.5) + 1) * 3)
    
    # Draw filled circle
    draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], 
                 fill=(255, 255, 255))


def main():
    print("Opening PioMatter device...")
    
    # Try different pinouts - uncomment the one that works for your hardware
    # For Seeed/Waveshare bonnets, try these in order:
    PINOUT = Pinout.Active3      # Try this first
    # PINOUT = Pinout.AdafruitMatrixBonnetBGR  # If colors are wrong (BGR instead of RGB)
    # PINOUT = Pinout.AdafruitMatrixHat        # Alternative pinout
    # PINOUT = Pinout.AdafruitMatrixHatBGR     # Alternative with BGR
    
    print(f"Using pinout: {PINOUT}")
    
    # Create PIL Image as framebuffer
    canvas = Image.new('RGB', (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Create numpy array from PIL image for PioMatter
    framebuffer = np.asarray(canvas) + 0  # Make a mutable copy
    print(f"Framebuffer shape: {framebuffer.shape}, dtype: {framebuffer.dtype}")
    
    # Create geometry for 64x64 matrix with 4 address lines (1/32 scan)
    geometry = Geometry(width=WIDTH, height=HEIGHT, n_addr_lines=N_ADDR_LINES, 
                       rotation=Orientation.Normal)
    print(f"Geometry created: {WIDTH}x{HEIGHT}, n_addr_lines={N_ADDR_LINES}")
    
    # Create PioMatter instance
    try:
        matrix = PioMatter(colorspace=Colorspace.RGB888Packed,
                          pinout=PINOUT,
                          framebuffer=framebuffer,
                          geometry=geometry)
        print("PioMatter initialized successfully!")
    except Exception as e:
        print(f"ERROR initializing PioMatter: {e}")
        raise

    try:
        start = time.time()
        t = 0.0
        frame_count = 0
        while True:
            t = time.time() - start
            
            # Clear and draw new frame
            draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(0, 0, 0))
            draw_frame(canvas, draw, t)
            
            # Update framebuffer from canvas
            framebuffer[:] = np.asarray(canvas)
            
            # Display on matrix
            try:
                matrix.show()
                frame_count += 1
                if frame_count % 30 == 0:
                    print(f"Frame {frame_count}, t={t:.1f}s, fps={matrix.fps:.1f}")
            except Exception as e:
                print(f"ERROR calling matrix.show(): {e}")
                raise
            
            # Cap framerate
            time.sleep(0.06)

    except KeyboardInterrupt:
        print(f"\nExiting... (displayed {frame_count} frames)")


if __name__ == '__main__':
    main()
