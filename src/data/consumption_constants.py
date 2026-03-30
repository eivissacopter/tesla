"""Consumption constant reference data and local persistence layer.

The consumption constant (Verbrauchskonstante, Wh/km) is the value Tesla's
BMS uses to convert usable battery energy into the Rated Range displayed in
the car. Tracking it over time lets owners isolate real degradation from
software-induced range changes.

The factory reference data below is verified against explicit
``Konstante: ... Wh/km`` entries in the TFF Akkuwiki. Variants where the wiki
still shows ``???`` are intentionally omitted until there is a confirmed value.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional

import pandas as pd


AKKUWIKI_URL = "https://tff-forum.de/t/wiki-akkuwiki-model-3-model-y-cybertruck/107641"


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
    pack_code: str = ""
    chemistry: str = ""
    supplier: str = ""
    wheels: str = ""
    release: str = ""
    notes: str = ""
    source_url: str = AKKUWIKI_URL

    def battery_label(self) -> str:
        """Return a selector-friendly battery label."""
        if self.pack_code:
            return f"{self.pack_code} | {self.battery}"
        return self.battery

    def preset_label(self) -> str:
        """Return a compact label for the sidebar energy monitor."""
        label = f"{self.model} {self.variant} {self.drivetrain} {self.years}"
        if self.pack_code:
            label += f" ({self.pack_code})"
        if self.wheels:
            label += f" {self.wheels}"
        return label


# Verified against explicit "Konstante" entries in the Akkuwiki.
FACTORY_CONSTANTS: List[FactoryConstant] = [
    FactoryConstant(
        "Model 3",
        "Standard Range",
        "CATL 6C LFP | 54.4 kWh",
        "RWD",
        "2020",
        133.0,
        54.4,
        pack_code="E6R",
        chemistry="LFP",
        supplier="CATL",
        release="Legacy",
        notes="Locked CATL 6C pack.",
    ),
    FactoryConstant(
        "Model 3",
        "Standard Range",
        "CATL 6C LFP | 54.4 kWh",
        "RWD",
        "2021",
        128.0,
        54.4,
        pack_code="E6CR",
        chemistry="LFP",
        supplier="CATL",
        release="Refresh",
        notes="Locked CATL 6C pack with the lower 2021 constant.",
    ),
    FactoryConstant(
        "Model 3",
        "Standard Range",
        "CATL 6L LFP | 62.0 kWh",
        "RWD",
        "2021-2023",
        139.0,
        62.0,
        pack_code="E6LR",
        chemistry="LFP",
        supplier="CATL",
        release="Refresh",
        notes="Main refreshed Model 3 RWD pack.",
    ),
    FactoryConstant(
        "Model 3",
        "Standard Range",
        "CATL 6L LFP | 62.0 kWh",
        "RWD",
        "2024",
        139.0,
        62.0,
        pack_code="H6LR",
        chemistry="LFP",
        supplier="CATL",
        release="Highland",
        notes="Highland RWD with the same verified constant as E6LR.",
    ),
    FactoryConstant(
        "Model 3",
        "Long Range",
        "Panasonic 3 NCA | 79.8 kWh",
        "RWD",
        "2019",
        145.5,
        79.8,
        pack_code="E3R",
        chemistry="NCA",
        supplier="Panasonic",
        release="Legacy",
        notes="Original Long Range RWD pack.",
    ),
    FactoryConstant(
        "Model 3",
        "Long Range",
        "Panasonic 3 NCA | 79.8 kWh",
        "AWD",
        "2019-2020",
        152.5,
        79.8,
        pack_code="E3D",
        chemistry="NCA",
        supplier="Panasonic",
        release="Legacy",
        notes="Original Long Range AWD pack.",
    ),
    FactoryConstant(
        "Model 3",
        "Long Range",
        "Panasonic 3C NCA | 75.4 kWh",
        "AWD",
        "2021",
        136.7,
        75.4,
        pack_code="E3CD",
        chemistry="NCA",
        supplier="Panasonic",
        release="Refresh",
        notes="Software-limited Panasonic 3C pack.",
    ),
    FactoryConstant(
        "Model 3",
        "Long Range",
        "LG 5C NMC | 77.0 kWh",
        "AWD",
        "2021",
        136.7,
        77.0,
        pack_code="E5CD",
        chemistry="NMC",
        supplier="LG",
        release="Refresh",
        notes="Early LG long-range pack.",
    ),
    FactoryConstant(
        "Model 3",
        "Long Range",
        "Panasonic 3L NCA | 82.1 kWh",
        "AWD",
        "2021-2022",
        136.7,
        82.1,
        pack_code="E3LD",
        chemistry="NCA",
        supplier="Panasonic",
        release="Refresh",
        notes="82.1 kWh Panasonic 3L long-range pack.",
    ),
    FactoryConstant(
        "Model 3",
        "Long Range",
        "LG 5L NMC | 79.0 kWh",
        "AWD",
        "2021-2023",
        136.7,
        79.0,
        pack_code="E5LD",
        chemistry="NMC",
        supplier="LG",
        release="Refresh",
        notes="Main LG 5L long-range AWD pack.",
    ),
    FactoryConstant(
        "Model 3",
        "Long Range",
        "LG 5L NMC | 79.0 kWh",
        "RWD",
        "2023",
        143.0,
        79.0,
        pack_code="E5LR",
        chemistry="NMC",
        supplier="LG",
        release="Refresh",
        notes="Short-lived Long Range RWD variant.",
    ),
    FactoryConstant(
        "Model 3",
        "Long Range",
        "LG 5L NMC | 79.0 kWh",
        "AWD",
        "2024-2025",
        143.5,
        79.0,
        pack_code="H5LD",
        chemistry="NMC",
        supplier="LG",
        release="Highland",
        notes="Verified Highland Long Range AWD constant.",
    ),
    FactoryConstant(
        "Model 3",
        "Performance",
        "Panasonic 3 NCA | 79.8 kWh",
        "AWD",
        "2019-2020",
        152.5,
        79.8,
        pack_code="E3D",
        chemistry="NCA",
        supplier="Panasonic",
        release="Legacy",
        notes="Original Performance pack.",
    ),
    FactoryConstant(
        "Model 3",
        "Performance",
        "Panasonic 3L NCA | 82.1 kWh",
        "AWD",
        "2021-2022",
        159.0,
        82.1,
        pack_code="E3LD",
        chemistry="NCA",
        supplier="Panasonic",
        release="Refresh",
        notes="Performance pack with the larger Panasonic 3L.",
    ),
    FactoryConstant(
        "Model 3",
        "Performance",
        "LG 5L NMC | 79.0 kWh",
        "AWD",
        "2022-2023",
        159.0,
        79.0,
        pack_code="E5LD",
        chemistry="NMC",
        supplier="LG",
        release="Refresh",
        notes="Later pre-Highland Performance constant.",
    ),
    FactoryConstant(
        "Model Y",
        "Standard Range",
        "CATL 6L LFP lock | 59.7 kWh",
        "RWD",
        "2022-2024",
        142.5,
        59.7,
        pack_code="Y6LR",
        chemistry="LFP",
        supplier="CATL",
        wheels='19"',
        release="Legacy",
        notes="Locked Y6LR pack on 19-inch wheels.",
    ),
    FactoryConstant(
        "Model Y",
        "Standard Range",
        "CATL 6L LFP lock | 59.7 kWh",
        "RWD",
        "2022-2024",
        153.0,
        59.7,
        pack_code="Y6LR",
        chemistry="LFP",
        supplier="CATL",
        wheels='20"',
        release="Legacy",
        notes="Locked Y6LR pack on 20-inch wheels.",
    ),
    FactoryConstant(
        "Model Y",
        "Standard Range",
        "BYD 7C Blade LFP | 60.0 kWh",
        "RWD",
        "2023-2024",
        142.5,
        60.0,
        pack_code="Y7CR",
        chemistry="LFP",
        supplier="BYD",
        wheels='19"',
        release="Structural",
        notes="BYD blade pack on 19-inch wheels.",
    ),
    FactoryConstant(
        "Model Y",
        "Standard Range",
        "BYD 7C Blade LFP | 60.0 kWh",
        "RWD",
        "2023-2024",
        153.0,
        60.0,
        pack_code="Y7CR",
        chemistry="LFP",
        supplier="BYD",
        wheels='20"',
        release="Structural",
        notes="BYD blade pack on 20-inch wheels.",
    ),
    FactoryConstant(
        "Model Y",
        "Standard Range",
        "CATL 6M LFP | 64.5 kWh",
        "RWD",
        "2025",
        147.6,
        64.5,
        pack_code="YS6MR",
        chemistry="LFP",
        supplier="CATL",
        wheels='19"',
        release="Opal",
        notes="Updated CATL 6M pack on 19-inch wheels.",
    ),
    FactoryConstant(
        "Model Y",
        "Standard Range",
        "CATL 6M LFP | 64.5 kWh",
        "RWD",
        "2025",
        152.6,
        64.5,
        pack_code="YS6MR",
        chemistry="LFP",
        supplier="CATL",
        wheels='20"',
        release="Opal",
        notes="Updated CATL 6M pack on 20-inch wheels.",
    ),
    FactoryConstant(
        "Model Y",
        "Long Range",
        "LG 5C NMC | 77.0 kWh",
        "AWD",
        "2021",
        148.5,
        77.0,
        pack_code="Y5CD",
        chemistry="NMC",
        supplier="LG",
        release="Legacy",
        notes="Early Model Y Long Range pack.",
    ),
    FactoryConstant(
        "Model Y",
        "Long Range",
        "LG 5L NMC | 79.0 kWh",
        "AWD",
        "2022-2025",
        148.5,
        79.0,
        pack_code="Y5LD",
        chemistry="NMC",
        supplier="LG",
        release="Legacy/Refresh",
        notes="Main Model Y Long Range AWD pack.",
    ),
    FactoryConstant(
        "Model Y",
        "Long Range",
        "LG 5L NMC | 79.0 kWh",
        "AWD",
        "2025",
        147.1,
        79.0,
        pack_code="YS5LD",
        chemistry="NMC",
        supplier="LG",
        wheels='19"',
        release="Opal",
        notes="Opal Long Range AWD on 19-inch wheels.",
    ),
    FactoryConstant(
        "Model Y",
        "Long Range",
        "LG 5L NMC | 79.0 kWh",
        "AWD",
        "2025",
        158.7,
        79.0,
        pack_code="YS5LD",
        chemistry="NMC",
        supplier="LG",
        wheels='20"',
        release="Opal",
        notes="Opal Long Range AWD on 20-inch wheels.",
    ),
    FactoryConstant(
        "Model Y",
        "Performance",
        "LG 5L NMC | 79.0 kWh",
        "AWD",
        "2022-2025",
        165.0,
        79.0,
        pack_code="Y5LD",
        chemistry="NMC",
        supplier="LG",
        release="Legacy/Refresh",
        notes="Verified Model Y Performance constant.",
    ),
    FactoryConstant(
        "Model Y",
        "Performance",
        "LG 5M NMC | 84.7 kWh",
        "AWD",
        "2025+",
        169.2,
        84.7,
        pack_code="YS5MD",
        chemistry="NMC",
        supplier="LG",
        wheels='21"',
        release="Opal",
        notes="Opal Performance with the larger 5M pack.",
    ),
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
        fc.battery_label() for fc in FACTORY_CONSTANTS
        if fc.model == model and fc.variant == variant
    })


def list_drivetrains(model: str, variant: str, battery: Optional[str] = None) -> List[str]:
    """Return sorted drivetrains for a model + variant."""
    return sorted({
        fc.drivetrain for fc in FACTORY_CONSTANTS
        if fc.model == model
        and fc.variant == variant
        and (not battery or fc.battery_label() == battery)
    })


def list_wheels(
    model: str,
    variant: str,
    battery: Optional[str] = None,
    drivetrain: Optional[str] = None,
) -> List[str]:
    """Return wheel-size selectors for the current slice."""
    wheels = sorted({
        fc.wheels or "All"
        for fc in FACTORY_CONSTANTS
        if fc.model == model
        and fc.variant == variant
        and (not battery or fc.battery_label() == battery)
        and (not drivetrain or fc.drivetrain == drivetrain)
    })
    return wheels if wheels else ["All"]


def lookup_constants(
    model: str,
    variant: str,
    battery: Optional[str] = None,
    drivetrain: Optional[str] = None,
    wheels: Optional[str] = None,
) -> List[FactoryConstant]:
    """Look up matching factory constants for a vehicle configuration."""
    matches = [
        fc for fc in FACTORY_CONSTANTS
        if fc.model == model and fc.variant == variant
    ]
    if battery:
        narrowed = [fc for fc in matches if fc.battery_label() == battery]
        if narrowed:
            matches = narrowed
    if drivetrain:
        narrowed = [fc for fc in matches if fc.drivetrain == drivetrain]
        if narrowed:
            matches = narrowed
    if wheels and wheels != "All":
        narrowed = [fc for fc in matches if fc.wheels == wheels]
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
            "Pack Code": fc.pack_code,
            "Battery": fc.battery,
            "Chemistry": fc.chemistry,
            "Supplier": fc.supplier,
            "Drive": fc.drivetrain,
            "Wheels": fc.wheels or "All",
            "Years": fc.years,
            "Constant (Wh/km)": fc.constant_wh_km,
            "Pack Net (kWh)": fc.nominal_capacity_kwh,
            "Release": fc.release,
            "Notes": fc.notes,
        }
        for fc in constants
    ])


_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "consumption_data.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS consumption_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL,
    car_name    TEXT    NOT NULL DEFAULT '',
    model       TEXT    NOT NULL,
    variant     TEXT    NOT NULL,
    battery     TEXT    NOT NULL DEFAULT '',
    pack_code   TEXT    NOT NULL DEFAULT '',
    drivetrain  TEXT    NOT NULL DEFAULT '',
    wheels      TEXT    NOT NULL DEFAULT '',
    release     TEXT    NOT NULL DEFAULT '',
    entry_date  TEXT    NOT NULL,
    constant    REAL    NOT NULL,
    rated_range REAL,
    odometer    REAL,
    software    TEXT    NOT NULL DEFAULT '',
    notes       TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

_REQUIRED_ENTRY_COLUMNS = {
    "car_name": "TEXT NOT NULL DEFAULT ''",
    "pack_code": "TEXT NOT NULL DEFAULT ''",
    "drivetrain": "TEXT NOT NULL DEFAULT ''",
    "wheels": "TEXT NOT NULL DEFAULT ''",
    "release": "TEXT NOT NULL DEFAULT ''",
}


def _get_connection() -> sqlite3.Connection:
    """Return a SQLite connection, creating the DB and table if needed."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute(_CREATE_TABLE_SQL)
    _ensure_entry_schema(conn)
    conn.commit()
    return conn


