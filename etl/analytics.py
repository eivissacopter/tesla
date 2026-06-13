"""Scientific analytics over Teslalogger data.

These functions take small/aggregated DataFrames (already pulled and, where
needed, aggregated in SQL) and return clean, defensible metrics. No raw PII
ever reaches here.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Optional

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------
# State of Health
# ----------------------------------------------------------------------------
@dataclass
class SohResult:
    design_capacity_kwh: Optional[float]
    baseline_kwh: Optional[float]        # robust early full-pack estimate
    current_kwh: Optional[float]         # robust recent full-pack estimate
    soh_pct: Optional[float]             # current / design * 100
    soh_vs_baseline_pct: Optional[float]
    degradation_pct: Optional[float]     # 100 - soh
    n_samples: int = 0
    method: str = "can71_nominal_full_pack"
    monthly: list = field(default_factory=list)  # [{month, kwh, soh_pct}]

    def as_dict(self) -> dict:
        return asdict(self)


def compute_soh(
    can71: pd.DataFrame,
    design_capacity_kwh: Optional[float],
    *,
    datum_col: str = "Datum",
    val_col: str = "val",
    robust_quantile: float = 0.90,
    plausible_frac: tuple[float, float] = (0.5, 1.15),
) -> SohResult:
    """Robust SOH from CAN id 71 (BMS 'nominal full pack' energy, kWh).

    The BMS estimate is SOC-independent but noisy, with rare glitch spikes.
    We clip to a plausible band around the design capacity, resample to monthly
    medians, and take a high quantile of the monthly medians as the stable
    baseline/current capacity. SOH = current / design * 100.
    """
    if can71 is None or can71.empty or not design_capacity_kwh:
        return SohResult(design_capacity_kwh, None, None, None, None, None, 0)

    df = can71[[datum_col, val_col]].copy()
    df[datum_col] = pd.to_datetime(df[datum_col], errors="coerce")
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    df = df.dropna()

    lo = design_capacity_kwh * plausible_frac[0]
    hi = design_capacity_kwh * plausible_frac[1]
    df = df[(df[val_col] >= lo) & (df[val_col] <= hi)]
    if df.empty:
        return SohResult(design_capacity_kwh, None, None, None, None, None, 0)

    df = df.set_index(datum_col).sort_index()
    monthly_med = df[val_col].resample("MS").median().dropna()
    if monthly_med.empty:
        return SohResult(design_capacity_kwh, None, None, None, None, None, len(df))

    # Baseline = high quantile of the earliest few months (pack near-new);
    # current = robust estimate of the most recent months.
    early = monthly_med.iloc[: min(3, len(monthly_med))]
    recent = monthly_med.iloc[-min(3, len(monthly_med)):]
    baseline = float(np.quantile(early.values, robust_quantile))
    current = float(np.quantile(recent.values, robust_quantile))

    soh = current / design_capacity_kwh * 100.0
    soh_vs_base = current / baseline * 100.0 if baseline else None
    monthly = [
        {"month": ts.strftime("%Y-%m"),
         "kwh": round(float(v), 2),
         "soh_pct": round(float(v) / design_capacity_kwh * 100.0, 2)}
        for ts, v in monthly_med.items()
    ]
    return SohResult(
        design_capacity_kwh=round(design_capacity_kwh, 1),
        baseline_kwh=round(baseline, 2),
        current_kwh=round(current, 2),
        soh_pct=round(soh, 1),
        soh_vs_baseline_pct=round(soh_vs_base, 1) if soh_vs_base else None,
        degradation_pct=round(100.0 - soh, 1),
        n_samples=int(len(df)),
        monthly=monthly,
    )


# ----------------------------------------------------------------------------
# Efficiency (real-world consumption)
# ----------------------------------------------------------------------------
@dataclass
class EfficiencyResult:
    real_wh_per_km: Optional[float] = None      # km-weighted, measured from trips
    real_km: Optional[float] = None             # distance the figure is based on
    factory_wh_per_km: Optional[float] = None   # from the knowledge brain
    vs_factory_pct: Optional[float] = None       # real / factory - 1, in %
    avg_temp_c: Optional[float] = None
    temp_curve: list = field(default_factory=list)  # [{temp_c, wh_per_km, km}]

    def as_dict(self) -> dict:
        return asdict(self)


def compute_efficiency(
    trips_overall: Optional[pd.Series],
    trips_by_temp: Optional[pd.DataFrame],
    factory_wh_per_km: Optional[float],
) -> EfficiencyResult:
    """Real-world efficiency from aggregated trip data.

    ``trips_overall`` has km/kwh/avg_temp for one car; ``trips_by_temp`` has
    per-temperature-bin km/kwh for the temperature curve. Both are tiny,
    already aggregated in SQL.
    """
    res = EfficiencyResult(factory_wh_per_km=factory_wh_per_km)
    if trips_overall is not None and not trips_overall.empty:
        km = float(trips_overall.get("km") or 0)
        kwh = float(trips_overall.get("kwh") or 0)
        if km > 0 and kwh > 0:
            res.real_wh_per_km = round(kwh / km * 1000.0, 0)
            res.real_km = round(km, 0)
            if factory_wh_per_km:
                res.vs_factory_pct = round((res.real_wh_per_km / factory_wh_per_km - 1) * 100, 1)
        if pd.notna(trips_overall.get("avg_temp")):
            res.avg_temp_c = round(float(trips_overall["avg_temp"]), 1)

    if trips_by_temp is not None and not trips_by_temp.empty:
        d = trips_by_temp.copy()
        for c in ("tbin", "km", "kwh"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d = d.dropna(subset=["tbin", "km", "kwh"])
        d = d[d["km"] > 5]
        curve = []
        for tbin, grp in d.groupby("tbin"):
            km = grp["km"].sum()
            kwh = grp["kwh"].sum()
            if km > 0:
                curve.append({"temp_c": int(tbin),
                              "wh_per_km": round(kwh / km * 1000.0, 0),
                              "km": round(float(km), 0)})
        res.temp_curve = sorted(curve, key=lambda r: r["temp_c"])
    return res


# ----------------------------------------------------------------------------
# Charging behaviour
# ----------------------------------------------------------------------------
@dataclass
class ChargingResult:
    sessions: int = 0
    total_energy_kwh: Optional[float] = None
    dc_sessions: int = 0
    ac_sessions: int = 0
    dc_energy_share_pct: Optional[float] = None
    max_charge_power_kw: Optional[float] = None
    avg_dc_peak_kw: Optional[float] = None

    def as_dict(self) -> dict:
        return asdict(self)


def compute_charging(sessions: pd.DataFrame) -> ChargingResult:
    """Summarise charging from the chargingstate session table.

    A session is DC (fast) if a fast charger was present or peak power > 25 kW.
    Location columns are intentionally never read here.
    """
    if sessions is None or sessions.empty:
        return ChargingResult()
    df = sessions.copy()
    for c in ("charge_energy_added", "max_charger_power", "fast_charger_present"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    energy = df["charge_energy_added"] if "charge_energy_added" in df else pd.Series(dtype=float)
    power = df["max_charger_power"] if "max_charger_power" in df else pd.Series(dtype=float)
    fast = df["fast_charger_present"] if "fast_charger_present" in df else pd.Series(0, index=df.index)

    is_dc = (fast.fillna(0) > 0) | (power.fillna(0) > 25)
    dc_energy = float(energy[is_dc].sum()) if not energy.empty else 0.0
    total_energy = float(energy.sum()) if not energy.empty else 0.0

    return ChargingResult(
        sessions=int(len(df)),
        total_energy_kwh=round(total_energy, 1) if total_energy else None,
        dc_sessions=int(is_dc.sum()),
        ac_sessions=int((~is_dc).sum()),
        dc_energy_share_pct=round(dc_energy / total_energy * 100, 1) if total_energy else None,
        max_charge_power_kw=round(float(power.max()), 1) if not power.empty and power.notna().any() else None,
        avg_dc_peak_kw=round(float(power[is_dc].mean()), 1) if is_dc.any() and power[is_dc].notna().any() else None,
    )
