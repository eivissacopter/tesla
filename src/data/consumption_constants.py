"""Consumption constant reference data and local persistence layer.

The consumption constant (Verbrauchskonstante, Wh/km) is the value Tesla's
BMS uses to convert usable battery energy into the Rated Range displayed in
the car.  Tracking it over time lets owners isolate real degradation from
software-induced range changes.

Reference data sourced from TFF Forum Akkuwiki:
https://tff-forum.de/t/wiki-akkuwiki-model-3-y-s-x-ct/107641
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Factory reference constants
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FactoryConstant:
    """A single known factory consumption constant."""

    model: str
    variant: str
    battery: str
    drivetrain: str
    years: str
    constant_wh_km: float
    nominal_capacity_kwh: float
    notes: str = ""


# Curated from the TFF Akkuwiki / Akkuchronik threads.
FACTORY_CONSTANTS: List[FactoryConstant] = [
    # ── Model 3 ──────────────────────────────────────────────────────────
    FactoryConstant("Model 3", "Standard Range Plus", "NCA 50 kWh (2170)", "RWD", "2019–2020", 136.0, 50.0, "Panasonic 2170"),
    FactoryConstant("Model 3", "Standard Range Plus", "LFP 60 kWh", "RWD", "2021–2023", 128.0, 60.0, "CATL LFP, early batches"),
    FactoryConstant("Model 3", "Standard Range Plus", "LFP 60 kWh", "RWD", "2021–2023", 131.0, 60.0, "CATL LFP, later firmware"),
    FactoryConstant("Model 3", "Standard Range Plus", "LFP 60 kWh", "RWD", "2021–2023", 139.0, 60.0, "CATL LFP, post 2022.36+"),
    FactoryConstant("Model 3", "Long Range", "NCA 75 kWh (2170)", "AWD", "2019–2020", 152.5, 75.0, "Panasonic 2170"),
    FactoryConstant("Model 3", "Long Range", "NCA 79 kWh (2170)", "AWD", "2021–2023", 142.0, 79.0, "Panasonic 2170"),
    FactoryConstant("Model 3", "Performance", "NCA 79 kWh (2170)", "AWD", "2021–2022", 159.0, 79.0, "Panasonic 2170"),
    FactoryConstant("Model 3", "Performance", "NCA 75 kWh (2170)", "AWD", "2019–2020", 159.0, 75.0, "Panasonic 2170"),
    FactoryConstant("Model 3", "Highland SR", "LFP 60 kWh", "RWD", "2024+", 139.0, 60.0, "BYD Blade LFP"),
    FactoryConstant("Model 3", "Highland LR", "NMC 75 kWh", "AWD", "2024+", 143.5, 75.0, "Samsung SDI NMC"),
    FactoryConstant("Model 3", "Highland LR", "NMC 75 kWh", "RWD", "2024+", 133.0, 75.0, "Samsung SDI NMC, RWD"),

    # ── Model Y ──────────────────────────────────────────────────────────
    FactoryConstant("Model Y", "Long Range", "NCA 75 kWh (2170)", "AWD", "2021–2023", 148.5, 75.0, "Panasonic 2170"),
    FactoryConstant("Model Y", "Performance", "NCA 75 kWh (2170)", "AWD", "2021–2023", 148.5, 75.0, "Same pack as LR"),
    FactoryConstant("Model Y", "Standard Range", "LFP 60 kWh", "RWD", "2022–2023", 139.0, 60.0, "CATL LFP"),
    FactoryConstant("Model Y", "LR RWD (Juniper)", "NMC", "RWD", "2024+", 158.7, 75.0, "Juniper refresh"),
    FactoryConstant("Model Y", "LR AWD (Juniper)", "NMC", "AWD", "2024+", 148.0, 75.0, "Juniper refresh"),

    # ── Model S ──────────────────────────────────────────────────────────
    FactoryConstant("Model S", "Long Range", "NCA 100 kWh (18650)", "AWD", "2019–2020", 163.0, 100.0, "Panasonic 18650"),
    FactoryConstant("Model S", "Long Range", "NCA 100 kWh (2170)", "AWD", "2021+", 166.0, 100.0, "Panasonic 2170"),
    FactoryConstant("Model S", "Plaid", "NCA 100 kWh (2170)", "AWD", "2021+", 170.0, 100.0, "Tri-motor Plaid"),

    # ── Model X ──────────────────────────────────────────────────────────
    FactoryConstant("Model X", "Long Range", "NCA 100 kWh (18650)", "AWD", "2019–2020", 190.0, 100.0, "Panasonic 18650"),
    FactoryConstant("Model X", "Long Range", "NCA 100 kWh (2170)", "AWD", "2021+", 186.0, 100.0, "Panasonic 2170"),
    FactoryConstant("Model X", "Plaid", "NCA 100 kWh (2170)", "AWD", "2021+", 192.0, 100.0, "Tri-motor Plaid"),
]


def list_models() -> List[str]:
    """Return sorted unique model names."""
    return sorted({fc.model for fc in FACTORY_CONSTANTS})


def list_variants(model: str) -> List[str]:
    """Return sorted variants for a given model."""
    return sorted({fc.variant for fc in FACTORY_CONSTANTS if fc.model == model})


def list_batteries(model: str, variant: str) -> List[str]:
    """Return sorted battery labels for a model + variant."""
    return sorted({
        fc.battery for fc in FACTORY_CONSTANTS
        if fc.model == model and fc.variant == variant
    })


def list_drivetrains(model: str, variant: str) -> List[str]:
    """Return sorted drivetrains for a model + variant."""
    return sorted({
        fc.drivetrain for fc in FACTORY_CONSTANTS
        if fc.model == model and fc.variant == variant
    })


def lookup_constants(
    model: str,
    variant: str,
    battery: Optional[str] = None,
    drivetrain: Optional[str] = None,
) -> List[FactoryConstant]:
    """Look up matching factory constants for a vehicle configuration."""
    matches = [
        fc for fc in FACTORY_CONSTANTS
        if fc.model == model and fc.variant == variant
    ]
    if battery:
        narrowed = [fc for fc in matches if fc.battery == battery]
        if narrowed:
            matches = narrowed
    if drivetrain:
        narrowed = [fc for fc in matches if fc.drivetrain == drivetrain]
        if narrowed:
            matches = narrowed
    return matches


def constants_to_dataframe(constants: List[FactoryConstant]) -> pd.DataFrame:
    """Convert a list of FactoryConstant to a presentable DataFrame."""
    if not constants:
        return pd.DataFrame()
    return pd.DataFrame([
        {
            "Model": fc.model,
            "Variant": fc.variant,
            "Battery": fc.battery,
            "Drive": fc.drivetrain,
            "Years": fc.years,
            "Constant (Wh/km)": fc.constant_wh_km,
            "Nominal Capacity (kWh)": fc.nominal_capacity_kwh,
            "Notes": fc.notes,
        }
        for fc in constants
    ])


# ---------------------------------------------------------------------------
# SQLite persistence for user-submitted entries
# ---------------------------------------------------------------------------

_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "consumption_data.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS consumption_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL,
    model       TEXT    NOT NULL,
    variant     TEXT    NOT NULL,
    battery     TEXT    NOT NULL DEFAULT '',
    entry_date  TEXT    NOT NULL,
    constant    REAL    NOT NULL,
    rated_range REAL,
    odometer    REAL,
    software    TEXT    NOT NULL DEFAULT '',
    notes       TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""


def _get_connection() -> sqlite3.Connection:
    """Return a SQLite connection, creating the DB and table if needed."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    return conn