def _ensure_entry_schema(conn: sqlite3.Connection) -> None:
    """Migrate the local SQLite table with any newly required columns."""
    existing_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(consumption_entries)").fetchall()
    }
    for column_name, column_definition in _REQUIRED_ENTRY_COLUMNS.items():
        if column_name not in existing_columns:
            conn.execute(
                f"ALTER TABLE consumption_entries ADD COLUMN {column_name} {column_definition}"
            )


def add_entry(
    username: str,
    car_name: str,
    model: str,
    variant: str,
    battery: str,
    pack_code: str,
    drivetrain: str,
    wheels: str,
    release: str,
    entry_date: date,
    constant: float,
    rated_range: Optional[float] = None,
    odometer: Optional[float] = None,
    software: str = "",
    notes: str = "",
) -> int:
    """Insert a new consumption constant entry and return the new row ID."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO consumption_entries
                (username, car_name, model, variant, battery, pack_code,
                 drivetrain, wheels, release, entry_date, constant,
                 rated_range, odometer, software, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                car_name,
                model,
                variant,
                battery,
                pack_code,
                drivetrain,
                wheels,
                release,
                entry_date.isoformat(),
                constant,
                rated_range,
                odometer,
                software,
                notes,
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
        for column_name in _REQUIRED_ENTRY_COLUMNS:
            if column_name not in df.columns:
                df[column_name] = ""
        return df
    finally:
        conn.close()


def delete_entry(entry_id: int) -> bool:
    """Delete an entry by ID. Return True if a row was removed."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM consumption_entries WHERE id = ?",
            (entry_id,),
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
        return [row[0] for row in rows]
    finally:
        conn.close()
