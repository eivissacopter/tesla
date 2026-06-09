"""Tesla Battery Analysis - Refactored Dashboard."""
import pandas as pd
import plotly.io as pio
import streamlit as st

from src.config import Config
from src.data.battery_chronology import BatteryChronologyClient
from src.data.google_sheets import GoogleSheetsClient
from src.models import FilterCriteria
from src.utils import BatteryDataProcessor, PlotBuilder
from src.ui import UIComponents


st.set_page_config(
    page_title='Tesla Battery Analysis',
    page_icon=':battery:',
    layout='wide'
)

pio.templates.default = Config.PLOTLY_TEMPLATE


def main():
    """Main application entry point."""
    sheets_client = GoogleSheetsClient()

    UIComponents.inject_global_styles()
    UIComponents.render_header()
    UIComponents.render_google_forms_banner()

    username = UIComponents.render_username_search()
    df, battery_pack_col = sheets_client.fetch_battery_data(username_filter=username)

    if df.empty:
        st.warning('No data available.')
        return

    df = BatteryChronologyClient.annotate_dataframe(df)
    UIComponents.render_latest_entries(df.iloc[-3:][::-1])

    with st.sidebar:
        filters_tab, energy_tab = st.tabs(['Filters', 'Energy Monitor'])

    tesla_models, versions, batteries = UIComponents.create_model_filters(df, container=filters_tab)
    filter_seed_df = _apply_basic_filters(df, tesla_models, versions, batteries)
    chronology_chemistries, chronology_plants, chronology_codes = UIComponents.create_chronology_filters(
        filter_seed_df,
        container=filters_tab,
    )
    filter_seed_df = _apply_basic_filters(
        df,
        tesla_models,
        versions,
        batteries,
        chronology_chemistries,
        chronology_plants,
        chronology_codes,
    )

    min_age, max_age, min_odo, max_odo = UIComponents.create_age_odo_filters(filter_seed_df, container=filters_tab)
    y_axis_data, x_axis_data = UIComponents.create_axis_selectors(container=filters_tab)
    add_trend_line, trend_line_type = UIComponents.create_trend_line_selector(container=filters_tab)
    hide_replaced_packs = UIComponents.create_hide_replaced_packs_filter(container=filters_tab)
    daily_soc_min, daily_soc_max, dc_ratio_min, dc_ratio_max = UIComponents.create_nerdy_options(
        filter_seed_df,
        container=filters_tab,
    )
    UIComponents.render_energy_monitor_calculator(container=energy_tab)

    criteria = FilterCriteria(
        tesla_models=tesla_models,
        versions=versions,
        batteries=batteries,
        min_age=min_age,
        max_age=max_age,
        min_odo=min_odo,
        max_odo=max_odo,
        chronology_chemistries=chronology_chemistries,
        chronology_plants=chronology_plants,
        chronology_codes=chronology_codes,
        hide_replaced_packs=hide_replaced_packs,
        daily_soc_min=daily_soc_min,
        daily_soc_max=daily_soc_max,
        dc_ratio_min=dc_ratio_min,
        dc_ratio_max=dc_ratio_max,
    )

    filtered_df = BatteryDataProcessor.apply_filters(df, criteria, battery_pack_col)
    UIComponents.render_cache_refresh_button(container=filters_tab)
    filters_tab.write(f'Filtered Data Rows: {filtered_df.shape[0]}')

    if filtered_df.empty:
        st.warning('No data available for the selected criteria.')
        return

    _render_overview_metrics(filtered_df)
    _render_chronology_resolver(tesla_models, versions, filtered_df)

    y_column, y_label = _get_y_axis_config(y_axis_data)
    x_column, x_label = _get_x_axis_config(x_axis_data)
    plot_df = BatteryDataProcessor.prepare_plot_data(filtered_df, x_column, y_column, battery_pack_col)

    if plot_df.empty:
        st.warning('No data available for the selected criteria.')
        return

    color_column = None
    if len(batteries) == 1:
        if daily_soc_min is not None and daily_soc_max is not None:
            color_column = 'Daily SOC Limit'
        elif dc_ratio_min is not None and dc_ratio_max is not None:
            color_column = 'DC Ratio'

    fig = PlotBuilder.create_scatter_plot(
        plot_df,
        x_column,
        y_column,
        x_label,
        y_label,
        color_column=color_column,
    )

    if add_trend_line and trend_line_type:
        battery_types = sorted(plot_df['Battery'].dropna().unique().tolist()) if 'Battery' in plot_df.columns else []
        fig = PlotBuilder.add_trend_lines(
            fig,
            plot_df,
            battery_types,
            x_column,
            y_column,
            trend_line_type,
        )

    if x_axis_data == 'Odometer' and y_axis_data == 'Degradation':
        odometer_km, retention = BatteryDataProcessor.get_tesla_retention_line()
        fig = PlotBuilder.add_tesla_retention_line(fig, odometer_km, retention)

    st.plotly_chart(fig, width='stretch')

    if batteries:
        projections = BatteryDataProcessor.predict_soh_70(batteries, filtered_df, x_axis_data)
        UIComponents.render_soh_projections(projections, batteries)

    _render_degradation_bar_chart(filtered_df, batteries, x_axis_data)
    _render_fleet_summary(filtered_df)
    _render_filtered_dataset(filtered_df)
    _render_battery_info_table(sheets_client, batteries)
    UIComponents.render_sidebar_footer()


