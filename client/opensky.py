"""Helpers for interacting with the OpenSky authentication endpoint.

This module provides a small helper to exchange client credentials for a
bearer token using the OpenID Connect token endpoint used by OpenSky.
"""

from __future__ import annotations

import typing as t
import requests
from logger import log_api_call
import os
from pydantic import BaseModel


# Read hosts from environment so .env can control them
OPENSKY_AUTH_HOST = os.getenv("OPENSKY_AUTH_HOST", "https://auth.opensky-network.org").rstrip("/")
OPENSKY_API_HOST = os.getenv("OPENSKY_API_HOST", "https://opensky-network.org").rstrip("/")

TOKEN_URL = OPENSKY_AUTH_HOST + "/auth/realms/opensky-network/protocol/openid-connect/token"

class ErrorResponse(BaseModel):
	"""Represents an error returned by the helper instead of a StatesResponse."""
	message: str
	code: t.Optional[int] = None


class Flight(BaseModel):
	"""Model for a single flight record returned by /api/flights/aircraft."""
	icao24: str
	firstSeen: int
	estDepartureAirport: t.Optional[str] = None
	lastSeen: int
	estArrivalAirport: t.Optional[str] = None
	callsign: t.Optional[str] = None
	estDepartureAirportHorizDistance: t.Optional[int] = None
	estDepartureAirportVertDistance: t.Optional[int] = None
	estArrivalAirportHorizDistance: t.Optional[int] = None
	estArrivalAirportVertDistance: t.Optional[int] = None
	departureAirportCandidatesCount: t.Optional[int] = None
	arrivalAirportCandidatesCount: t.Optional[int] = None

def get_opensky_token(client_id: str, client_secret: str) -> t.Optional[str]:
	"""Exchange client credentials for a bearer token.

	Returns the access token string on success, or None on failure.
	Raises requests.RequestException for network-level errors.
	"""
	data = {
		"grant_type": "client_credentials",
		"client_id": client_id,
		"client_secret": client_secret,
	}
	headers = {"Content-Type": "application/x-www-form-urlencoded"}
	url = TOKEN_URL
	try:
		import time as _time
		t0 = _time.monotonic()
		resp = requests.post(url, data=data, headers=headers, timeout=10)
		resp.raise_for_status()
		elapsed = int((_time.monotonic() - t0) * 1000)
	except requests.RequestException as e:
		try:
			elapsed = int((__import__("time").monotonic() - t0) * 1000)
		except Exception:
			elapsed = None
		log_api_call(url, params={"client_id": client_id}, success=False, message=str(e), elapsed_ms=elapsed)
		raise
	j = resp.json()
	# The token is typically in the access_token field
	log_api_call(url, params={"client_id": client_id}, success=True, message="token received")
	return j.get("access_token")


class State(BaseModel):
	"""Typed representation of a single OpenSky state vector.

	OpenSky returns each state as a list with fixed indices; this maps those
	positions to named attributes.
	"""
	icao24: str
	callsign: t.Optional[str] = None
	origin_country: t.Optional[str] = None
	time_position: t.Optional[int] = None
	last_contact: t.Optional[int] = None
	longitude: t.Optional[float] = None
	latitude: t.Optional[float] = None
	baro_altitude: t.Optional[float] = None
	on_ground: t.Optional[bool] = None
	velocity: t.Optional[float] = None
	true_track: t.Optional[float] = None
	vertical_rate: t.Optional[float] = None
	sensors: t.Optional[t.List[int]] = None
	geo_altitude: t.Optional[float] = None
	squawk: t.Optional[str] = None
	spi: t.Optional[bool] = None
	position_source: t.Optional[int] = None

	@classmethod
	def from_list(cls, data: t.List[t.Any]) -> "State":
		# Ensure we have at least 17 elements
		padded = list(data) + [None] * (17 - len(data))
		callsign = padded[1].strip() if padded[1] and isinstance(padded[1], str) else None
		return cls(
			icao24=padded[0],
			callsign=callsign,
			origin_country=padded[2],
			time_position=padded[3],
			last_contact=padded[4],
			longitude=padded[5],
			latitude=padded[6],
			baro_altitude=padded[7],
			on_ground=padded[8],
			velocity=padded[9],
			true_track=padded[10],
			vertical_rate=padded[11],
			sensors=padded[12],
			geo_altitude=padded[13],
			squawk=padded[14],
			spi=padded[15],
			position_source=padded[16],
		)


class StatesResponse(BaseModel):
	time: t.Optional[int] = None
	states: t.List[State] = []

	@classmethod
	def from_raw(cls, raw: t.Dict[str, t.Any]) -> "StatesResponse":
		raw_states = raw.get("states") or []
		parsed = [State.from_list(s) for s in raw_states]
		return cls(time=raw.get("time"), states=parsed)


