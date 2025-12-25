# ADS-B Aircraft Tracking Display for Raspberry Pi 5

A real-time aircraft tracking system that displays nearby aircraft information on a 64x64 RGB LED matrix using ADS-B data. The system decodes aircraft transponder signals, enriches the data with flight route information from FlightAware, and displays the nearest aircraft with distance, altitude, speed, and destination information.

## Features

- **Real-time ADS-B Data Processing**: Decodes Mode-S/ADS-B messages using pyModeS
- **LED Matrix Display**: Shows aircraft information on HUB75 RGB LED panels
- **FlightAware Integration**: Scrapes origin/destination airport information
- **Automatic Brightness**: Adjusts display brightness based on time of day
- **Distance Calculation**: Shows distance to nearest aircraft from your location
- **Systemd Service**: Runs automatically on boot as a background service
- **Multiple Aircraft Tracking**: Rotates through nearby aircraft display

## Hardware Requirements

- **Raspberry Pi 5** (4GB or 8GB recommended)
- **HUB75 RGB LED Matrix Panel** (64x64 pixels)
- **ADS-B Receiver** (RTL-SDR dongle or similar)
- **Power Supply**: 5V power supply adequate for Pi 5 and LED matrix
- **Antenna**: 1090 MHz antenna for ADS-B reception

## Software Prerequisites

### 1. Raspberry Pi OS Setup

Install Raspberry Pi OS (64-bit recommended) on your Raspberry Pi 5:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential build tools and dependencies
sudo apt install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    cmake \
    libusb-1.0-0-dev \
    pkg-config \
    librtlsdr-dev \
    rtl-sdr
```

### 2. Install readsb (ADS-B Decoder)

readsb is a Mode-S/ADS-B decoder that processes signals from your RTL-SDR receiver:

```bash
# Install dependencies
sudo apt install -y \
    libncurses-dev \
    zlib1g-dev \
    libzstd-dev

# Clone and build readsb
cd /tmp
git clone https://github.com/wiedehopf/readsb.git
cd readsb
make RTLSDR=yes
sudo make install

# Create readsb service
sudo useradd --system --no-create-home readsb || true

# Create readsb systemd service
sudo tee /etc/systemd/system/readsb.service > /dev/null <<'EOF'
[Unit]
Description=readsb ADS-B decoder
After=network.target

[Service]
User=readsb
RuntimeDirectory=readsb
RuntimeDirectoryMode=0755
ExecStart=/usr/local/bin/readsb \
    --net \
    --net-bi-port 30004,30104 \
    --net-bo-port 30005 \
    --net-sbs-port 30003 \
    --device-type rtlsdr \
    --gain -10 \
    --fix \
    --write-json /run/readsb \
    --quiet
Type=simple
Restart=on-failure
RestartSec=30
Nice=-5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start readsb
sudo systemctl daemon-reload
sudo systemctl enable readsb
sudo systemctl start readsb

# Check status
sudo systemctl status readsb
```

**View readsb web interface**: After installation, readsb provides a web interface at `http://<raspberry-pi-ip>/tar1090/`

### 3. Install FL24 (FlightRadar24 Feeder) - Optional

If you want to contribute data to FlightRadar24:

```bash
# Download and install FR24 feeder
cd /tmp
wget https://repo.feed.flightradar24.com/rpi_binaries/fr24feed_1.0.48-0_armhf.tgz
tar -xzf fr24feed_1.0.48-0_armhf.tgz
cd fr24feed_armhf-1.0.48-0
sudo ./install_fr24feed.sh

# Configure FR24 feeder (follow the interactive setup)
sudo fr24feed --signup

# Start the service
sudo systemctl start fr24feed
sudo systemctl enable fr24feed
```

**View FR24 local page**: `http://localhost:8754/index.html`

## Installation

### 1. Clone the Repository

```bash
cd /home/admin
git clone <your-repo-url> airplane-project
cd airplane-project/client-5
```

