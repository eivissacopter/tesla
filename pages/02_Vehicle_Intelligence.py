"""Tesla Vehicle Intelligence reference and resolver page."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data.battery_chronology import BatteryChronologyClient
from src.data.vehicle_intelligence import VehicleIntelligenceClient
from src.data.wltp import WltpReference
from src.ui import UIComponents
from src.utils import PlotBuilder


st.set_page_config(
    page_title='Tesla Vehicle Intelligence',
    page_icon=':mag:',
    layout='wide'
)


def main():
    """Main page entry point."""
    UIComponents.inject_global_styles()
    st.title('Tesla Vehicle Intelligence')
    st.caption('Decode Tesla battery, motors, release family, and registration clues in one place.')


    resolver_tab, wltp_tab, releases_tab, hsn_tab, motors_tab, unicorns_tab = st.tabs([
        'Resolver', 'WLTP', 'VC/VS Timeline', 'HSN/TSN', 'Motors', 'Unicorns'
    ])

    with resolver_tab:
        _render_resolver()
    with wltp_tab:
        _render_wltp()
    with releases_tab:
        _render_release_timeline()
    with hsn_tab:
        _render_hsn_lookup()
    with motors_tab:
        _render_motor_reference()
    with unicorns_tab:
        _render_unicorns()

    st.markdown('### Sources')
    st.markdown('- [Motor / Drive Units wiki](https://tff-forum.de/t/wiki-model-3-model-y-motoren-drive-units/190111)')
    st.markdown('- [HSN / TSN wiki](https://tff-forum.de/t/wiki-hsn-tsn-schluesselnummern/281435)')
    st.markdown('- [Technical changes wiki](https://tff-forum.de/t/wiki-model-3-model-y-technische-veraenderungen/100784)')
    st.markdown('- [Battery chronology / Akkuwiki thread](https://tff-forum.de/t/wiki-akkuwiki-model-3-y-s-x-ct/107641)')


def _render_resolver() -> None:
    """Render the cross-source vehicle resolver."""
    st.markdown('### Vehicle Resolver')
    st.caption('Mix battery chronology, motor families, HSN/TSN registration data, and the VC/VS release timeline into one identity summary.')

    market = 'Europe'
    model_options = BatteryChronologyClient.list_models(market)
    default_model = 'Model 3' if 'Model 3' in model_options else model_options[0]

    col1, col2, col3, col4 = st.columns(4)
    model = col1.selectbox('Model', model_options, index=model_options.index(default_model))
    trim_options = BatteryChronologyClient.list_trims(market, model)
    trim = col2.selectbox('Trim', trim_options, index=0)
    drivetrain_options = BatteryChronologyClient.list_drivetrains(market, model, trim)
    drivetrain = col3.selectbox('Drive', drivetrain_options, index=0)
    year_options = BatteryChronologyClient.available_years(market, model)
    year = col4.selectbox('Year', year_options, index=len(year_options) - 1)

    col5, col6, col7, col8 = st.columns(4)
    quarter = col5.selectbox('Quarter', [1, 2, 3, 4], format_func=lambda value: f'Q{value}', index=0)
    release_options = [''] + VehicleIntelligenceClient.list_release_codes()
    version_code = col6.selectbox('VC/VS Code', release_options, index=0, format_func=lambda value: 'Optional' if value == '' else value)
    tsn_options = [''] + VehicleIntelligenceClient.list_tsn_options(model)
    tsn = col7.selectbox('TSN', tsn_options, index=0, format_func=lambda value: 'Optional' if value == '' else value)
    show_tables = col8.checkbox('Show Resolver Tables', value=True)

    result = VehicleIntelligenceClient.resolve_vehicle(
        market=market,
        model=model,
        trim=trim,
        drivetrain=drivetrain,
        year=year,
        quarter=quarter,
        version_code=version_code,
        tsn=tsn,
    )
    summary = result['summary']

    top1, top2, top3, top4, top5, top6 = st.columns(6)
    top1.metric('Likely Pack', _metric_value(summary['Likely Pack']))
    top2.metric('Chemistry', _metric_value(summary['Chemistry']))
    top3.metric('Front Motor', _metric_value(summary['Front Motor']))
    top4.metric('Rear Motor', _metric_value(summary['Rear Motor']))
    top5.metric('Architecture', _metric_value(summary['Pack Architecture']))
    top6.metric('Release', _metric_value(summary['Release Family']))

    mid1, mid2, mid3, mid4, mid5, mid6 = st.columns(6)
    mid1.metric('Battery Code', _metric_value(summary['Battery Code']))
    mid2.metric('Plant', _metric_value(summary['Plant']))
    mid3.metric('DU Category', _metric_value(summary['DU Category']))
    mid4.metric('Release Code', _metric_value(summary['Release Code']))
    mid5.metric('Insurance Power', _metric_value(summary['Insurance Power']))
    mid6.metric('30 Min Power', _metric_value(summary['30 Minute Power']))

    chemistry_guidance = BatteryChronologyClient.chemistry_guidance(summary['Chemistry'])
    if chemistry_guidance:
        st.info(chemistry_guidance)

    if result['notes']:
        st.markdown('### Notes')
        for note in result['notes']:
            st.write(f'- {note}')

    if show_tables:
        _render_resolver_tables(result)


def _render_resolver_tables(result: dict) -> None:
    """Render detailed resolver tables."""
    if not result['battery_candidates'].empty:
        st.markdown('#### Battery Candidates')
        battery_df = result['battery_candidates'][[
            'battery_label', 'battery_code', 'chemistry', 'plant', 'year_from', 'quarter_from', 'year_to', 'quarter_to', 'confidence', 'match_type'
        ]].rename(columns={
            'battery_label': 'Battery',
            'battery_code': 'Code',
            'chemistry': 'Chemistry',
            'plant': 'Plant',
            'year_from': 'From Year',
            'quarter_from': 'From Q',
            'year_to': 'To Year',
            'quarter_to': 'To Q',
            'confidence': 'Confidence',
            'match_type': 'Match',
        })
        st.dataframe(battery_df, use_container_width=True, hide_index=True)

    if not result['identity_candidates'].empty:
        st.markdown('#### Vehicle Identity Candidates')
        identity_df = result['identity_candidates'][[
            'release_family', 'release_code', 'front_motor', 'rear_motor', 'du_category', 'pack_architecture', 'confidence', 'match_type', 'notes'
        ]].rename(columns={
            'release_family': 'Release Family',
            'release_code': 'Release Code',
            'front_motor': 'Front Motor',
            'rear_motor': 'Rear Motor',
            'du_category': 'DU Category',
            'pack_architecture': 'Architecture',
            'confidence': 'Confidence',
            'match_type': 'Match',
            'notes': 'Notes',
        })
        st.dataframe(identity_df, use_container_width=True, hide_index=True)

    if not result['tsn_matches'].empty:
        st.markdown('#### HSN/TSN Match')
        st.dataframe(result['tsn_matches'], use_container_width=True, hide_index=True)

    if not result['release_match'].empty:
        st.markdown('#### VC/VS Release Match')
        release_df = result['release_match'].copy()
        if 'effective_date' in release_df.columns:
            release_df['effective_date'] = pd.to_datetime(release_df['effective_date']).dt.date
        st.dataframe(release_df, use_container_width=True, hide_index=True)


def _render_release_timeline() -> None:
    """Render the VC/VS release timeline."""
    st.markdown('### VC/VS Timeline')
    release_df = VehicleIntelligenceClient.get_release_df().copy()
    if release_df.empty:
        st.info('No VC/VS data available.')
        return

    scope_options = sorted(release_df['model_scope'].dropna().unique().tolist())
    selected_scope = st.multiselect('Model Scope', scope_options, default=[])
    if selected_scope:
        release_df = release_df[release_df['model_scope'].isin(selected_scope)]

    release_df['effective_date'] = pd.to_datetime(release_df['effective_date']).dt.date
    st.dataframe(
        release_df.rename(columns={
            'version_code': 'Code',
            'effective_date': 'Date',
            'release_name': 'Release',
            'pack_architecture': 'Architecture',
            'model_scope': 'Scope',
            'highlights': 'Highlights',
            'notes': 'Notes',
        }),
        use_container_width=True,
        hide_index=True,
    )


def _render_hsn_lookup() -> None:
    """Render the HSN/TSN lookup table."""
    st.markdown('### HSN / TSN Lookup')
    st.caption('This is most useful for German users who have registration papers but not the full approval documents.')

    hsn_df = VehicleIntelligenceClient.get_hsn_tsn_df().copy()
    if hsn_df.empty:
        st.info('No HSN/TSN data available.')
        return

    col1, col2 = st.columns(2)
    model_options = sorted(hsn_df['model'].dropna().unique().tolist())
    selected_models = col1.multiselect('Model Filter', model_options, default=[])
    tsn_query = col2.text_input('TSN Search', value='').strip().upper()

    if selected_models:
        hsn_df = hsn_df[hsn_df['model'].isin(selected_models)]
    if tsn_query:
        hsn_df = hsn_df[hsn_df['tsn'].str.upper().str.contains(tsn_query, na=False)]

    st.dataframe(hsn_df, use_container_width=True, hide_index=True)


def _render_motor_reference() -> None:
    """Render the motor reference table and quick lookup."""
    st.markdown('### Motor Reference')
    motor_df = VehicleIntelligenceClient.get_motor_df().copy()
    if motor_df.empty:
        st.info('No motor data available.')
        return

    motor_codes = motor_df['motor_code'].dropna().tolist()
    selected_motor = st.selectbox('Motor Code', [''] + motor_codes, index=0, format_func=lambda value: 'Pick a motor code' if value == '' else value)
    if selected_motor:
        selected_df = motor_df[motor_df['motor_code'] == selected_motor].copy()
        if not selected_df.empty:
            row = selected_df.iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric('Position', _metric_value(row['position']))
            col2.metric('DU Category', _metric_value(row['du_category']))
            col3.metric('Peak Power', _metric_value(f"{row['max_power_kw']} kW" if pd.notna(row['max_power_kw']) else None))
            col4.metric('30 Min Power', _metric_value(f"{row['power_30_min_kw']} kW" if pd.notna(row['power_30_min_kw']) else None))
            st.write(row['notes'])

    st.dataframe(motor_df, use_container_width=True, hide_index=True)
    st.info('Quick rule of thumb: Cat 4 rear motors usually mean noticeably higher insurance power and stronger sustained output than the older base-motor families.')


def _render_unicorns() -> None:
    """Render the curated unicorn list."""
    st.markdown('### Unicorn Finder')
    st.caption('These are standout combinations explicitly called out in the technical-changes wiki because they mix rare hardware in a particularly attractive way.')

    unicorn_df = VehicleIntelligenceClient.get_unicorn_df().copy()
    if unicorn_df.empty:
        st.info('No unicorn data available.')
        return

    st.dataframe(unicorn_df, use_container_width=True, hide_index=True)


def _metric_value(value) -> str:
    """Format nullable metric values consistently."""
    if value is None:
        return 'n/a'
    if isinstance(value, float) and pd.isna(value):
        return 'n/a'
    value_str = str(value).strip()
    return value_str if value_str else 'n/a'


def _render_wltp() -> None:
    """Compare WLTP range and consumption across packs, trims, and wheel sizes."""
    st.markdown('### WLTP Range & Efficiency')
    st.caption(
        'Homologated WLTP figures per variant and wheel size. WLTP consumption is '
        'a European test cycle value and is distinct from the EPA-based rated constant.'
    )

    df = WltpReference.get_df()

    col1, col2, col3 = st.columns(3)
    sel_models = col1.multiselect('Model', sorted(df['Model'].unique()), default=[])
    sel_trims = col2.multiselect('Trim', sorted(df['Trim'].unique()), default=[])
    sel_wheels = col3.multiselect('Wheel size', sorted(df['Wheel Label'].unique()), default=[])

    view = df.copy()
    if sel_models:
        view = view[view['Model'].isin(sel_models)]
    if sel_trims:
        view = view[view['Trim'].isin(sel_trims)]
    if sel_wheels:
        view = view[view['Wheel Label'].isin(sel_wheels)]

    if view.empty:
        st.info('No variants match the current filters.')
        return

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric('Configurations', len(view))
    best = view.loc[view['Range_km'].idxmax()]
    metric2.metric('Longest range', f"{int(best['Range_km'])} km", help=best['Label'])
    efficient = view.dropna(subset=['Wh_km'])
    if not efficient.empty:
        low = efficient.loc[efficient['Wh_km'].idxmin()]
        metric3.metric('Most efficient', f"{low['Wh_km']:.0f} Wh/km", help=low['Label'])

    # Range, coloured by consumption (greener = more efficient).
    ranked = view.sort_values('Range_km')
    range_fig = go.Figure(go.Bar(
        x=ranked['Range_km'],
        y=ranked['Label'],
        orientation='h',
        marker=dict(
            color=ranked['Wh_km'],
            colorscale='RdYlGn_r',
            colorbar=dict(title='Wh/km'),
            line=dict(width=0.5, color='rgba(255,255,255,0.2)'),
        ),
        customdata=ranked[['Config', 'Wh_km', 'Battery', 'Chemistry']].to_numpy(),
        hovertemplate=(
            '<b>%{y}</b><br>%{customdata[0]}<br>Range: %{x} km'
            '<br>Consumption: %{customdata[1]} Wh/km'
            '<br>Pack: %{customdata[2]} (%{customdata[3]})<extra></extra>'
        ),
    ))
    range_fig.update_layout(
        xaxis_title='WLTP range [km]',
        yaxis_title=None,
        height=max(320, 22 * len(ranked)),
        margin=dict(l=20, r=20, t=30, b=20),
    )
    PlotBuilder._apply_theme(range_fig)
    st.plotly_chart(range_fig, width='stretch')

    # Efficiency frontier: consumption vs range.
    scatter_df = view.dropna(subset=['Wh_km'])
    if not scatter_df.empty:
        st.markdown('#### Consumption vs. range')
        eff_fig = px.scatter(
            scatter_df,
            x='Wh_km',
            y='Range_km',
            color='Model',
            symbol='Drive',
            hover_name='Label',
            hover_data={'Battery': True, 'Chemistry': True, 'Wheel Label': True, 'Wh_km': True, 'Range_km': True},
            labels={'Wh_km': 'WLTP consumption [Wh/km]', 'Range_km': 'WLTP range [km]'},
            render_mode='svg',
        )
        eff_fig.update_traces(marker=dict(size=11, line=dict(width=0.5, color='rgba(255,255,255,0.4)')))
        eff_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        PlotBuilder._apply_theme(eff_fig)
        st.plotly_chart(eff_fig, width='stretch')

    # Wheel-size impact for individual variants homologated on more than one wheel.
    multi_wheel = view.groupby('Spec').filter(lambda group: group['Wheel'].nunique() > 1)
    if not multi_wheel.empty:
        st.markdown('#### Wheel-size impact on range')
        wheel_fig = px.bar(
            multi_wheel.sort_values(['Spec', 'Wheel']),
            x='Spec',
            y='Range_km',
            color='Wheel Label',
            barmode='group',
            labels={'Range_km': 'WLTP range [km]', 'Spec': '', 'Wheel Label': 'Wheel'},
        )
        wheel_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        PlotBuilder._apply_theme(wheel_fig)
        st.plotly_chart(wheel_fig, width='stretch')

    # RWD vs AWD efficiency. Consumption is the fair comparison (range is confounded
    # by battery size); AWD adds a front motor and typically consumes more.
    drive_df = view.dropna(subset=['Wh_km'])
    if drive_df['Drive'].nunique() > 1:
        st.markdown('#### RWD vs. AWD efficiency')
        st.caption('WLTP consumption by drivetrain. Range is omitted here because it is confounded by battery size.')
        drive_fig = px.box(
            drive_df,
            x='Drive',
            y='Wh_km',
            color='Model',
            points='all',
            labels={'Wh_km': 'WLTP consumption [Wh/km]', 'Drive': ''},
        )
        drive_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), boxmode='group')
        PlotBuilder._apply_theme(drive_fig)
        st.plotly_chart(drive_fig, width='stretch')

    table = view[['Model', 'Trim', 'Drive', 'Year', 'Variant', 'Battery', 'Chemistry',
                  'Wheel Label', 'Range_km', 'Wh_km']].rename(columns={
        'Wheel Label': 'Wheel', 'Range_km': 'WLTP Range [km]', 'Wh_km': 'WLTP [Wh/km]',
    })
    st.dataframe(table.sort_values('WLTP Range [km]', ascending=False),
                 use_container_width=True, hide_index=True)


if __name__ == '__main__':
    main()