def get_opensky_states(
	bearer_token: str,
	lamin: float,
	lamax: float,
	lomin: float,
	lomax: float,
	timeout: int = 10,
	) -> t.Union[StatesResponse, ErrorResponse]:
	"""GET /api/states/all from OpenSky using a Bearer token and bbox params.

	Parameters:
	- bearer_token: the access token string (do not log this value)
	- lamin, lamax, lomin, lomax: bounding box floats
	- timeout: request timeout in seconds

	Returns the parsed JSON response (usually a dict) or the raw text if JSON
	decoding fails. Raises requests.RequestException on network errors and
	requests.HTTPError for non-2xx responses.
	"""
	url = OPENSKY_API_HOST + "/api/states/all"
	headers = {"Authorization": f"Bearer {bearer_token}"}
	params = {"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax}

	try:
		import time as _time
		t0 = _time.monotonic()
		resp = requests.get(url, headers=headers, params=params, timeout=timeout)
		resp.raise_for_status()
		elapsed = int((_time.monotonic() - t0) * 1000)
	except requests.RequestException as e:
		# Network-level error or non-2xx response
		code = None
		# HTTPError may have a response with status_code
		try:
			code = e.response.status_code  # type: ignore[attr-defined]
		except Exception:
			code = None
		try:
			elapsed = int((__import__("time").monotonic() - t0) * 1000)
		except Exception:
			elapsed = None
		log_api_call(url, params=params, success=False, message=str(e), elapsed_ms=elapsed)
		return ErrorResponse(message=str(e), code=code)

	try:
		payload = resp.json()
	except ValueError as e:
		log_api_call(url, params=params, success=False, message=f"Invalid JSON: {e}", elapsed_ms=elapsed if 'elapsed' in locals() else None)
		return ErrorResponse(message=f"Invalid JSON response: {e}", code=resp.status_code)

	# Convert into typed model and validate
	try:
		out = StatesResponse.from_raw(payload)
		return out
	except Exception as e:
		# pydantic.ValidationError or other conversion error
		return ErrorResponse(message=f"Response validation failed: {e}", code=None)

def get_aircraft_flights(
	bearer_token: str,
	icao24: str,
	begin: int,
	end: int,
	timeout: int = 10,
) -> t.Union[t.List[Flight], ErrorResponse]:
	"""GET /api/flights/aircraft for a given `icao24` between begin and end.

	Returns a list of `Flight` on success or an `ErrorResponse` on failure.
	"""
	url = OPENSKY_API_HOST + "/api/flights/aircraft"
	headers = {"Authorization": f"Bearer {bearer_token}"}
	params = {"icao24": icao24, "begin": begin, "end": end}

	try:
		import time as _time
		t0 = _time.monotonic()
		resp = requests.get(url, headers=headers, params=params, timeout=timeout)
		resp.raise_for_status()
		elapsed = int((_time.monotonic() - t0) * 1000)
	except requests.RequestException as e:
		code = None
		try:
			print(e)
			code = e.response.status_code  # type: ignore[attr-defined]
		except Exception:
			code = None
		try:
			elapsed = int((__import__("time").monotonic() - t0) * 1000)
		except Exception:
			elapsed = None
		log_api_call(url, params={"icao24": icao24, "begin": begin, "end": end}, success=False, message=str(e), elapsed_ms=elapsed)
		return ErrorResponse(message=str(e), code=code)

	try:
		payload = resp.json()
	except ValueError as e:
		log_api_call(url, params={"icao24": icao24, "begin": begin, "end": end}, success=False, message=f"Invalid JSON: {e}", elapsed_ms=elapsed if 'elapsed' in locals() else None)
		return ErrorResponse(message=f"Invalid JSON response: {e}", code=resp.status_code)

	if not isinstance(payload, list):
		return ErrorResponse(message="Unexpected response shape: expected list", code=resp.status_code)

	flights: t.List[Flight] = []
	for item in payload:
		try:
			flights.append(Flight.parse_obj(item))
		except Exception as e:
			log_api_call(url, params={"icao24": icao24, "begin": begin, "end": end}, success=False, message=f"Flight item validation failed: {e}", elapsed_ms=elapsed if 'elapsed' in locals() else None)
			return ErrorResponse(message=f"Flight item validation failed: {e}", code=None)

	log_api_call(url, params={"icao24": icao24, "begin": begin, "end": end}, success=True, message=f"{len(flights)} flights parsed", elapsed_ms=elapsed if 'elapsed' in locals() else None)
	return flights

