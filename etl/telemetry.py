"""Extract an anonymized, downsampled telemetry cloud per car.

For the detailed scatter explorer (power / torque vs SOC vs cell temperature),
the public app needs the *relationships* between signals — not the time series.
So we bin the raw CAN signals to a few-second grid, align them, strip the
timestamp entirely, and downsample to a few thousand points per car. What
survives is pure physics (SOC, temp, power, torque…) with no time or location —
nothing that could re-identify a drive.

Signal ids are the official Teslalogger/ScanMyTesla ids
(https://teslalogger.de/en/docs/extras/signalIds/).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# id -> (column, unit). Confirmed against the Teslalogger signal-id docs.
SIGNALS = {
    23: ("soc", "%"),
    2: ("cell_temp", "°C"),
    29: ("max_discharge_kw", "kW"),
    28: ("max_charge_kw", "kW"),
    43: ("battery_power_kw", "kW"),
    30: ("battery_voltage", "V"),
    44: ("battery_current", "A"),
    405: ("front_power_kw", "kW"),
    415: ("rear_power_kw", "kW"),
    400: ("front_torque_nm", "Nm"),
    403: ("rear_torque_nm", "Nm"),
    442: ("speed_kmh", "km/h"),
}

# Physically plausible ranges per signal; out-of-range bins are glitches.
PLAUSIBLE = {
    "soc": (0, 100),
    "cell_temp": (-40, 80),
    "max_discharge_kw": (0, 800),
    "max_charge_kw": (0, 400),
    "battery_power_kw": (-400, 800),
    "battery_voltage": (0, 460),
    "battery_current": (-1500, 1500),
    "front_power_kw": (-300, 400),
    "rear_power_kw": (-300, 600),
    "front_torque_nm": (-600, 600),
    "rear_torque_nm": (-900, 900),
    "speed_kmh": (0, 320),
}

# Friendly labels for the UI.
SIGNAL_LABELS = {
    "soc": "State of charge (%)",
    "cell_temp": "Cell temperature (°C)",
    "max_discharge_kw": "Max discharge power (kW)",
    "max_charge_kw": "Max charge power (kW)",
    "battery_power_kw": "Battery power (kW)",
    "battery_voltage": "Battery voltage (V)",
    "battery_current": "Battery current (A)",
    "front_power_kw": "Front motor power (kW)",
    "rear_power_kw": "Rear motor power (kW)",
    "front_torque_nm": "Front motor torque (Nm)",
    "rear_torque_nm": "Rear motor torque (Nm)",
    "speed_kmh": "Speed (km/h)",
}


def extract_car_telemetry(
    reader, car_id: int, *, days: int = 365, bin_seconds: int = 20,
    max_points: int = 3000, since: str | None = None,
) -> pd.DataFrame:
    """Return a downsampled, time-stripped wide telemetry frame for one car.

    ``since`` is an explicit 'YYYY-MM-DD' lower bound (preferred; computed once
    from each car's last activity). If omitted, falls back to a correlated
    subquery anchored to the car's own MAX(Datum).
    """
    ids = ",".join(str(i) for i in SIGNALS)
    if since:
        date_clause = f"AND Datum > '{since}'"
    elif days:
        date_clause = (
            f"AND Datum > DATE_SUB((SELECT MAX(Datum) FROM can c2 WHERE c2.CarID={int(car_id)}), "
            f"INTERVAL {int(days)} DAY)"
        )
    else:
        date_clause = ""
    q = (
        f"SELECT FLOOR(UNIX_TIMESTAMP(Datum)/{int(bin_seconds)}) b, id, AVG(val) v "
        f"FROM can WHERE CarID={int(car_id)} AND id IN ({ids}) {date_clause} "
        f"GROUP BY b, id"
    )
    long = reader.read_sql(q)
    if long is None or long.empty:
        return pd.DataFrame()
    long["id"] = pd.to_numeric(long["id"], errors="coerce")
    long["v"] = pd.to_numeric(long["v"], errors="coerce")
    wide = long.pivot_table(index="b", columns="id", values="v", aggfunc="mean")
    wide = wide.rename(columns={i: SIGNALS[i][0] for i in SIGNALS if i in wide.columns})
    # Drop physically-impossible glitch values (set out-of-range to NaN).
    for col, (lo, hi) in PLAUSIBLE.items():
        if col in wide.columns:
            wide[col] = wide[col].where((wide[col] >= lo) & (wide[col] <= hi))
    # Light alignment: signals update on >10% change, so fill small gaps across bins.
    wide = wide.sort_index().ffill(limit=3).bfill(limit=1)
    # Keep rows that have SOC and at least one of the headline axes.
    axes = [c for c in ("max_discharge_kw", "battery_power_kw", "rear_power_kw") if c in wide.columns]
    if "soc" not in wide.columns or not axes:
        return pd.DataFrame()
    wide = wide.dropna(subset=["soc"]).dropna(subset=axes, how="all")
    wide = wide.drop(columns=[], errors="ignore").reset_index(drop=True)   # drop the time bin -> anonymized
    if len(wide) > max_points:
        idx = np.linspace(0, len(wide) - 1, max_points).astype(int)
        wide = wide.iloc[idx].reset_index(drop=True)
    return wide.round(2)


def _anchor_dates(reader, car_ids, days: int) -> dict[int, str]:
    """One cheap query: each car's (MAX(Datum) - days) as a 'YYYY-MM-DD' bound."""
    if not days:
        return {}
    ids = ",".join(str(int(c)) for c in car_ids)
    df = reader.read_sql(
        f"SELECT CarID, DATE_SUB(MAX(Datum), INTERVAL {int(days)} DAY) since "
        f"FROM can WHERE CarID IN ({ids}) GROUP BY CarID"
    )
    out = {}
    if df is not None and not df.empty:
        for _, r in df.iterrows():
            try:
                out[int(r["CarID"])] = str(pd.to_datetime(r["since"]).date())
            except Exception:
                pass
    return out


def build_telemetry(reader, car_map: dict[int, str], *, days: int = 365, **kw) -> dict[str, list[dict]]:
    """car_map: {CarID -> public_car_id}. Returns {public_id: [rows...]}.

    Resilient: a per-car query failure (e.g. a transient SSH reset in dev) is
    logged and skipped rather than aborting the whole export.
    """
    out: dict[str, list[dict]] = {}
    anchors = _anchor_dates(reader, list(car_map.keys()), days)
    for cid, public_id in car_map.items():
        try:
            df = extract_car_telemetry(reader, cid, days=days, since=anchors.get(cid), **kw)
        except Exception as e:
            print(f"  [telemetry] car {cid} skipped: {str(e)[:120]}")
            continue
        if not df.empty:
            out[public_id] = df.where(pd.notnull(df), None).to_dict(orient="records")
            print(f"  [telemetry] car {cid}: {len(df)} points")
    return out
