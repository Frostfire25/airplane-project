from __future__ import annotations

import os
from pathlib import Path
import datetime
from dataclasses import dataclass
import typing as t

# Use the standard-library sqlite3 module (available on Windows and Linux)
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_NAME = os.getenv('DB_NAME', 'airplane.db')


@dataclass
class NearestPlane:
	id: str
	latitude: float
	longitude: float
	icao24: str
	callsign: t.Optional[str]
	velocity: t.Optional[float]
	last_conact: float
	updateRow: float
	arrivalAirport: t.Optional[str] = None
	departureAirport: t.Optional[str] = None
	distance: t.Optional[float] = None

def _db_path(path: t.Optional[t.Union[str, Path]] = None) -> Path:
	"""Return a Path to the database file; default is `client/airplane.db`."""
	if path is None:
		return BASE_DIR / DEFAULT_DB_NAME
	return Path(path)


def database_exists(path: t.Optional[t.Union[str, Path]] = None) -> bool:
	"""Return True if the sqlite database file exists on disk."""
	p = _db_path(path)
	return p.exists()


def create_database(path: t.Optional[t.Union[str, Path]] = None) -> Path:
	"""Create a new sqlite database file and initialize a minimal schema.

	The function will create the file if it doesn't exist and add a small
	`meta` table with a created_at timestamp. Returns the Path to the DB.
	"""
	if sqlite3 is None:
		raise RuntimeError("No sqlite3 available in this Python environment")

	p = _db_path(path)
	# Ensure directory exists
	p.parent.mkdir(parents=True, exist_ok=True)

	# Connecting will create the database file if it does not exist.
	conn = sqlite3.connect(str(p))
	try:
		cur = conn.cursor()
		# Minimal meta table to record creation time and optional version
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS meta (
				key TEXT PRIMARY KEY,
				value TEXT NOT NULL
			)
			"""
		)
		created = datetime.datetime.utcnow().isoformat()
		cur.execute(
			"INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
			("created_at", created),
		)
		conn.commit()
	finally:
		conn.close()

	return p


def ensure_database(path: t.Optional[t.Union[str, Path]] = None) -> Path:
	"""Ensure a local sqlite database exists; create it if missing.

	Returns the Path to the database file.
	"""
	p = _db_path(path)
	if not p.exists():
		create_database(p)
	return p


def table_exists(path: t.Optional[t.Union[str, Path]] = None, table_name: str = "") -> bool:
	"""Return True if the given table exists in the sqlite database at `path`.

	If `path` is None the default DB path is used.
	"""
	p = ensure_database(path)
	conn = sqlite3.connect(str(p))
	try:
		cur = conn.cursor()
		cur.execute(
			"SELECT name FROM sqlite_master WHERE type='table' AND name=?",
			(table_name,)
		)
		row = cur.fetchone()
		return row is not None
	finally:
		conn.close()


def ensure_nearestplane_table(path: t.Optional[t.Union[str, Path]] = None) -> Path:
	p = ensure_database(path)
	if table_exists(p, "NearestPlane"):
		return p

	conn = sqlite3.connect(str(p))
	try:
		cur = conn.cursor()
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS NearestPlane (
					id TEXT PRIMARY KEY NOT NULL,
					latitude REAL NOT NULL,
					longitude REAL NOT NULL,
					icao24 TEXT NOT NULL,
					callsign TEXT,
					velocity REAL,
					last_conact REAL NOT NULL,
					updateRow REAL NOT NULL,
					arrivalAirport TEXT,
					departureAirport TEXT,
					distance REAL
			)
			"""
		)
		conn.commit()
		return p
	finally:
		conn.close()


def get_nearestplane_by_id(
	pk: str, path: t.Optional[t.Union[str, Path]] = None
) -> t.Optional[NearestPlane]:
	"""Return the row from `NearestPlane` with primary key `pk` as a dict.

	If the row does not exist, returns None. The function ensures the table
	exists first.
	"""
	p = ensure_nearestplane_table(path)
	conn = sqlite3.connect(str(p))
	# Return rows as dict-like
	conn.row_factory = sqlite3.Row
	try:
		cur = conn.cursor()
		cur.execute("SELECT * FROM NearestPlane WHERE id = ?", (pk,))
		row = cur.fetchone()
		if row is None:
			return None
		# sqlite3.Row is convertible to dict; map to NearestPlane
		data = dict(row)
		return NearestPlane(**data)
	finally:
		conn.close()


def create_nearestplane(
	id: str,
	latitude: float,
	longitude: float,
	icao24: str,
	callsign: t.Optional[str],
	velocity: t.Optional[float],
	last_conact: float,
	updateRow: float,
	arrivalAirport: t.Optional[str] = None,
	departureAirport: t.Optional[str] = None,
	distance: t.Optional[float] = None,
	path: t.Optional[t.Union[str, Path]] = None,
) -> t.Optional[NearestPlane]:
	"""Insert a new row into `NearestPlane` and return the inserted row as a dict.

	If insertion fails due to a primary-key conflict, the function returns None.
	The function ensures the database and table exist before inserting.
	"""
	p = ensure_nearestplane_table(path)
	conn = sqlite3.connect(str(p))
	try:
		cur = conn.cursor()
		try:
			cur.execute(
				"""
				INSERT INTO NearestPlane
				(id, latitude, longitude, icao24, callsign, velocity, last_conact, updateRow, arrivalAirport, departureAirport, distance)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
				""",
				(id, latitude, longitude, icao24, callsign, velocity, last_conact, updateRow, arrivalAirport, departureAirport, distance),
			)
			exception = None
		except sqlite3.IntegrityError as e:
			# primary key conflict or other integrity error
			exception = e
			return None
		else:
			conn.commit()
			# return the inserted row as a NearestPlane
			return get_nearestplane_by_id(id, p)
	finally:
		conn.close()


def drop_nearestplane_table(path: t.Optional[t.Union[str, Path]] = None) -> None:
	"""Drop the NearestPlane table if it exists. Use with caution.

	This is destructive and will remove all stored rows.
	"""
	p = _db_path(path)
	if not p.exists():
		# nothing to do
		return
	conn = sqlite3.connect(str(p))
	try:
		cur = conn.cursor()
		cur.execute("DROP TABLE IF EXISTS NearestPlane")
		conn.commit()
	finally:
		conn.close()


__all__ = [
	"BASE_DIR",
	"DEFAULT_DB_NAME",
	"database_exists",
	"create_database",
	"ensure_database",
	"table_exists",
	"ensure_nearestplane_table",
	"get_nearestplane_by_id",
	"create_nearestplane",
	"drop_nearestplane_table",
]

