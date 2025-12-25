#!/usr/bin/env python3
"""
Streamlit Web Interface for Airplane Tracker Configuration
Edit .env settings from your phone or any device on the network
"""

import streamlit as st
import os
from pathlib import Path
import re

# Page configuration
st.set_page_config(
    page_title="Airplane Tracker Config",
    page_icon="✈️",
    layout="wide"
)

ENV_FILE = Path(__file__).parent / ".env"

def parse_env_file(file_path):
    """Parse .env file and return dict of key-value pairs with comments"""
    config = {}
    current_section = "General"
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        
        # Section headers (comments that look like headers)
        if line.startswith('# ') and not '=' in line and len(line) > 10:
            if line.endswith('Configuration'):
                current_section = line[2:].strip()
        
        # Key-value pairs
        elif '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            if key not in config:
                config[key] = {
                    'value': value,
                    'section': current_section,
                    'comment': ''
                }
        
        # Comments for the next line
        elif line.startswith('#') and '=' not in line:
            pass  # We'll keep it simple for now
    
    return config

def save_env_file(file_path, original_lines, updates):
    """Update .env file preserving structure and comments"""
    new_lines = []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0].strip()
            if key in updates:
                # Replace with new value, preserve indentation
                indent = len(line) - len(line.lstrip())
                new_lines.append(' ' * indent + f"{key}={updates[key]}\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Write back
    with open(file_path, 'w') as f:
        f.writelines(new_lines)

def parse_color(color_str):
    """Parse R,G,B string to tuple"""
    try:
        r, g, b = map(int, color_str.split(','))
        return (r, g, b)
    except:
        return (255, 255, 255)

def color_to_str(color_tuple):
    """Convert color tuple to R,G,B string"""
    return f"{color_tuple[0]},{color_tuple[1]},{color_tuple[2]}"

# Main app
st.title("✈️ Airplane Tracker Configuration")
st.markdown("Edit your ADS-B aircraft tracking settings from any device")

if not ENV_FILE.exists():
    st.error(f"Configuration file not found: {ENV_FILE}")
    st.stop()

# Load configuration
config = parse_env_file(ENV_FILE)

# Create tabs for different sections
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📍 Location", 
    "📡 Data Source", 
    "⏱️ Scheduling", 
    "🖥️ Display Hardware",
    "🎨 Colors & Brightness"
])

# Store updates
updates = {}

with tab1:
    st.header("Location Settings")
    st.markdown("Your location is used to calculate aircraft distance and bearing")
    
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input(
            "Latitude",
            value=float(config.get('LATITUDE', {}).get('value', '0')),
            format="%.4f",
            help="Your location latitude (decimal degrees)"
        )
        updates['LATITUDE'] = str(lat)
    
    with col2:
        lon = st.number_input(
            "Longitude",
            value=float(config.get('LONGITUDE', {}).get('value', '0')),
            format="%.4f",
            help="Your location longitude (decimal degrees)"
        )
        updates['LONGITUDE'] = str(lon)
    
    timezone = st.text_input(
        "Timezone",
        value=config.get('TIMEZONE', {}).get('value', 'America/New_York'),
        help="IANA timezone name (e.g., America/New_York, Europe/London)"
    )
    updates['TIMEZONE'] = timezone
    updates['TZ'] = timezone

with tab2:
    st.header("ADS-B Data Source")
    st.markdown("Configure connection to your dump1090/readsb receiver")
    
    col1, col2 = st.columns(2)
    with col1:
        host = st.text_input(
            "Host",
            value=config.get('ADSB_HOST', {}).get('value', '127.0.0.1'),
            help="IP address of your ADS-B receiver"
        )
        updates['ADSB_HOST'] = host
        
        port = st.number_input(
            "Port",
            value=int(config.get('ADSB_PORT', {}).get('value', '30005')),
            min_value=1,
            max_value=65535,
            help="30002 = raw/AVR format, 30005 = Beast binary"
        )
        updates['ADSB_PORT'] = str(port)
    
    with col2:
        data_type = st.selectbox(
            "Data Format",
            options=['beast', 'raw', 'avr'],
            index=['beast', 'raw', 'avr'].index(config.get('ADSB_DATA_TYPE', {}).get('value', 'beast')),
            help="Data format from your receiver"
        )
        updates['ADSB_DATA_TYPE'] = data_type

with tab3:
    st.header("Scheduling & Timing")
    st.markdown("Control how often data is updated and displayed")
    
    col1, col2 = st.columns(2)
    with col1:
        adsb_poll = st.number_input(
            "ADS-B Poll Interval (seconds)",
            value=int(config.get('ADSB_POLL_SCHEDULE_SECONDS', {}).get('value', '5')),
            min_value=1,
            max_value=60,
            help="How often to fetch new aircraft data"
        )
        updates['ADSB_POLL_SCHEDULE_SECONDS'] = str(adsb_poll)
        
        matrix_update = st.number_input(
            "Display Update Interval (seconds)",
            value=int(config.get('MATRIX_SCHEDULE_SECONDS', {}).get('value', '5')),
            min_value=1,
            max_value=60,
            help="How often to refresh the display"
        )
        updates['MATRIX_SCHEDULE_SECONDS'] = str(matrix_update)
    
    with col2:
        display_duration = st.number_input(
            "Aircraft Display Duration (seconds)",
            value=int(config.get('AIRCRAFT_DISPLAY_DURATION', {}).get('value', '30')),
            min_value=5,
            max_value=300,
            help="How long to show each aircraft before cycling"
        )
        updates['AIRCRAFT_DISPLAY_DURATION'] = str(display_duration)
        
        anim_delay = st.number_input(
            "Animation Delay (milliseconds)",
            value=int(config.get('MATRIX_ANIMATION_DELAY_MS', {}).get('value', '500')),
            min_value=0,
            max_value=2000,
            help="Delay between character reveals"
        )
        updates['MATRIX_ANIMATION_DELAY_MS'] = str(anim_delay)
    
    scramble_opacity = st.slider(
        "Scramble Character Opacity",
        min_value=0,
        max_value=100,
        value=int(config.get('MATRIX_SCRAMBLE_OPACITY', {}).get('value', '65')),
        help="Brightness of scrambling characters (0=invisible, 100=full)"
    )
    updates['MATRIX_SCRAMBLE_OPACITY'] = str(scramble_opacity)

