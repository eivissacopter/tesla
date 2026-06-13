"""Minimal Supabase REST (PostgREST) client for the public app.

The app talks to Supabase with the *publishable* (anon) key only — never the
secret. Row-level security (see deploy/supabase_schema.sql) lets anon read the
fleet artifact and read/insert questionnaire rows, nothing else.

Config resolution: st.secrets['supabase'] {url, publishable_key}  ->  env
SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY. If neither is present, ``enabled()`` is
False and callers fall back to their local backend.
"""

from __future__ import annotations

import os
from typing import Optional

import requests


def _cfg() -> tuple[Optional[str], Optional[str]]:
    url = key = None
    try:
        import streamlit as st
        if "supabase" in st.secrets:
            sb = st.secrets["supabase"]
            url = sb.get("url")
            key = sb.get("publishable_key") or sb.get("anon_key") or sb.get("key")
    except Exception:
        pass
    url = url or os.environ.get("SUPABASE_URL")
    key = key or os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    return (url.rstrip("/") if url else None, key)


def enabled() -> bool:
    url, key = _cfg()
    return bool(url and key)


def _headers(key: str, extra: Optional[dict] = None) -> dict:
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h


def select(table: str, params: dict, timeout: int = 20) -> list[dict]:
    url, key = _cfg()
    if not (url and key):
        return []
    resp = requests.get(f"{url}/rest/v1/{table}", headers=_headers(key), params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def insert(table: str, row: dict, timeout: int = 20) -> bool:
    url, key = _cfg()
    if not (url and key):
        return False
    resp = requests.post(f"{url}/rest/v1/{table}", headers=_headers(key, {"Prefer": "return=minimal"}),
                         json=row, timeout=timeout)
    resp.raise_for_status()
    return True


def latest_fleet_artifact() -> Optional[dict]:
    rows = select("fleet_artifacts",
                  {"select": "payload", "order": "published_at.desc", "limit": "1"})
    if rows:
        return rows[0].get("payload")
    return None
