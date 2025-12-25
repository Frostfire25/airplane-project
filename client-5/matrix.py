"""
LED Matrix Display Module for ADS-B Aircraft Tracking
Displays time and nearest aircraft information on RGB LED matrix.
"""

import os
import datetime
import time
import traceback
from pathlib import Path
from typing import Optional, Dict
import numpy as np

# Import dynamic configuration
from config import get_config

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
        
        # Get configuration instance
        self.config = get_config()
        
        # Check simulate mode
        self.simulate = self.config.get('SIMULATE_MATRIX', '0', str) == '1' or not MATRIX_AVAILABLE
        
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
    
    def _get_config_values(self):
        """Get current configuration values (refreshes if .env changed)."""
        # Matrix hardware configuration - dynamically fetched
        width = self.config.get('MATRIX_WIDTH', 64, int)
        height = self.config.get('MATRIX_HEIGHT', 64, int)
        bit_depth = self.config.get('MATRIX_BIT_DEPTH', 6, int)
        n_addr_lines = self.config.get('MATRIX_N_ADDR_LINES', 5, int)
        
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
        
        # Animation configuration
        animation_delay = self.config.get('MATRIX_ANIMATION_DELAY_MS', 500, int) / 1000.0
        scramble_opacity = self.config.get('MATRIX_SCRAMBLE_OPACITY', 65, int) / 100.0
        
        return {
            'width': width,
            'height': height,
            'bit_depth': bit_depth,
            'n_addr_lines': n_addr_lines,
            'color_time': color_time,
            'color_callsign': color_callsign,
            'color_distance': color_distance,
            'color_altitude': color_altitude,
            'color_speed': color_speed,
            'color_no_aircraft': color_no_aircraft,
            'color_border': color_border,
            'brightness_max': brightness_max,
            'brightness_min': brightness_min,
            'animation_delay': animation_delay,
            'scramble_opacity': scramble_opacity,
        }
    
    def _parse_color(self, color_str: str) -> tuple:
        """Parse color string 'R,G,B' to tuple."""
        try:
            r, g, b = color_str.split(',')
            return (int(r.strip()), int(g.strip()), int(b.strip()))
        except:
            return (255, 255, 255)  # Default white
    
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
    
    def _draw_border(self, draw, brightness_factor: float = 1.0):
        """Draw a 1-pixel border around the entire display."""
        cfg = self._get_config_values()
        border_color = self._apply_brightness(cfg['color_border'], brightness_factor)
        width = cfg['width']
        height = cfg['height']
        # Top border
        draw.line([(0, 0), (width - 1, 0)], fill=border_color)
        # Bottom border
        draw.line([(0, height - 1), (width - 1, height - 1)], fill=border_color)
        # Left border
        draw.line([(0, 0), (0, height - 1)], fill=border_color)
        # Right border
        draw.line([(width - 1, 0), (width - 1, height - 1)], fill=border_color)
    
    def _center_text(self, text: str, font) -> int:
        """Calculate x position to center text."""
        cfg = self._get_config_values()
        width = cfg['width']
        try:
            # Try to get actual text width from font
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
        except:
            # Fallback to estimation
            text_width = len(text) * 6
        return (width - text_width) // 2
    
    def _init_hardware(self):
        """Initialize the LED matrix hardware."""
        try:
            cfg = self._get_config_values()
            width = cfg['width']
            height = cfg['height']
            bit_depth = cfg['bit_depth']
            n_addr_lines = cfg['n_addr_lines']
            
            print(f"Matrix Display: Attempting hardware init {width}x{height}...")
            
            # Create PIL Image as framebuffer
            self.canvas = Image.new('RGB', (width, height), (0, 0, 0))
            print("Matrix Display: Canvas created")
            
            # Create numpy array from PIL image for PioMatter - use + 0 to make mutable copy
            self.framebuffer = np.asarray(self.canvas) + 0
            print(f"Matrix Display: Framebuffer created: shape={self.framebuffer.shape}, dtype={self.framebuffer.dtype}")
            
            # Ensure it's contiguous and the right type
            if not self.framebuffer.flags['C_CONTIGUOUS']:
                self.framebuffer = np.ascontiguousarray(self.framebuffer)
            
            # Create geometry
            geometry = Geometry(
                width=width,
                height=height,
                n_addr_lines=n_addr_lines,
                rotation=Orientation.Normal
            )
            print(f"Matrix Display: Geometry created: {width}x{height}, n_addr={n_addr_lines}")
            
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
        """Load appropriate PIL font based on size."""
        try:
            if size == 'large':
                # Use 10x20 for large text (time display)
                font_path = self.font_dir / '10x20.pil'
            elif size == 'medium':
                # Use 7x13 for medium text (aircraft info)
                font_path = self.font_dir / '7x13.pil'
            elif size == 'medium-small':
                # Use 6x13 for medium-large text
                font_path = self.font_dir / '6x13.pil'
            elif size == 'small':
                # Use 6x10 for small text
                font_path = self.font_dir / '6x10.pil'
            else:
                font_path = self.font_dir / '7x13.pil'
            
            # Try to load the PIL font
            if font_path.exists():
                return ImageFont.load(str(font_path))
        except Exception as e:
            pass
        
        # Fallback to default font
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
    
    def _draw_text_animated(self, text: str, x: int, y: int, color: tuple, font, previous_elements: list = None, delay: float = 0.05, brightness_factor: float = 1.0):
        """
        Draw text with Vestaboard-style character-by-character animation.
        Characters scramble rapidly and then settle into place one by one.
        Previous elements stay on screen during animation.
        
        Args:
            text: Text to display
            x, y: Position
            color: RGB color tuple
            font: Font to use
            previous_elements: List of (text, x, y, color, font) tuples for already-revealed elements
            delay: Delay before revealing each character (seconds)
            brightness_factor: Factor to adjust color brightness (0.0 to 1.0)
        """
        # Get current config
        cfg = self._get_config_values()
        width = cfg['width']
        height = cfg['height']
        
        # Apply brightness factor to color
        color = self._apply_brightness(color, brightness_factor)
        
        import random
        
        # Characters to use for scrambling effect
        scramble_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:-'
        
        # Fast flip rate for scrambling effect (milliseconds between scramble updates)
        flip_rate = 0.05  # 50ms = 20 flips per second
        
        if previous_elements is None:
            previous_elements = []
        
        # Animate each character position
        for i in range(len(text)):
            # Calculate how many scramble iterations to show before reveal
            num_flips = int(delay / flip_rate)
            
            # Rapidly scramble before revealing this character
            for flip in range(num_flips):
                # Clear canvas and redraw from scratch
                self.canvas = Image.new("RGB", (width, height), (0, 0, 0))
                draw = ImageDraw.Draw(self.canvas)
                
                # Draw border first
                self._draw_border(draw, brightness_factor)
                
                # Draw all previous elements (already revealed)
                for prev_text, prev_x, prev_y, prev_color, prev_font in previous_elements:
                    draw.text((prev_x, prev_y), prev_text, fill=prev_color, font=prev_font)
                
                # Build the current display text: revealed chars + scrambled chars
                display_text = ""
                for j, char in enumerate(text):
                    if j < i:
                        # Character is already revealed
                        display_text += char
                    else:
                        # Character is still scrambling
                        if char == ' ':
                            display_text += ' '
                        else:
                            display_text += random.choice(scramble_chars)
                
                # Draw revealed characters at full brightness
                revealed_text = display_text[:i]
                if revealed_text:
                    draw.text((x, y), revealed_text, fill=color, font=font)
                
                # Draw scrambling characters at reduced opacity
                scramble_text = display_text[i:]
                if scramble_text:
                    # Calculate width of revealed text to offset scrambling text
                    try:
                        revealed_bbox = font.getbbox(revealed_text) if revealed_text else (0, 0, 0, 0)
                        scramble_x = x + (revealed_bbox[2] - revealed_bbox[0])
                    except:
                        scramble_x = x + len(revealed_text) * 6
                    
                    # Apply scramble opacity from config
                    scramble_opacity = cfg['scramble_opacity']
                    scramble_color = self._apply_brightness(color, scramble_opacity)
                    draw.text((scramble_x, y), scramble_text, fill=scramble_color, font=font)
                
                # Update framebuffer and display
                self.framebuffer[:] = np.asarray(self.canvas)
                try:
                    self.matrix.show()
                except TimeoutError:
                    # If hardware times out, continue animation in memory
                    pass
                
                # Small delay before next scramble
                time.sleep(flip_rate)
            
            # Now reveal the character by drawing it one final time
            self.canvas = Image.new("RGB", (width, height), (0, 0, 0))
            draw = ImageDraw.Draw(self.canvas)
            
            # Draw border first
            self._draw_border(draw, brightness_factor)
            
            # Draw all previous elements
            for prev_text, prev_x, prev_y, prev_color, prev_font in previous_elements:
                draw.text((prev_x, prev_y), prev_text, fill=prev_color, font=prev_font)
            
            # Build text with this character now revealed
            display_text = ""
            for j, char in enumerate(text):
                if j <= i:
                    display_text += char
                else:
                    if char == ' ':
                        display_text += ' '
                    else:
                        display_text += random.choice(scramble_chars)
            
            draw.text((x, y), display_text, fill=color, font=font)
            
            # Update framebuffer and display
            self.framebuffer[:] = np.asarray(self.canvas)
            try:
                self.matrix.show()
            except TimeoutError:
                pass
    
    def clear(self):
        """Clear the matrix display."""
        if self.simulate:
            print("Matrix: [CLEAR]")
            return
        
        if self.canvas and self.matrix:
            try:
                cfg = self._get_config_values()
                # Create a fresh black canvas
                self.canvas = Image.new("RGB", (cfg['width'], cfg['height']), (0, 0, 0))
                
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
            # Get current config
            cfg = self._get_config_values()
            width = cfg['width']
            height = cfg['height']
            
            # Create a fresh canvas
            self.canvas = Image.new("RGB", (width, height), (0, 0, 0))
            draw = ImageDraw.Draw(self.canvas)
            
            # Calculate brightness factor based on time of day
            brightness_factor = self._calculate_brightness_factor(current_time)
            
            # Format time - always display with AM/PM
            time_str = current_time.strftime("%I:%M %p")
            
            # Draw time at top (centered, shifted 4px right) - use medium font
            font = self._get_font('medium')
            x_pos = self._center_text(time_str, font)
            
            # Track revealed elements
            revealed_elements = []
            
            # Always draw border and time (even when no aircraft)
            self._draw_border(draw, brightness_factor)
            adjusted_color = self._apply_brightness(cfg['color_time'], brightness_factor)
            self._draw_text(draw, time_str, x_pos, 4, adjusted_color, font)
            revealed_elements.append((time_str, x_pos, 4, adjusted_color, font))
            
            if aircraft_data:
                # Draw aircraft information
                y_offset = 24
                
                # Callsign with animation - centered
                callsign = aircraft_data.get('callsign', aircraft_data.get('icao', 'N/A'))
                if callsign and callsign != 'N/A':
                    callsign = callsign.strip()[:10]  # Limit length
                    
                    # Center the callsign
                    callsign_width = len(callsign) * 6  # Estimate 6 pixels per character for medium font
                    callsign_x = (width - callsign_width) // 2
                    
                    self._draw_text_animated(callsign, callsign_x, y_offset, cfg['color_callsign'], self._get_font('medium-small'), revealed_elements, delay=cfg['animation_delay'], brightness_factor=brightness_factor)
                    adjusted_callsign_color = self._apply_brightness(cfg['color_callsign'], brightness_factor)
                    revealed_elements.append((callsign, callsign_x, y_offset, adjusted_callsign_color, self._get_font('medium-small')))
                    y_offset += 12
                
                # Route information (origin -> destination) with animation - centered
                route_info = aircraft_data.get('route_info')
                print(f"   DEBUG matrix.py: route_info = {route_info}")
                if route_info:
                    origin = route_info.get('origin', '')[:4]
                    dest = route_info.get('destination', '')[:4]
                    if origin and dest:
                        # Remove first character from airport codes
                        origin_short = origin[1:] if len(origin) > 1 else origin
                        dest_short = dest[1:] if len(dest) > 1 else dest
                        route_str = f"{origin_short}-{dest_short}"
                        
                        # Center the route
                        route_width = len(route_str) * 6  # Estimate 6 pixels per character
                        route_x = (width - route_width) // 2
                        
                        self._draw_text_animated(route_str, route_x, y_offset, cfg['color_callsign'], self._get_font('medium-small'), revealed_elements, delay=cfg['animation_delay'], brightness_factor=brightness_factor)
                        adjusted_route_color = self._apply_brightness(cfg['color_callsign'], brightness_factor)
                        revealed_elements.append((route_str, route_x, y_offset, adjusted_route_color, self._get_font('medium-small')))
                        y_offset += 12
                
                # Distance with animation - centered (or show altitude/speed if no distance)
                distance = aircraft_data.get('distance')
                altitude = aircraft_data.get('altitude')
                groundspeed = aircraft_data.get('groundspeed')
                
                if distance is not None:
                    dist_str = f"{distance:.1f}mi"
                    
                    # Center the distance
                    dist_width = len(dist_str) * 6  # Estimate 6 pixels per character
                    dist_x = (width - dist_width) // 2
                    
                    self._draw_text_animated(dist_str, dist_x, y_offset, cfg['color_distance'], self._get_font('medium-small'), revealed_elements, delay=cfg['animation_delay'], brightness_factor=brightness_factor)
                else:
                    # No position data - show altitude and speed instead
                    if altitude is not None:
                        alt_str = f"{altitude}ft"
                        
                        # Center the altitude
                        alt_width = len(alt_str) * 6
                        alt_x = (width - alt_width) // 2
                        
                        self._draw_text_animated(alt_str, alt_x, y_offset, cfg['color_altitude'], self._get_font('medium-small'), revealed_elements, delay=cfg['animation_delay'], brightness_factor=brightness_factor)
                        adjusted_alt_color = self._apply_brightness(cfg['color_altitude'], brightness_factor)
                        revealed_elements.append((alt_str, alt_x, y_offset, adjusted_alt_color, self._get_font('medium-small')))
                        y_offset += 12
                    
                    if groundspeed is not None:
                        spd_str = f"{groundspeed}kt"
                        
                        # Center the speed
                        spd_width = len(spd_str) * 6
                        spd_x = (width - spd_width) // 2
                        
                        self._draw_text_animated(spd_str, spd_x, y_offset, cfg['color_speed'], self._get_font('medium-small'), revealed_elements, delay=cfg['animation_delay'], brightness_factor=brightness_factor)
            # If no aircraft_data, just show border and time (already drawn above)
            
            # Single update after all text is drawn
            self.framebuffer[:] = np.asarray(self.canvas)
            self.matrix.show()
            
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
            cfg = self._get_config_values()
            
            # Create fresh canvas
            self.canvas = Image.new("RGB", (cfg['width'], cfg['height']), (0, 0, 0))
            draw = ImageDraw.Draw(self.canvas)
            
            # Draw startup message
            self._draw_text(draw, "ADS-B", 12, 20, (0, 255, 0), self._get_font('medium'))
            self._draw_text(draw, "Starting", 8, 35, (0, 255, 0), self._get_font('small'))
            
            # Update framebuffer and display
            self.framebuffer[:] = np.asarray(self.canvas)
            self.matrix.show()
            
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
