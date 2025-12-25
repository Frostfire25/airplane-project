#!/usr/bin/env python3
"""
Main entry point for ADS-B aircraft tracking and display system.
Uses APScheduler for periodic data collection and matrix display updates.
"""

import os
import time as _time
from pathlib import Path
from dotenv import load_dotenv as _load_dotenv

# Load .env early and set TZ before importing other modules
try:
    _base_dir = Path(__file__).resolve().parent
    _env_file = _base_dir / '.env'
    _load_dotenv(dotenv_path=_env_file)
    _env_tz = os.getenv('TZ') or os.getenv('TIMEZONE')
    if _env_tz:
        os.environ['TZ'] = _env_tz
        try:
            if hasattr(_time, 'tzset'):
                _time.tzset()
        except Exception:
            pass
except Exception:
    pass

import datetime
import sys
import signal
import threading
from dateutil.tz import gettz
from atexit import register as atexit_register
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor

# Import ADS-B decoder utilities
from adsbfeeder import ADSBDecoder, is_valid_message, get_message_type

# Import matrix display
from matrix import display_aircraft_info, matrix_startup, matrix_shutdown

# Import FlightAware scraper
from flightaware import FlightAwareScraper

# Load .env located next to this module
base_dir = Path(__file__).resolve().parent
env_path = base_dir / '.env'
_load_dotenv(dotenv_path=env_path)

# Matrix timezone: read from .env (TIMEZONE or TZ) or default to America/New_York
MATRIX_TIMEZONE = os.getenv('TIMEZONE') or os.getenv('TZ') or 'America/New_York'
MATRIX_ZONE = gettz(MATRIX_TIMEZONE) or gettz('UTC')

# Load configuration from environment
LATITUDE = float(os.getenv('LATITUDE', '0.0'))
LONGITUDE = float(os.getenv('LONGITUDE', '0.0'))
ADSB_HOST = os.getenv('ADSB_HOST', '127.0.0.1')
ADSB_PORT = int(os.getenv('ADSB_PORT', '30005'))
ADSB_DATA_TYPE = os.getenv('ADSB_DATA_TYPE', 'beast')  # 'raw', 'beast', or 'avr'
MATRIX_SCHEDULE_SECONDS = int(os.getenv('MATRIX_SCHEDULE_SECONDS', '60'))
ADSB_POLL_SCHEDULE_SECONDS = int(os.getenv('ADSB_POLL_SCHEDULE_SECONDS', '5'))
AIRCRAFT_DISPLAY_DURATION = int(os.getenv('AIRCRAFT_DISPLAY_DURATION', '10'))

# Aircraft display rotation
current_aircraft_index = 0
last_rotation_time = datetime.datetime.now(datetime.timezone.utc)

# Initialize the ADS-B decoder with reference position for single-message decoding
adsb_decoder = ADSBDecoder(reference_lat=LATITUDE, reference_lon=LONGITUDE)

# Initialize FlightAware scraper
flightaware_scraper = FlightAwareScraper()

# Track aircraft data
aircraft_tracking = {}
nearest_aircraft = None

# Cache for flight route lookups to avoid excessive requests
route_cache = {}  # {callsign: route_info}

# Create APScheduler with a thread pool executor
executors = {"default": ThreadPoolExecutor(max_workers=4)}
sched = BackgroundScheduler(executors=executors)

# Event to block main thread; set on shutdown to exit cleanly
stop_event = threading.Event()


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in miles.
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 3959.0  # Earth radius in miles
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c


