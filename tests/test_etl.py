"""Tests for the privacy-first ETL: VIN decode, anonymization, SOH, identity."""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from etl.vin import decode_vin
from etl.anonymize import public_car_id, assert_clean, FORBIDDEN_FIELDS
from etl.analytics import compute_soh, compute_charging, compute_efficiency


# --- VIN decoder ------------------------------------------------------------
def test_vin_decodes_known_cars():
    d = decode_vin("XP7YGCEKXRB268805")          # Morty#6 ground truth
    assert d.valid
    assert d.model == "Model Y"
    assert d.model_year == 2024
    assert d.factory_code == "MIG"

    assert decode_vin("LRWYGCEK4MC065820").factory_code == "MIC"   # Shanghai
    assert decode_vin("5YJ3E7ECXLF683812").model == "Model 3"      # Fremont 2020


def test_vin_rejects_garbage():
    assert not decode_vin("").valid
    assert not decode_vin("NOTAVIN").valid
    assert not decode_vin(None).valid


# --- Anonymization ----------------------------------------------------------
def test_public_id_stable_and_irreversible():
    os.environ["TESLATECH_ANON_SALT"] = "unit-test-salt"
    a = public_car_id("XP7YGCEKXRB268805")
    b = public_car_id("XP7YGCEKXRB268805")
    assert a == b and len(a) == 10
    assert public_car_id("LRWYGCEK4MC065820") != a   # different car, different id
    assert "268805" not in a                          # serial not leaked


def test_assert_clean_blocks_pii():
    assert_clean({"car": "abc", "model": "Model Y"})  # ok
    for field in list(FORBIDDEN_FIELDS)[:3]:
        with pytest.raises(ValueError):
            assert_clean({field: "secret"})


# --- SOH --------------------------------------------------------------------
def test_soh_filters_glitches_and_scales_to_design():
    # mostly ~79 kWh with a glitch spike at 188; design 79 -> ~100% SOH
    can71 = pd.DataFrame({
        "Datum": pd.date_range("2024-01-01", periods=6, freq="MS"),
        "val": [79, 78, 188.9, 79, 78, 77],
    })
    res = compute_soh(can71, design_capacity_kwh=79.0)
    assert res.soh_pct is not None
    assert 90 <= res.soh_pct <= 102          # glitch did not blow it up
    assert res.degradation_pct == round(100 - res.soh_pct, 1)


def test_soh_handles_empty():
    assert compute_soh(pd.DataFrame(), 79.0).soh_pct is None
    assert compute_soh(pd.DataFrame({"Datum": [], "val": []}), None).soh_pct is None


# --- Charging ---------------------------------------------------------------
def test_charging_splits_dc_and_ac():
    sessions = pd.DataFrame({
        "charge_energy_added": [50, 10, 40],
        "max_charger_power": [250, 11, 150],
        "fast_charger_present": [1, 0, 1],
    })
    res = compute_charging(sessions)
    assert res.sessions == 3
    assert res.dc_sessions == 2 and res.ac_sessions == 1
    assert res.max_charge_power_kw == 250.0
    assert 0 < res.dc_energy_share_pct < 100


# --- Efficiency -------------------------------------------------------------
def test_efficiency_vs_factory():
    overall = pd.Series({"km": 10000.0, "kwh": 2000.0, "avg_temp": 12.0})
    by_temp = pd.DataFrame({"tbin": [0, 20], "km": [1000, 2000], "kwh": [300, 380]})
    res = compute_efficiency(overall, by_temp, factory_wh_per_km=150.0)
    assert res.real_wh_per_km == 200.0                  # 2000kWh/10000km
    assert res.vs_factory_pct == pytest.approx(33.3, abs=0.5)
    assert len(res.temp_curve) == 2
    assert res.temp_curve[0]["temp_c"] == 0
