"""Tesla VIN decoder.

Decodes the *non-identifying* structural fields of a Tesla VIN: manufacturer
plant, model line, model year and (where encodable) drivetrain hint. The serial
(chars 12-17) and the VIN itself are never returned in public output -- this
module exists so the home-server ETL can turn an identifying VIN into the
handful of public physical attributes the owner is happy to share.

Pure standard library so it can run anywhere (home server cron, CI, tests).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


# --- World Manufacturer Identifier (chars 1-3) -> factory / country ----------
# Tesla assigns a WMI per assembly plant. We keep both a human plant name and
# the community "factory code" (MIC/MIG/MIA/Fremont) used by the online tool.
WMI_PLANT = {
    "5YJ": ("Fremont, USA", "Fremont"),
    "7SA": ("Fremont, USA", "Fremont"),
    "7G2": ("Austin, USA", "MIA"),
    "LRW": ("Shanghai, China", "MIC"),
    "XP7": ("Berlin, Germany", "MIG"),
}

# --- Model line (char 4) -----------------------------------------------------
LINE_MODEL = {
    "3": "Model 3",
    "Y": "Model Y",
    "S": "Model S",
    "X": "Model X",
    "C": "Cybertruck",
    "R": "Roadster",
}

# --- Model year (char 10) ----------------------------------------------------
# ISO 3779 year letters; Tesla skips I,O,Q,U,Z and the digit 0.
YEAR_CODE = {
    "L": 2020, "M": 2021, "N": 2022, "P": 2023, "R": 2024,
    "S": 2025, "T": 2026, "V": 2027, "W": 2028, "X": 2029, "Y": 2030,
    "A": 2010, "B": 2011, "C": 2012, "D": 2013, "E": 2014, "F": 2015,
    "G": 2016, "H": 2017, "J": 2018, "K": 2019,
}

# --- Plant (char 11) ---------------------------------------------------------
PLANT_CODE = {
    "F": ("Fremont, USA", "Fremont"),
    "B": ("Berlin, Germany", "MIG"),
    "C": ("Shanghai, China", "MIC"),
    "A": ("Austin, USA", "MIA"),
}

# --- Drivetrain hint (char 8, Model 3/Y) -------------------------------------
# Not authoritative across all years; the Teslalogger trim badge is preferred.
# Kept only as a fallback signal.
DRIVE_HINT = {
    "C": "RWD",   # single-motor (US Model 3 SR/LR RWD)
    "J": "RWD",   # single-motor (Model Y RWD / SR)
    "E": "AWD",   # dual-motor
    "K": "AWD",   # dual-motor (Model Y LR/Performance)
    "B": "AWD",
}


@dataclass
class DecodedVin:
    model: Optional[str]
    model_year: Optional[int]
    plant: Optional[str]          # human readable, e.g. "Berlin, Germany"
    factory_code: Optional[str]   # community code, e.g. "MIG"
    drivetrain_hint: Optional[str]
    valid: bool

    def as_public_dict(self) -> dict:
        """Public attributes only -- never includes the VIN or serial."""
        d = asdict(self)
        return d


def decode_vin(vin: Optional[str]) -> DecodedVin:
    """Decode a Tesla VIN into non-identifying structural attributes.

    Returns valid=False (with whatever could be parsed) for malformed input
    rather than raising, so the ETL can skip cleanly.
    """
    if not vin or not isinstance(vin, str):
        return DecodedVin(None, None, None, None, None, False)
    v = vin.strip().upper()
    if len(v) != 17:
        return DecodedVin(None, None, None, None, None, False)

    wmi = v[0:3]
    line = v[3]
    drive_char = v[7]
    year_char = v[9]
    plant_char = v[10]

    model = LINE_MODEL.get(line)
    model_year = YEAR_CODE.get(year_char)

    # Plant: prefer the dedicated plant char (pos 11); fall back to the WMI.
    plant, factory = PLANT_CODE.get(plant_char, (None, None))
    if plant is None and wmi in WMI_PLANT:
        plant, factory = WMI_PLANT[wmi]

    drivetrain = DRIVE_HINT.get(drive_char)

    valid = model is not None and model_year is not None and plant is not None
    return DecodedVin(model, model_year, plant, factory, drivetrain, valid)


def model_year_quarter(model_year: Optional[int], first_seen=None) -> Optional[int]:
    """Best-effort quarter (1-4) from the first-seen timestamp, else None.

    The VIN does not encode the quarter; the chronology resolver needs one, so
    we derive it from when the car first appears in the log.
    """
    if first_seen is None:
        return None
    try:
        return (first_seen.month - 1) // 3 + 1
    except Exception:
        return None