with tab4:
    st.header("Matrix Display Hardware")
    st.markdown("Configure your LED matrix panel settings")
    
    col1, col2 = st.columns(2)
    with col1:
        width = st.number_input(
            "Matrix Width",
            value=int(config.get('MATRIX_WIDTH', {}).get('value', '64')),
            min_value=32,
            max_value=256,
            help="Width of your LED matrix in pixels"
        )
        updates['MATRIX_WIDTH'] = str(width)
        
        height = st.number_input(
            "Matrix Height",
            value=int(config.get('MATRIX_HEIGHT', {}).get('value', '64')),
            min_value=32,
            max_value=256,
            help="Height of your LED matrix in pixels"
        )
        updates['MATRIX_HEIGHT'] = str(height)
        
        bit_depth = st.number_input(
            "Bit Depth",
            value=int(config.get('MATRIX_BIT_DEPTH', {}).get('value', '6')),
            min_value=1,
            max_value=11,
            help="Color depth (higher = more colors, more CPU)"
        )
        updates['MATRIX_BIT_DEPTH'] = str(bit_depth)
    
    with col2:
        addr_lines = st.number_input(
            "Address Lines",
            value=int(config.get('MATRIX_N_ADDR_LINES', {}).get('value', '5')),
            min_value=1,
            max_value=6,
            help="Number of address lines (usually 4 or 5)"
        )
        updates['MATRIX_N_ADDR_LINES'] = str(addr_lines)
        
        simulate = st.checkbox(
            "Simulate Matrix (Testing Mode)",
            value=config.get('SIMULATE_MATRIX', {}).get('value', '0') == '1',
            help="Enable to test without real hardware"
        )
        updates['SIMULATE_MATRIX'] = '1' if simulate else '0'

with tab5:
    st.header("Colors & Brightness")
    st.markdown("Customize display colors and brightness levels")
    
    st.subheader("Display Colors")
    st.markdown("Choose colors for different display elements (RGB format)")
    
    col1, col2 = st.columns(2)
    
    color_configs = [
        ('MATRIX_COLOR_TIME', 'Time Display', col1),
        ('MATRIX_COLOR_CALLSIGN', 'Callsign/Flight', col2),
        ('MATRIX_COLOR_DISTANCE', 'Distance', col1),
        ('MATRIX_COLOR_ALTITUDE', 'Altitude', col2),
        ('MATRIX_COLOR_SPEED', 'Speed', col1),
        ('MATRIX_COLOR_NO_AIRCRAFT', 'No Aircraft Message', col2),
        ('MATRIX_COLOR_BORDER', 'Border', col1),
    ]
    
    for key, label, column in color_configs:
        with column:
            current_color = parse_color(config.get(key, {}).get('value', '255,255,255'))
            color = st.color_picker(
                label,
                value=f"#{current_color[0]:02x}{current_color[1]:02x}{current_color[2]:02x}",
                key=key
            )
            # Convert hex to RGB
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            updates[key] = f"{r},{g},{b}"
    
    st.subheader("Brightness Control")
    st.markdown("Set brightness levels for day and night")
    
    col1, col2 = st.columns(2)
    with col1:
        brightness_max = st.slider(
            "Maximum Brightness (Noon)",
            min_value=0,
            max_value=255,
            value=int(config.get('MATRIX_BRIGHTNESS_MAX', {}).get('value', '255')),
            help="Maximum brightness during daytime"
        )
        updates['MATRIX_BRIGHTNESS_MAX'] = str(brightness_max)
    
    with col2:
        brightness_min = st.slider(
            "Minimum Brightness (Midnight)",
            min_value=0,
            max_value=255,
            value=int(config.get('MATRIX_BRIGHTNESS_MIN', {}).get('value', '100')),
            help="Minimum brightness during nighttime"
        )
        updates['MATRIX_BRIGHTNESS_MIN'] = str(brightness_min)

# Save button
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("💾 Save Configuration", type="primary", use_container_width=True):
        try:
            with open(ENV_FILE, 'r') as f:
                original_lines = f.readlines()
            
            save_env_file(ENV_FILE, original_lines, updates)
            st.success("✅ Configuration saved successfully!")
            st.info("🔄 Changes will be automatically applied within a few seconds - no restart needed!")
            st.balloons()
        except Exception as e:
            st.error(f"❌ Error saving configuration: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    "**ℹ️ Auto-Reload Enabled:** Configuration changes are automatically detected and applied without restarting the service.\n\n"
    f"Configuration file: `{ENV_FILE}`"
)
