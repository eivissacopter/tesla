"""Tesla Battery Analysis - Refactored Dashboard."""
import pandas as pd
import plotly.io as pio
import streamlit as st

from src.config import Config
from src.data import GoogleSheetsClient
from src.models import FilterCriteria
from src.utils import BatteryDataProcessor, PlotBuilder
from src.ui import UIComponents


st.set_page_config(
    page_title="Tesla Battery Analysis",
    page_icon=":battery:",
    layout="wide"
)

pio.templates.default = Config.PLOTLY_TEMPLATE


def main():
    """Main application entry point."""
    sheets_client = GoogleSheetsClient()

    UIComponents.render_header()
    UIComponents.render_google_forms_banner()

    username = UIComponents.render_username_search()
    df, battery_pack_col = sheets_client.fetch_battery_data(username_filter=username)

    if df.empty:
        st.warning("No data available.")
        return

    UIComponents.render_latest_entries(df.iloc[-3:][::-1])

    tesla_models, versions, batteries = UIComponents.create_model_filters(df)
    filter_seed_df = _apply_basic_filters(df, tesla_models, versions, batteries)

    min_age, max_age, min_odo, max_odo = UIComponents.create_age_odo_filters(filter_seed_df)
    y_axis_data, x_axis_data = UIComponents.create_axis_selectors()
    add_trend_line, trend_line_type = UIComponents.create_trend_line_selector()
    hide_replaced_packs = UIComponents.create_hide_replaced_packs_filter()
    daily_soc_min, daily_soc_max, dc_ratio_min, dc_ratio_max = UIComponents.create_nerdy_options(filter_seed_df)

    criteria = FilterCriteria(
        tesla_models=tesla_models,
        versions=versions,
        batteries=batteries,
        min_age=min_age,
        max_age=max_age,
        min_odo=min_odo,
        max_odo=max_odo,
        hide_replaced_packs=hide_replaced_packs,
        daily_soc_min=daily_soc_min,
        daily_soc_max=daily_soc_max,
        dc_ratio_min=dc_ratio_min,
        dc_ratio_max=dc_ratio_max
    )

    filtered_df = BatteryDataProcessor.apply_filters(df, criteria, battery_pack_col)
    UIComponents.render_cache_refresh_button()
    st.sidebar.write(f"Filtered Data Rows: {filtered_df.shape[0]}")

    if filtered_df.empty:
        st.warning("No data available for the selected criteria.")
        return

    _render_overview_metrics(filtered_df)

    y_column, y_label = _get_y_axis_config(y_axis_data)
    x_column, x_label = _get_x_axis_config(x_axis_data)
    plot_df = BatteryDataProcessor.prepare_plot_data(filtered_df, x_column, y_column, battery_pack_col)

    if plot_df.empty:
        st.warning("No data available for the selected criteria.")
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
        color_column=color_column
    )

    if add_trend_line and trend_line_type:
        battery_types = sorted(plot_df['Battery'].dropna().unique().tolist()) if 'Battery' in plot_df.columns else []
        fig = PlotBuilder.add_trend_lines(
            fig,
            plot_df,
            battery_types,
            x_column,
            y_column,
            trend_line_type
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


def _apply_basic_filters(df: pd.DataFrame, tesla_models: list, versions: list, batteries: list) -> pd.DataFrame:
    """Apply the coarse-grained filters to derive slider ranges."""
    filtered_df = df.copy()
    if tesla_models and 'Tesla' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Tesla'].isin(tesla_models)]
    if versions and 'Version' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Version'].isin(versions)]
    if batteries and 'Battery' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Battery'].isin(batteries)]
    return filtered_df if not filtered_df.empty else df


def _render_overview_metrics(filtered_df: pd.DataFrame) -> None:
    """Render headline datanerd metrics for the current filter slice."""
    metrics = BatteryDataProcessor.calculate_overview_metrics(filtered_df)
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric('Entries', f"{metrics['entries']:,}")
    col2.metric('Users', f"{metrics['users']:,}")
    col3.metric('Battery Types', f"{metrics['batteries']:,}")
    col4.metric(
        'Median SOH',
        f"{metrics['median_soh']:.1f}%" if metrics['median_soh'] is not None else 'n/a'
    )
    col5.metric(
        'Median Degradation',
        f"{metrics['median_degradation']:.1f}%" if metrics['median_degradation'] is not None else 'n/a'
    )
    col6.metric(
        'Median ODO',
        f"{metrics['median_odometer']:,.0f} km" if metrics['median_odometer'] is not None else 'n/a'
    )


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

    if len(batteries) == 1:
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
            mime='text/csv'
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


if __name__ == "__main__":
    main()