def update_aircraft_position(decoded_data: dict):
    """Update aircraft tracking data with new decoded information."""
    global nearest_aircraft, aircraft_tracking
    
    icao = decoded_data.get('icao')
    if not icao:
        return
    
    # Initialize or update aircraft data
    if icao not in aircraft_tracking:
        aircraft_tracking[icao] = {
            'icao': icao,
            'last_seen': datetime.datetime.now(datetime.timezone.utc),
            'messages_received': 0
        }
    
    aircraft = aircraft_tracking[icao]
    aircraft['last_seen'] = datetime.datetime.now(datetime.timezone.utc)
    aircraft['messages_received'] += 1
    
    # Update with new data - filter out 'timestamp' and other non-aircraft fields
    for key in ['callsign', 'altitude', 'groundspeed', 'track', 'vertical_rate', 
                'latitude', 'longitude', 'typecode', 'category']:
        if key in decoded_data and decoded_data[key] is not None:
            aircraft[key] = decoded_data[key]
    
    # Try to get route information if we have a callsign (for any aircraft, not just nearest)
    callsign = aircraft.get('callsign', '').strip()
    if callsign and 'route_info' not in aircraft:
        # Check cache first (cache stores None for failed lookups to avoid retrying)
        if callsign in route_cache:
            route_info = route_cache[callsign]
            if route_info:  # Only populate if route info was found
                aircraft['route_info'] = route_info
        else:
            # Fetch from FlightAware (only once per callsign)
            try:
                route_info = flightaware_scraper.get_flight_info(callsign)
                if route_info:
                    route_cache[callsign] = route_info
                    aircraft['route_info'] = route_info
                    origin = route_info.get('origin', '?')[:3]
                    dest = route_info.get('destination', '?')[:3]
                    print(f"🛫 Route: {callsign} {origin}→{dest}")
                else:
                    # Cache the failed lookup to avoid retrying
                    route_cache[callsign] = None
            except Exception as e:
                # Cache the failed lookup to avoid retrying
                route_cache[callsign] = None
    
    # Calculate distance if we have position
    if 'latitude' in aircraft and 'longitude' in aircraft:
        aircraft['distance'] = calculate_distance(
            LATITUDE, LONGITUDE,
            aircraft['latitude'], aircraft['longitude']
        )
        
        # Update nearest aircraft
        if nearest_aircraft is None or aircraft['distance'] < nearest_aircraft.get('distance', float('inf')):
            nearest_aircraft = aircraft.copy()
            callsign = aircraft.get('callsign', icao)
            route_info = aircraft.get('route_info')
            route_str = ""
            if route_info:
                origin = route_info.get('origin', '')[:3]
                dest = route_info.get('destination', '')[:3]
                if origin and dest:
                    route_str = f" | {origin}→{dest}"
            print(f"🎯 Nearest: {callsign} @ {aircraft['distance']:.1f}mi{route_str}")


def _adsb_poll_run():
    """
    Poll for ADS-B messages and decode them.
    This is a simplified version - in production you'd want to connect to a TCP stream.
    """
    # Clean up old aircraft (not seen in last 60 seconds)
    cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=60)
    stale_aircraft = [icao for icao, data in aircraft_tracking.items() 
                      if data['last_seen'] < cutoff_time]
    for icao in stale_aircraft:
        callsign = aircraft_tracking[icao].get('callsign', icao)
        print(f"✈️  Lost: {callsign} ({icao})")
        del aircraft_tracking[icao]
    
    # Count aircraft with position data
    aircraft_with_position = [a for a in aircraft_tracking.values() 
                             if 'latitude' in a and 'longitude' in a]
    
    # Summary output
    if len(aircraft_tracking) > 0:
        status_parts = []
        status_parts.append(f"Tracking: {len(aircraft_tracking)} aircraft")
        
        if len(aircraft_with_position) > 0:
            status_parts.append(f"{len(aircraft_with_position)} with position")
        
        # List aircraft with callsigns
        aircraft_list = []
        for data in aircraft_tracking.values():
            callsign = data.get('callsign', data['icao'])
            route_info = data.get('route_info')
            route_str = ""
            if route_info:
                origin = route_info.get('origin', '')[:3]
                dest = route_info.get('destination', '')[:3]
                if origin and dest:
                    route_str = f" {origin}→{dest}"
            
            if 'distance' in data:
                aircraft_list.append(f"{callsign}{route_str} ({data['distance']:.1f}mi)")
            else:
                aircraft_list.append(f"{callsign}{route_str}")
        
        if aircraft_list:
            status_parts.append("| " + ", ".join(aircraft_list))
        
        print(f"✈️  {' '.join(status_parts)}")
        
        if nearest_aircraft:
            callsign = nearest_aircraft.get('callsign', nearest_aircraft['icao'])
            dist = nearest_aircraft.get('distance', 0)
            alt = nearest_aircraft.get('altitude', 'N/A')
            route_info = nearest_aircraft.get('route_info')
            route_str = ""
            if route_info:
                origin = route_info.get('origin', '')[:3]
                dest = route_info.get('destination', '')[:3]
                if origin and dest:
                    route_str = f" | {origin}→{dest}"
            print(f"   Nearest: {callsign} @ {dist:.1f}mi, {alt}ft{route_str}")
    else:
        print("✈️  No aircraft currently tracked")


