Piomatter 64x64 Demo
=====================

This folder contains a small demo for driving a 64x64 HUB75 RGB matrix on
Raspberry Pi 5 using Adafruit's Piomatter bindings (Adafruit_Blinka_Raspberry_Pi5_Piomatter).

Prerequisites
-------------
- Raspberry Pi 5 with firmware and kernel supporting PIO (check `/dev/pio0`).
- A HUB75-compatible RGB matrix (64x64). Hardware wiring must match a
  compatible adapter or the pin mapping used by the Piomatter library.
- Python 3.9+ and pip.

Install the library
-------------------
Run on the Pi:

```bash
# Create a virtual environment to avoid externally-managed-environment errors
python3 -m venv .venv
source .venv/bin/activate
pip install Adafruit-Blinka-Raspberry-Pi5-Piomatter
```

System setup
------------
If `/dev/pio0` does not exist, update your Pi 5 firmware and kernel to a
release that includes PIO support. If `/dev/pio0` exists but is owned by
`root:root`, add the following udev rule (requires reboot or `udevadm` reload):

```
SUBSYSTEM=="*-pio", GROUP="gpio", MODE="0660"
```

Usage
-----
Run the demo from this folder on the Pi where PioMatter is installed:

```bash
# Activate the virtual environment
source .venv/bin/activate
# Run with sudo (required for GPIO/PIO access)
sudo .venv/bin/python demo.py
```

Simulation / local testing
--------------------------
If you don't have a Pi 5 or PioMatter installed you can test the logic
(note: simulation mode was removed in the current version as the actual
library is required for the numpy/PIL integration).

Notes
-----
- The PioMatter Python API uses numpy arrays as framebuffers. This demo uses
  PIL (Pillow) to draw graphics, then copies the result to the numpy framebuffer.
- The API: create a `Geometry` instance describing your matrix layout, create a
  numpy framebuffer array, pass both to `PioMatter()` constructor along with
  `Colorspace` and `Pinout` settings, then call `matrix.show()` to update the display.
- For 64x64 matrices, use `n_addr_lines=5` (since 64/2 = 32 = 2^5).
- This demo assumes `AdafruitMatrixBonnet` pinout; if you have different hardware
  or BGR pixel order, change to `Pinout.AdafruitMatrixBonnetBGR` or other values.

License
-------
This demo is supplementary to the Adafruit Piomatter project and does not
change the license of that project. Ensure you follow the upstream license
terms when redistributing.