### 2. Create Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Adafruit_Blinka_Raspberry_Pi5_Piomatter

The project includes a custom version of the Adafruit library for Raspberry Pi 5:

```bash
# Install the custom library from the included directory
cd Adafruit_Blinka_Raspberry_Pi5_Piomatter
pip install -e .
cd ..
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy the example environment file and customize it:

```bash
cp .env.example .env
nano .env
```

**Required Configuration**:

```bash
# Your GPS coordinates (required for distance calculations)
LATITUDE=40.7128
LONGITUDE=-74.0060

# Timezone (important for display)
TIMEZONE=America/New_York
TZ=America/New_York

# ADS-B data source (readsb connection)
ADSB_HOST=127.0.0.1
ADSB_PORT=30005
ADSB_DATA_TYPE=beast

# Matrix hardware settings
MATRIX_WIDTH=64
MATRIX_HEIGHT=64
MATRIX_BIT_DEPTH=6
MATRIX_N_ADDR_LINES=5

# Simulation mode (1 = test without hardware, 0 = use real matrix)
SIMULATE_MATRIX=0

# Update intervals (seconds)
ADSB_POLL_SCHEDULE_SECONDS=5
MATRIX_SCHEDULE_SECONDS=60
AIRCRAFT_DISPLAY_DURATION=10
```

**Get Your Coordinates**: You can find your latitude/longitude using [Google Maps](https://maps.google.com) (right-click > "What's here?").

### 6. Test the Display

Test without matrix hardware (simulation mode):

```bash
# Set simulation mode
export SIMULATE_MATRIX=1

# Run the application
python main.py
```

Test with matrix hardware:

```bash
# Test display modes
sudo ./.venv/bin/python test_display.py cycle

# Run main application
sudo ./.venv/bin/python main.py
```

**Note**: Matrix display requires root/sudo access for GPIO control on Raspberry Pi 5.

## Systemd Service Setup

To run the aircraft tracker automatically on boot:

### 1. Install the Service

```bash
# Copy service file to systemd directory
sudo cp airplane.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload
```

### 2. Enable and Start the Service

```bash
# Enable the service to start on boot
sudo systemctl enable airplane.service

# Start the service immediately
sudo systemctl start airplane.service

# Check service status
sudo systemctl status airplane.service
```

### 3. Service Management Commands

```bash
# Stop the service
sudo systemctl stop airplane.service

# Restart the service
sudo systemctl restart airplane.service

# View service logs (live)
sudo journalctl -u airplane.service -f

# View recent logs
sudo journalctl -u airplane.service -n 50
```

### 4. Troubleshooting Service Issues

If the service fails to start:

```bash
# Check detailed service status
sudo systemctl status airplane.service -l

# Check for permission issues
sudo journalctl -u airplane.service --since "5 minutes ago"

# Verify the service file
sudo systemctl cat airplane.service

# Test manually with the same environment
cd /home/admin/airplane-project/client-5
sudo -u admin /home/admin/airplane-project/client-5/.venv/bin/python main.py
```

## Usage

### Manual Operation

```bash
# Activate virtual environment
cd /home/admin/airplane-project/client-5
source .venv/bin/activate

