"""Render the Fleet Telemetry charts to static PNGs from the real artifact.

Used to preview the visuals without a running Streamlit server (whose
persistent websocket defeats headless screenshot tools).
"""
import json
import os
import sys

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

CHEM_COLORS = {"NCA": "#ff2b2b", "NMC": "#0068c9", "LFP": "#29b09d", "Unknown": "#808495"}
BG = "#0B0E14"
TEMPLATE = "plotly_dark"


def theme(fig, height, ylab, xlab, title):
    fig.update_layout(
        template=TEMPLATE, paper_bgcolor=BG, plot_bgcolor=BG, height=height,
        title=dict(text=title, font=dict(size=18, color="#E6E9EF")),
        margin=dict(l=60, r=20, t=60, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        font=dict(size=13, color="#E6E9EF"),
    )
    fig.update_yaxes(title_text=ylab, gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    fig.update_xaxes(title_text=xlab, gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    return fig


def main(artifact, outdir):
    os.makedirs(outdir, exist_ok=True)
    d = json.load(open(artifact, encoding="utf-8"))
    df = pd.DataFrame(d["fleet"])
    series = d["soh_series"]
    meta = {r["car"]: r for _, r in df.iterrows()}

    # 1) SOH over time
    fig = go.Figure()
    for car, s in series.items():
        if not s or len(s) < 2 or car not in meta:
            continue
        m = meta[car]
        chem = m.get("chemistry") or "Unknown"
        label = f"{m.get('model','?')} {m.get('trim') or ''} · {chem}".strip()
        fig.add_trace(go.Scatter(
            x=[p["month"] for p in s], y=[p["soh_pct"] for p in s], mode="lines",
            name=label, line=dict(width=2, color=CHEM_COLORS.get(chem, "#808495")), opacity=0.9))
    fig.add_hline(y=100, line=dict(color="rgba(255,255,255,0.25)", dash="dot"))
    fig.add_hline(y=70, line=dict(color="rgba(255,43,43,0.5)", dash="dash"),
                  annotation_text="70% warranty floor", annotation_position="bottom left")
    theme(fig, 480, "State of Health (%)", "Month", "State-of-Health over time — measured, anonymized fleet")
    fig.write_image(os.path.join(outdir, "soh_over_time.png"), scale=2, width=1100)

    # 2) SOH vs odometer
    e = df.copy()
    for c in ("soh_pct", "odometer_km", "design_kwh"):
        e[c] = pd.to_numeric(e[c], errors="coerce")
    e = e.dropna(subset=["soh_pct", "odometer_km"])
    fig2 = px.scatter(e, x="odometer_km", y="soh_pct", color="chemistry", size="design_kwh",
                      size_max=24, color_discrete_map=CHEM_COLORS,
                      hover_data=["model", "trim", "model_year", "pack"])
    fig2.update_traces(marker=dict(line=dict(width=1, color="rgba(0,0,0,0.4)")))
    theme(fig2, 430, "State of Health (%)", "Odometer (km)", "Degradation vs distance (bubble = pack kWh)")
    fig2.write_image(os.path.join(outdir, "soh_vs_odo.png"), scale=2, width=1100)

    # 3) Charging fingerprint
    g = df.copy()
    for c in ("dc_share_pct", "max_charge_kw", "charge_sessions"):
        g[c] = pd.to_numeric(g[c], errors="coerce")
    g = g.dropna(subset=["dc_share_pct", "max_charge_kw"])
    fig3 = px.scatter(g, x="dc_share_pct", y="max_charge_kw", color="chemistry",
                      size="charge_sessions", size_max=30, color_discrete_map=CHEM_COLORS,
                      hover_data=["model", "trim", "charge_sessions"])
    fig3.update_traces(marker=dict(line=dict(width=1, color="rgba(0,0,0,0.4)")))
    theme(fig3, 430, "Peak charge power (kW)", "DC fast-charge share (%)", "Charging fingerprint (bubble = sessions)")
    fig3.write_image(os.path.join(outdir, "charging_fingerprint.png"), scale=2, width=1100)
    print("rendered:", os.listdir(outdir))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "artifacts/fleet.json",
         sys.argv[2] if len(sys.argv) > 2 else "artifacts/preview")
