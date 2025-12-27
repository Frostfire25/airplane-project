"""
LED Matrix Display Module for ADS-B Aircraft Tracking
Displays time and nearest aircraft information on RGB LED matrix.
Uses rgbmatrix library instead of adafruit_blinka_raspberry_pi5_piomatter.
"""

import os
import datetime
import time
import traceback
from pathlib import Path
from typing import Optional, Dict
import threading

# Import dynamic configuration
from config import get_config

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    MATRIX_AVAILABLE = True
except ImportError:
    MATRIX_AVAILABLE = False
    print("Warning: Matrix hardware libraries not available. Running in simulation mode.")


class MatrixDisplay:
    """Manages LED matrix display for aircraft tracking."""
    
    _instance = None
    _initialized = False
    _state_lock = threading.Lock()
    
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
        
        # Get configuration instance
        self.config = get_config()
        
        # Check simulate mode
        self.simulate = self.config.get('SIMULATE_MATRIX', '0', str) == '1' or not MATRIX_AVAILABLE
        
        # Font paths - look in the fonts folder next to this file
        self.font_dir = Path(__file__).parent / 'fonts'
        
        # Initialize matrix hardware
        self.matrix = None
        self.canvas = None
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        
        if not self.simulate:
            self._init_hardware()
        else:
            print("Matrix Display: Running in SIMULATION mode")
    
    def _get_config_values(self):
        """Get current configuration values (refreshes if .env changed)."""
        # Matrix hardware configuration - dynamically fetched
        width = self.config.get('MATRIX_WIDTH', 64, int)
        height = self.config.get('MATRIX_HEIGHT', 64, int)
        brightness = self.config.get('MATRIX_BRIGHTNESS', 50, int)
        
        # Color configuration (RGB tuples)
        color_time = self.config.get_color('MATRIX_COLOR_TIME', (255, 255, 255))
        color_callsign = self.config.get_color('MATRIX_COLOR_CALLSIGN', (255, 255, 255))
        color_distance = self.config.get_color('MATRIX_COLOR_DISTANCE', (255, 255, 255))
        color_altitude = self.config.get_color('MATRIX_COLOR_ALTITUDE', (255, 255, 255))
        color_speed = self.config.get_color('MATRIX_COLOR_SPEED', (255, 255, 255))
        color_no_aircraft = self.config.get_color('MATRIX_COLOR_NO_AIRCRAFT', (255, 255, 255))
        color_border = self.config.get_color('MATRIX_COLOR_BORDER', (100, 100, 100))
        
        # Brightness configuration
        brightness_max = self.config.get('MATRIX_BRIGHTNESS_MAX', 255, int)
        brightness_min = self.config.get('MATRIX_BRIGHTNESS_MIN', 100, int)
        
        return {
            'width': width,
            'height': height,
            'brightness': brightness,
            'color_time': color_time,
            'color_callsign': color_callsign,
            'color_distance': color_distance,
            'color_altitude': color_altitude,
            'color_speed': color_speed,
            'color_no_aircraft': color_no_aircraft,
            'color_border': color_border,
            'brightness_max': brightness_max,
            'brightness_min': brightness_min,
        }
    
    def _apply_brightness(self, color: tuple, brightness_factor: float) -> tuple:
        """Apply brightness factor to a color."""
        return tuple(int(c * brightness_factor) for c in color)
    
    def _calculate_brightness_factor(self, current_time: datetime.datetime) -> float:
        """Calculate brightness factor based on time of day (0.0 to 1.0)."""
        # Get current config values
        cfg = self._get_config_values()
        brightness_max = cfg['brightness_max']
        brightness_min = cfg['brightness_min']
        
        # Get hour as decimal (e.g., 13.5 for 1:30 PM)
        hour_decimal = current_time.hour + current_time.minute / 60.0
        
        # Noon is 12.0, midnight is 0.0 or 24.0
        # Calculate how far we are from noon (in hours)
        distance_from_noon = abs(hour_decimal - 12.0)
        
        # Maximum distance from noon is 12 hours
        # At noon: distance = 0, brightness = max
        # At midnight: distance = 12, brightness = min
        brightness_range = brightness_max - brightness_min
        brightness = brightness_max - (distance_from_noon / 12.0) * brightness_range
        
        # Return as factor (0.0 to 1.0)
        return brightness / 255.0
    
    def _init_hardware(self):
        """Initialize the LED matrix hardware."""
        try:
            cfg = self._get_config_values()
            width = cfg['width']
            height = cfg['height']
            brightness = cfg['brightness']
            
            print(f"Matrix Display: Attempting hardware init {width}x{height}...")
            
            # Configure rgbmatrix options
            options = RGBMatrixOptions()
            options.rows = height
            options.cols = width
            options.chain_length = 1
            options.brightness = brightness
            options.parallel = 1
            options.hardware_mapping = 'regular'
            options.pwm_lsb_nanoseconds = 150
            options.disable_hardware_pulsing = True
            options.gpio_slowdown = 3
            
            self.matrix = RGBMatrix(options=options)
            self.canvas = self.matrix.CreateFrameCanvas()
            
            print("Matrix Display: Canvas created")
            
            # Load fonts
            base = os.path.dirname(__file__)
            def _try_load(filename: str):
                path = os.path.join(base, 'fonts', filename)
                try:
                    f = graphics.Font()
                    f.LoadFont(path)
                    return f
                except Exception:
                    return None

            self.font_large = _try_load('10x20.bdf')
            self.font_medium = _try_load('7x13.bdf')
            self.font_small = _try_load('6x10.bdf')
            
            print(f"Matrix Display: Hardware initialized successfully!")
            
            # Test display by clearing it
            self.canvas.Clear()
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            print("Matrix Display: Test clear completed")
            
        except Exception as e:
            import traceback
            print(f"Matrix Display: Hardware init failed with exception: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            print("Matrix Display: Falling back to simulation mode")
            self.simulate = True
            self.matrix = None
            self.canvas = None
    
    def clear(self):
        """Clear the matrix display."""
        if self.simulate:
            print("Matrix: [CLEAR]")
            return
        
        if self.canvas and self.matrix:
            try:
                with self._state_lock:
                    self.canvas.Clear()
                    self.canvas = self.matrix.SwapOnVSync(self.canvas)
            except Exception as e:
                print(f"Matrix clear error: {e}")
    
    def display_time_and_aircraft(
        self,
        current_time: datetime.datetime,
        aircraft_data: Optional[Dict] = None
    ):
        """
        Display time and aircraft information on matrix.
        
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
            with self._state_lock:
                # Get current config
                cfg = self._get_config_values()
                width = cfg['width']
                height = cfg['height']
                
                # Calculate brightness factor based on time of day
                brightness_factor = self._calculate_brightness_factor(current_time)
                
                # Clear canvas
                self.canvas.Clear()
                
                # Draw border
                border_color = self._apply_brightness(cfg['color_border'], brightness_factor)
                border_gfx = graphics.Color(*border_color)
                graphics.DrawLine(self.canvas, 0, 0, width - 1, 0, border_gfx)
                graphics.DrawLine(self.canvas, 0, height - 1, width - 1, height - 1, border_gfx)
                graphics.DrawLine(self.canvas, 0, 0, 0, height - 1, border_gfx)
                graphics.DrawLine(self.canvas, width - 1, 0, width - 1, height - 1, border_gfx)
                
                # Format time - always display with AM/PM
                time_str = current_time.strftime("%I:%M %p")
                
                # Draw time at top (line 1)
                time_color = self._apply_brightness(cfg['color_time'], brightness_factor)
                time_gfx = graphics.Color(*time_color)
                graphics.DrawText(self.canvas, self.font_medium or self.font_large, 4, 12, time_gfx, time_str)
                
                if aircraft_data:
                    # Draw aircraft information
                    y_offset = 24
                    
                    # Callsign
                    callsign = aircraft_data.get('callsign', aircraft_data.get('icao', 'N/A'))
                    if callsign and callsign != 'N/A':
                        callsign = callsign.strip()[:10]  # Limit length
                        callsign_color = self._apply_brightness(cfg['color_callsign'], brightness_factor)
                        callsign_gfx = graphics.Color(*callsign_color)
                        graphics.DrawText(self.canvas, self.font_medium or self.font_small, 4, y_offset, callsign_gfx, callsign)
                        y_offset += 12
                    
                    # Route information (origin -> destination)
                    route_info = aircraft_data.get('route_info')
                    if route_info:
                        origin = route_info.get('origin', '')[:4]
                        dest = route_info.get('destination', '')[:4]
                        if origin and dest:
                            # Remove first character from airport codes
                            origin_short = origin[1:] if len(origin) > 1 else origin
                            dest_short = dest[1:] if len(dest) > 1 else dest
                            route_str = f"{origin_short}-{dest_short}"
                            
                            route_color = self._apply_brightness(cfg['color_callsign'], brightness_factor)
                            route_gfx = graphics.Color(*route_color)
                            graphics.DrawText(self.canvas, self.font_small, 4, y_offset, route_gfx, route_str)
                            y_offset += 12
                    
                    # Distance or altitude/speed
                    distance = aircraft_data.get('distance')
                    altitude = aircraft_data.get('altitude')
                    groundspeed = aircraft_data.get('groundspeed')
                    
                    if distance is not None:
                        dist_str = f"{distance:.1f}mi"
                        dist_color = self._apply_brightness(cfg['color_distance'], brightness_factor)
                        dist_gfx = graphics.Color(*dist_color)
                        graphics.DrawText(self.canvas, self.font_small, 4, y_offset, dist_gfx, dist_str)
                        y_offset += 12
                    else:
                        # No position data - show altitude and speed instead
                        if altitude is not None:
                            alt_str = f"{altitude}ft"
                            alt_color = self._apply_brightness(cfg['color_altitude'], brightness_factor)
                            alt_gfx = graphics.Color(*alt_color)
                            graphics.DrawText(self.canvas, self.font_small, 4, y_offset, alt_gfx, alt_str)
                            y_offset += 12
                        
                        if groundspeed is not None:
                            spd_str = f"{groundspeed}kt"
                            spd_color = self._apply_brightness(cfg['color_speed'], brightness_factor)
                            spd_gfx = graphics.Color(*spd_color)
                            graphics.DrawText(self.canvas, self.font_small, 4, y_offset, spd_gfx, spd_str)
                
                # Swap canvas to display
                self.canvas = self.matrix.SwapOnVSync(self.canvas)
            
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
        """Display startup message."""
        if self.simulate:
            print("\n" + "=" * 40)
            print("MATRIX: SYSTEM STARTING...")
            print("=" * 40 + "\n")
            return
        
        if not self.matrix or not self.canvas:
            return
        
        try:
            with self._state_lock:
                self.canvas.Clear()
                
                # Draw startup message
                startup_color = graphics.Color(0, 255, 0)
                graphics.DrawText(self.canvas, self.font_medium or self.font_large, 12, 20, startup_color, "ADS-B")
                graphics.DrawText(self.canvas, self.font_small or self.font_medium, 8, 35, startup_color, "Starting")
                
                # Swap canvas
                self.canvas = self.matrix.SwapOnVSync(self.canvas)
                
                time.sleep(2)
        except Exception as e:
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
