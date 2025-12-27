#!/bin/bash
# Setup script for client-3-4 (rgbmatrix version)

set -e

echo "=========================================="
echo "ADS-B Tracker Setup - rgbmatrix version"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "WARNING: This script should be run with sudo for full setup"
    echo "Run: sudo bash setup.sh"
    echo ""
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Step 1: Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi
python3 --version
echo "✓ Python 3 found"
echo ""

echo "Step 2: Checking for rgbmatrix library..."
if python3 -c "import rgbmatrix" 2>/dev/null; then
    echo "✓ rgbmatrix library is installed"
else
    echo "✗ rgbmatrix library NOT found"
    echo ""
    echo "The rgbmatrix library must be built from source."
    echo "Installation instructions:"
    echo ""
    echo "  cd ~"
    echo "  curl https://codeload.github.com/hzeller/rpi-rgb-led-matrix/tar.gz/master | tar -xzv"
    echo "  cd rpi-rgb-led-matrix"
    echo "  make build-python HARDWARE_DESC=regular"
    echo "  sudo make install-python"
    echo ""
    echo "For more details, see:"
    echo "https://github.com/hzeller/rpi-rgb-led-matrix/tree/master/bindings/python"
    echo ""
    read -p "Continue with Python package installation anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

echo "Step 3: Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    echo "✓ Python packages installed"
else
    echo "ERROR: requirements.txt not found"
    exit 1
fi
echo ""

echo "Step 4: Setting up configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env from .env.example"
        echo ""
        echo "IMPORTANT: Edit .env with your settings:"
        echo "  - LATITUDE and LONGITUDE"
        echo "  - ADSB_HOST and ADSB_PORT"
        echo "  - TIMEZONE"
        echo ""
        echo "Edit now? (opens nano)"
        read -p "Press Enter to edit, or Ctrl+C to skip..."
        nano .env
    else
        echo "WARNING: .env.example not found, skipping configuration setup"
    fi
else
    echo "✓ .env already exists"
fi
echo ""

echo "Step 5: Checking fonts directory..."
if [ -d "fonts" ]; then
    echo "✓ Fonts directory found"
else
    echo "WARNING: fonts directory not found"
    echo "Matrix display may not work properly without fonts"
fi
echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Test the matrix display:"
echo "   sudo python3 demo.py"
echo ""
echo "2. Test with simulated aircraft data:"
echo "   sudo python3 test_display.py"
echo ""
echo "3. Run the main application:"
echo "   sudo python3 main.py"
echo ""
echo "4. (Optional) Install as a service:"
echo "   sudo cp airplane.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable airplane.service"
echo "   sudo systemctl start airplane.service"
echo ""
echo "Note: sudo is required for rgbmatrix GPIO access"
echo ""
echo "For configuration editing, you can also use:"
echo "   streamlit run config_editor.py"
echo ""