def _apply_basic_filters(
    df: pd.DataFrame,
    tesla_models: list,
    versions: list,
    batteries: list,
    chronology_chemistries: list | None = None,
    chronology_plants: list | None = None,
    chronology_codes: list | None = None,
) -> pd.DataFrame:
    """Apply the coarse-grained filters to derive slider ranges."""
    filtered_df = df.copy()
    if tesla_models and 'Tesla' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Tesla'].isin(tesla_models)]
    if versions and 'Version' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Version'].isin(versions)]
    if batteries and 'Battery' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Battery'].isin(batteries)]
    if chronology_chemistries and 'Chronology Chemistry' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Chronology Chemistry'].isin(chronology_chemistries)]
    if chronology_plants and 'Chronology Plant' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Chronology Plant'].isin(chronology_plants)]
    if chronology_codes and 'Chronology Code' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Chronology Code'].isin(chronology_codes)]
    return filtered_df if not filtered_df.empty else df


def _render_overview_metrics(filtered_df: pd.DataFrame) -> None:
    """Render headline datanerd metrics for the current filter slice."""
    metrics = BatteryDataProcessor.calculate_overview_metrics(filtered_df)
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric('Entries', f"{metrics['entries']:,}")
    col2.metric('Users', f"{metrics['users']:,}")
    col3.metric('Battery Types', f"{metrics['batteries']:,}")
    col4.metric('Median SOH', f"{metrics['median_soh']:.1f}%" if metrics['median_soh'] is not None else 'n/a')
    col5.metric('Median Degradation', f"{metrics['median_degradation']:.1f}%" if metrics['median_degradation'] is not None else 'n/a')
    col6.metric('Median ODO', f"{metrics['median_odometer']:,.0f} km" if metrics['median_odometer'] is not None else 'n/a')


