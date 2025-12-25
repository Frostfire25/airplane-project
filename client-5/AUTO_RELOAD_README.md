# 🔄 Auto-Reload Configuration System

## What Changed?

Your airplane tracking system now **automatically reloads configuration changes** from the .env file without needing a restart! 

### New Files Created

1. **[config.py](config.py)** - Dynamic configuration module that:
   - Monitors the .env file for changes
   - Automatically reloads when modifications are detected
   - Provides thread-safe access to configuration values
   - Caches values for performance while staying fresh

2. **[config_editor.py](config_editor.py)** - Streamlit web interface (already created)

3. **[CONFIG_EDITOR.md](CONFIG_EDITOR.md)** - Updated with auto-reload information

### Files Modified

1. **[main.py](main.py)** - Now uses dynamic configuration:
   - All `os.getenv()` calls replaced with `get_config()` functions
   - Configuration values fetched dynamically on each use
   - Location, timing, colors, and connection settings auto-update

2. **[matrix.py](matrix.py)** - Now uses dynamic configuration:
   - Display settings (colors, brightness, animations) reload automatically
   - Hardware configuration updates without restart
   - All settings fetched fresh on each display update

## How It Works

The new `DynamicConfig` class:

```python
from config import get_config, get_latitude, get_longitude

# Get configuration instance
config = get_config()

# Get values - automatically checks if .env was modified
lat = get_latitude()  # Always fresh from .env
lon = get_longitude()  # Always fresh from .env

# Color values automatically parsed
color = config.get_color('MATRIX_COLOR_TIME', (255, 255, 255))
```

### Auto-Reload Mechanism

Every time you access a configuration value:
1. System checks .env file modification time
2. If changed, automatically reloads the entire file
3. Updates all environment variables
4. Returns the fresh value

**No restart needed!** Changes apply within seconds.

## What Gets Auto-Reloaded?

✅ **Location Settings**
- LATITUDE, LONGITUDE
- TIMEZONE

✅ **ADS-B Connection**  
- ADSB_HOST, ADSB_PORT
- ADSB_DATA_TYPE

✅ **Timing & Scheduling**
- ADSB_POLL_SCHEDULE_SECONDS
- MATRIX_SCHEDULE_SECONDS  
- AIRCRAFT_DISPLAY_DURATION
- MATRIX_ANIMATION_DELAY_MS

✅ **Display Hardware**
- MATRIX_WIDTH, MATRIX_HEIGHT
- MATRIX_BIT_DEPTH
- MATRIX_N_ADDR_LINES
- SIMULATE_MATRIX

✅ **Colors & Brightness**
- All MATRIX_COLOR_* settings
- MATRIX_BRIGHTNESS_MAX/MIN
- MATRIX_SCRAMBLE_OPACITY

## Using the Web Editor

1. **Start the config editor:**
   ```bash
   streamlit run config_editor.py --server.port 8501 --server.address 0.0.0.0
   ```

2. **Access from your phone:**
   ```
   http://YOUR_PI_IP:8501
   ```

3. **Make changes and click Save**

4. **Watch them apply automatically!**
   - No restart needed
   - Changes take effect within seconds
   - Airplane tracker keeps running

## Console Feedback

When the system detects configuration changes, you'll see:
```
🔄 Configuration file changed, reloading...
```

At startup, you'll see:
```
Configuration: Auto-reload enabled
💡 Tip: Changes to .env will be auto-detected and applied
```

## Technical Details

### Thread Safety
The `DynamicConfig` class uses threading locks to ensure safe concurrent access from multiple scheduler jobs.

### Performance
- File modification time checked on every access (very fast)
- Full reload only when file actually changes
- No polling or background threads needed

### Backwards Compatibility
Old code that uses `os.getenv()` still works, but won't auto-reload. The new system is opt-in through the `config` module.

## Testing

You can test the auto-reload feature:

```bash
# Start the airplane tracker
python3 main.py

# In another terminal, edit .env
nano .env
# Change MATRIX_BRIGHTNESS_MAX from 255 to 200
# Save and exit

# Watch the console - you'll see:
# 🔄 Configuration file changed, reloading...
# The display brightness will adjust automatically!
```

## Troubleshooting

**Changes not applying?**
- Check console for "Configuration file changed, reloading..." message
- Verify .env file was actually saved
- Check file permissions on .env

**Performance concerns?**
- The file stat check is extremely fast (microseconds)
- Full reload only happens when file actually changes
- No performance impact during normal operation

## Migration Notes

If you have custom code that reads from .env:

**Before:**
```python
SETTING = os.getenv('SETTING', 'default')
```

**After:**
```python
from config import get_config
config = get_config()
setting = config.get('SETTING', 'default')
```

Or use convenience functions:
```python
from config import get_latitude, get_longitude, get_timezone
lat = get_latitude()  # Always fresh
```

## Summary

🎉 **You can now edit your airplane tracker configuration from your phone and see changes apply in real-time - no restart needed!**

The system is smart enough to:
- ✅ Detect .env changes automatically
- ✅ Reload only when necessary  
- ✅ Apply changes to running services
- ✅ Keep your display running smoothly
- ✅ Work safely with multiple concurrent accesses

Enjoy your live-configurable airplane tracker! ✈️
