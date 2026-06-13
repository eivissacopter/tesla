"""Real-world fleet telemetry from a live Teslalogger database.

This page closes the loop the survey never could: instead of self-reported
numbers, it shows *measured* State-of-Health, charging behaviour and efficiency
for a real, continuously-logged fleet -- fully anonymized. Each car is identity-
resolved (VIN -> model/year/plant/pack/chemistry/motors) on the home server;
only physics reaches this page.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import Config
from src.data.fleet import load_fleet
from src.data.benchmark import benchmark_car, tesla_expected_soh, population_cloud
from src.utils.data_processing import BatteryDataProcessor
from src.ui import UIComponents

st.set_page_config(page_title="Tesla Fleet Telemetry", page_icon=":battery:", layout="wide")

CHEM_COLORS = {"NCA": "#ff2b2b", "NMC": "#0068c9", "LFP": "#29b09d", "Unknown": "#808495"}


def _theme(fig, height=420, ylab="", xlab=""):
    fig.update_layout(
        template=Config.PLOTLY_TEMPLATE,
        paper_bgcolor=Config.CHART_BACKGROUND,
        plot_bgcolor=Config.CHART_BACKGROUND,
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        font=dict(size=13),
    )
    if ylab:
        fig.update_yaxes(title_text=ylab, gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    if xlab:
        fig.update_xaxes(title_text=xlab, gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    return fig


def _metric_row(df):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Cars logged", len(df))
    soh = pd.to_numeric(df["soh_pct"], errors="coerce").dropna()
    c2.metric("Median SOH", f"{soh.median():.1f}%" if not soh.empty else "—")
    km = pd.to_numeric(df["odometer_km"], errors="coerce").dropna()
    c3.metric("Distance logged", f"{km.sum()/1000:,.0f}k km" if not km.empty else "—")
    sess = pd.to_numeric(df["charge_sessions"], errors="coerce").dropna()
    c4.metric("Charge sessions", f"{int(sess.sum()):,}" if not sess.empty else "—")
    wh = pd.to_numeric(df.get("real_wh_per_km", df["wh_per_km"]), errors="coerce").dropna()
    c5.metric("Median real-world", f"{wh.median():.0f} Wh/km" if not wh.empty else "—")


def _soh_curves(soh_series, df):
    fig = go.Figure()
    id_to_meta = {r["car"]: r for _, r in df.iterrows()}
    plotted = 0
    for car, series in soh_series.items():
        if not series or car not in id_to_meta:
            continue
        meta = id_to_meta[car]
        chem = meta.get("chemistry") or "Unknown"
        xs = [s["month"] for s in series]
        ys = [s["soh_pct"] for s in series]
        if len(xs) < 2:
            continue
        label = f"{meta.get('model','?')} {meta.get('trim') or ''} · {chem} · {car[:6]}"
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=label.strip(),
            line=dict(width=2, color=CHEM_COLORS.get(chem, "#808495")),
            hovertemplate="%{x}<br>SOH %{y:.1f}%<extra>" + label.strip() + "</extra>",
            opacity=0.9,
        ))
        plotted += 1
    fig.add_hline(y=100, line=dict(color="rgba(255,255,255,0.25)", dash="dot"),
                  annotation_text="design capacity", annotation_position="top left")
    fig.add_hline(y=70, line=dict(color="rgba(255,43,43,0.5)", dash="dash"),
                  annotation_text="70% end-of-warranty floor", annotation_position="bottom left")
    _theme(fig, height=460, ylab="State of Health (%)", xlab="Month")
    return fig, plotted


def _soh_vs_odo(df):
    d = df.copy()
    d["soh_pct"] = pd.to_numeric(d["soh_pct"], errors="coerce")
    d["odometer_km"] = pd.to_numeric(d["odometer_km"], errors="coerce")
    d["design_kwh"] = pd.to_numeric(d["design_kwh"], errors="coerce")
    d = d.dropna(subset=["soh_pct", "odometer_km"])
    fig = px.scatter(
        d, x="odometer_km", y="soh_pct", color="chemistry",
        size="design_kwh", size_max=22,
        color_discrete_map=CHEM_COLORS,
        hover_data={"model": True, "trim": True, "model_year": True,
                    "pack": True, "design_kwh": True, "odometer_km": ":,.0f"},
    )
    fig.update_traces(marker=dict(line=dict(width=1, color="rgba(0,0,0,0.4)")))
    _theme(fig, height=440, ylab="State of Health (%)", xlab="Odometer (km)")
    return fig


def _charging_fingerprint(df):
    d = df.copy()
    for c in ("dc_share_pct", "max_charge_kw", "charge_sessions"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["dc_share_pct", "max_charge_kw"])
    fig = px.scatter(
        d, x="dc_share_pct", y="max_charge_kw", color="chemistry",
        size="charge_sessions", size_max=26, color_discrete_map=CHEM_COLORS,
        hover_data={"model": True, "trim": True, "charge_sessions": True},
    )
    fig.update_traces(marker=dict(line=dict(width=1, color="rgba(0,0,0,0.4)")))
    _theme(fig, height=380, ylab="Peak charge power (kW)", xlab="DC fast-charge share of energy (%)")
    return fig


def _temp_curve(temp_curves, df):
    """Efficiency vs ambient temperature -- the real winter-range curve."""
    id_to_meta = {r["car"]: r for _, r in df.iterrows()}
    fig = go.Figure()
    plotted = 0
    for car, curve in temp_curves.items():
        if not curve or car not in id_to_meta or len(curve) < 3:
            continue
        chem = id_to_meta[car].get("chemistry") or "Unknown"
        xs = [p["temp_c"] for p in curve]
        ys = [p["wh_per_km"] for p in curve]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers", name=car[:6],
            line=dict(width=1.5, color=CHEM_COLORS.get(chem, "#808495")),
            marker=dict(size=4), opacity=0.55, showlegend=False,
            hovertemplate="%{x}°C → %{y:.0f} Wh/km<extra>" + car[:6] + "</extra>"))
        plotted += 1
    # Fleet median curve (bold)
    allpts = {}
    for car, curve in temp_curves.items():
        for p in curve or []:
            allpts.setdefault(p["temp_c"], []).append(p["wh_per_km"])
    if allpts:
        xs = sorted(allpts)
        ys = [float(np.median(allpts[t])) for t in xs]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name="Fleet median",
                                 line=dict(width=4, color="#E82127"), marker=dict(size=7)))
    _theme(fig, height=420, ylab="Consumption (Wh/km)", xlab="Ambient temperature (°C)")
    return fig, plotted


def _eff_vs_factory(df):
    d = df.copy()
    for c in ("real_wh_per_km", "factory_wh_per_km", "vs_factory_pct"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["real_wh_per_km", "factory_wh_per_km"]).sort_values("vs_factory_pct")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=d["car"].str[:6], x=d["factory_wh_per_km"], orientation="h",
                         name="Factory constant", marker_color="#3a4a63"))
    fig.add_trace(go.Bar(y=d["car"].str[:6], x=d["real_wh_per_km"] - d["factory_wh_per_km"],
                         orientation="h", name="Real-world penalty", marker_color="#E82127",
                         base=d["factory_wh_per_km"],
                         hovertemplate="real %{customdata[0]:.0f} Wh/km (+%{customdata[1]:.0f}%)<extra></extra>",
                         customdata=d[["real_wh_per_km", "vs_factory_pct"]].values))
    fig.update_layout(barmode="overlay")
    _theme(fig, height=420, ylab="", xlab="Wh/km")
    return fig


def _benchmark_plot(df, car_id, population=None):
    cloud = population_cloud(df, population)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cloud["odometer_km"], y=cloud["soh_pct"], mode="markers", name="Population",
        marker=dict(size=9, color="rgba(140,150,170,0.55)", line=dict(width=1, color="rgba(0,0,0,0.4)")),
        hovertext=cloud["car"].str[:6], hovertemplate="%{hovertext}: %{y:.1f}% @ %{x:,.0f} km<extra></extra>"))
    try:
        odo, retention = BatteryDataProcessor.get_tesla_retention_line()
        fig.add_trace(go.Scatter(x=odo, y=100.0 + np.asarray(retention, dtype=float), mode="lines",
                                 name="Tesla published curve", line=dict(color="#E82127", width=2, dash="dash")))
    except Exception:
        pass
    sel = df[df["car"] == car_id]
    if not sel.empty:
        r = sel.iloc[0]
        fig.add_trace(go.Scatter(
            x=[pd.to_numeric(pd.Series([r.get("odometer_km")]), errors="coerce").iloc[0]],
            y=[pd.to_numeric(pd.Series([r.get("soh_pct")]), errors="coerce").iloc[0]],
            mode="markers", name="This car",
            marker=dict(size=20, color="#29b09d", symbol="star", line=dict(width=1.5, color="#fff"))))
    _theme(fig, height=420, ylab="State of Health (%)", xlab="Odometer (km)")
    return fig


def _render_benchmark(view):
    st.subheader("Benchmark a car against the world")
    st.caption("How one car compares to Tesla's published retention curve and to the population. "
               "The population is this fleet today; once the public survey is connected, it becomes "
               "thousands of real cars.")
    benchable = view[pd.to_numeric(view["soh_pct"], errors="coerce").notna()]
    if benchable.empty:
        st.info("No cars with computed SOH in the current selection.")
        return
    labels = {f"{r['car'][:6]} · {r.get('model','?')} {r.get('trim') or ''} · {r.get('chemistry') or '?'}".strip(): r["car"]
              for _, r in benchable.iterrows()}
    pick = st.selectbox("Car", list(labels.keys()))
    car_id = labels[pick]
    res = benchmark_car(view, car_id)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SOH", f"{res['soh_pct']:.1f}%" if res.get("soh_pct") else "—")
    m2.metric("Tesla expected", f"{res['tesla_expected_soh']:.1f}%" if res.get("tesla_expected_soh") else "—")
    m3.metric("vs Tesla curve", f"{res['vs_tesla_pp']:+.1f} pp" if res.get("vs_tesla_pp") is not None else "—")
    m4.metric("Fleet percentile", f"{res['fleet_percentile']:.0f}th" if res.get("fleet_percentile") is not None else "—")
    if res.get("verdict"):
        st.markdown(f"> {res['verdict']}")
    st.plotly_chart(_benchmark_plot(view, car_id), use_container_width=True)


def main():
    UIComponents.inject_global_styles()
    data = load_fleet()
    df, soh_series, meta = data["df"], data["soh_series"], data["meta"]
    temp_curves = data.get("temp_curves", {})

    st.title("Real-World Fleet Telemetry")
    st.caption(
        "Measured State-of-Health, charging and efficiency from a continuously-logged, "
        "fully anonymized real Tesla fleet. Each car is identity-resolved from its VIN; "
        "no names, locations or identifiers are ever exposed."
    )
    if meta.get("data_version"):
        st.caption(f":material/sync: Data version **{meta['data_version']}** · synced weekly from the source database.")

    if df.empty:
        st.warning("No fleet artifact found. Run the home-server ETL (`python -m etl.export_fleet`).")
        return

    # Filters
    chems = sorted([c for c in df["chemistry"].dropna().unique()])
    models = sorted([m for m in df["model"].dropna().unique()])
    fc1, fc2 = st.columns(2)
    sel_models = fc1.multiselect("Model", models, default=models)
    sel_chems = fc2.multiselect("Chemistry", chems, default=chems)
    view = df[df["model"].isin(sel_models) & (df["chemistry"].isin(sel_chems) | df["chemistry"].isna())]

    _metric_row(view)
    st.divider()

    st.subheader("State-of-Health over time")
    st.caption("Robust monthly BMS nominal-full-pack estimate ÷ design capacity. Glitch spikes filtered; "
               "each line is one anonymized car, coloured by cell chemistry.")
    fig, n = _soh_curves(soh_series, view)
    st.plotly_chart(fig, use_container_width=True)
    if n == 0:
        st.info("No multi-point SOH history for the current selection.")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Degradation vs distance")
        st.caption("Where each pack sits on the SOH/odometer plane. Bubble size = pack kWh.")
        st.plotly_chart(_soh_vs_odo(view), use_container_width=True)
    with c2:
        st.subheader("Charging fingerprint")
        st.caption("How hard the fleet charges. Bubble size = number of sessions.")
        st.plotly_chart(_charging_fingerprint(view), use_container_width=True)

    st.divider()
    _render_benchmark(view)

    st.divider()
    st.subheader("Real-world efficiency")
    st.caption("Measured km-weighted consumption from logged trips — what the cars actually use, "
               "versus the factory rating. Temperature drives most of the spread.")
    e1, e2 = st.columns([3, 2])
    with e1:
        st.markdown("**Consumption vs ambient temperature**")
        tfig, tn = _temp_curve(temp_curves, view)
        st.plotly_chart(tfig, use_container_width=True)
        if tn == 0:
            st.info("No temperature curve for the current selection.")
    with e2:
        st.markdown("**Measured vs factory constant**")
        st.plotly_chart(_eff_vs_factory(view), use_container_width=True)

    st.divider()
    st.subheader("Anonymized fleet")
    show_cols = ["car", "model", "trim", "drivetrain", "model_year", "factory", "pack",
                 "chemistry", "front_motor", "rear_motor", "odometer_km", "design_kwh",
                 "soh_pct", "degradation_pct", "real_wh_per_km", "factory_wh_per_km", "vs_factory_pct",
                 "charge_sessions", "dc_share_pct", "max_charge_kw"]
    show_cols = [c for c in show_cols if c in view.columns]
    st.dataframe(view[show_cols], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
else:
    main()