def _render_chronology_resolver(tesla_models: list, versions: list, filtered_df: pd.DataFrame) -> None:
    """Render a chronology-based battery resolver using the provided Akkuchronik snapshot."""
    st.markdown('### Akkuchronik Resolver')
    st.caption('Resolve likely battery, chemistry, and plant from model, trim, and delivery period.')

    market_options = ['Europe']
    default_model = _guess_model_default(tesla_models)
    market = st.selectbox('Market', market_options, index=0, key='chronik_market')

    model_options = BatteryChronologyClient.list_models(market)
    model_index = model_options.index(default_model) if default_model in model_options else 0
    model = st.selectbox('Model', model_options, index=model_index, key='chronik_model')

    trim_options = BatteryChronologyClient.list_trims(market, model)
    default_trim = _guess_trim_default(versions, trim_options)
    trim_index = trim_options.index(default_trim) if default_trim in trim_options else 0

    col1, col2, col3, col4 = st.columns(4)
    trim = col1.selectbox('Trim', trim_options, index=trim_index, key='chronik_trim')

    drivetrain_options = BatteryChronologyClient.list_drivetrains(market, model, trim)
    default_drive = _guess_drivetrain_default(versions, drivetrain_options)
    drive_index = drivetrain_options.index(default_drive) if default_drive in drivetrain_options else 0
    drivetrain = col2.selectbox('Drive', drivetrain_options, index=drive_index, key='chronik_drive')

    year_options = BatteryChronologyClient.available_years(market, model)
    year = col3.selectbox('Year', year_options, index=len(year_options) - 1, key='chronik_year')
    quarter = col4.selectbox('Quarter', [1, 2, 3, 4], format_func=lambda value: f'Q{value}', index=0, key='chronik_quarter')

    candidates = BatteryChronologyClient.resolve_candidates(
        market=market,
        model=model,
        trim=trim,
        drivetrain=drivetrain,
        year=year,
        quarter=quarter,
    )

    if candidates.empty:
        st.info('No Akkuchronik candidate found for the current selection yet.')
    else:
        top_candidate = candidates.iloc[0]
        top1, top2, top3, top4 = st.columns(4)
        top1.metric('Likely Pack', top_candidate['battery_label'])
        top2.metric('Battery Code', top_candidate['battery_code'] or 'n/a')
        top3.metric('Chemistry', top_candidate['chemistry'])
        top4.metric('Plant', top_candidate['plant'])

        guidance = BatteryChronologyClient.chemistry_guidance(top_candidate['chemistry'])
        if guidance:
            st.info(guidance)

        if not filtered_df.empty and 'Chronology Pack' in filtered_df.columns:
            pack_matches = int(filtered_df['Chronology Pack'].fillna('').eq(top_candidate['battery_label']).sum())
            st.caption(f"{pack_matches} filtered entries currently resolve to this pack guess.")

        display_columns = [
            'battery_label', 'battery_code', 'chemistry', 'plant',
            'year_from', 'quarter_from', 'year_to', 'quarter_to', 'confidence', 'match_type', 'notes'
        ]
        st.dataframe(
            candidates[display_columns].rename(columns={
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
                'notes': 'Notes',
            }),
            use_container_width=True,
            hide_index=True,
        )

    with st.expander('Battery Code Taxonomy'):
        code_df = BatteryChronologyClient.get_battery_code_df()
        st.dataframe(code_df, use_container_width=True, hide_index=True)


def _guess_model_default(tesla_models: list) -> str:
    """Guess the chronology model selector from the active dashboard filter."""
    if len(tesla_models) == 1:
        model = tesla_models[0]
        if model in ['Model 3', 'Model Y']:
            return model
    return 'Model 3'


def _guess_trim_default(versions: list, trim_options: list[str]) -> str:
    """Guess a chronology trim from the active dashboard version filter."""
    if len(versions) != 1:
        return trim_options[0]

    version = versions[0].lower()
    if 'plaid' in version and 'Plaid' in trim_options:
        return 'Plaid'
    if 'performance' in version and 'Performance' in trim_options:
        return 'Performance'
    if ('long range' in version or 'lr' in version) and 'Long Range' in trim_options:
        return 'Long Range'
    if ('standard' in version or 'rwd' in version or 'sr' in version) and 'Standard' in trim_options:
        return 'Standard'
    return trim_options[0]


def _guess_drivetrain_default(versions: list, drivetrain_options: list[str]) -> str:
    """Guess a chronology drivetrain from the active dashboard version filter."""
    if len(versions) != 1:
        return drivetrain_options[0]

    version = versions[0].lower()
    if ('performance' in version or 'plaid' in version or 'awd' in version or 'dual' in version) and 'AWD' in drivetrain_options:
        return 'AWD'
    if ('rwd' in version or 'standard' in version or 'sr' in version) and 'RWD' in drivetrain_options:
        return 'RWD'
    return drivetrain_options[0]


