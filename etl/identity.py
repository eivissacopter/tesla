"""Resolve a Teslalogger car row into its public physical identity.

Bridges the home-server database (VIN + Teslalogger trim badge) to the online
reference brain (battery chronology + vehicle intelligence) so that a car like
``Morty#6`` becomes, to the world, exactly: ``Model Y Long Range, 2024, MIG,
LG 5L NMC, 3D3 / 4D1`` -- and nothing that leads back to the owner.

The online reference modules live in the Streamlit repo. We add that repo to
``sys.path`` so both apps share a single source of reference truth.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, asdict
from typing import Optional

from etl.vin import decode_vin, DecodedVin

# --- Make the shared reference brain importable ------------------------------
# Works in both layouts: split dev (teslatechlocal/etl + teslatechlocal/streamlit_repo)
# and consolidated (repo/etl + repo/src). Pick the first dir that has src/data.
def _find_reference_repo() -> str:
    env = os.environ.get("TESLATECH_REFERENCE_REPO")
    if env:
        return env
    here = os.path.dirname(os.path.dirname(__file__))   # parent of etl/
    for cand in (os.path.join(here, "streamlit_repo"), here, os.path.dirname(here)):
        if os.path.exists(os.path.join(cand, "src", "data", "vehicle_intelligence.py")):
            return cand
    return os.path.join(here, "streamlit_repo")


_REPO = _find_reference_repo()
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from etl import _st_shim  # noqa: E402
_st_shim.install()

from src.data.vehicle_intelligence import VehicleIntelligenceClient  # noqa: E402
from src.data import consumption_constants as _cc  # noqa: E402


def factory_constant(model, trim, drivetrain):
    """Factory consumption (Wh/km) + net capacity (kWh) from the knowledge brain.

    Returns (wh_per_km, capacity_kwh) or (None, None). Picks the matching
    factory constant for the resolved configuration; if several match (wheel
    variants), uses their median Wh/km.
    """
    if not model or not trim:
        return None, None
    try:
        matches = _cc.lookup_constants(model=model, variant=trim, drivetrain=drivetrain)
    except Exception:
        matches = []
    if not matches:
        return None, None
    whs = sorted(fc.constant_wh_km for fc in matches)
    caps = [fc.nominal_capacity_kwh for fc in matches]
    wh = whs[len(whs) // 2]
    return round(float(wh), 0), round(float(caps[0]), 1)


# --- Teslalogger trim badge -> (reference trim, drivetrain) ------------------
# Teslalogger stores a short badge in cars.car_trim_badging. Map it to the
# vocabulary used by the reference rules ('Long Range'/'Performance'/'Standard'
# and 'AWD'/'RWD').
BADGE_MAP = {
    "p74d": ("Performance", "AWD"),
    "74d": ("Long Range", "AWD"),
    "100d": ("Long Range", "AWD"),
    "90d": ("Long Range", "AWD"),
    "74": ("Long Range", "RWD"),
    "62": ("Standard", "RWD"),
    "60": ("Standard", "RWD"),
    "50": ("Standard", "RWD"),
}


@dataclass
class PublicIdentity:
    """Everything the world is allowed to know about a car -- no PII."""
    model: Optional[str]
    trim: Optional[str]
    drivetrain: Optional[str]
    model_year: Optional[int]
    factory: Optional[str]            # MIG / MIC / Fremont / MIA
    pack_label: Optional[str]         # e.g. "79 MIG" / "LG 5L NMC | 79 kWh"
    battery_code: Optional[str]       # e.g. "5L"
    chemistry: Optional[str]          # LFP / NMC / NCA
    front_motor: Optional[str]        # e.g. "3D3"
    rear_motor: Optional[str]         # e.g. "4D1"
    release_family: Optional[str]
    confidence: Optional[str]

    def label(self) -> str:
        bits = [b for b in [self.model, self.trim, self.drivetrain,
                             str(self.model_year) if self.model_year else None,
                             self.factory] if b]
        return " ".join(bits)

    def as_dict(self) -> dict:
        return asdict(self)


def _clean_motor(value):
    """Tidy a reference motor field: drop 'nan', dedupe, keep order."""
    if value is None:
        return None
    s = str(value)
    if s.lower() in ("nan", "none", ""):
        return None
    parts = [p.strip() for p in s.replace(",", "/").split("/")]
    seen, out = set(), []
    for p in parts:
        if p and p.lower() not in ("nan", "none") and p not in seen:
            seen.add(p)
            out.append(p)
    return "/".join(out) if out else None


# Fallback chemistry by (model, trim, factory) when the chronology has no record.
# Tesla Model 3/Y: Standard = LFP; Long Range/Performance = NMC, except early
# US (Fremont) packs which are NCA (Panasonic).
def _fallback_chemistry(model, trim, factory, year):
    if not model:
        return None
    # Early Fremont 18650/2170 packs were Panasonic NCA across all trims.
    if factory == "Fremont" and model in ("Model 3", "Model Y"):
        return "NCA"
    if not trim:
        return None
    if trim == "Standard":
        return "LFP"
    if trim in ("Long Range", "Performance"):
        return "NMC"
    return None


def _badge_to_trim_drive(badge: Optional[str], vin_drive_hint: Optional[str]):
    if badge:
        key = str(badge).strip().lower()
        if key in BADGE_MAP:
            return BADGE_MAP[key]
        # Free-text badges like "M3 LR P" / "Y SR" -> parse keywords.
        if " p" in f" {key}" or key.endswith("p") or "perf" in key:
            return ("Performance", "AWD")
        if "lr" in key or "long" in key:
            return ("Long Range", vin_drive_hint or "AWD")
        if "sr" in key or "standard" in key:
            return ("Standard", "RWD")
    # Fall back to the VIN drivetrain hint with an unknown trim.
    return (None, vin_drive_hint)


def resolve_identity(
    vin: Optional[str],
    trim_badge: Optional[str] = None,
    car_type: Optional[str] = None,
    first_seen=None,
    market: str = "Europe",
) -> PublicIdentity:
    """Resolve a car into its public identity using VIN + badge + reference brain."""
    decoded: DecodedVin = decode_vin(vin)

    model = decoded.model
    if model is None and car_type:
        model = {"model3": "Model 3", "modely": "Model Y",
                 "models": "Model S", "modelx": "Model X"}.get(str(car_type).lower())

    trim, drivetrain = _badge_to_trim_drive(trim_badge, decoded.drivetrain_hint)

    year = decoded.model_year
    quarter = None
    if first_seen is not None:
        try:
            quarter = (first_seen.month - 1) // 3 + 1
        except Exception:
            quarter = None

    summary = {}
    if model:
        try:
            res = VehicleIntelligenceClient.resolve_vehicle(
                market=market, model=model, trim=trim, drivetrain=drivetrain,
                year=year, quarter=quarter,
            )
            summary = res.get("summary", {}) or {}
        except Exception:
            summary = {}

    factory = decoded.factory_code or summary.get("Plant")
    chemistry = summary.get("Chemistry")
    if not chemistry or str(chemistry).lower() in ("nan", "none", "unknown"):
        chemistry = _fallback_chemistry(model, trim, factory, year)

    return PublicIdentity(
        model=model,
        trim=trim,
        drivetrain=drivetrain,
        model_year=year,
        factory=factory,
        pack_label=summary.get("Likely Pack"),
        battery_code=summary.get("Battery Code"),
        chemistry=chemistry,
        front_motor=_clean_motor(summary.get("Front Motor")),
        rear_motor=_clean_motor(summary.get("Rear Motor")),
        release_family=summary.get("Release Family"),
        confidence=summary.get("Confidence"),
    )
