# Import dotenv and os to load environment variables
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the FLIGHTRADAR_API_KEY from environment
FLIGHTRADAR_API_KEY = os.getenv('FLIGHTRADAR_API_KEY')
