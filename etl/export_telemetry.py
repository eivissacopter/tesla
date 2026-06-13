"""Home-server ETL: anonymized per-car telemetry cloud for the scatter explorer.

Produces ``telemetry.json`` -- a downsampled, time-stripped sample of the raw
CAN signals per anonymized car. Kept separate from ``fleet.json`` because it is
larger and only the explorer page needs it.
"""

from __future__ import annotations

import argparse
import json
import os
import re

import pandas as pd

from etl.db import make_reader_from_env
from etl.telemetry import build_telemetry, SIGNAL_LABELS
from etl.anonymize import public_car_id
from etl.identity import resolve_identity
from etl.labels import build_car_labels

EXCLUDE_NAME = re.compile(r"test", re.I)


def _car_map(reader) -> tuple[dict[int, str], dict[str, str]]:
    """Return (carid -> hash) and (hash -> readable label)."""
    cars = reader.read_sql(
        "SELECT id, display_name, vin, car_type, car_trim_badging FROM cars ORDER BY id")
    mapping, seen, id_records = {}, set(), []
    for _, c in cars.iterrows():
        name, vin = c.get("display_name"), c.get("vin")
        if name and EXCLUDE_NAME.search(str(name)):
            continue
        vkey = str(vin).strip().upper() if isinstance(vin, str) else None
        if vkey and vkey in seen:
            continue
        if vkey:
            seen.add(vkey)
        cid = int(c["id"])
        car_hash = public_car_id(vin, fallback=str(cid))
        mapping[cid] = car_hash
        pid = resolve_identity(vin=vin, trim_badge=c.get("car_trim_badging"),
                               car_type=c.get("car_type"))
        id_records.append({"car": car_hash, "model": pid.model, "trim": pid.trim,
                           "drivetrain": pid.drivetrain, "model_year": pid.model_year,
                           "factory": pid.factory})
    return mapping, build_car_labels(id_records)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--bin-seconds", type=int, default=20)
    ap.add_argument("--max-points", type=int, default=3000)
    ap.add_argument("--version", default=None)
    args = ap.parse_args()
    version = args.version or pd.Timestamp.today().strftime("%Y-%m-%d")

    reader = make_reader_from_env()
    car_map, car_labels = _car_map(reader)
    telem = build_telemetry(reader, car_map, days=args.days,
                            bin_seconds=args.bin_seconds, max_points=args.max_points)

    os.makedirs(args.out, exist_ok=True)
    payload = {
        "data_version": version,
        "labels": SIGNAL_LABELS,
        "car_labels": {c: car_labels.get(c, c) for c in telem},
        "n_cars": len(telem),
        "points": sum(len(v) for v in telem.values()),
        "telemetry": telem,
    }
    from etl.jsonsafe import clean
    path = os.path.join(args.out, "telemetry.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean(payload), f, separators=(",", ":"), default=str, allow_nan=False)
    print(f"Wrote telemetry for {len(telem)} cars, {payload['points']} points -> {path}")


if __name__ == "__main__":
    main()
