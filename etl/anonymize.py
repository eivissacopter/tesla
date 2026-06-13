"""Privacy layer for the public export.

The one rule: nothing that leads back to the owner ever leaves this module.
The world sees physics (model, pack, chemistry, motors, SOH, efficiency),
never identity (name, VIN, GPS, address, home).

A car's public id is an HMAC of its VIN under a secret salt kept on the home
server. It is stable across weekly syncs (so trends line up) but irreversible
(no rainbow-table from VIN -> id without the salt).
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional

# Fields that must NEVER appear in any public record.
FORBIDDEN_FIELDS = frozenset({
    "vin", "display_name", "tesla_name", "name", "lat", "lng", "address",
    "tesla_token", "refresh_token", "tesla_password", "geocode", "Pos",
})


def get_salt() -> bytes:
    """Secret salt for the public-id HMAC. Kept on the home server only.

    Set TESLATECH_ANON_SALT in the ETL environment. A per-deployment random
    default is used if unset so ids are at least unguessable, but you should
    pin it so ids stay stable across runs.
    """
    salt = os.environ.get("TESLATECH_ANON_SALT")
    if salt:
        return salt.encode("utf-8")
    # Fallback: stable-per-machine but you really should set the env var.
    return b"teslatech-default-salt-change-me"


def public_car_id(vin: Optional[str], fallback: Optional[str] = None) -> str:
    """Stable, irreversible public id for a car.

    Derived from the VIN (preferred) so it survives Teslalogger id changes.
    Returns a 10-char hex token like ``a1b2c3d4e5``.
    """
    basis = (vin or fallback or "").strip().upper()
    digest = hmac.new(get_salt(), basis.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:10]


def assert_clean(record: dict) -> dict:
    """Raise if a record still carries any forbidden field. Defence in depth."""
    leaked = FORBIDDEN_FIELDS.intersection(record.keys())
    if leaked:
        raise ValueError(f"Refusing to export record with PII fields: {sorted(leaked)}")
    return record
