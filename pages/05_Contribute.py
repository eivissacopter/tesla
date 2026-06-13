"""Public questionnaire -- contribute a battery datapoint (replaces Google Sheets).

Writes validated submissions to the contribution store (SQLite in dev, managed
Postgres in prod). Mirrors the survey's fields and sanity bounds so the new
native dataset is drop-in compatible with the existing analysis.
"""

import pandas as pd
import streamlit as st

from src.data.contributions import add_submission, get_submissions, count_submissions
from src.ui import UIComponents

st.set_page_config(page_title="Contribute Battery Data", page_icon=":pencil:", layout="wide")

MODELS = ["Model 3", "Model Y", "Model S", "Model X"]
TRIMS = ["Standard", "Long Range", "Performance"]
DRIVETRAINS = ["RWD", "AWD"]
CHEMISTRIES = ["LFP", "NMC", "NCA"]
ORIGINS = ["Germany (MIG)", "China (MIC)", "USA (Fremont)", "USA (Austin)", "Other"]


def main():
    UIComponents.inject_global_styles()
    st.title("Contribute your battery data")
    st.caption("Help grow the open dataset. Your datapoint is stored directly in the TeslaTech "
               "database — no Google Forms, no spreadsheet. Only the values below are saved.")

    total = count_submissions()
    if total:
        st.caption(f":material/database: {total:,} community submissions so far.")

    with st.form("contribute", clear_on_submit=True):
        st.subheader("Vehicle")
        c1, c2, c3, c4 = st.columns(4)
        model = c1.selectbox("Model *", MODELS)
        trim = c2.selectbox("Trim", TRIMS)
        drivetrain = c3.selectbox("Drivetrain", DRIVETRAINS)
        model_year = c4.number_input("Model year", min_value=2012, max_value=2027, value=2023, step=1)
        c5, c6, c7 = st.columns(3)
        chemistry = c5.selectbox("Cell chemistry", ["(unknown)"] + CHEMISTRIES)
        origin = c6.selectbox("Built in", ORIGINS)
        battery = c7.text_input("Battery label (optional)", placeholder="e.g. LG 5L 79 kWh")

        st.subheader("Measurements")
        m1, m2, m3, m4 = st.columns(4)
        age_months = m1.number_input("Age (months)", min_value=0.0, max_value=220.0, value=24.0, step=1.0)
        odometer_km = m2.number_input("Odometer (km)", min_value=0.0, max_value=1_500_000.0, value=30000.0, step=1000.0)
        rated_range_km = m3.number_input("Rated range at 100% (km)", min_value=0.0, max_value=800.0, value=0.0, step=1.0)
        capacity_net_kwh = m4.number_input("Usable capacity now (kWh)", min_value=0.0, max_value=130.0, value=0.0, step=0.1)
        m5, m6, m7, m8 = st.columns(4)
        degradation_pct = m5.number_input("Degradation (%)", min_value=0.0, max_value=60.0, value=0.0, step=0.1,
                                          help="Percent of capacity lost vs new (positive number).")
        daily_soc_limit = m6.number_input("Daily charge limit (%)", min_value=0.0, max_value=100.0, value=80.0, step=1.0)
        dc_ratio = m7.number_input("DC fast-charge share (%)", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
        cycles = m8.number_input("Equivalent full cycles", min_value=0.0, max_value=6000.0, value=0.0, step=1.0)

        st.subheader("About you (optional)")
        u1, u2 = st.columns(2)
        username = u1.text_input("Username / handle", placeholder="anonymous")
        software = u2.text_input("Software version", placeholder="e.g. 2025.20.7")
        notes = st.text_area("Notes", placeholder="Anything notable about this pack…")

        submitted = st.form_submit_button("Submit datapoint", type="primary")

    if submitted:
        entry = {
            "username": username or "anonymous",
            "model": model, "trim": trim, "drivetrain": drivetrain,
            "chemistry": None if chemistry == "(unknown)" else chemistry,
            "origin": origin, "model_year": int(model_year),
            "age_months": age_months or None,
            "odometer_km": odometer_km or None,
            "rated_range_km": rated_range_km or None,
            "capacity_net_kwh": capacity_net_kwh or None,
            # Store degradation as the survey does: non-positive.
            "degradation_pct": -abs(degradation_pct) if degradation_pct else None,
            "daily_soc_limit": daily_soc_limit, "dc_ratio": dc_ratio,
            "cycles": cycles or None, "battery": battery or None,
            "software": software or None, "notes": notes or None,
        }
        ok, errors = add_submission(entry)
        if ok:
            st.success("Thank you! Your datapoint is now part of the open dataset.")
            st.balloons()
        else:
            for e in errors:
                st.error(e)

    recent = get_submissions(limit=8)
    if not recent.empty:
        st.divider()
        st.subheader("Latest contributions")
        cols = [c for c in ["submitted_at", "model", "trim", "drivetrain", "chemistry",
                            "age_months", "odometer_km", "degradation_pct", "username"] if c in recent.columns]
        st.dataframe(recent[cols], use_container_width=True, hide_index=True)


main()
