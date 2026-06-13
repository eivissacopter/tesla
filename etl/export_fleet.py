"""Home-server ETL: read Teslalogger -> anonymized public fleet artifact.

Runs (weekly) where the database is reachable. Pushes heavy aggregation into
SQL, resolves each car's public identity via the shared knowledge brain,
computes scientific metrics (SOH, charging), strips all PII, and writes a small
artifact (Parquet + JSON) that the public Streamlit app consumes. Raw rows and
identity never leave the server.

Usage (dev, via SSH):
    SSH_PASS=... TESLATECH_ANON_SALT=... \
        python -m etl.export_fleet --out artifacts/

Usage (prod, on server, direct DB):
    TESLATECH_DB_MODE=direct DB_HOST=teslalogger-db TESLATECH_ANON_SALT=... \
        python -m etl.export_fleet --out /data/teslatech/
"""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Optional

import pandas as pd

from etl.db import make_reader_from_env
from etl.identity import resolve_identity, factory_constant
from etl.analytics import compute_soh, compute_charging, compute_efficiency
from etl.anonymize import public_car_id, assert_clean
from etl.labels import build_car_labels

# Cars whose telemetry is not a real, distinct vehicle (test rigs, imports with
# duplicated VINs). Excluded from the public set.
EXCLUDE_NAME_PATTERNS = (re.compile(r"test", re.I),)

# Fallback design capacities (kWh) when the pack label has no number.
FALLBACK_CAPACITY = {
    ("Model Y", "Long Range"): 79.0,
    ("Model Y", "Performance"): 79.0,
    ("Model Y", "Standard"): 60.0,
    ("Model 3", "Long Range"): 79.0,
    ("Model 3", "Performance"): 82.0,
    ("Model 3", "Standard"): 62.0,
}


def _design_capacity(pack_label: Optional[str], model, trim) -> Optional[float]:
    if pack_label:
        m = re.search(r"(\d{2,3}(?:\.\d)?)", str(pack_label))
        if m:
            val = float(m.group(1))
            if 30 <= val <= 130:
                return val
    return FALLBACK_CAPACITY.get((model, trim))


def _excluded(name: Optional[str]) -> bool:
    if not name:
        return False
    return any(p.search(name) for p in EXCLUDE_NAME_PATTERNS)


