"""
LED Matrix Display Module for ADS-B Aircraft Tracking
Displays time and nearest aircraft information on RGB LED matrix.
"""

import os
import datetime
from pathlib import Path
from typing import Optional, Dict
import numpy as np

try:
    from adafruit_blinka_raspberry_pi5_piomatter import PioMatter, Geometry, Orientation, Pinout, Colorspace
    from PIL import Image, ImageDraw, ImageFont
    MATRIX_AVAILABLE = True
except ImportError:
    MATRIX_AVAILABLE = False
    print("Warning: Matrix hardware libraries not available. Running in simulation mode.")


class MatrixDisplay:
    """Manages LED matrix display for aircraft tracking."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(MatrixDisplay, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize matrix display with configuration from environment."""
        # Only initialize once
        if MatrixDisplay._initialized:
            return
        
        MatrixDisplay._initialized = True
        self.simulate = os.getenv('SIMULATE_MATRIX', '0') == '1' or not MATRIX_AVAILABLE
        
        # Matrix hardware configuration
        self.width = int(os.getenv('MATRIX_WIDTH', '64'))
        self.height = int(os.getenv('MATRIX_HEIGHT', '64'))
        self.bit_depth = int(os.getenv('MATRIX_BIT_DEPTH', '6'))
        self.n_addr_lines = int(os.getenv('MATRIX_N_ADDR_LINES', '5'))
        
        # Color configuration (RGB tuples)
        self.color_time = self._parse_color(os.getenv('MATRIX_COLOR_TIME', '255,255,0'))  # Yellow
        self.color_callsign = self._parse_color(os.getenv('MATRIX_COLOR_CALLSIGN', '0,255,255'))  # Cyan
        self.color_distance = self._parse_color(os.getenv('MATRIX_COLOR_DISTANCE', '255,165,0'))  # Orange
        self.color_altitude = self._parse_color(os.getenv('MATRIX_COLOR_ALTITUDE', '0,255,0'))  # Green
        self.color_speed = self._parse_color(os.getenv('MATRIX_COLOR_SPEED', '255,100,255'))  # Pink
        self.color_no_aircraft = self._parse_color(os.getenv('MATRIX_COLOR_NO_AIRCRAFT', '255,0,0'))  # Red
        
        # Font paths - look in the fonts folder next to this file
        self.font_dir = Path(__file__).parent / 'fonts'
        
        # Initialize matrix hardware
        self.matrix = None
        self.canvas = None
        self.framebuffer = None
        
        if not self.simulate:
            self._init_hardware()
        else:
            print("Matrix Display: Running in SIMULATION mode")
    
    def _parse_color(self, color_str: str) -> tuple:
        """Parse color string 'R,G,B' to tuple."""
        try:
            r, g, b = color_str.split(',')
            return (int(r.strip()), int(g.strip()), int(b.strip()))
        except:
            return (255, 255, 255)  # Default white
    
    def _init_hardware(self):
        """Initialize the LED matrix hardware."""
        try:
            print(f"Matrix Display: Attempting hardware init {self.width}x{self.height}...")
            
            # Create PIL Image as framebuffer
            self.canvas = Image.new('RGB', (self.width, self.height), (0, 0, 0))
            print("Matrix Display: Canvas created")
            
            # Create numpy array from PIL image for PioMatter - use + 0 to make mutable copy
            self.framebuffer = np.asarray(self.canvas) + 0
            print(f"Matrix Display: Framebuffer created: shape={self.framebuffer.shape}, dtype={self.framebuffer.dtype}")
            
            # Ensure it's contiguous and the right type
            if not self.framebuffer.flags['C_CONTIGUOUS']:
                self.framebuffer = np.ascontiguousarray(self.framebuffer)
            
            # Create geometry
            geometry = Geometry(
                width=self.width,
                height=self.height,
                n_addr_lines=self.n_addr_lines,
                rotation=Orientation.Normal
            )
            print(f"Matrix Display: Geometry created: {self.width}x{self.height}, n_addr={self.n_addr_lines}")
            
            # Configure matrix with Active3 pinout (for Waveshare/Seeed bonnets)
            print("Matrix Display: Initializing PioMatter...")
            self.matrix = PioMatter(
                colorspace=Colorspace.RGB888Packed,
                pinout=Pinout.Active3,
                framebuffer=self.framebuffer,
                geometry=geometry
            )
            
            print(f"Matrix Display: Hardware initialized successfully!")
            
            # Test display by clearing it
            self.matrix.show()
            print("Matrix Display: Test show() completed")
            
        except Exception as e:
            import traceback
            print(f"Matrix Display: Hardware init failed with exception: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            print("Matrix Display: Falling back to simulation mode")
            self.simulate = True
            self.matrix = None
            self.framebuffer = None
    
    def _get_font(self, size: str = 'medium'):
        """Load appropriate BDF font."""
        # Just use the default font for now - it works reliably
        return ImageFont.load_default()
    
    def _draw_text(self, draw, text: str, x: int, y: int, color: tuple, font):
        """
        Draw text directly without animation for smooth display.
        
        Args:
            draw: ImageDraw object
            text: Text to display
            x, y: Position
            color: RGB color tuple
            font: Font to use
        """
        draw.text((x, y), text, fill=color, font=font)
    
    def clear(self):
        """Clear the matrix display."""
        if self.simulate:
            print("Matrix: [CLEAR]")
            return
        
        if self.canvas and self.matrix:
            try:
                # Create a fresh black canvas
                self.canvas = Image.new("RGB", (self.width, self.height), (0, 0, 0))
                
                # Update framebuffer with the cleared canvas
                self.framebuffer[:] = np.asarray(self.canvas)
                self.matrix.show()
            except Exception as e:
                print(f"Matrix clear error: {e}")
    
    def display_time_and_aircraft(
        self,
        current_time: datetime.datetime,
        aircraft_data: Optional[Dict] = None
    ):
        """
        Display time and aircraft information on matrix with Vestaboard-style animations.
        
        Args:
            current_time: Current datetime to display
            aircraft_data: Dictionary with aircraft info (callsign, distance, altitude, etc.)
        """
        if self.simulate:
            self._simulate_display(current_time, aircraft_data)
            return
        
        if not self.matrix or not self.canvas:
            print("Matrix display skipped: matrix or canvas not initialized")
            return
        
        try:
            print(f"Drawing to matrix: aircraft_data={'present' if aircraft_data else 'None'}")
            
            # Create a fresh canvas
            self.canvas = Image.new("RGB", (self.width, self.height), (0, 0, 0))
            draw = ImageDraw.Draw(self.canvas)
            
            # Format time - always display with AM/PM
            time_str = current_time.strftime("%I:%M %p")
            
            # Draw time at top (centered)
            font = self._get_font('large')
            # Simple centering - estimate 5 pixels per character
            text_width = len(time_str) * 5
            x_pos = (self.width - text_width) // 2
            self._draw_text(draw, time_str, x_pos, 2, self.color_time, font)
            
            if aircraft_data:
                print("Drawing aircraft data to matrix")
                # Draw aircraft information
                y_offset = 20
                
                # Callsign
                callsign = aircraft_data.get('callsign', aircraft_data.get('icao', 'N/A'))
                if callsign and callsign != 'N/A':
                    callsign = callsign.strip()[:10]  # Limit length
                    print(f"  Drawing callsign: {callsign}")
                    self._draw_text(draw, callsign, 2, y_offset, self.color_callsign, self._get_font('medium'))
                    y_offset += 12
                
                # Route information (origin -> destination)
                route_info = aircraft_data.get('route_info')
                if route_info:
                    origin = route_info.get('origin', '')[:4]
                    dest = route_info.get('destination', '')[:4]
                    if origin and dest:
                        route_str = f"{origin}-{dest}"
                        print(f"  Drawing route: {route_str}")
                        self._draw_text(draw, route_str, 2, y_offset, self.color_callsign, self._get_font('medium'))
                        y_offset += 12
                
                # Distance
                distance = aircraft_data.get('distance')
                if distance is not None:
                    dist_str = f"{distance:.1f}mi"
                    print(f"  Drawing distance: {dist_str}")
                    self._draw_text(draw, dist_str, 2, y_offset, self.color_distance, self._get_font('medium'))
            else:
                print("Drawing 'No Aircraft' message")
                # No aircraft - show message
                self._draw_text(draw, "No Aircraft", 6, 28, self.color_no_aircraft, self._get_font('medium'))
                self._draw_text(draw, "Tracked", 14, 42, self.color_no_aircraft, self._get_font('medium'))
            
            # Single update after all text is drawn
            print("Updating framebuffer and showing on matrix")
            self.framebuffer[:] = np.asarray(self.canvas)
            self.matrix.show()
            print("Matrix update complete")
            
        except Exception as e:
            import traceback
            print(f"Matrix display error: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            print("Falling back to simulation mode")
            self.simulate = True
    
    def _simulate_display(
        self,
        current_time: datetime.datetime,
        aircraft_data: Optional[Dict] = None
    ):
        """Simulate matrix display output to console."""
        time_str = current_time.strftime("%H:%M")
        
        print("\n" + "=" * 40)
        print(f"MATRIX DISPLAY [{time_str}]")
        print("=" * 40)
        
        if aircraft_data:
            callsign = aircraft_data.get('callsign', aircraft_data.get('icao', 'N/A'))
            distance = aircraft_data.get('distance', 0)
            altitude = aircraft_data.get('altitude', 'N/A')
            speed = aircraft_data.get('groundspeed', 'N/A')
            route_info = aircraft_data.get('route_info')
            
            print(f"┌─────────────────────────┐")
            print(f"│ TIME:     {time_str:8s}      │")
            print(f"│ FLIGHT:   {str(callsign)[:8]:8s}      │")
            
            if route_info:
                origin = route_info.get('origin', '???')[:4]
                dest = route_info.get('destination', '???')[:4]
                route_str = f"{origin}->{dest}"
                print(f"│ ROUTE:    {route_str:8s}      │")
            
            print(f"│ DIST:     {distance:.1f} mi       │")
            print(f"│ ALT:      {altitude} ft       │")
            print(f"│ SPEED:    {speed} kt       │")
            print(f"└─────────────────────────┘")
        else:
            print(f"┌─────────────────────────┐")
            print(f"│ TIME:     {time_str:8s}      │")
            print(f"│                         │")
            print(f"│   No Aircraft Tracked   │")
            print(f"│                         │")
            print(f"└─────────────────────────┘")
        
        print("=" * 40 + "\n")
    
    def show_startup_message(self):
        """Display startup message with animation."""
        if self.simulate:
            print("\n" + "=" * 40)
            print("MATRIX: SYSTEM STARTING...")
            print("=" * 40 + "\n")
            return
        
        if not self.matrix or not self.canvas:
            return
        
        try:
            draw = ImageDraw.Draw(self.canvas)
            
            # Create fresh canvas
            self.canvas = Image.new("RGB", (self.width, self.height), (0, 0, 0))
            draw = ImageDraw.Draw(self.canvas)
            
            # Draw startup message
            self._draw_text(draw, "ADS-B", 12, 20, (0, 255, 0), self._get_font('medium'))
            self._draw_text(draw, "Starting", 8, 35, (0, 255, 0), self._get_font('small'))
            
            # Update framebuffer and display
            self.framebuffer[:] = np.asarray(self.canvas)
            self.matrix.show()
            
            import time
        except Exception as e:
            import traceback
            print(f"Matrix startup message error: {e}")
            print(f"Traceback: {traceback.format_exc()}")
    
    def shutdown(self):
        """Clean shutdown of matrix display."""
        if self.simulate:
            print("Matrix: Shutdown (simulated)")
            return
        try:
            if self.matrix:
                self.clear()
                # Add any additional cleanup needed
        except Exception as e:
            print(f"Matrix shutdown error: {e}")


# Global matrix display instance
_matrix_display = None


def get_matrix_display() -> MatrixDisplay:
    """Get or create the global matrix display instance."""
    global _matrix_display
    if _matrix_display is None:
        _matrix_display = MatrixDisplay()
    return _matrix_display


def display_aircraft_info(current_time: datetime.datetime, aircraft_data: Optional[Dict] = None):
    """
    Convenience function to display aircraft information on matrix.
    
    Args:
        current_time: Current datetime
        aircraft_data: Dictionary with aircraft info or None
    """
    print(f"display_aircraft_info called with aircraft_data: {type(aircraft_data)} = {aircraft_data}")
    matrix = get_matrix_display()
    matrix.display_time_and_aircraft(current_time, aircraft_data)


def matrix_startup():
    """Initialize and show startup message."""
    matrix = get_matrix_display()
    matrix.show_startup_message()


def matrix_shutdown():
    """Shutdown matrix display."""
    global _matrix_display
    if _matrix_display:
        _matrix_display.shutdown()
        _matrix_display = None
