"""Public contribution store -- the replacement for Google Sheets.

One small table of owner-submitted battery datapoints. The backend is chosen by
a single connection URL so the same code runs in development (a local SQLite
file) and production (managed Postgres on Supabase/Neon):

    resolution: st.secrets['connections']['postgres']['url']
             -> env TESLATECH_DB_URL
             -> local sqlite file data/contributions.db

Submissions are sanity-checked against ``Config.SANITY_BOUNDS`` before insert so
the public dataset stays clean, exactly like the survey pipeline does on read.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from sqlalchemy import (Column, DateTime, Float, Integer, MetaData, String,
                        Table, Text, create_engine, insert, select)

from src.config import Config

_metadata = MetaData()
submissions = Table(
    "contributions", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("submitted_at", DateTime),
    Column("username", String(80)),
    Column("model", String(40)),
    Column("trim", String(40)),
    Column("drivetrain", String(10)),
    Column("battery", String(60)),
    Column("chemistry", String(10)),
    Column("origin", String(40)),
    Column("model_year", Integer),
    Column("age_months", Float),
    Column("odometer_km", Float),
    Column("rated_range_km", Float),
    Column("capacity_net_kwh", Float),
    Column("cycles", Float),
    Column("daily_soc_limit", Float),
    Column("dc_ratio", Float),
    Column("degradation_pct", Float),
    Column("software", String(40)),
    Column("notes", Text),
    Column("source", String(20)),   # 'survey' | 'questionnaire' | 'fleet-sync'
)

# Map a submission field to the sanity-bound key in Config.
_BOUND_KEY = {
    "age_months": "Age", "odometer_km": "Odometer", "rated_range_km": "Rated Range",
    "capacity_net_kwh": "Capacity Net Now", "cycles": "Cycles",
    "daily_soc_limit": "Daily SOC Limit", "dc_ratio": "DC Ratio",
    "degradation_pct": "Degradation",
}


def _db_url() -> str:
    try:
        import streamlit as st
        conns = st.secrets.get("connections", {})
        if "postgres" in conns and "url" in conns["postgres"]:
            return conns["postgres"]["url"]
    except Exception:
        pass
    if os.environ.get("TESLATECH_DB_URL"):
        return os.environ["TESLATECH_DB_URL"]
    here = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.makedirs(os.path.join(here, "data"), exist_ok=True)
    return "sqlite:///" + os.path.join(here, "data", "contributions.db")


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_db_url(), future=True)
        _metadata.create_all(_engine)
    return _engine


def validate(entry: dict) -> list[str]:
    """Return a list of human-readable problems (empty == valid)."""
    errors = []
    if not entry.get("model"):
        errors.append("Model is required.")
    for field, key in _BOUND_KEY.items():
        val = entry.get(field)
        if val is None or val == "":
            continue
        try:
            v = float(val)
        except (TypeError, ValueError):
            errors.append(f"{field} must be a number.")
            continue
        lo, hi = Config.SANITY_BOUNDS[key]
        if not (lo <= v <= hi):
            errors.append(f"{field} {v} is outside the plausible range [{lo}, {hi}].")
    return errors


def _supabase():
    """Return the supabase_client module if configured, else None."""
    try:
        from src.data import supabase_client
        if supabase_client.enabled():
            return supabase_client
    except Exception:
        pass
    return None


_COLS = [c for c in submissions.columns.keys() if c not in ("id",)]


def add_submission(entry: dict, source: str = "questionnaire") -> tuple[bool, list[str]]:
    errors = validate(entry)
    if errors:
        return False, errors
    payload = {k: entry.get(k) for k in submissions.columns.keys() if k in entry}
    payload["source"] = source

    sb = _supabase()
    if sb is not None:
        sb.insert("contributions", payload)   # submitted_at defaulted by the DB
        return True, []

    payload["submitted_at"] = datetime.now(timezone.utc)
    with _get_engine().begin() as conn:
        conn.execute(insert(submissions).values(**payload))
    return True, []


def get_submissions(username: Optional[str] = None, limit: int = 5000) -> pd.DataFrame:
    sb = _supabase()
    if sb is not None:
        params = {"select": "*", "order": "submitted_at.desc", "limit": str(limit)}
        if username:
            params["username"] = f"eq.{username}"
        try:
            return pd.DataFrame(sb.select("contributions", params))
        except Exception:
            return pd.DataFrame()   # table not created yet / transient

    stmt = select(submissions).order_by(submissions.c.submitted_at.desc()).limit(limit)
    if username:
        stmt = stmt.where(submissions.c.username == username)
    with _get_engine().connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return pd.DataFrame(rows)


def count_submissions() -> int:
    sb = _supabase()
    if sb is not None:
        try:
            import requests
            url, key = sb._cfg()
            resp = requests.get(f"{url}/rest/v1/contributions", params={"select": "id"},
                                headers={"apikey": key, "Authorization": f"Bearer {key}",
                                         "Prefer": "count=exact", "Range": "0-0"}, timeout=15)
            cr = resp.headers.get("content-range", "")
            return int(cr.split("/")[-1]) if "/" in cr else len(resp.json())
        except Exception:
            return 0
    try:
        with _get_engine().connect() as conn:
            from sqlalchemy import func
            return int(conn.execute(select(func.count()).select_from(submissions)).scalar() or 0)
    except Exception:
        return 0