def _matrix_display_run():
    """Update matrix display with current aircraft, cycling through all tracked aircraft."""
    global nearest_aircraft, current_aircraft_index, last_rotation_time
    
    now_local = datetime.datetime.now(MATRIX_ZONE)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    time_str = now_local.strftime("%I:%M %p")
    
    try:
        display_aircraft = None
        
        # Get all tracked aircraft sorted by distance (nearest first), then by last_seen
        if aircraft_tracking:
            sorted_aircraft = sorted(
                aircraft_tracking.values(),
                key=lambda a: (a.get('distance', float('inf')), -a['last_seen'].timestamp())
            )
            
            # Check if it's time to rotate to next aircraft
            time_since_rotation = (now_utc - last_rotation_time).total_seconds()
            if time_since_rotation >= AIRCRAFT_DISPLAY_DURATION:
                current_aircraft_index = (current_aircraft_index + 1) % len(sorted_aircraft)
                last_rotation_time = now_utc
            
            # Ensure index is valid
            if current_aircraft_index >= len(sorted_aircraft):
                current_aircraft_index = 0
            
            display_aircraft = sorted_aircraft[current_aircraft_index]
        else:
            # Reset rotation when no aircraft
            current_aircraft_index = 0
            last_rotation_time = now_utc
        
        if display_aircraft:
            icao = display_aircraft['icao']
            callsign = display_aircraft.get('callsign', 'N/A').strip()
            distance = display_aircraft.get('distance')  # May be None
            altitude = display_aircraft.get('altitude', 'N/A')
            groundspeed = display_aircraft.get('groundspeed', 'N/A')
            route_info = display_aircraft.get('route_info')
            
            # Build compact status message with rotation info
            total_aircraft = len(aircraft_tracking)
            status = f"🖥️  Display: {callsign} [{current_aircraft_index + 1}/{total_aircraft}]"
            if distance is not None:
                status += f" @ {distance:.1f}mi"
            status += f", {altitude}ft, {groundspeed}kt"
            if route_info:
                origin = route_info.get('origin', '')[:3]
                dest = route_info.get('destination', '')[:3]
                if origin and dest:
                    status += f" | {origin}→{dest}"
            print(status)
            
            # Debug: Show what's being sent to matrix display
            print(f"   DEBUG: route_info in display_aircraft = {display_aircraft.get('route_info')}")
            
            # Update matrix display with aircraft data
            display_aircraft_info(now_local, display_aircraft)
        else:
            # No aircraft - just show time without "No Aircraft" message
            display_aircraft_info(now_local, None)
    except Exception as e:
        import traceback
        print(f"Error updating matrix display: {e}")
        print(f"Traceback: {traceback.format_exc()}")


def process_adsb_message(message: str):
    """
    Process a single ADS-B message.
    This should be called when receiving messages from your ADS-B source.
    """
    if not is_valid_message(message):
        return
    
    # Decode with current timestamp
    import time
    decoded = adsb_decoder.decode_message(message, timestamp=time.time())
    if decoded:
        icao = decoded.get('icao', 'N/A')
        
        # Log significant events only
        if 'callsign' in decoded:
            callsign = decoded.get('callsign', '').strip()
            print(f"✈️  New: {callsign} ({icao})")
        elif 'latitude' in decoded:
            # First position decode for this aircraft
            if icao in aircraft_tracking and 'latitude' not in aircraft_tracking[icao]:
                callsign = aircraft_tracking[icao].get('callsign', icao)
                print(f"📍 Position: {callsign} @ {decoded['latitude']:.4f}, {decoded['longitude']:.4f}")
        
        update_aircraft_position(decoded)


def shutdown_scheduler(signum=None, frame=None):
    """Idempotent shutdown handler invoked by signals or manually."""
    try:
        if stop_event.is_set():
            return
        print("Shutting down...")
        
        # Shutdown scheduler
        try:
            sched.shutdown(wait=False)
        except Exception:
            pass
        
        # Remove pending jobs
        try:
            sched.remove_all_jobs()
        except Exception:
            pass
        
        # Signal main thread to exit
        try:
            stop_event.set()
        except Exception:
            pass
        
        # Shutdown matrix hardware
        try:
            matrix_shutdown()
        except Exception as e:
            print(f"Matrix shutdown error: {e}")
        
        print("Shutdown complete.")
        try:
            sys.exit(0)
        except Exception:
            pass
    except Exception as e:
        print(f"Error shutting down scheduler: {e}")


# Ensure scheduler shuts down cleanly on exit or signals
atexit_register(shutdown_scheduler)
signal.signal(signal.SIGINT, shutdown_scheduler)
signal.signal(signal.SIGTERM, shutdown_scheduler)


