"""Detailed telemetry explorer — power/torque vs SOC & cell temperature.

Scatter plots over the anonymized raw-signal cloud, in the spirit of the old
TeslaTech visualizer: dot colour encodes cell temperature, dot size encodes SOC.
Pick a preset (max discharge power, battery power, motor power, motor torque) or
build your own axes.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import Config
from src.data.telemetry import load_telemetry
from src.ui import UIComponents

st.set_page_config(page_title="Tesla Telemetry Explorer", page_icon=":zap:", layout="wide")

# Preset: (label, x, y, color, size). Temperature → colour, SOC → size.
PRESETS = {
    "Max discharge power vs SOC": ("soc", "max_discharge_kw", "cell_temp", "soc"),
    "Battery power vs SOC": ("soc", "battery_power_kw", "cell_temp", "soc"),
    "Max charge power vs SOC": ("soc", "max_charge_kw", "cell_temp", "soc"),
    "Rear motor power vs speed": ("speed_kmh", "rear_power_kw", "cell_temp", "soc"),
    "Front motor power vs speed": ("speed_kmh", "front_power_kw", "cell_temp", "soc"),
    "Rear motor torque vs speed": ("speed_kmh", "rear_torque_nm", "cell_temp", "soc"),
    "Front motor torque vs speed": ("speed_kmh", "front_torque_nm", "cell_temp", "soc"),
    "Battery power vs voltage": ("battery_voltage", "battery_power_kw", "cell_temp", "soc"),
    "Custom…": None,
}


def _scatter(df, x, y, color, size, labels):
    d = df.copy()
    for c in (x, y, color, size):
        if c and c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=[c for c in (x, y) if c in d.columns])
    if d.empty:
        return None
    kwargs = dict(x=x, y=y,
                  labels={k: labels.get(k, k) for k in d.columns},
                  color_continuous_scale="Turbo")
    if color in d.columns:
        kwargs["color"] = color
    if size in d.columns:
        s = d[size].clip(lower=0).fillna(0)
        d["_sz"] = 4 + (s / max(s.max(), 1)) * 16
        kwargs["size"] = "_sz"
        kwargs["size_max"] = 14
    fig = px.scatter(d, **kwargs)
    fig.update_traces(marker=dict(opacity=0.65, line=dict(width=0)))
    fig.update_layout(
        template=Config.PLOTLY_TEMPLATE, paper_bgcolor=Config.CHART_BACKGROUND,
        plot_bgcolor=Config.CHART_BACKGROUND, height=560,
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_colorbar=dict(title=labels.get(color, color)),
        font=dict(size=13),
    )
    fig.update_xaxes(title=labels.get(x, x), gridcolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(title=labels.get(y, y), gridcolor="rgba(255,255,255,0.06)")
    return fig


def main():
    UIComponents.inject_global_styles()
    data = load_telemetry()
    frames, labels, meta = data["frames"], data["labels"], data["meta"]

    st.title("Telemetry Explorer")
    st.caption("Detailed signal relationships from the anonymized fleet — battery and motor "
               "power, torque, voltage against SOC, speed and cell temperature. Colour is cell "
               "temperature, dot size is state of charge.")
    if meta.get("data_version"):
        st.caption(f":material/bolt: {meta.get('points', 0):,} points · {meta.get('n_cars', 0)} cars · "
                   f"data version {meta['data_version']}.")

    if not frames:
        st.warning("No telemetry artifact found. Run `python -m etl.export_telemetry`.")
        return

    c1, c2 = st.columns([2, 3])
    car = c1.selectbox("Car", list(frames.keys()),
                       format_func=lambda k: k[:8])
    preset = c2.selectbox("View", list(PRESETS.keys()))
    df = frames[car]
    avail = [col for col in df.columns if col in labels]

    if PRESETS[preset] is None:
        cc = st.columns(4)
        x = cc[0].selectbox("X", avail, index=avail.index("soc") if "soc" in avail else 0)
        y = cc[1].selectbox("Y", avail, index=avail.index("battery_power_kw") if "battery_power_kw" in avail else 0)
        color = cc[2].selectbox("Colour", ["(none)"] + avail,
                                index=(avail.index("cell_temp") + 1) if "cell_temp" in avail else 0)
        size = cc[3].selectbox("Size", ["(none)"] + avail,
                               index=(avail.index("soc") + 1) if "soc" in avail else 0)
        color = None if color == "(none)" else color
        size = None if size == "(none)" else size
    else:
        x, y, color, size = PRESETS[preset]

    fig = _scatter(df, x, y, color, size, labels)
    if fig is None:
        st.info("This car has no data for the selected axes.")
    else:
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"{labels.get(y, y)} vs {labels.get(x, x)} · colour = {labels.get(color, color)} "
                   f"· size = {labels.get(size, size)}")


main()
