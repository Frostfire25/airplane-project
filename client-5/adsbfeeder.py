"""
ADS-B Data Feeder Utility Module
Provides functions to decode and process ADS-B messages using pyModeS library.
"""

import pyModeS as pms
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)


class ADSBDecoder:
    """Decoder for ADS-B messages with caching and position tracking."""
    
    def __init__(self):
        """Initialize the ADS-B decoder with position tracking."""
        self.position_cache = {}  # Store odd/even messages for position decoding
        self.aircraft_data = {}   # Store decoded aircraft information
        
    def decode_message(self, msg: str, timestamp: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Decode a single ADS-B message and return structured data.
        
        Args:
            msg: Hexadecimal Mode-S/ADS-B message string
            timestamp: Optional timestamp of message reception
            
        Returns:
            Dictionary with decoded data or None if invalid message
        """
        if not msg or len(msg) not in [14, 28]:
            logger.debug(f"Invalid message length: {len(msg) if msg else 0}")
            return None
            
        # Verify CRC
        if pms.crc(msg, encode=False) != 0:
            logger.debug("CRC check failed")
            return None
            
        df = pms.df(msg)
        result = {
            'timestamp': timestamp or datetime.utcnow().timestamp(),
            'raw_message': msg,
            'downlink_format': df,
        }
        
        # Handle different downlink formats
        if df == 17 or df == 18:  # ADS-B messages
            result.update(self._decode_adsb(msg))
        elif df in [4, 20]:  # Altitude replies
            result.update(self._decode_altitude(msg))
        elif df in [5, 21]:  # Identity replies
            result.update(self._decode_identity(msg))
        else:
            logger.debug(f"Unsupported downlink format: {df}")
            return None
            
        return result
    
    def _decode_adsb(self, msg: str) -> Dict[str, Any]:
        """Decode ADS-B (DF17/18) messages."""
        result = {}
        
        # Get ICAO address
        icao = pms.adsb.icao(msg)
        result['icao'] = icao
        
        # Get typecode
        tc = pms.adsb.typecode(msg)
        result['typecode'] = tc
        
        # Decode based on typecode
        if 1 <= tc <= 4:  # Aircraft identification
            result['callsign'] = pms.adsb.callsign(msg)
            result['category'] = pms.adsb.category(msg)
            
        elif 5 <= tc <= 8:  # Surface position
            result['message_type'] = 'surface_position'
            self._decode_position(msg, icao, result, is_surface=True)
            
        elif 9 <= tc <= 18:  # Airborne position (barometric altitude)
            result['message_type'] = 'airborne_position'
            result['altitude'] = pms.adsb.altitude(msg)
            self._decode_position(msg, icao, result, is_surface=False)
            
        elif tc == 19:  # Airborne velocity
            result['message_type'] = 'velocity'
            velocity_data = pms.adsb.velocity(msg)
            if velocity_data:
                result['groundspeed'] = velocity_data[0]  # knots
                result['track'] = velocity_data[1]  # degrees
                result['vertical_rate'] = velocity_data[2]  # ft/min
                result['speed_type'] = velocity_data[3]  # GS or TAS
                
        elif 20 <= tc <= 22:  # Airborne position (GNSS altitude)
            result['message_type'] = 'airborne_position_gnss'
            result['altitude'] = pms.adsb.altitude(msg)
            self._decode_position(msg, icao, result, is_surface=False)
            
        return result
    
    def _decode_position(self, msg: str, icao: str, result: Dict[str, Any], is_surface: bool = False):
        """
        Decode position from ADS-B message.
        Requires both odd and even messages for CPR decoding.
        """
        # Determine if this is odd or even frame
        oe_flag = pms.adsb.oe_flag(msg)
        
        # Store message in cache
        if icao not in self.position_cache:
            self.position_cache[icao] = {'even': None, 'odd': None, 'even_time': None, 'odd_time': None}
        
        timestamp = result['timestamp']
        if oe_flag == 0:  # Even
            self.position_cache[icao]['even'] = msg
            self.position_cache[icao]['even_time'] = timestamp
        else:  # Odd
            self.position_cache[icao]['odd'] = msg
            self.position_cache[icao]['odd_time'] = timestamp
        
        # Try to decode position if we have both messages
        cache = self.position_cache[icao]
        if cache['even'] and cache['odd']:
            try:
                if is_surface:
                    # Surface position requires reference position
                    # Would need to be provided by caller
                    result['position_available'] = False
                    result['needs_reference'] = True
                else:
                    # Airborne position
                    position = pms.adsb.airborne_position(
                        cache['even'], 
                        cache['odd'],
                        cache['even_time'],
                        cache['odd_time']
                    )
                    if position:
                        result['latitude'] = position[0]
                        result['longitude'] = position[1]
                        result['position_available'] = True
            except Exception as e:
                logger.error(f"Position decode error for {icao}: {e}")
                result['position_available'] = False
    
    def _decode_altitude(self, msg: str) -> Dict[str, Any]:
        """Decode altitude from DF4/DF20 messages."""
        result = {}
        try:
            icao = pms.icao(msg)
            result['icao'] = icao
            altitude = pms.common.altcode(msg)
            if altitude:
                result['altitude'] = altitude
        except Exception as e:
            logger.error(f"Altitude decode error: {e}")
        return result
    
    def _decode_identity(self, msg: str) -> Dict[str, Any]:
        """Decode identity (squawk) from DF5/DF21 messages."""
        result = {}
        try:
            icao = pms.icao(msg)
            result['icao'] = icao
            squawk = pms.common.idcode(msg)
            if squawk:
                result['squawk'] = squawk
        except Exception as e:
            logger.error(f"Identity decode error: {e}")
        return result
    
    def decode_position_with_reference(self, msg: str, lat_ref: float, lon_ref: float) -> Optional[Tuple[float, float]]:
        """
        Decode position from a single message using a reference position.
        Useful when you have a known nearby location.
        
        Args:
            msg: ADS-B message
            lat_ref: Reference latitude
            lon_ref: Reference longitude
            
        Returns:
            Tuple of (latitude, longitude) or None
        """
        try:
            return pms.adsb.position_with_ref(msg, lat_ref, lon_ref)
        except Exception as e:
            logger.error(f"Position with reference decode error: {e}")
            return None
    
    def get_aircraft_info(self, icao: str) -> Optional[Dict[str, Any]]:
        """Get stored information for a specific aircraft by ICAO address."""
        return self.aircraft_data.get(icao)
    
    def update_aircraft_data(self, icao: str, data: Dict[str, Any]):
        """Update stored aircraft data."""
        if icao not in self.aircraft_data:
            self.aircraft_data[icao] = {}
        self.aircraft_data[icao].update(data)
        self.aircraft_data[icao]['last_update'] = datetime.utcnow().timestamp()


# Utility functions for quick decoding

def decode_icao(msg: str) -> Optional[str]:
    """
    Extract ICAO address from any Mode-S message.
    
    Args:
        msg: Hexadecimal Mode-S message
        
    Returns:
        ICAO address as hex string or None
    """
    try:
        return pms.icao(msg)
    except Exception:
        return None


def decode_callsign(msg: str) -> Optional[str]:
    """
    Extract aircraft callsign from ADS-B message.
    
    Args:
        msg: ADS-B message (TC 1-4)
        
    Returns:
        Callsign string or None
    """
    try:
        if pms.df(msg) in [17, 18]:
            tc = pms.adsb.typecode(msg)
            if 1 <= tc <= 4:
                return pms.adsb.callsign(msg)
    except Exception:
        pass
    return None


def decode_altitude(msg: str) -> Optional[int]:
    """
    Extract altitude from ADS-B or altitude reply message.
    
    Args:
        msg: Mode-S message
        
    Returns:
        Altitude in feet or None
    """
    try:
        df = pms.df(msg)
        if df in [17, 18]:
            return pms.adsb.altitude(msg)
        elif df in [4, 20]:
            return pms.common.altcode(msg)
    except Exception:
        pass
    return None


def decode_velocity(msg: str) -> Optional[Dict[str, Any]]:
    """
    Extract velocity information from ADS-B message.
    
    Args:
        msg: ADS-B message (TC 19)
        
    Returns:
        Dictionary with velocity data or None
    """
    try:
        if pms.df(msg) in [17, 18] and pms.adsb.typecode(msg) == 19:
            velocity_data = pms.adsb.velocity(msg)
            if velocity_data:
                return {
                    'groundspeed': velocity_data[0],  # knots
                    'track': velocity_data[1],  # degrees
                    'vertical_rate': velocity_data[2],  # ft/min
                    'speed_type': velocity_data[3]  # GS or TAS
                }
    except Exception:
        pass
    return None


def is_valid_message(msg: str) -> bool:
    """
    Check if a Mode-S message is valid (correct length and CRC).
    
    Args:
        msg: Hexadecimal Mode-S message
        
    Returns:
        True if valid, False otherwise
    """
    if not msg or len(msg) not in [14, 28]:
        return False
    try:
        return pms.crc(msg, encode=False) == 0
    except Exception:
        return False


def get_message_type(msg: str) -> Optional[str]:
    """
    Get a human-readable description of the message type.
    
    Args:
        msg: Mode-S message
        
    Returns:
        String description of message type or None
    """
    try:
        df = pms.df(msg)
        
        if df in [17, 18]:
            tc = pms.adsb.typecode(msg)
            if 1 <= tc <= 4:
                return "Aircraft Identification"
            elif 5 <= tc <= 8:
                return "Surface Position"
            elif 9 <= tc <= 18:
                return "Airborne Position (Baro)"
            elif tc == 19:
                return "Airborne Velocity"
            elif 20 <= tc <= 22:
                return "Airborne Position (GNSS)"
            else:
                return f"ADS-B TC{tc}"
        elif df in [4, 20]:
            return "Altitude Reply"
        elif df in [5, 21]:
            return "Identity Reply (Squawk)"
        else:
            return f"Mode-S DF{df}"
    except Exception:
        return None


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example ADS-B messages (these are sample messages)
    test_messages = [
        # Replace with actual messages from your ADS-B receiver
        "8D4840D6202CC371C32CE0576098",  # Example position message
        "8D4840D6234CC371C32CE0576098",  # Example position message (different frame)
    ]
    
    decoder = ADSBDecoder()
    
    print("ADS-B Decoder Test")
    print("-" * 50)
    
    for msg in test_messages:
        print(f"\nMessage: {msg}")
        print(f"Valid: {is_valid_message(msg)}")
        print(f"Type: {get_message_type(msg)}")
        print(f"ICAO: {decode_icao(msg)}")
        
        decoded = decoder.decode_message(msg)
        if decoded:
            print(f"Decoded data: {decoded}")