def start_tcp_listener():
    """
    Start a background thread to listen for ADS-B messages from TCP source.
    This connects to dump1090/readsb and processes messages in real-time.
    """
    import socket
    import threading
    
    def tcp_listener_thread():
        print(f"Connecting to ADS-B source at {ADSB_HOST}:{ADSB_PORT} ({ADSB_DATA_TYPE} format)...")
        
        while not stop_event.is_set():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((ADSB_HOST, ADSB_PORT))
                print(f"Connected to ADS-B source at {ADSB_HOST}:{ADSB_PORT}")
                
                buffer = b''
                while not stop_event.is_set():
                    try:
                        data = sock.recv(4096)
                        if not data:
                            print("Connection closed by ADS-B source")
                            break
                        
                        buffer += data
                        
                        # Process messages based on format
                        if ADSB_DATA_TYPE == 'raw':
                            # Raw format: one message per line, ASCII hex
                            lines = buffer.split(b'\n')
                            buffer = lines[-1]  # Keep incomplete line
                            
                            for line in lines[:-1]:
                                try:
                                    msg = line.decode('ascii').strip()
                                    if msg and len(msg) in [14, 28]:
                                        process_adsb_message(msg)
                                except Exception as e:
                                    pass
                        
                        elif ADSB_DATA_TYPE == 'beast':
                            # Beast binary format parsing - simplified version
                            # Beast format: <esc> "1" + 6 bytes timestamp + mode-S data
                            msg_count = 0
                            while len(buffer) > 0:
                                # Look for escape character (0x1A)
                                esc_pos = buffer.find(b'\x1a')
                                if esc_pos == -1:
                                    buffer = b''
                                    break
                                
                                buffer = buffer[esc_pos:]
                                
                                if len(buffer) < 2:
                                    break
                                
                                msg_type = buffer[1:2]
                                
                                # Calculate expected message length based on type
                                if msg_type == b'1':  # Mode-AC
                                    msg_len = 11
                                elif msg_type == b'2':  # Mode-S short (7 bytes)
                                    msg_len = 16
                                elif msg_type == b'3':  # Mode-S long (14 bytes)
                                    msg_len = 23
                                else:
                                    buffer = buffer[1:]
                                    continue
                                
                                if len(buffer) < msg_len:
                                    break
                                
                                # Extract message (skip esc + type + 6 byte timestamp)
                                msg_data = buffer[9:msg_len]
                                
                                # Convert to hex string
                                try:
                                    hex_msg = msg_data.hex().upper()
                                    if len(hex_msg) in [14, 28]:
                                        msg_count += 1
                                        if msg_count % 100 == 0:
                                            print(f"Processed {msg_count} messages, last: {hex_msg[:14]}")
                                        process_adsb_message(hex_msg)
                                except (AttributeError, ValueError, TypeError) as e:
                                    # Skip malformed messages silently
                                    pass
                                except Exception as e:
                                    if str(e) != 'timestamp':  # Suppress timestamp errors
                                        print(f"Error processing message: {e}")
                                
                                buffer = buffer[msg_len:]
                        
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"Error receiving data: {e}")
                        break
                
                sock.close()
                
            except Exception as e:
                print(f"Connection error: {e}")
                if not stop_event.is_set():
                    print("Retrying connection in 5 seconds...")
                    _time.sleep(5)
    
    # Start TCP listener in background thread
    listener_thread = threading.Thread(target=tcp_listener_thread, daemon=True)
    listener_thread.start()
    return listener_thread


if __name__ == "__main__":
    """Start APScheduler with periodic jobs for ADS-B polling and matrix display."""
    
    print("=" * 60)
    print("ADS-B Aircraft Tracking System")
    print("=" * 60)
    print(f"Location: {LATITUDE}, {LONGITUDE}")
    print(f"Timezone: {MATRIX_TIMEZONE}")
    print(f"ADS-B Source: {ADSB_HOST}:{ADSB_PORT} ({ADSB_DATA_TYPE})")
    print("=" * 60)
    
    # Schedule the ADS-B poll job
    now = datetime.datetime.now(tz=sched.timezone)
    sched.add_job(
        _adsb_poll_run,
        "interval",
        seconds=ADSB_POLL_SCHEDULE_SECONDS,
        id="adsb_poll",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
        next_run_time=now,
    )
    
    # Schedule the matrix display update job
    sched.add_job(
        _matrix_display_run,
        "interval",
        seconds=MATRIX_SCHEDULE_SECONDS,
        id="matrix_display",
        max_instances=1,
        coalesce=True,
        next_run_time=now  # Start immediately
    )
    
    # Start the scheduler
    sched.start()
    print("Scheduler started (APScheduler). Ctrl-C to exit.")
    
    # Initialize matrix display
    try:
        matrix_startup()
    except Exception as e:
        print(f"Matrix startup error: {e}")
    
    # Display initial time immediately after startup
    try:
        import time
        time.sleep(2.5)  # Wait for startup message to show
        _matrix_display_run()  # Run once immediately
    except Exception as e:
        print(f"Initial display error: {e}")
    
    # Start TCP listener for real-time ADS-B messages
    listener = start_tcp_listener()
    
    try:
        # Use a short sleep loop for responsive Ctrl-C handling
        while not stop_event.is_set():
            _time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        print("\nReceived shutdown signal...")
        shutdown_scheduler()
        sys.exit(0)
