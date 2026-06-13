"""Publish the anonymized fleet artifact to the cloud (the weekly push).

Targets (choose with --target, repeatable):
* ``s3``       -- upload fleet.json/parquet to an S3-compatible bucket
                  (Cloudflare R2 recommended). Streamlit reads it by URL, cached.
                  Cheapest + most traffic-efficient; raw data never leaves home.
* ``postgres`` -- upsert the artifact JSON into a ``fleet_artifacts`` table
                  (one row per data_version) on managed Postgres (Supabase/Neon).
                  Use this if you'd rather keep one datastore for everything.

This runs on the home server after ``export_fleet``. It pushes a few hundred KB
once a week -- not live traffic.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from sqlalchemy import (Column, DateTime, MetaData, String, Table, Text,
                        create_engine, text)

_metadata = MetaData()
fleet_artifacts = Table(
    "fleet_artifacts", _metadata,
    Column("data_version", String(40), primary_key=True),
    Column("published_at", DateTime),
    Column("payload", Text),
)


def publish_s3(artifact_path: str) -> str:
    """Upload the artifact to an S3-compatible bucket. Returns the object URL."""
    import boto3
    endpoint = os.environ["S3_ENDPOINT"]          # e.g. https://<acct>.r2.cloudflarestorage.com
    bucket = os.environ["S3_BUCKET"]
    key = os.environ.get("S3_KEY", "fleet.json")
    public_base = os.environ.get("S3_PUBLIC_BASE")  # e.g. https://pub-xxxx.r2.dev
    s3 = boto3.client(
        "s3", endpoint_url=endpoint,
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("S3_REGION", "auto"),
    )
    with open(artifact_path, "rb") as f:
        s3.put_object(Bucket=bucket, Key=key, Body=f.read(),
                      ContentType="application/json", CacheControl="public, max-age=3600")
    url = f"{public_base.rstrip('/')}/{key}" if public_base else f"{endpoint}/{bucket}/{key}"
    return url


def publish_postgres(artifact_path: str) -> str:
    """Upsert the artifact JSON into fleet_artifacts on the configured database."""
    url = os.environ.get("TESLATECH_DB_URL")
    if not url:
        raise RuntimeError("TESLATECH_DB_URL not set")
    with open(artifact_path, "r", encoding="utf-8") as f:
        payload = f.read()
    data_version = json.loads(payload).get("data_version") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    engine = create_engine(url, future=True)
    _metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fleet_artifacts WHERE data_version = :v"), {"v": data_version})
        conn.execute(fleet_artifacts.insert().values(
            data_version=data_version, published_at=datetime.now(timezone.utc), payload=payload))
    return f"postgres:fleet_artifacts/{data_version}"


def publish_supabase(artifact_path: str, table: str = "fleet_artifacts") -> str:
    """Upsert an artifact into a Supabase table via REST using the SECRET key.

    Needs SUPABASE_URL + SUPABASE_SECRET_KEY (service_role; bypasses RLS).
    The target table must exist (deploy/supabase_schema.sql).
    """
    import requests
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SECRET_KEY"]
    from etl.jsonsafe import clean
    with open(artifact_path, "r", encoding="utf-8") as f:
        payload = clean(json.load(f))
    data_version = payload.get("data_version") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = {"data_version": data_version,
           "published_at": datetime.now(timezone.utc).isoformat(),
           "payload": payload}
    resp = requests.post(
        f"{url}/rest/v1/{table}",
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        json=row, timeout=60)
    resp.raise_for_status()
    return f"supabase:{table}/{data_version}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default="artifacts/fleet.json")
    ap.add_argument("--table", default="fleet_artifacts",
                    help="Supabase/Postgres table for this artifact")
    ap.add_argument("--target", action="append",
                    choices=["s3", "postgres", "supabase"], required=True)
    args = ap.parse_args()
    for tgt in args.target:
        if tgt == "s3":
            print("published to S3:", publish_s3(args.artifact))
        elif tgt == "postgres":
            print("published to Postgres:", publish_postgres(args.artifact))
        elif tgt == "supabase":
            print("published to Supabase:", publish_supabase(args.artifact, table=args.table))


if __name__ == "__main__":
    main()
