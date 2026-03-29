"""Tesla Consumption Constant Tracker.

Lets users select their vehicle, see the known factory consumption constant
(Verbrauchskonstante, Wh/km), log their own readings over time, and
visualise how the constant (and derived usable capacity) changes.

Data is persisted locally in SQLite so it survives browser refreshes.
"""
from datetime import date, datetime
from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from src.config import Config
from src.data.consumption_constants import (
    FACTORY_CONSTANTS,
    FactoryConstant,
    add_entry,
    constants_to_dataframe,
    delete_entry,
    get_entries,
    get_usernames,
    list_batteries,
    list_drivetrains,
    list_models,
    list_variants,
    lookup_constants,
)
from src.ui import UIComponents

st.set_page_config(
    page_title="Tesla Consumption Constant Tracker",
    page_icon=":zap:",
    layout="wide",
)

pio.templates.default = Config.PLOTLY_TEMPLATE


# ── Helpers ────────────────────────────────────────────────────────────────


def _safe_capacity(rated_range: Optional[float], constant: float) -> Optional[float]:
    """Compute usable capacity in kWh from rated range and constant."""
    if rated_range is None or rated_range <= 0 or constant <= 0:
        return None
    return round(rated_range * constant / 1000, 2)


# ── Page Sections ──────────────────────────────────────────────────────────


