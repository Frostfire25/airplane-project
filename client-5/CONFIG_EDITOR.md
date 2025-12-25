# 📱 Web Configuration Editor

Edit your airplane tracker settings from your phone or any device on your network.

## 🚀 Quick Start

### 1. Install Streamlit (if not already installed)
```bash
cd /home/admin/airplane-project/client-5
pip install streamlit
```

### 2. Start the Configuration Editor
```bash
streamlit run config_editor.py --server.port 8501 --server.address 0.0.0.0
```

### 3. Access from Your Phone
Open your phone's web browser and navigate to:
```
http://YOUR_RASPBERRY_PI_IP:8501
```

Replace `YOUR_RASPBERRY_PI_IP` with your Raspberry Pi's IP address.

**To find your Raspberry Pi's IP:**
```bash
hostname -I
```

## 📋 Features

- **📍 Location Settings** - Configure your coordinates and timezone
- **📡 Data Source** - Set up ADS-B receiver connection
- **⏱️ Scheduling** - Control update intervals and display timing
- **🖥️ Display Hardware** - Configure LED matrix parameters
- **🎨 Colors & Brightness** - Customize colors with visual color pickers

## 🔒 Security Notes

- The web interface is accessible to anyone on your network
- Consider using a firewall or changing the port if security is a concern
- The app directly modifies the `.env` file

## 🔄 Applying Changes

**Good news!** Changes are now automatically applied - no restart needed!

When you save changes through the web interface, the airplane tracker automatically detects the .env file modification and reloads the configuration within seconds. You'll see updated colors, timing, and other settings applied live.

**What gets auto-reloaded:**
- ✅ All color settings
- ✅ Brightness levels  
- ✅ Timing intervals (polling, display updates, rotation)
- ✅ Display dimensions and hardware settings
- ✅ Location and timezone
- ✅ ADS-B connection settings

The auto-reload happens every time a configuration value is accessed, so changes take effect immediately without interrupting your airplane tracking.

## 🛠️ Run at Startup (Optional)

To automatically start the config editor when the Pi boots:

### Create a systemd service:
```bash
sudo nano /etc/systemd/system/airplane-config.service
```

### Add this content:
```ini
[Unit]
Description=Airplane Tracker Configuration Web Interface
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/airplane-project/client-5
ExecStart=/usr/bin/streamlit run config_editor.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and start:
```bash
sudo systemctl enable airplane-config.service
sudo systemctl start airplane-config.service
```

### Check status:
```bash
sudo systemctl status airplane-config.service
```

## 📱 Bookmark on Your Phone

For easy access, bookmark the page on your phone's home screen:

- **iOS Safari**: Tap Share → Add to Home Screen
- **Android Chrome**: Tap Menu (⋮) → Add to Home screen

## 🔍 Troubleshooting

### Can't access from phone?
- Make sure your phone and Raspberry Pi are on the same network
- Check firewall settings on the Raspberry Pi
- Verify the Pi's IP address hasn't changed

### Port already in use?
Change the port number:
```bash
streamlit run config_editor.py --server.port 8502 --server.address 0.0.0.0
```

### Changes not taking effect?
- Make sure to click "Save Configuration" button
- Restart the airplane tracker service
- Check that the `.env` file was actually modified

## 💡 Tips

- **Dark Mode**: Streamlit automatically adapts to your phone's dark/light mode
- **Color Picker**: Tap the color boxes to select colors visually
- **Responsive**: Works on phones, tablets, and computers
- **Real-time**: Changes are saved immediately when you click Save

## 🌐 Advanced: Access from Anywhere (Port Forwarding)

⚠️ **Security Warning**: Only do this if you understand the security implications.

To access from outside your home network:
1. Set up port forwarding on your router (port 8501 → Pi's IP:8501)
2. Use Dynamic DNS if your ISP changes your IP
3. Consider adding authentication (not built into this app)
