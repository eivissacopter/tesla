"""Loader for the anonymized real-world fleet artifact.

This is the public app's *read path*. The home-server ETL publishes a small,
anonymized ``fleet.json`` (identity + SOH + charging, no PII) once a week. The
app loads it from whichever source is configured and caches it, so visitor
traffic never touches the private server:

Resolution order (first that works wins):
1. ``st.secrets['fleet']['url']`` or env ``TESLATECH_FLEET_URL`` -- a published
   artifact (Cloudflare R2 / any HTTPS object store). Recommended for prod.
2. A bundled/local ``data/fleet.json`` -- used in development and as a fallback.

Returns a tidy :class:`pandas.DataFrame` plus the raw SOH time series.
"""

from __future__ import annotations

import json
import os
from typing import Optional

import pandas as pd

try:
    import streamlit as st
    _cache = st.cache_data
except Exception:  # headless / tests
    def _cache(*a, **k):
        def wrap(f):
            return f
        return wrap if not (a and callable(a[0])) else a[0]

_LOCAL_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "fleet.json"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "artifacts", "fleet.json"),
]


def _artifact_url() -> Optional[str]:
    try:
        import streamlit as st
        if "fleet" in st.secrets and "url" in st.secrets["fleet"]:
            return st.secrets["fleet"]["url"]
    except Exception:
        pass
    return os.environ.get("TESLATECH_FLEET_URL")


def _db_url() -> Optional[str]:
    try:
        import streamlit as st
        conns = st.secrets.get("connections", {})
        if "postgres" in conns and "url" in conns["postgres"]:
            return conns["postgres"]["url"]
    except Exception:
        pass
    return os.environ.get("TESLATECH_DB_URL")


def _load_from_postgres(url: str) -> Optional[dict]:
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url, future=True)
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT payload FROM fleet_artifacts ORDER BY published_at DESC LIMIT 1"
            )).first()
        if row and row[0]:
            return json.loads(row[0])
    except Exception:
        return None
    return None


def _load_raw() -> dict:
    # 1) Supabase REST (publishable key) -- the default cloud read path
    try:
        from src.data.supabase_client import enabled as _sb_enabled, latest_fleet_artifact
        if _sb_enabled():
            payload = latest_fleet_artifact()
            if payload:
                return payload
    except Exception:
        pass
    # 2) explicit artifact URL (object storage / R2)
    url = _artifact_url()
    if url:
        import requests
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.json()
    # 3) managed Postgres (fleet_artifacts table)
    db = _db_url()
    if db:
        payload = _load_from_postgres(db)
        if payload:
            return payload
    # 3) bundled/local artifact (dev + fallback)
    for path in _LOCAL_CANDIDATES:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return {"data_version": None, "n_cars": 0, "fleet": [], "soh_series": {}}


@_cache(ttl=3600)
def load_fleet() -> dict:
    """Return {'meta', 'df', 'soh_series'} for the anonymized fleet."""
    raw = _load_raw()
    df = pd.DataFrame(raw.get("fleet", []))
    return {
        "meta": {"data_version": raw.get("data_version"), "n_cars": raw.get("n_cars", len(df))},
        "df": df,
        "soh_series": raw.get("soh_series", {}),
        "temp_curves": raw.get("temp_curves", {}),
    }