def _render_header() -> None:
    """Page header matching the overall app style."""
    st.markdown(
        f"""
        <style>
            .header {{
                display: flex;
                justify-content: center;
                align-items: center;
                flex-direction: column;
                padding: 0rem 0;
                margin-bottom: 0rem;
            }}
            .header img {{
                width: 100%;
                height: auto;
            }}
            .header h1 {{
                margin: 0;
                padding-top: 1rem;
                text-align: center;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 32px;
            }}
            .header h1 span {{
                margin: 0 10px;
            }}
        </style>
        <div class="header">
            <img src="{Config.HEADER_IMAGE_URL}" alt="Consumption Constant Tracker">
            <h1><span>&#9889;</span> Consumption Constant Tracker <span>&#9889;</span></h1>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_vehicle_selector() -> tuple:
    """Vehicle selection + factory constant display.

    Returns:
        (model, variant, battery, drivetrain, matching_constants)
    """
    st.markdown("### Vehicle Selector")
    st.caption(
        "Select your vehicle configuration to look up the known factory "
        "consumption constant (Verbrauchskonstante)."
    )

    col1, col2, col3, col4 = st.columns(4)

    models = list_models()
    model = col1.selectbox("Model", models, index=0, key="cc_model")

    variants = list_variants(model)
    variant = col2.selectbox("Variant", variants, index=0, key="cc_variant")

    batteries = list_batteries(model, variant)
    battery = col3.selectbox(
        "Battery",
        batteries if batteries else ["—"],
        index=0,
        key="cc_battery",
    )
    if battery == "—":
        battery = ""

    drivetrains = list_drivetrains(model, variant)
    drivetrain = col4.selectbox(
        "Drive",
        drivetrains if drivetrains else ["—"],
        index=0,
        key="cc_drive",
    )
    if drivetrain == "—":
        drivetrain = ""

    matches = lookup_constants(model, variant, battery or None, drivetrain or None)

    if matches:
        top = matches[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Factory Constant", f"{top.constant_wh_km} Wh/km")
        m2.metric("Nominal Capacity", f"{top.nominal_capacity_kwh} kWh")
        m3.metric("Years", top.years)
        m4.metric("Battery", top.battery)

        if len(matches) > 1:
            with st.expander("All matching factory constants"):
                st.dataframe(
                    constants_to_dataframe(matches),
                    use_container_width=True,
                    hide_index=True,
                )
    else:
        st.info("No factory constant found for this exact configuration.")

    # Formula explanation
    with st.expander("How it works"):
        st.markdown(
            """
**Formula:**
```
Usable Capacity (kWh) = Rated Range at 100% (km) × Constant (Wh/km) / 1000
```

The **consumption constant** is the internal value Tesla's BMS uses to
translate the battery's usable energy into the "Rated Range" shown on the
dashboard.  Software updates can change this value, making it essential to
track over time for accurate degradation analysis.

**Example:**
- Rated Range at 100 %: 453 km
- Consumption Constant: 158.4 Wh/km
- Usable Capacity: 453 × 158.4 / 1000 = **71.8 kWh**

Source: [TFF Forum Akkuwiki](https://tff-forum.de/t/wiki-akkuwiki-model-3-y-s-x-ct/107641)
            """
        )

    return model, variant, battery, drivetrain, matches


def _render_data_entry(
    model: str,
    variant: str,
    battery: str,
    default_constant: Optional[float],
) -> None:
    """Form for logging a new consumption constant reading."""
    st.markdown("### Log New Reading")

    with st.form("cc_entry_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        username = fc1.text_input(
            "Username *",
            value=st.session_state.get("cc_username", ""),
            help="Your TFF Forum or TeslaTech username",
        )
        entry_date = fc2.date_input(
            "Date *",
            value=date.today(),
            max_value=date.today(),
        )

        fc3, fc4, fc5 = st.columns(3)
        constant = fc3.number_input(
            "Consumption Constant (Wh/km) *",
            min_value=50.0,
            max_value=300.0,
            value=default_constant or 150.0,
            step=0.1,
            format="%.1f",
        )
        rated_range = fc4.number_input(
            "Rated Range at 100 % (km)",
            min_value=0.0,
            max_value=1000.0,
            value=0.0,
            step=1.0,
            help="Leave at 0 if unknown",
        )
        odometer = fc5.number_input(
            "Odometer (km)",
            min_value=0.0,
            max_value=999999.0,
            value=0.0,
            step=100.0,
            help="Leave at 0 if unknown",
        )

        fc6, fc7 = st.columns(2)
        software = fc6.text_input("Software Version", value="")
        notes = fc7.text_input("Notes", value="")

        submitted = st.form_submit_button("💾 Save Reading", use_container_width=True)

    if submitted:
        if not username.strip():
            st.error("Username is required.")
            return
        st.session_state["cc_username"] = username.strip()

        add_entry(
            username=username.strip(),
            model=model,
            variant=variant,
            battery=battery,
            entry_date=entry_date,
            constant=constant,
            rated_range=rated_range if rated_range > 0 else None,
            odometer=odometer if odometer > 0 else None,
            software=software.strip(),
            notes=notes.strip(),
        )
        st.success("Reading saved!")
        st.rerun()


def _render_data_viewer() -> None:
    """Display logged entries with chart + table + export."""
    st.markdown("### Your Readings")

    existing_users = get_usernames()
    if not existing_users:
        st.info("No readings logged yet. Use the form above to add your first entry.")
        return

    col1, col2 = st.columns([3, 1])
    selected_user = col1.selectbox(
        "Select User",
        existing_users,
        index=(
            existing_users.index(st.session_state.get("cc_username", ""))
            if st.session_state.get("cc_username", "") in existing_users
            else 0
        ),
        key="cc_viewer_user",
    )

    df = get_entries(selected_user)
    if df.empty:
        st.info("No entries for this user yet.")
        return

    # Derived columns
    df["Capacity (kWh)"] = df.apply(
        lambda r: _safe_capacity(r["rated_range"], r["constant"]), axis=1
    )

    # ── Metrics row ──
    latest = df.iloc[-1]
    earliest = df.iloc[0]
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("Entries", len(df))
    mc2.metric("Latest Constant", f"{latest['constant']:.1f} Wh/km")

    if len(df) > 1:
        delta = latest["constant"] - earliest["constant"]
        mc3.metric(
            "Change",
            f"{latest['constant']:.1f}",
            delta=f"{delta:+.1f} Wh/km",
            delta_color="inverse",
        )
    else:
        mc3.metric("Change", "—")

    if latest["Capacity (kWh)"] is not None:
        mc4.metric("Latest Capacity", f"{latest['Capacity (kWh)']:.1f} kWh")
    else:
        mc4.metric("Latest Capacity", "—")

    if latest["odometer"] is not None and not pd.isna(latest["odometer"]):
        mc5.metric("Latest Odometer", f"{latest['odometer']:,.0f} km")
    else:
        mc5.metric("Latest Odometer", "—")

    # ── Plotly Chart ──
    _render_chart(df)

    # ── Data table ──
    display_cols = [
        "entry_date", "constant", "rated_range", "Capacity (kWh)",
        "odometer", "software", "model", "variant", "battery", "notes",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    display_df = df[display_cols].copy()
    display_df = display_df.rename(columns={
        "entry_date": "Date",
        "constant": "Constant (Wh/km)",
        "rated_range": "Rated Range (km)",
        "odometer": "Odometer (km)",
        "software": "Software",
        "model": "Model",
        "variant": "Variant",
        "battery": "Battery",
        "notes": "Notes",
    })

    with st.expander("Data Table", expanded=True):
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # CSV export
        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"consumption_constant_{selected_user}.csv",
            mime="text/csv",
        )

    # ── Delete entries ──
    with st.expander("Manage Entries"):
        st.caption("Select an entry ID to delete.")
        entry_ids = df["id"].tolist()
        if entry_ids:
            del_id = st.selectbox("Entry ID", entry_ids, key="cc_del_id")
            del_row = df[df["id"] == del_id].iloc[0]
            st.write(
                f"**{del_row['entry_date'].strftime('%Y-%m-%d')}** — "
                f"{del_row['constant']:.1f} Wh/km"
                + (f", Range {del_row['rated_range']:.0f} km" if pd.notna(del_row['rated_range']) else "")
            )
            if st.button("🗑️ Delete Selected Entry", key="cc_del_btn"):
                delete_entry(del_id)
                st.success("Entry deleted.")
                st.rerun()


def _render_chart(df: pd.DataFrame) -> None:
    """Render a dual-axis Plotly chart: constant + capacity over time."""
    fig = go.Figure()

    # Consumption constant trace
    fig.add_trace(
        go.Scatter(
            x=df["entry_date"],
            y=df["constant"],
            name="Consumption Constant",
            mode="lines+markers",
            line=dict(color="#0068c9", width=3),
            marker=dict(size=8, symbol="circle"),
            yaxis="y",
            hovertemplate=(
                "<b>%{x|%Y-%m-%d}</b><br>"
                "Constant: %{y:.1f} Wh/km<br>"
                "<extra></extra>"
            ),
        )
    )

    # Capacity trace (secondary axis)
    cap_series = df.apply(
        lambda r: _safe_capacity(r["rated_range"], r["constant"]), axis=1
    )
    has_capacity = cap_series.notna().any()

    if has_capacity:
        fig.add_trace(
            go.Scatter(
                x=df["entry_date"],
                y=cap_series,
                name="Usable Capacity",
                mode="lines+markers",
                line=dict(color="#29b09d", width=3, dash="dot"),
                marker=dict(size=8, symbol="diamond"),
                yaxis="y2",
                hovertemplate=(
                    "<b>%{x|%Y-%m-%d}</b><br>"
                    "Capacity: %{y:.1f} kWh<br>"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text="Consumption Constant & Capacity Over Time", x=0.5),
        xaxis=dict(title="Date"),
        yaxis=dict(
            title="Constant (Wh/km)",
            titlefont=dict(color="#0068c9"),
            tickfont=dict(color="#0068c9"),
        ),
        yaxis2=dict(
            title="Usable Capacity (kWh)",
            titlefont=dict(color="#29b09d"),
            tickfont=dict(color="#29b09d"),
            overlaying="y",
            side="right",
        ) if has_capacity else None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=450,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_reference_table() -> None:
    """Show the full factory constants reference table."""
    st.markdown("### Factory Constants Reference")
    st.caption(
        "Known consumption constants from the TFF Forum Akkuwiki. "
        "Values may differ slightly depending on firmware version, wheel size, "
        "and regional calibration."
    )
    ref_df = constants_to_dataframe(FACTORY_CONSTANTS)

    # Sidebar-style model filter
    model_options = sorted(ref_df["Model"].unique().tolist())
    selected_models = st.multiselect(
        "Filter by Model",
        model_options,
        default=[],
        key="cc_ref_model_filter",
    )
    if selected_models:
        ref_df = ref_df[ref_df["Model"].isin(selected_models)]

    st.dataframe(ref_df, use_container_width=True, hide_index=True)
    st.markdown(
        "Source: [TFF Forum Akkuwiki](https://tff-forum.de/t/wiki-akkuwiki-model-3-y-s-x-ct/107641)"
    )


# ── Main ───────────────────────────────────────────────────────────────────


def main() -> None:
    """Main page entry point."""
    _render_header()

    tracker_tab, reference_tab = st.tabs(["Tracker", "Reference Constants"])

    with tracker_tab:
        model, variant, battery, drivetrain, matches = _render_vehicle_selector()
        default_constant = matches[0].constant_wh_km if matches else None

        st.markdown("---")
        _render_data_entry(model, variant, battery, default_constant)

        st.markdown("---")
        _render_data_viewer()

    with reference_tab:
        _render_reference_table()

    UIComponents.render_sidebar_footer()


if __name__ == "__main__":
    main()