# Run with sudo (required for GPIO/matrix access)
sudo ./.venv/bin/python main.py
```

### Display Modes Testing

```bash
# Test different display modes
sudo ./.venv/bin/python test_display.py cycle
sudo ./.venv/bin/python test_display.py time
sudo ./.venv/bin/python test_display.py aircraft
sudo ./.venv/bin/python test_display.py no_aircraft
```

## Troubleshooting

### Matrix Display Issues

#### Problem: "RuntimeError: Failed to allocate memory"

**Solution**: Ensure you're running with sudo and the virtual environment Python:

```bash
sudo ./.venv/bin/python main.py
# NOT just: sudo python main.py
```

#### Problem: Matrix display shows nothing or garbled output

**Checklist**:
1. Verify GPIO connections are correct for HUB75
2. Check power supply is adequate (3-5A for 64x64 matrix)
3. Verify matrix configuration in `.env` matches your hardware:
   ```bash
   MATRIX_WIDTH=64
   MATRIX_HEIGHT=64
   MATRIX_N_ADDR_LINES=5  # Check your panel specs
   ```
4. Test in simulation mode first: `SIMULATE_MATRIX=1`

#### Problem: "Matrix hardware libraries not available"

**Solution**: Reinstall the Adafruit library:

```bash
cd Adafruit_Blinka_Raspberry_Pi5_Piomatter
pip install --force-reinstall -e .
```

### ADS-B Data Issues

#### Problem: No aircraft data showing

**Checklist**:
1. Verify readsb is running:
   ```bash
   sudo systemctl status readsb
   ```

2. Check if readsb is receiving data:
   ```bash
   # Connect to Beast output port
   nc localhost 30005 | hexdump -C
   # Should see data streaming (Ctrl+C to exit)
   ```

3. Check antenna connection and placement (needs clear view of sky)

4. Verify correct port in `.env`:
   ```bash
   ADSB_PORT=30005  # Beast binary format
   ```

#### Problem: "Connection refused" to readsb

**Solution**:
1. Check readsb is listening on correct ports:
   ```bash
   sudo netstat -tlnp | grep readsb
   ```

2. Verify firewall isn't blocking:
   ```bash
   sudo ufw status
   ```

3. Check readsb configuration includes network output:
   ```bash
   ps aux | grep readsb
   # Should see --net-bo-port 30005
   ```

### RTL-SDR Issues

#### Problem: "usb_claim_interface error -6"

**Solution**: RTL-SDR device is already in use by another program.

```bash
# Find processes using the RTL-SDR
sudo lsof /dev/bus/usb/*/0*

# Kill conflicting processes
sudo killall rtl_tcp dump1090

# Restart readsb
sudo systemctl restart readsb
```

#### Problem: No RTL-SDR device found

**Checklist**:
1. Check device is connected:
   ```bash
   lsusb | grep RTL
   ```

2. Install RTL-SDR udev rules:
   ```bash
   sudo wget -O /etc/udev/rules.d/rtl-sdr.rules https://raw.githubusercontent.com/osmocom/rtl-sdr/master/rtl-sdr.rules
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

3. Test RTL-SDR directly:
   ```bash
   rtl_test
   ```

### Python Environment Issues

#### Problem: Import errors or missing modules

**Solution**: Ensure you're using the virtual environment:

```bash
# Check Python path
which python
# Should show: /home/admin/airplane-project/client-5/.venv/bin/python

# If not, activate venv
source .venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt
```

#### Problem: Permission denied errors in service

**Solution**: Check service is running as correct user:

```bash
# Service should run as 'admin' user (see airplane.service)
sudo systemctl cat airplane.service | grep User=
# Should show: User=admin

# Check file ownership
ls -la /home/admin/airplane-project/client-5/
# Files should be owned by admin:admin
```

### FlightAware Scraping Issues

#### Problem: No route information showing

This is normal - FlightAware scraping is best-effort:
- Some aircraft don't have callsigns in the ADS-B data
- Private/military aircraft may not appear on FlightAware
- Rate limiting may occur with heavy traffic
- The scraper uses caching to minimize requests

No action needed - aircraft will still display with available data.

### Performance Issues

#### Problem: High CPU usage

**Solutions**:
1. Increase polling intervals in `.env`:
   ```bash
   ADSB_POLL_SCHEDULE_SECONDS=10  # Reduce polling frequency
   MATRIX_SCHEDULE_SECONDS=120     # Update display less often
   ```

2. Check for multiple instances running:
   ```bash
   ps aux | grep python | grep main.py
   ```

3. Monitor system resources:
   ```bash
   htop
   ```

### Timezone Issues

#### Problem: Time showing incorrectly on display

**Solution**: Set correct timezone in `.env`:

```bash
# Set your timezone
TIMEZONE=America/New_York
TZ=America/New_York

# Available timezones:
timedatectl list-timezones

# Also set system timezone
sudo timedatectl set-timezone America/New_York
```

## Web Interfaces

After installation, you can access:

- **readsb/tar1090**: `http://<raspberry-pi-ip>/tar1090/` (`http://10.0.0.5/tar1090/`) - Live aircraft map
- **FR24 Status**: `http://localhost:8754/index.html` - FlightRadar24 feeder stats (if installed)

## Project Structure

```
client-5/
├── main.py                     # Main application entry point
├── adsbfeeder.py              # ADS-B message decoder (pyModeS)
├── matrix.py                  # LED matrix display controller
├── flightaware.py             # FlightAware web scraper
├── airplane.service           # Systemd service file
├── requirements.txt           # Python dependencies
├── .env                       # Configuration (create from .env.example)
├── .env.example              # Example configuration
└── Adafruit_Blinka_Raspberry_Pi5_Piomatter/  # Custom matrix library
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LATITUDE` | 0.0 | Your location latitude |
| `LONGITUDE` | 0.0 | Your location longitude |
| `TIMEZONE` | America/New_York | Display timezone |
| `ADSB_HOST` | 127.0.0.1 | readsb server host |
| `ADSB_PORT` | 30005 | readsb Beast output port |
| `ADSB_DATA_TYPE` | beast | Data format (raw/beast/avr) |
| `ADSB_POLL_SCHEDULE_SECONDS` | 5 | How often to poll ADS-B data |
| `MATRIX_SCHEDULE_SECONDS` | 60 | Display update interval |
| `AIRCRAFT_DISPLAY_DURATION` | 10 | Seconds per aircraft rotation |
| `MATRIX_WIDTH` | 64 | LED matrix width |
| `MATRIX_HEIGHT` | 64 | LED matrix height |
| `MATRIX_BIT_DEPTH` | 6 | Color bit depth |
| `SIMULATE_MATRIX` | 0 | 1=simulation, 0=real hardware |

### Display Colors

Customize colors in `.env` (R,G,B format):

```bash
MATRIX_COLOR_TIME=255,255,0          # Yellow
MATRIX_COLOR_CALLSIGN=0,255,255      # Cyan
MATRIX_COLOR_DISTANCE=255,165,0      # Orange
MATRIX_COLOR_ALTITUDE=0,255,0        # Green
MATRIX_COLOR_SPEED=255,100,255       # Pink
MATRIX_COLOR_NO_AIRCRAFT=255,0,0     # Red
```

## Contributing

Contributions are welcome! Areas for improvement:
- Additional data sources (OpenSky Network, ADS-B Exchange)
- More display modes and animations
- Weather information integration
- Historical flight tracking
- Mobile app companion

## License

This project is provided as-is for educational and hobbyist purposes.

## Acknowledgments

- **readsb** by wiedehopf - ADS-B decoder
- **pyModeS** - Python Mode-S/ADS-B decoder library
- **Adafruit** - LED matrix libraries
- **FlightAware** - Flight route data source
- **RTL-SDR** community - Software defined radio tools

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs: `sudo journalctl -u airplane.service -f`
3. Test in simulation mode to isolate hardware issues
4. Verify readsb is receiving data: `nc localhost 30005 | hexdump -C`

## Quick Links

- [Flight Aware Local Page](http://localhost:8754/index.html)
- [ReadSb Local Page](http://10.0.0.5/tar1090/)
- [ReadSb Github](https://github.com/wiedehopf/readsb)
- [pyModeS Documentation](https://pymodes.readthedocs.io/)
- [FlightAware](https://www.flightaware.com)
- [RTL-SDR Setup Guide](https://www.rtl-sdr.com/rtl-sdr-quick-start-guide/)