def build_fleet(reader) -> pd.DataFrame:
    cars = reader.read_sql(
        "SELECT id, display_name, vin, car_type, car_trim_badging, "
        "db_wh_tr, db_wh_tr_count FROM cars ORDER BY id"
    )
    odo = reader.read_sql(
        "SELECT CarID, MIN(Datum) first_seen, MAX(Datum) last_seen, "
        "MIN(odometer) odo_min, MAX(odometer) odo_max "
        "FROM pos WHERE odometer IS NOT NULL GROUP BY CarID"
    )
    can71 = reader.read_sql(
        "SELECT CarID, Datum, val FROM can WHERE id=71 AND val > 0 ORDER BY CarID, Datum"
    )
    sessions = reader.read_sql(
        "SELECT CarID, charge_energy_added, max_charger_power, fast_charger_present "
        "FROM chargingstate"
    )
    trips = reader.read_sql(
        "SELECT CarID, SUM(km_diff) km, SUM(consumption_kWh) kwh, AVG(outside_temp_avg) avg_temp "
        "FROM trip WHERE km_diff > 1 AND consumption_kWh > 0 GROUP BY CarID"
    )
    trips_temp = reader.read_sql(
        "SELECT CarID, ROUND(outside_temp_avg/5)*5 tbin, SUM(km_diff) km, SUM(consumption_kWh) kwh "
        "FROM trip WHERE km_diff > 1 AND consumption_kWh > 0 AND outside_temp_avg IS NOT NULL "
        "GROUP BY CarID, tbin"
    )

    odo = odo.set_index("CarID") if not odo.empty else odo
    trips = trips.set_index("CarID") if not trips.empty else trips
    records = []
    seen_vins = set()

    for _, car in cars.iterrows():
        cid = int(car["id"])
        name = car.get("display_name")
        vin = car.get("vin")
        if _excluded(name):
            continue
        # Drop duplicate-VIN rigs (keep the first real occurrence).
        vkey = (str(vin).strip().upper() if isinstance(vin, str) else None)
        if vkey and vkey in seen_vins:
            continue
        if vkey:
            seen_vins.add(vkey)

        first_seen = last_seen = None
        odo_km = None
        if not odo.empty and cid in odo.index:
            row = odo.loc[cid]
            first_seen = pd.to_datetime(row.get("first_seen"), errors="coerce")
            last_seen = pd.to_datetime(row.get("last_seen"), errors="coerce")
            try:
                odo_km = float(row.get("odo_max")) if pd.notna(row.get("odo_max")) else None
            except Exception:
                odo_km = None

        pid = resolve_identity(
            vin=vin, trim_badge=car.get("car_trim_badging"),
            car_type=car.get("car_type"), first_seen=first_seen,
        )
        design = _design_capacity(pid.pack_label, pid.model, pid.trim)

        car_can71 = can71[can71["CarID"] == cid] if not can71.empty else can71
        soh = compute_soh(car_can71, design)

        car_sessions = sessions[sessions["CarID"] == cid] if not sessions.empty else sessions
        charging = compute_charging(car_sessions)

        factory_wh, _factory_cap = factory_constant(pid.model, pid.trim, pid.drivetrain)
        trips_overall = trips.loc[cid] if (not trips.empty and cid in trips.index) else None
        car_trips_temp = trips_temp[trips_temp["CarID"] == cid] if not trips_temp.empty else trips_temp
        eff = compute_efficiency(trips_overall, car_trips_temp, factory_wh)

        age_months = None
        if first_seen is not None and last_seen is not None and pd.notna(first_seen) and pd.notna(last_seen):
            age_months = round((last_seen - first_seen).days / 30.44, 1)

        wh_km = None
        try:
            raw = car.get("db_wh_tr")
            if pd.notna(raw) and float(raw) > 0:
                v = float(raw)
                # Teslalogger stores this as kWh/km (~0.15); normalise to Wh/km.
                if v < 5:
                    v *= 1000.0
                if 80 <= v <= 350:  # plausible real-world band
                    wh_km = round(v, 0)
        except Exception:
            pass

        rec = {
            "car": public_car_id(vin, fallback=str(cid)),
            # --- public identity ---
            "model": pid.model,
            "trim": pid.trim,
            "drivetrain": pid.drivetrain,
            "model_year": pid.model_year,
            "factory": pid.factory,
            "pack": pid.pack_label,
            "battery_code": pid.battery_code,
            "chemistry": pid.chemistry,
            "front_motor": pid.front_motor,
            "rear_motor": pid.rear_motor,
            "release_family": pid.release_family,
            "id_confidence": pid.confidence,
            # --- lifetime ---
            "odometer_km": round(odo_km) if odo_km else None,
            "age_months": age_months,
            "logging_until": last_seen.strftime("%Y-%m") if last_seen is not None and pd.notna(last_seen) else None,
            # --- SOH ---
            "design_kwh": soh.design_capacity_kwh,
            "current_kwh": soh.current_kwh,
            "soh_pct": soh.soh_pct,
            "degradation_pct": soh.degradation_pct,
            "soh_samples": soh.n_samples,
            # --- efficiency ---
            "wh_per_km": wh_km,                       # Teslalogger rated constant
            "real_wh_per_km": eff.real_wh_per_km,     # measured, km-weighted from trips
            "real_km": eff.real_km,
            "factory_wh_per_km": eff.factory_wh_per_km,
            "vs_factory_pct": eff.vs_factory_pct,
            "avg_trip_temp_c": eff.avg_temp_c,
            # --- charging ---
            "charge_sessions": charging.sessions,
            "charge_energy_kwh": charging.total_energy_kwh,
            "dc_share_pct": charging.dc_energy_share_pct,
            "max_charge_kw": charging.max_charge_power_kw,
        }
        assert_clean(rec)
        rec["_soh_monthly"] = soh.monthly        # series for charts (no PII)
        rec["_temp_curve"] = eff.temp_curve      # efficiency vs temperature
        records.append(rec)

    # Readable, de-duplicated labels in place of the opaque car id.
    car_labels = build_car_labels(records)
    for rec in records:
        rec["label"] = car_labels.get(rec["car"], rec["car"])

    return pd.DataFrame(records)


def write_artifact(fleet: pd.DataFrame, out_dir: str, data_version: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    flat = fleet.drop(columns=["_soh_monthly", "_temp_curve"], errors="ignore")
    parquet_path = os.path.join(out_dir, "fleet.parquet")
    try:
        flat.to_parquet(parquet_path, index=False)
    except Exception:
        parquet_path = None
    series = {row["car"]: row.get("_soh_monthly", []) for _, row in fleet.iterrows()}
    temp_curves = {row["car"]: row.get("_temp_curve", []) for _, row in fleet.iterrows()}
    car_labels = {row["car"]: row.get("label", row["car"]) for _, row in fleet.iterrows()}
    payload = {
        "data_version": data_version,
        "n_cars": int(len(fleet)),
        "fleet": flat.where(pd.notnull(flat), None).to_dict(orient="records"),
        "soh_series": series,
        "temp_curves": temp_curves,
        "car_labels": car_labels,
    }
    from etl.jsonsafe import clean
    json_path = os.path.join(out_dir, "fleet.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(clean(payload), f, indent=2, default=str, allow_nan=False)
    return {"json": json_path, "parquet": parquet_path, "n_cars": len(fleet)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts", help="output directory")
    ap.add_argument("--version", default=None, help="data_version stamp (default: today)")
    args = ap.parse_args()
    version = args.version or pd.Timestamp.today().strftime("%Y-%m-%d")

    reader = make_reader_from_env()
    fleet = build_fleet(reader)
    info = write_artifact(fleet, args.out, version)
    print(f"Wrote {info['n_cars']} cars -> {info['json']}"
          + (f" + {info['parquet']}" if info["parquet"] else ""))
    return fleet


if __name__ == "__main__":
    main()
