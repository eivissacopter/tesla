"""Tesla Battery Analysis - Refactored Dashboard."""
import streamlit as st
import plotly.io as pio

from src.config import Config
from src.data import GoogleSheetsClient
from src.models import FilterCriteria
from src.utils import BatteryDataProcessor, PlotBuilder
from src.ui import UIComponents


# Set page config as the first Streamlit command
st.set_page_config(
    page_title="Tesla Battery Analysis",
    page_icon=":battery:",
    layout="wide"
)

# Set default Plotly template
pio.templates.default = Config.PLOTLY_TEMPLATE


def main():
    """Main application entry point."""
    
    # Initialize data client
    sheets_client = GoogleSheetsClient()
    
    # Render header
    UIComponents.render_header()
    UIComponents.render_google_forms_banner()
    
    # Username search
    username = UIComponents.render_username_search()
    
    # Fetch data
    df, battery_pack_col = sheets_client.fetch_battery_data(username_filter=username)
    
    if df.empty:
        st.warning("No data available.")
        return
    
    # Display latest entries
    latest_entries = df.iloc[-3:][::-1]
    UIComponents.render_latest_entries(latest_entries)
    
    # Create filters
    tesla_models, versions, batteries = UIComponents.create_model_filters(df)
    
    # Initialize session state for filtered data
    if 'filtered_df' not in st.session_state:
        st.session_state.filtered_df = df.copy()
    
    # Apply model/version/battery filters
    if tesla_models or versions or batteries:
        filtered_df = df.copy()
        if tesla_models:
            filtered_df = filtered_df[filtered_df["Tesla"].isin(tesla_models)]
        if versions:
            filtered_df = filtered_df[filtered_df["Version"].isin(versions)]
        if batteries:
            filtered_df = filtered_df[filtered_df["Battery"].isin(batteries)]
        st.session_state.filtered_df = filtered_df
    else:
        st.session_state.filtered_df = df.copy()
    
    # Age and odometer filters
    min_age, max_age, min_odo, max_odo = UIComponents.create_age_odo_filters(
        st.session_state.filtered_df
    )
    
    # Axis selectors
    y_axis_data, x_axis_data = UIComponents.create_axis_selectors()
    
    # Trend line selector
    add_trend_line, trend_line_type = UIComponents.create_trend_line_selector()
    
    # Hide replaced packs
    hide_replaced_packs = UIComponents.create_hide_replaced_packs_filter()
    
    # Advanced filters
    daily_soc_min, daily_soc_max, dc_ratio_min, dc_ratio_max = UIComponents.create_nerdy_options(
        st.session_state.filtered_df
    )
    
    # Create filter criteria
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
    
    # Apply filters
    st.session_state.filtered_df = BatteryDataProcessor.apply_filters(
        df,
        criteria,
        battery_pack_col
    )
    
    # Cache refresh button
    UIComponents.render_cache_refresh_button()
    
    # Show filtered row count
    st.sidebar.write(f"Filtered Data Rows: {st.session_state.filtered_df.shape[0]}")
    
    # Determine column names based on selection
    y_column, y_label = _get_y_axis_config(y_axis_data)
    x_column, x_label = _get_x_axis_config(x_axis_data)
    
    # Prepare plot data
    plot_df = BatteryDataProcessor.prepare_plot_data(
        st.session_state.filtered_df,
        x_column,
        y_column,
        battery_pack_col
    )
    
    if plot_df.empty:
        st.warning("No data available for the selected criteria.")
        return
    
    # Determine color column for single battery filter
    color_column = None
    if len(batteries) == 1:
        if daily_soc_min is not None and daily_soc_max is not None:
            color_column = "Daily SOC Limit"
        elif dc_ratio_min is not None and dc_ratio_max is not None:
            color_column = "DC Ratio"
    
    # Create scatter plot
    fig = PlotBuilder.create_scatter_plot(
        plot_df,
        x_column,
        y_column,
        x_label,
        y_label,
        color_column=color_column
    )
    
    # Add trend lines if requested
    if add_trend_line and trend_line_type:
        battery_types = plot_df['Battery'].unique()
        fig = PlotBuilder.add_trend_lines(
            fig,
            plot_df,
            battery_types,
            x_column,
            y_column,
            trend_line_type
        )
    
    # Add Tesla retention line if applicable
    if x_axis_data == 'Odometer' and y_axis_data == 'Degradation':
        odometer_km, retention = BatteryDataProcessor.get_tesla_retention_line()
        fig = PlotBuilder.add_tesla_retention_line(fig, odometer_km, retention)
    
    # Display plot
    st.plotly_chart(fig, width="stretch")
    
    # SOH 70% projection
    if batteries:
        projections = BatteryDataProcessor.predict_soh_70(
            batteries,
            st.session_state.filtered_df,
            x_axis_data
        )
        UIComponents.render_soh_projections(projections, batteries)
    
    # Degradation per X bar chart
    _render_degradation_bar_chart(batteries, x_axis_data)
    
    # Battery info table
    _render_battery_info_table(sheets_client, batteries)
    
    # Sidebar footer
    UIComponents.render_sidebar_footer()


