"""
FlightAware Web Scraper
Scrapes flight information from FlightAware to get origin and destination airports.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Optional, Dict
from datetime import datetime


class FlightAwareScraper:
    """Scraper for FlightAware flight information."""
    
    BASE_URL = "https://www.flightaware.com/live/flight"
    
    def __init__(self, timeout: int = 10):
        """
        Initialize the FlightAware scraper.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        # Set a user agent to avoid being blocked
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_flight_info(self, callsign: str) -> Optional[Dict]:
        """
        Scrape flight information from FlightAware.
        
        Args:
            callsign: Flight callsign (e.g., 'DAL144', 'UAL1234')
        
        Returns:
            Dictionary with flight information or None if not found:
            {
                'callsign': str,
                'origin': str,          # Airport code (e.g., 'KJFK')
                'destination': str,     # Airport code (e.g., 'KLAX')
                'origin_name': str,     # Airport name
                'destination_name': str, # Airport name
                'aircraft_type': str,   # Aircraft type if available
                'status': str,          # Flight status
                'url': str              # FlightAware URL
            }
        """
        try:
            # Clean up callsign - remove any spaces
            callsign = callsign.strip().upper()
            
            # Build URL
            url = f"{self.BASE_URL}/{callsign}"
            
            # Fetch page
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Extract flight route information
            flight_info = {
                'callsign': callsign,
                'url': url
            }
            
            # FlightAware embeds flight data in a JavaScript variable
            # Look for trackpollBootstrap JSON data
            json_pattern = re.compile(r'var\s+trackpollBootstrap\s*=\s*(\{.*?\});', re.DOTALL)
            match = json_pattern.search(response.text)
            
            if match:
                try:
                    data = json.loads(match.group(1))
                    
                    # Extract flight information from the flights object
                    if 'flights' in data and data['flights']:
                        # Get the first flight (usually there's only one)
                        flight_data = list(data['flights'].values())[0]
                        
                        # Extract origin
                        if 'origin' in flight_data:
                            origin = flight_data['origin']
                            flight_info['origin'] = origin.get('icao') or origin.get('iata', '')
                            if 'friendlyName' in origin:
                                flight_info['origin_name'] = origin['friendlyName']
                            elif 'name' in origin:
                                flight_info['origin_name'] = origin['name']
                        
                        # Extract destination
                        if 'destination' in flight_data:
                            dest = flight_data['destination']
                            flight_info['destination'] = dest.get('icao') or dest.get('iata', '')
                            if 'friendlyName' in dest:
                                flight_info['destination_name'] = dest['friendlyName']
                            elif 'name' in dest:
                                flight_info['destination_name'] = dest['name']
                        
                        # Extract aircraft type
                        if 'aircraftType' in flight_data and flight_data['aircraftType']:
                            flight_info['aircraft_type'] = flight_data['aircraftType']
                        elif 'aircraftTypeFriendly' in flight_data:
                            flight_info['aircraft_type'] = flight_data['aircraftTypeFriendly']
                        
                        # Extract status if available
                        if 'status' in flight_data:
                            flight_info['status'] = flight_data['status']
                        
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON data: {e}")
                except Exception as e:
                    print(f"Error extracting flight data: {e}")
            
            # Fallback: Parse HTML if JSON extraction failed
            if 'origin' not in flight_info or 'destination' not in flight_info:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try to find in page title
                title = soup.find('title')
                if title:
                    title_text = title.get_text()
                    # Look for pattern like "KJFK-KLAX" or "JFK-LAX"
                    route_match = re.search(r'([A-Z]{3,4})\s*[-–—]\s*([A-Z]{3,4})', title_text)
                    if route_match:
                        flight_info['origin'] = route_match.group(1)
                        flight_info['destination'] = route_match.group(2)
            
            # Return info if we have at least origin or destination
            if 'origin' in flight_info or 'destination' in flight_info:
                return flight_info
            
            # If we couldn't find route info, return None
            print(f"Could not extract route information for {callsign}")
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching flight data for {callsign}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing flight data for {callsign}: {e}")
            return None
    
    def get_route_string(self, callsign: str) -> Optional[str]:
        """
        Get a simple route string for a flight.
        
        Args:
            callsign: Flight callsign
        
        Returns:
            Route string like "KJFK -> KLAX" or None
        """
        info = self.get_flight_info(callsign)
        if info and 'origin' in info and 'destination' in info:
            return f"{info['origin']} -> {info['destination']}"
        return None


def lookup_flight_route(callsign: str) -> Optional[Dict]:
    """
    Convenience function to look up a flight's route.
    
    Args:
        callsign: Flight callsign (e.g., 'DAL144')
    
    Returns:
        Flight information dictionary or None
    """
    scraper = FlightAwareScraper()
    return scraper.get_flight_info(callsign)


if __name__ == "__main__":
    """Test the scraper with example flights."""
    
    # Test with a few example flights
    test_flights = ['DAL144', 'UAL1', 'AAL100']
    
    scraper = FlightAwareScraper()
    
    print("=" * 60)
    print("FlightAware Flight Route Scraper")
    print("=" * 60)
    
    for callsign in test_flights:
        print(f"\nLooking up {callsign}...")
        info = scraper.get_flight_info(callsign)
        
        if info:
            print(f"  Callsign: {info.get('callsign', 'N/A')}")
            print(f"  Route: {info.get('origin', '???')} -> {info.get('destination', '???')}")
            
            if 'origin_name' in info:
                print(f"  Origin: {info['origin_name']}")
            if 'destination_name' in info:
                print(f"  Destination: {info['destination_name']}")
            if 'aircraft_type' in info:
                print(f"  Aircraft: {info['aircraft_type']}")
            if 'status' in info:
                print(f"  Status: {info['status']}")
            
            print(f"  URL: {info['url']}")
        else:
            print(f"  Could not retrieve flight information")
        
        print("-" * 60)