def add_entry(
    username: str,
    model: str,
    variant: str,
    battery: str,
    entry_date: date,
    constant: float,
    rated_range: Optional[float] = None,
    odometer: Optional[float] = None,
    software: str = "",
    notes: str = "",
) -> int:
    """Insert a new consumption constant entry. Returns the new row ID."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO consumption_entries
                (username, model, variant, battery, entry_date, constant,
                 rated_range, odometer, software, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username, model, variant, battery,
                entry_date.isoformat(), constant,
                rated_range, odometer, software, notes,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_entries(username: Optional[str] = None) -> pd.DataFrame:
    """Retrieve entries, optionally filtered by username."""
    conn = _get_connection()
    try:
        if username:
            df = pd.read_sql_query(
                "SELECT * FROM consumption_entries WHERE username = ? ORDER BY entry_date",
                conn,
                params=(username,),
            )
        else:
            df = pd.read_sql_query(
                "SELECT * FROM consumption_entries ORDER BY username, entry_date",
                conn,
            )
        if not df.empty and "entry_date" in df.columns:
            df["entry_date"] = pd.to_datetime(df["entry_date"])
        return df
    finally:
        conn.close()


def delete_entry(entry_id: int) -> bool:
    """Delete an entry by ID. Returns True if a row was removed."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM consumption_entries WHERE id = ?", (entry_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_usernames() -> List[str]:
    """Return all unique usernames that have submitted entries."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT username FROM consumption_entries ORDER BY username"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()