def _get_y_axis_config(y_axis_data: str):
    """Get Y-axis configuration."""
    if y_axis_data == 'Degradation':
        return 'Degradation', 'Degradation [%]'
    if y_axis_data == 'Capacity':
        return 'Capacity Net Now', 'Capacity [kWh]'
    return 'Rated Range', 'Rated Range [km]'


def _get_x_axis_config(x_axis_data: str):
    """Get X-axis configuration."""
    if x_axis_data == 'Age':
        return 'Age', 'Age [months]'
    if x_axis_data == 'Odometer':
        return 'Odometer', 'Odometer [km]'
    return 'Cycles', 'Cycles [n]'


def _render_degradation_bar_chart(filtered_df: pd.DataFrame, batteries: list, x_axis_data: str):
    """Render degradation per X-axis bar chart."""
    if x_axis_data == 'Age':
        denominator_column = 'Age'
        x_label = 'Month'
        divisor = 1
    elif x_axis_data == 'Odometer':
        denominator_column = 'Odometer'
        x_label = '1000 km'
        divisor = 1000
    else:
        denominator_column = 'Cycles'
        x_label = 'Cycle'
        divisor = 1

    degradation_df = BatteryDataProcessor.calculate_degradation_per_x(filtered_df, denominator_column, divisor)
    if degradation_df.empty:
        return

    if len(batteries) == 1 and 'Version' in degradation_df.columns:
        battery_data = degradation_df[degradation_df['Battery'] == batteries[0]]
        avg_degradation = battery_data.groupby('Version')['DegradationPerX'].agg(['mean', 'count']).reset_index()
        avg_degradation['custom_text'] = 'n=' + avg_degradation['count'].astype(str)
        avg_degradation['degradation_text'] = avg_degradation['mean'].map(lambda value: f"{value:.2f}%")
        avg_degradation = avg_degradation.sort_values(by='mean', ascending=True)
        bar_fig = PlotBuilder.create_bar_chart(avg_degradation, 'mean', 'Version', f'Average Degradation / {x_label}')
    else:
        avg_degradation = degradation_df.groupby('Battery')['DegradationPerX'].agg(['mean', 'count']).reset_index()
        avg_degradation['custom_text'] = 'n=' + avg_degradation['count'].astype(str)
        avg_degradation['degradation_text'] = avg_degradation['mean'].map(lambda value: f"{value:.2f}%")
        avg_degradation = avg_degradation.sort_values(by='mean', ascending=True)
        bar_fig = PlotBuilder.create_bar_chart(avg_degradation, 'mean', 'Battery', f'Average Degradation / {x_label}')

    st.plotly_chart(bar_fig, width='stretch')


def _render_fleet_summary(filtered_df: pd.DataFrame) -> None:
    """Render a grouped summary table for the current slice."""
    summary_df = BatteryDataProcessor.build_battery_summary(filtered_df)
    if summary_df.empty:
        return

    st.markdown('### Fleet Summary')
    st.dataframe(summary_df, use_container_width=True, hide_index=True)


def _render_filtered_dataset(filtered_df: pd.DataFrame) -> None:
    """Expose the filtered dataset for deep dives and export."""
    with st.expander('Filtered Dataset'):
        st.caption('Use this to inspect the exact rows behind the current charts and metrics.')
        st.download_button(
            'Download filtered CSV',
            data=filtered_df.to_csv(index=False).encode('utf-8'),
            file_name='teslatech_filtered_dataset.csv',
            mime='text/csv',
        )
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)


def _render_battery_info_table(sheets_client: GoogleSheetsClient, batteries: list):
    """Render battery pack information table."""
    battery_info = sheets_client.fetch_battery_info()
    if battery_info.empty:
        return

    if batteries and 'Battery' in battery_info.columns:
        selected_battery_info = battery_info[battery_info['Battery'].isin(batteries)]
    else:
        selected_battery_info = battery_info

    st.markdown('### Battery Pack Information')
    st.table(selected_battery_info.style.hide(axis='index'))


if __name__ == '__main__':
    main()

