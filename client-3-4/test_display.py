#!/usr/bin/env python3
"""
Test script to simulate ADS-B aircraft data for UI testing.
Creates fake aircraft with position data to test the matrix display.
"""

import os
import time
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment
base_dir = Path(__file__).resolve().parent
env_path = base_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Import matrix display functions
from matrix import display_aircraft_info, matrix_startup, matrix_shutdown, get_matrix_display
from dateutil.tz import gettz

# Get timezone
MATRIX_TIMEZONE = os.getenv('TIMEZONE') or os.getenv('TZ') or 'America/New_York'
MATRIX_ZONE = gettz(MATRIX_TIMEZONE) or gettz('UTC')

# Your location (from .env)
YOUR_LAT = float(os.getenv('LATITUDE', '42.8270'))
YOUR_LON = float(os.getenv('LONGITUDE', '-71.3960'))


class FakeAircraft:
    """Simulates aircraft data for testing."""
    
    def __init__(self, icao, callsign, lat, lon, altitude, groundspeed, origin=None, destination=None):
        self.icao = icao
        self.callsign = callsign
        self.lat = lat
        self.lon = lon
        self.altitude = altitude
        self.groundspeed = groundspeed
        self.origin = origin
        self.destination = destination
        
    def to_dict(self):
        """Convert to aircraft tracking dictionary."""
        from math import radians, sin, cos, sqrt, atan2
        
        # Calculate distance using Haversine formula
        R = 3959.0  # Earth radius in miles
        lat1_rad = radians(YOUR_LAT)
        lat2_rad = radians(self.lat)
        delta_lat = radians(self.lat - YOUR_LAT)
        delta_lon = radians(self.lon - YOUR_LON)
        
        a = sin(delta_lat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c
        
        data = {
            'icao': self.icao,
            'callsign': self.callsign,
            'latitude': self.lat,
            'longitude': self.lon,
            'altitude': self.altitude,
            'groundspeed': self.groundspeed,
            'distance': distance,
            'last_seen': datetime.datetime.now(datetime.timezone.utc),
            'messages_received': 100
        }
        
        # Add route info if available
        if self.origin and self.destination:
            data['route_info'] = {
                'callsign': self.callsign,
                'origin': self.origin,
                'destination': self.destination,
                'origin_name': f'{self.origin} Airport',
                'destination_name': f'{self.destination} Airport'
            }
        
        return data


def create_test_aircraft():
    """Create a list of fake aircraft for testing."""
    return [
        # EL AL flight from Tel Aviv to NYC (nearby)
        FakeAircraft(
            icao='738012',
            callsign='ELY001',
            lat=42.9,  # Near your location (Nashua, NH)
            lon=-71.5,
            altitude=35000,
            groundspeed=450,
            origin='LLBG',  # Tel Aviv
            destination='KJFK'  # JFK
        ),
        
        # Delta flight further away
        FakeAircraft(
            icao='A12345',
            callsign='DAL123',
            lat=43.2,
            lon=-72.0,
            altitude=28000,
            groundspeed=420,
            origin='KATL',  # Atlanta
            destination='KBOS'  # Boston
        ),
        
        # United flight even further
        FakeAircraft(
            icao='AB1234',
            callsign='UAL456',
            lat=44.0,
            lon=-73.0,
            altitude=31000,
            groundspeed=480,
            origin='KSFO',  # San Francisco
            destination='KEWR'  # Newark
        ),
    ]


def test_display_cycle(duration_seconds=60, update_interval=5):
    """
    Run a test cycle displaying fake aircraft data.
    
    Args:
        duration_seconds: How long to run the test
        update_interval: Seconds between display updates
    """
    print("=" * 60)
    print("ADS-B Display Test Mode")
    print("=" * 60)
    print(f"Your location: {YOUR_LAT}, {YOUR_LON}")
    print(f"Timezone: {MATRIX_TIMEZONE}")
    print(f"Duration: {duration_seconds} seconds")
    print(f"Update interval: {update_interval} seconds")
    print("=" * 60)
    
    # Initialize matrix
    try:
        matrix_startup()
        time.sleep(2)
    except Exception as e:
        print(f"Matrix startup error: {e}")
    
    # Create test aircraft
    aircraft_list = create_test_aircraft()
    current_index = 0
    
    start_time = time.time()
    iteration = 0
    
    try:
        while time.time() - start_time < duration_seconds:
            iteration += 1
            
            # Get current aircraft to display (cycle through them)
            aircraft = aircraft_list[current_index]
            aircraft_data = aircraft.to_dict()
            
            # Get current time
            now = datetime.datetime.now(MATRIX_ZONE)
            
            print(f"\n--- Test Iteration {iteration} ---")
            print(f"Displaying: {aircraft.callsign} ({aircraft.icao})")
            print(f"  Position: {aircraft.lat:.4f}, {aircraft.lon:.4f}")
            print(f"  Altitude: {aircraft.altitude} ft")
            print(f"  Speed: {aircraft.groundspeed} kt")
            print(f"  Distance: {aircraft_data['distance']:.2f} mi")
            if 'route_info' in aircraft_data:
                route = aircraft_data['route_info']
                print(f"  Route: {route['origin']} -> {route['destination']}")
            
            # Update display
            display_aircraft_info(now, aircraft_data)
            
            # Move to next aircraft for next iteration
            current_index = (current_index + 1) % len(aircraft_list)
            
            # Wait before next update
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        print("\n\nTest stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "=" * 60)
        print("Test Complete")
        print("=" * 60)
        try:
            matrix_shutdown()
        except Exception as e:
            print(f"Matrix shutdown error: {e}")


def test_single_aircraft():
    """Test display with a single aircraft."""
    print("Testing with single aircraft...")
    
    try:
        matrix_startup()
        time.sleep(2)
    except Exception as e:
        print(f"Matrix startup error: {e}")
    
    aircraft = FakeAircraft(
        icao='738012',
        callsign='ELY001',
        lat=42.9,
        lon=-71.5,
        altitude=35000,
        groundspeed=450,
        origin='LLBG',
        destination='KJFK'
    )
    
    aircraft_data = aircraft.to_dict()
    now = datetime.datetime.now(MATRIX_ZONE)
    
    print("\nAircraft Data:")
    for key, value in aircraft_data.items():
        print(f"  {key}: {value}")
    
    print("\nDisplaying on matrix...")
    display_aircraft_info(now, aircraft_data)
    
    print("\nHolding for 30 seconds... Press Ctrl+C to exit")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\nStopped")
    
    matrix_shutdown()


def test_no_aircraft():
    """Test display with no aircraft."""
    print("Testing 'No Aircraft' display...")
    
    try:
        matrix_startup()
        time.sleep(2)
    except Exception as e:
        print(f"Matrix startup error: {e}")
    
    now = datetime.datetime.now(MATRIX_ZONE)
    
    print("\nDisplaying 'No Aircraft' message...")
    display_aircraft_info(now, None)
    
    print("\nHolding for 10 seconds...")
    time.sleep(10)
    
    matrix_shutdown()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == "single":
            test_single_aircraft()
        elif mode == "none":
            test_no_aircraft()
        elif mode == "cycle":
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            interval = int(sys.argv[3]) if len(sys.argv) > 3 else 5
            test_display_cycle(duration, interval)
        else:
            print("Unknown mode. Use: single, none, or cycle")
    else:
        print("ADS-B Display Test Utility")
        print("=" * 60)
        print("\nUsage:")
        print("  python test_display.py single           - Test with one aircraft")
        print("  python test_display.py none             - Test 'No Aircraft' display")
        print("  python test_display.py cycle [dur] [int] - Cycle through aircraft")
        print("                                            dur=duration in seconds (default: 60)")
        print("                                            int=update interval (default: 5)")
        print("\nExamples:")
        print("  sudo ./.venv/bin/python test_display.py single")
        print("  sudo ./.venv/bin/python test_display.py cycle 120 10")
        print()
