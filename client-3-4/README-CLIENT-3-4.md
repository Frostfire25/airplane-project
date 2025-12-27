# ADS-B Aircraft Tracker - Client 3-4 (rgbmatrix version)

This project is adapted from the client-5 version to use the `rgbmatrix` library instead of `adafruit_blinka_raspberry_pi5_piomatter`. This version is compatible with standard Raspberry Pi models (not just Pi 5) using the hzeller rpi-rgb-led-matrix library.

## Key Differences from client-5

### Matrix Library
- **client-5**: Uses `Adafruit_Blinka_Raspberry_Pi5_Piomatter` (PioMatter) - Raspberry Pi 5 specific
- **client-3-4**: Uses `rgbmatrix` from hzeller/rpi-rgb-led-matrix - Compatible with Pi 3, 4, and 5

### Display Implementation
- **client-5**: Uses PIL (Pillow) for drawing, numpy arrays for framebuffers
- **client-3-4**: Uses rgbmatrix's native graphics functions for drawing
- **client-5**: Includes Vestaboard-style character animation
- **client-3-4**: Simplified, immediate display (animations removed for performance)

## Hardware Requirements

- Raspberry Pi (3, 4, or 5)
- HUB75 RGB LED Matrix (64x64 recommended)
- Matrix HAT or bonnet (e.g., Adafruit RGB Matrix HAT, Waveshare RGB Matrix HAT)
- Power supply (5V, 4A+ recommended for 64x64 matrix)

## Software Installation

### 1. Install rgbmatrix Library

The rgbmatrix library must be built from source:

```bash
cd ~
curl https://codeload.github.com/hzeller/rpi-rgb-led-matrix/tar.gz/master | tar -xzv
cd rpi-rgb-led-matrix

# Build the library
make build-python HARDWARE_DESC=regular
sudo make install-python
```

For detailed installation instructions, see:
https://github.com/hzeller/rpi-rgb-led-matrix/tree/master/bindings/python

### 2. Install Python Dependencies

```bash
cd /home/admin/airplane-project/client-3-4
pip install -r requirements.txt
```

Note: The `rgbmatrix` library is not in PyPI and must be installed separately (see step 1).

### 3. Configure Environment

Copy and edit the environment configuration:

```bash
cp .env.example .env
nano .env
```

Key settings to configure:
- `LATITUDE` and `LONGITUDE`: Your location
- `ADSB_HOST` and `ADSB_PORT`: Your ADS-B receiver (dump1090, etc.)
- `MATRIX_WIDTH` and `MATRIX_HEIGHT`: Your matrix dimensions
- `MATRIX_BRIGHTNESS`: Display brightness (0-100)
- `TIMEZONE`: Your local timezone

### 4. Test the Display

Run the demo to verify matrix functionality:

```bash
# With hardware
sudo python3 demo.py

# Simulation mode (no hardware)
SIMULATE_MATRIX=1 python3 demo.py
```

Run the full display test:

```bash
sudo python3 test_display.py
```

### 5. Run the Main Application

```bash
sudo python3 main.py
```

Note: sudo is typically required for rgbmatrix to access GPIO pins.

## Running as a Service

Install as a systemd service for automatic startup:

```bash
# Copy service file
sudo cp airplane.service /etc/systemd/system/

# Edit paths if needed
sudo nano /etc/systemd/system/airplane.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable airplane.service
sudo systemctl start airplane.service

# Check status
sudo systemctl status airplane.service

# View logs
sudo journalctl -u airplane.service -f
```

## Configuration Editor

The project includes a Streamlit-based configuration editor:

```bash
streamlit run config_editor.py
```

This provides a web interface for editing the `.env` file without manual editing.

## Features

- Real-time ADS-B aircraft tracking
- LED matrix display showing:
  - Current time
  - Nearest aircraft callsign
  - Flight route (origin → destination)
  - Distance from your location
  - Altitude and speed
- Dynamic brightness based on time of day
- FlightAware integration for route information
- Configurable colors and display settings
- Simulation mode for testing without hardware

## File Structure

```
client-3-4/
├── main.py                 # Main application entry point
├── matrix.py               # LED matrix display (rgbmatrix version)
├── adsbfeeder.py          # ADS-B message decoder
├── flightaware.py         # FlightAware web scraper
├── config.py              # Dynamic configuration loader
├── config_editor.py       # Web-based config editor
├── demo.py                # Hardware test demo
├── test_display.py        # Display test with simulated data
├── requirements.txt       # Python dependencies
├── .env.example           # Environment configuration template
├── airplane.service       # Systemd service file
└── fonts/                 # BDF fonts for matrix display
```

## Troubleshooting

### Matrix doesn't display anything
- Check power supply (matrices need significant power)
- Verify GPIO connections
- Try running with sudo
- Check matrix dimensions in `.env` match your hardware
- Test with demo.py first

### Permission errors
- rgbmatrix requires root access for GPIO
- Always run with `sudo python3 main.py`

### Module not found: rgbmatrix
- Install from source (see step 1 above)
- Cannot be installed via pip

### No aircraft showing
- Verify ADS-B receiver is running (dump1090, readsb, etc.)
- Check ADSB_HOST and ADSB_PORT in `.env`
- Confirm aircraft are in range
- Test with `nc ADSB_HOST ADSB_PORT` to see raw data

### Display is too bright/dim
- Adjust MATRIX_BRIGHTNESS in `.env` (0-100)
- Adjust MATRIX_BRIGHTNESS_MIN and MATRIX_BRIGHTNESS_MAX for time-based dimming

## Performance Notes

The rgbmatrix version is more efficient than the PIL-based client-5 version:
- Lower CPU usage
- Faster rendering
- No numpy/PIL overhead
- Direct hardware control

However, it lacks the fancy animations from client-5 (character-by-character reveals).

## Credits

- Original project: client-5 (adafruit_blinka version)
- Adapted for: rgbmatrix library by hzeller
- ADS-B decoding: pyModeS library
- Matrix library: https://github.com/hzeller/rpi-rgb-led-matrix

## License

See individual library licenses. This adaptation maintains compatibility with all original licenses.
