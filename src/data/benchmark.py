"""Benchmark a measured car against references and a population.

Two yardsticks:

1. **Tesla's official retention curve** (``DataProcessor.get_tesla_retention_line``)
   -- the published "expected" degradation at a given mileage. We interpolate it
   and report how far above/below a car sits.
2. **A population distribution** -- the fleet itself today, and the public survey
   cloud once it is connected (pass it as ``population``). We percentile-rank a
   car's SOH against peers at a similar odometer.

Pure pandas/numpy; works the moment any fleet artifact is loaded and scales
unchanged to thousands of survey rows.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from src.utils.data_processing import BatteryDataProcessor


def tesla_expected_soh(odometer_km: float) -> Optional[float]:
    """Tesla's published expected SOH (%) at a given odometer."""
    try:
        odo, retention = BatteryDataProcessor.get_tesla_retention_line()
    except Exception:
        return None
    if odometer_km is None or np.isnan(odometer_km):
        return None
    # retention values are degradation deltas (<=0); SOH = 100 + delta.
    soh_curve = 100.0 + np.asarray(retention, dtype=float)
    odo = np.asarray(odo, dtype=float)
    odometer_km = float(np.clip(odometer_km, odo.min(), odo.max()))
    return float(np.interp(odometer_km, odo, soh_curve))


def _peer_percentile(value: float, peers: pd.Series) -> Optional[float]:
    peers = pd.to_numeric(peers, errors="coerce").dropna()
    if len(peers) < 3 or value is None or np.isnan(value):
        return None
    return round(float((peers < value).mean() * 100), 0)


def benchmark_car(
    df: pd.DataFrame,
    car_id: str,
    population: Optional[pd.DataFrame] = None,
    odo_window_km: float = 20000,
) -> dict:
    """Benchmark one car (by public id) against Tesla + a population.

    ``population`` defaults to ``df``. Returns metrics + a plain-language verdict.
    """
    row = df[df["car"] == car_id]
    if row.empty:
        return {}
    row = row.iloc[0]
    soh = pd.to_numeric(pd.Series([row.get("soh_pct")]), errors="coerce").iloc[0]
    odo = pd.to_numeric(pd.Series([row.get("odometer_km")]), errors="coerce").iloc[0]

    pop = population if population is not None else df
    pop = pop.copy()
    pop["soh_pct"] = pd.to_numeric(pop["soh_pct"], errors="coerce")
    pop["odometer_km"] = pd.to_numeric(pop["odometer_km"], errors="coerce")

    expected = tesla_expected_soh(odo) if pd.notna(odo) else None
    vs_tesla = round(float(soh - expected), 1) if (expected is not None and pd.notna(soh)) else None

    # Percentile among peers at a similar odometer (fall back to whole population).
    peers = pop
    if pd.notna(odo):
        near = pop[(pop["odometer_km"] - odo).abs() <= odo_window_km]
        if len(near) >= 3:
            peers = near
    pct = _peer_percentile(soh, peers["soh_pct"]) if pd.notna(soh) else None
    same_chem = pop[pop.get("chemistry") == row.get("chemistry")] if "chemistry" in pop else pop
    pct_chem = _peer_percentile(soh, same_chem["soh_pct"]) if pd.notna(soh) else None

    verdict = _verdict(vs_tesla, pct, row)
    return {
        "car": car_id,
        "label": f"{row.get('model','?')} {row.get('trim') or ''} · {row.get('chemistry') or '?'}".strip(),
        "soh_pct": None if pd.isna(soh) else float(soh),
        "odometer_km": None if pd.isna(odo) else float(odo),
        "tesla_expected_soh": round(expected, 1) if expected is not None else None,
        "vs_tesla_pp": vs_tesla,
        "fleet_percentile": pct,
        "chemistry_percentile": pct_chem,
        "peer_count": int(len(peers)),
        "population_size": int(len(pop)),
        "verdict": verdict,
    }


def _verdict(vs_tesla, pct, row) -> str:
    if vs_tesla is None and pct is None:
        return "Not enough data to benchmark this car yet."
    bits = []
    if vs_tesla is not None:
        if vs_tesla >= 0.5:
            bits.append(f"**{vs_tesla:+.1f} pp** healthier than Tesla's published curve at this mileage")
        elif vs_tesla <= -0.5:
            bits.append(f"**{vs_tesla:+.1f} pp** below Tesla's published curve at this mileage")
        else:
            bits.append("right on Tesla's published retention curve")
    if pct is not None:
        if pct >= 50:
            bits.append(f"healthier than {pct:.0f}% of similar-mileage peers")
        else:
            bits.append(f"healthier than only {pct:.0f}% of similar-mileage peers")
    return " — ".join(bits) + "."


def population_cloud(df: pd.DataFrame, population: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Tidy SOH-vs-odometer frame for the background benchmarking cloud."""
    pop = population if population is not None else df
    d = pop.copy()
    d["soh_pct"] = pd.to_numeric(d["soh_pct"], errors="coerce")
    d["odometer_km"] = pd.to_numeric(d["odometer_km"], errors="coerce")
    return d.dropna(subset=["soh_pct", "odometer_km"])
