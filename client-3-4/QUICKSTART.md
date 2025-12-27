# Quick Start Guide - Client-3-4

Get up and running with the ADS-B Aircraft Tracker in minutes!

## Prerequisites

- Raspberry Pi (3, 4, or 5) running Raspberry Pi OS
- HUB75 RGB LED Matrix (64x64 recommended)
- Matrix HAT/bonnet properly connected
- ADS-B receiver running (dump1090, readsb, etc.)
- Internet connection (for FlightAware route lookups)

## Installation (5 minutes)

### 1. Run the Setup Script

```bash
cd /home/admin/airplane-project/client-3-4
sudo bash setup.sh
```

This script will:
- Check Python installation
- Check for rgbmatrix library
- Install Python dependencies
- Set up configuration file

**Note:** If rgbmatrix is not found, the script will show installation instructions. Follow them before continuing.

### 2. Configure Your Settings

Edit the `.env` file with your specific settings:

```bash
nano .env
```

**Must change:**
- `LATITUDE=` (your latitude)
- `LONGITUDE=` (your longitude)
- `ADSB_HOST=` (your ADS-B receiver IP, usually 127.0.0.1)
- `TIMEZONE=` (e.g., America/New_York)

**Optional (defaults are usually fine):**
- `MATRIX_WIDTH=64`
- `MATRIX_HEIGHT=64`
- `MATRIX_BRIGHTNESS=50`
- Color settings (if you want custom colors)

### 3. Test the Display

```bash
sudo python3 demo.py
```

You should see:
- A border around the matrix
- Animated colorful text saying "RGB TEST"
- A moving dot
- Frame counter

Press Ctrl+C to exit.

### 4. Test with Simulated Aircraft Data

```bash
sudo python3 test_display.py
```

This will show fake aircraft data cycling on your display. Verify:
- Time displays correctly
- Callsigns appear
- Distance shows
- Route information displays (if available)

Press Ctrl+C to exit.

### 5. Run the Main Application

```bash
sudo python3 main.py
```

The system will:
- Connect to your ADS-B receiver
- Find the nearest aircraft
- Display it on the matrix
- Update every few seconds
- Look up route info from FlightAware

Press Ctrl+C to exit.

## Install as System Service (Optional)

To run automatically on boot:

```bash
# Copy service file
sudo cp airplane.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable airplane.service
sudo systemctl start airplane.service

# Check status
sudo systemctl status airplane.service

# View logs
sudo journalctl -u airplane.service -f
```

## Troubleshooting

### "No module named 'rgbmatrix'"

Install the rgbmatrix library from source:

```bash
cd ~
curl https://codeload.github.com/hzeller/rpi-rgb-led-matrix/tar.gz/master | tar -xzv
cd rpi-rgb-led-matrix
make build-python HARDWARE_DESC=regular
sudo make install-python
```

### "Permission denied" or GPIO errors

Always run with sudo:

```bash
sudo python3 main.py
```

### Matrix shows nothing

1. Check power supply (matrices need 4-5A)
2. Verify connections (GPIO pins, HUB75 cable)
3. Check matrix dimensions in `.env` match your hardware
4. Try `demo.py` first to isolate issues

### No aircraft showing

1. Verify ADS-B receiver is running:
   ```bash
   nc 127.0.0.1 30005
   ```
   You should see hex messages streaming.

2. Check `ADSB_HOST` and `ADSB_PORT` in `.env`

3. Ensure aircraft are in range (30-200 miles typical)

4. Check logs for connection errors

### Display too bright/dim

Adjust in `.env`:
```
MATRIX_BRIGHTNESS=50  # 0-100
```

Or for time-based auto-dimming:
```
MATRIX_BRIGHTNESS_MIN=50   # Midnight brightness
MATRIX_BRIGHTNESS_MAX=255  # Noon brightness
```

### Wrong timezone

Set in `.env`:
```
TIMEZONE=America/New_York
```

Find your timezone:
```bash
timedatectl list-timezones | grep <your_location>
```

## Running Without Hardware (Simulation Mode)

Test the software without a matrix connected:

```bash
SIMULATE_MATRIX=1 python3 demo.py
SIMULATE_MATRIX=1 python3 test_display.py
SIMULATE_MATRIX=1 python3 main.py
```

Output will print to console instead of the matrix.

## Configuration Web Interface

For easy configuration editing:

```bash
streamlit run config_editor.py
```

Then open your web browser to the URL shown (typically http://localhost:8501).

## Daily Operation

Once set up as a service, the tracker runs automatically:

- Updates every few seconds
- Brightness adjusts with time of day
- Configuration reloads automatically when `.env` changes
- Logs to systemd journal

View logs:
```bash
sudo journalctl -u airplane.service -f
```

Stop/start:
```bash
sudo systemctl stop airplane.service
sudo systemctl start airplane.service
```

## Performance Tips

- Default settings are optimized for Raspberry Pi 4
- On Pi 3, reduce `MATRIX_SCHEDULE_SECONDS` if needed
- Lower `MATRIX_BRIGHTNESS` for less power consumption
- Disable route lookups if network is slow (set `ENABLE_ROUTE_LOOKUP=false`)

## Next Steps

- Customize colors in `.env`
- Adjust update intervals
- Add multiple matrix panels (chain them)
- Integrate with flight tracking networks
- Build a custom enclosure

## Getting Help

Check the documentation:
- [README-CLIENT-3-4.md](README-CLIENT-3-4.md) - Full documentation
- [COMPARISON.md](COMPARISON.md) - Compare with client-5
- [CONFIG_EDITOR.md](CONFIG_EDITOR.md) - Configuration guide

Common resources:
- rgbmatrix library: https://github.com/hzeller/rpi-rgb-led-matrix
- pyModeS: https://github.com/junzis/pyModeS
- ADS-B Exchange: https://www.adsbexchange.com/

## Success!

If you see aircraft data on your matrix, congratulations! 🎉

Your system is tracking aircraft in real-time and displaying them on your LED matrix.

Enjoy your ADS-B tracker!