def _get_y_axis_config(y_axis_data: str):
    """Get Y-axis configuration.
    
    Args:
        y_axis_data: Y-axis selection.
        
    Returns:
        Tuple of (column_name, label).
    """
    if y_axis_data == 'Degradation':
        return 'Degradation', 'Degradation [%]'
    elif y_axis_data == 'Capacity':
        return 'Capacity Net Now', 'Capacity [kWh]'
    else:  # 'Rated Range'
        return 'Rated Range', 'Rated Range [km]'


def _get_x_axis_config(x_axis_data: str):
    """Get X-axis configuration.
    
    Args:
        x_axis_data: X-axis selection.
        
    Returns:
        Tuple of (column_name, label).
    """
    if x_axis_data == 'Age':
        return 'Age', 'Age [months]'
    elif x_axis_data == 'Odometer':
        return 'Odometer', 'Odometer [km]'
    else:  # 'Cycles'
        return 'Cycles', 'Cycles [n]'


def _render_degradation_bar_chart(batteries: list, x_axis_data: str):
    """Render degradation per X-axis bar chart.
    
    Args:
        batteries: List of selected batteries.
        x_axis_data: X-axis selection.
    """
    # Determine divisor and label
    if x_axis_data == 'Age':
        denominator_column = 'Age'
        x_label = 'Month'
        divisor = 1
    elif x_axis_data == 'Odometer':
        denominator_column = 'Odometer'
        x_label = '1000km]'
        divisor = 1000
    else:  # 'Cycles'
        denominator_column = 'Cycles'
        x_label = 'Cycle'
        divisor = 1
    
    # Calculate degradation per X
    degradation_df = BatteryDataProcessor.calculate_degradation_per_x(
        st.session_state.filtered_df,
        denominator_column,
        divisor
    )
    
    if degradation_df.empty:
        return
    
    # Group by battery or version
    if len(batteries) == 1:
        selected_battery = batteries[0]
        battery_data = degradation_df[degradation_df['Battery'] == selected_battery]
        avg_degradation = battery_data.groupby('Version')['DegradationPerX'].agg(['mean', 'count']).reset_index()
        avg_degradation['custom_text'] = avg_degradation.apply(lambda row: f"n={row['count']}", axis=1)
        avg_degradation['degradation_text'] = avg_degradation.apply(lambda row: f"{row['mean']:.2f}%", axis=1)
        avg_degradation = avg_degradation.sort_values(by='mean', ascending=True)
        
        bar_fig = PlotBuilder.create_bar_chart(
            avg_degradation,
            'mean',
            'Version',
            f'Average Degradation / {x_label}'
        )
    else:
        avg_degradation = degradation_df.groupby('Battery')['DegradationPerX'].agg(['mean', 'count']).reset_index()
        avg_degradation['custom_text'] = avg_degradation.apply(lambda row: f"n={row['count']}", axis=1)
        avg_degradation['degradation_text'] = avg_degradation.apply(lambda row: f"{row['mean']:.2f}%", axis=1)
        avg_degradation = avg_degradation.sort_values(by='mean', ascending=True)
        
        bar_fig = PlotBuilder.create_bar_chart(
            avg_degradation,
            'mean',
            'Battery',
            f'Average Degradation / {x_label}'
        )
    
    st.plotly_chart(bar_fig, width="stretch")


def _render_battery_info_table(sheets_client: GoogleSheetsClient, batteries: list):
    """Render battery pack information table.
    
    Args:
        sheets_client: Google Sheets client.
        batteries: List of selected batteries.
    """
    battery_info = sheets_client.fetch_battery_info()
    
    if battery_info.empty:
        return
    
    # Filter by selected batteries
    if batteries:
        selected_battery_info = battery_info[battery_info['Battery'].isin(batteries)]
    else:
        selected_battery_info = battery_info
    
    st.markdown("### Battery Pack Information")
    st.table(selected_battery_info.style.hide(axis='index'))


if __name__ == "__main__":
    main()
