"""Loader for the anonymized telemetry cloud (detailed scatter explorer).

Larger than the fleet summary, so it loads from object storage (R2) by URL in
production, or a bundled local file in development. Cached aggressively.

Resolution: st.secrets['telemetry']['url'] / env TESLATECH_TELEMETRY_URL
         -> local data/telemetry.json / artifacts/telemetry.json
"""

from __future__ import annotations

import json
import os
from typing import Optional

import pandas as pd

try:
    import streamlit as st
    _cache = st.cache_data
except Exception:
    def _cache(*a, **k):
        def wrap(f):
            return f
        return wrap if not (a and callable(a[0])) else a[0]

_LOCAL = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "telemetry.json"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "artifacts", "telemetry.json"),
]


def _url() -> Optional[str]:
    try:
        import streamlit as st
        if "telemetry" in st.secrets and "url" in st.secrets["telemetry"]:
            return st.secrets["telemetry"]["url"]
    except Exception:
        pass
    return os.environ.get("TESLATECH_TELEMETRY_URL")


@_cache(ttl=3600)
def load_telemetry() -> dict:
    url = _url()
    raw = None
    # 1) Supabase REST (fleet_telemetry table)
    try:
        from src.data.supabase_client import enabled as _sb_enabled, select as _sb_select
        if raw is None and _sb_enabled():
            rows = _sb_select("fleet_telemetry",
                              {"select": "payload", "order": "published_at.desc", "limit": "1"})
            if rows:
                raw = rows[0].get("payload")
    except Exception:
        raw = None
    # 2) explicit URL (object storage / R2 — best for the larger telemetry file)
    if raw is None and url:
        import requests
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        raw = r.json()
    # 3) bundled/local
    if raw is None:
        for p in _LOCAL:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                break
    if not raw:
        return {"labels": {}, "telemetry": {}, "frames": {}, "meta": {}}
    frames = {car: pd.DataFrame(rows) for car, rows in raw.get("telemetry", {}).items()}
    return {
        "labels": raw.get("labels", {}),
        "telemetry": raw.get("telemetry", {}),
        "frames": frames,
        "meta": {"data_version": raw.get("data_version"), "n_cars": raw.get("n_cars", len(frames)),
                 "points": raw.get("points", 0)},
    }
