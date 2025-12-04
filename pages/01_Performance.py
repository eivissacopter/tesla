"""Tesla Performance Analysis - Refactored Page."""
import streamlit as st
import pandas as pd
from scipy.ndimage import uniform_filter1d
from typing import List, Dict, Tuple

from src.config import Config
from src.data import PerformanceDataClient
from src.models import PerformanceFolder, PerformanceFileInfo
from src.utils import PlotBuilder
from src.ui import UIComponents


# Set page config
st.set_page_config(
    page_title="Tesla Performance Analysis",
    page_icon=":racing_car:",
    layout="wide"
)


def main():
    """Main application entry point."""
    
    # Render header
    UIComponents.render_performance_header()
    
    # Initialize data client
    perf_client = PerformanceDataClient()
    
    # Scan and classify folders
    classified_folders = perf_client.scan_and_classify_folders()
    
    if not classified_folders:
        st.error("The directory structure is empty. No options available.")
        return
    
    # Create dynamic filters
    selected_filters = {}
    
    # Model and Variant filters
    col1, col2 = st.sidebar.columns(2)
    models = get_unique_values(classified_folders, 'model', selected_filters)
    selected_model = col1.multiselect(
        "Model",
        models,
        default=models if len(models) == 1 else []
    )
    if selected_model:
        selected_filters['model'] = selected_model
    
    variants = get_unique_values(classified_folders, 'variant', selected_filters)
    selected_variant = col2.multiselect(
        "Variant",
        variants,
        default=variants if len(variants) == 1 else []
    )
    if selected_variant:
        selected_filters['variant'] = selected_variant
    
    # Model Year and Battery filters
    col3, col4 = st.sidebar.columns(2)
    model_years = get_unique_values(classified_folders, 'model_year', selected_filters)
    selected_model_year = col3.multiselect(
        "Model Year",
        model_years,
        default=model_years if len(model_years) == 1 else []
    )
    if selected_model_year:
        selected_filters['model_year'] = selected_model_year
    
    batteries = get_unique_values(classified_folders, 'battery', selected_filters)
    selected_battery = col4.multiselect(
        "Battery",
        batteries,
        default=batteries if len(batteries) == 1 else []
    )
    if selected_battery:
        selected_filters['battery'] = selected_battery
    
    # Front Motor and Rear Motor filters
    col5, col6 = st.sidebar.columns(2)
    front_motors = get_unique_values(classified_folders, 'front_motor', selected_filters)
    selected_front_motor = col5.multiselect(
        "Front Motor",
        front_motors,
        default=front_motors if len(front_motors) == 1 else []
    )
    if selected_front_motor:
        selected_filters['front_motor'] = selected_front_motor
    
    rear_motors = get_unique_values(classified_folders, 'rear_motor', selected_filters)
    selected_rear_motor = col6.multiselect(
        "Rear Motor",
        rear_motors,
        default=rear_motors if len(rear_motors) == 1 else []
    )
    if selected_rear_motor:
        selected_filters['rear_motor'] = selected_rear_motor
    
    # Tuning filter
    tunings = get_unique_values(classified_folders, 'tuning', selected_filters)
    selected_tuning = st.sidebar.multiselect(
        "Tuning",
        tunings,
        default=tunings if len(tunings) == 1 else []
    )
    if selected_tuning:
        selected_filters['tuning'] = selected_tuning
    
    # Acceleration Mode filter
    acceleration_modes = get_unique_values(classified_folders, 'acceleration_mode', selected_filters)
    acceleration_modes_ordered = ["Chill", "Standard", "Sport"]
    selected_acceleration_mode = st.sidebar.multiselect(
        "Acceleration Mode",
        acceleration_modes_ordered,
        default=acceleration_modes_ordered if len(acceleration_modes_ordered) == 1 else []
    )
    if selected_acceleration_mode:
        selected_filters['acceleration_mode'] = selected_acceleration_mode
    
    # Filter folders based on selections
    filtered_folders = filter_folders(classified_folders, selected_filters)
    
    if not filtered_folders:
        st.warning("No folders found matching the selected criteria.")
        return
    
    # Get file information
    file_info = perf_client.get_file_info(filtered_folders)
    
    if not file_info:
        st.warning("No data files found after applying the filters.")
        return
    
    # SOC and temperature range sliders
    soc_range, temp_range = create_soc_temp_sliders(file_info)
    
    # Filter files based on ranges
    filtered_file_info = [
        info for info in file_info
        if soc_range[0] <= info.soc <= soc_range[1] and
           temp_range[0] <= info.cell_temp_mid <= temp_range[1]
    ]
    
    if not filtered_file_info:
        st.warning("No data files match the selected SOC and temperature ranges.")
        return
    
    # Column selection
    selected_columns = create_column_selectors()
    
    if not selected_columns:
        st.warning("Please select at least one data column to plot.")
        return
    
    # Smoothing slider
    smoothing_value = st.sidebar.slider(
        "Line Smoothing",
        min_value=0,
        max_value=20,
        value=20
    )
    
    # Generate plot
    plot_df, color_map = generate_plot_data(
        filtered_file_info,
        selected_columns,
        perf_client,
        smoothing_value
    )
    
    if plot_df.empty:
        st.write("No data available to plot with the selected options.")
        return
    
    # Create and display plot
    fig = PlotBuilder.create_performance_line_plot(
        plot_df,
        'Speed [kph]',
        "Values" if len(selected_columns) > 1 else selected_columns[0],
        color_map
    )
    
    # Add color pickers
    unique_labels = plot_df['Label'].unique()
    for label in unique_labels:
        color = st.sidebar.color_picker(f"Pick a color for {label}", color_map[label])
        color_map[label] = color
    
    # Update colors in plot
    fig.for_each_trace(
        lambda trace: trace.update(line_color=color_map.get(trace.name, trace.line.color))
    )
    
    st.plotly_chart(fig, width="stretch")
    
    # Sidebar footer
    UIComponents.render_sidebar_footer()


def get_unique_values(folders: List[PerformanceFolder], key: str, filters: Dict = None) -> List[str]:
    """Get unique values for a specific key from folders.
    
    Args:
        folders: List of PerformanceFolder objects.
        key: Attribute name to extract.
        filters: Optional filters to apply.
        
    Returns:
        Sorted list of unique values.
    """
    if filters is None:
        filters = {}
    
    values = set()
    for folder in folders:
        folder_dict = folder.to_dict()
        match = all(folder_dict[k] in v for k, v in filters.items() if k in folder_dict)
        if match:
            values.add(folder_dict[key])
    
    return sorted(values)


def filter_folders(folders: List[PerformanceFolder], filters: Dict) -> List[PerformanceFolder]:
    """Filter folders based on criteria.
    
    Args:
        folders: List of PerformanceFolder objects.
        filters: Dictionary of filter criteria.
        
    Returns:
        Filtered list of folders.
    """
    return [
        f for f in folders
        if all(f.to_dict()[k] in v for k, v in filters.items() if k in f.to_dict())
    ]


def create_soc_temp_sliders(file_info: List[PerformanceFileInfo]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Create SOC and temperature range sliders.
    
    Args:
        file_info: List of PerformanceFileInfo objects.
        
    Returns:
        Tuple of (soc_range, temp_range).
    """
    min_soc = min(info.soc for info in file_info)
    max_soc = max(info.soc for info in file_info)
    min_temp = min(info.cell_temp_mid for info in file_info)
    max_temp = max(info.cell_temp_mid for info in file_info)
    
    if min_soc == max_soc:
        st.sidebar.write(f"Only one SOC value available: {min_soc}")
        soc_range = (min_soc, max_soc)
    else:
        soc_range = st.sidebar.slider(
            "State Of Charge [%]",
            min_soc,
            max_soc,
            (95, 100)
        )
    
    if min_temp == max_temp:
        st.sidebar.write(f"Only one Cell Temp value available: {min_temp}")
        temp_range = (min_temp, max_temp)
    else:
        temp_range = st.sidebar.slider(
            "Battery Temperature [°C]",
            min_temp,
            max_temp,
            (min_temp, max_temp)
        )
    
    return soc_range, temp_range


def create_column_selectors() -> List[str]:
    """Create column selection checkboxes.
    
    Returns:
        List of selected column labels.
    """
    columns_to_plot = {
        "Max Discharge Power [kW]": "Max discharge power",
        "Battery Power [kW]": "Battery power",
        "Battery Current [A]": "Battery current",
        "Battery Voltage [V]": "Battery voltage",
        "Front/Rear Motor Power [kW]": ["F power", "R power"],
        "Combined Motor Power [kW]": ["F power", "R power"],
        "Front/Rear Motor Torque [Nm]": ["F torque", "R torque"],
        "Combined Motor Torque [Nm]": ["F torque", "R torque"]
    }
    
    selected_columns = []
    for label in columns_to_plot.keys():
        if st.sidebar.checkbox(label, key=f"y_{label}"):
            selected_columns.append(label)
    
    return selected_columns


def generate_plot_data(
    file_info: List[PerformanceFileInfo],
    selected_columns: List[str],
    perf_client: PerformanceDataClient,
    smoothing_value: int
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Generate plot data from selected files and columns.
    
    Args:
        file_info: List of file information objects.
        selected_columns: Selected columns to plot.
        perf_client: Performance data client.
        smoothing_value: Smoothing window size.
        
    Returns:
        Tuple of (plot_df, color_map).
    """
    columns_map = {
        "Max Discharge Power [kW]": "Max discharge power",
        "Battery Power [kW]": "Battery power",
        "Battery Current [A]": "Battery current",
        "Battery Voltage [V]": "Battery voltage",
        "Front/Rear Motor Power [kW]": ["F power", "R power"],
        "Combined Motor Power [kW]": ["F power", "R power"],
        "Front/Rear Motor Torque [Nm]": ["F torque", "R torque"],
        "Combined Motor Torque [Nm]": ["F torque", "R torque"]
    }
    
    # Fixed colors for folders
    folder_colors = {}
    plot_data = []
    
    for i, info in enumerate(file_info):
        legend_label = info.folder.get_legend_label()
        
        if legend_label not in folder_colors:
            folder_colors[legend_label] = Config.PERFORMANCE_COLORS[
                len(folder_colors) % len(Config.PERFORMANCE_COLORS)
            ]
        
        df = perf_client.fetch_csv_data(info.path)
        if df is None:
            continue
        
        # Collect subset columns for dropna
        subset_columns = ['Speed']
        for column in selected_columns:
            y_cols = columns_map[column]
            if isinstance(y_cols, list):
                subset_columns.extend(y_cols)
            else:
                subset_columns.append(y_cols)
        
        # Filter columns that exist
        subset_columns = [col for col in subset_columns if col in df.columns]
        
        if not subset_columns:
            st.warning(f"Required columns not found in file {info.name}. Skipping.")
            continue
        
        df = df.dropna(subset=subset_columns)
        
        if df.empty:
            continue
        
        # Process selected columns
        for column in selected_columns:
            y_cols = columns_map[column]
            
            if isinstance(y_cols, list):
                available_cols = [col for col in y_cols if col in df.columns]
                
                if not available_cols:
                    continue
                
                if column in ["Combined Motor Power [kW]", "Combined Motor Torque [Nm]"]:
                    combined_value = df[available_cols].sum(axis=1, skipna=True)
                    
                    if column == "Combined Motor Power [kW]":
                        combined_value = combined_value[combined_value >= Config.COMBINED_MOTOR_POWER_THRESHOLD]
                    
                    if len(combined_value) > 0:
                        plot_data.append(pd.DataFrame({
                            'X': df['Speed'].loc[combined_value.index],
                            'Y': combined_value,
                            'Label': f"{legend_label} - Combined Motor {'Power' if 'Power' in column else 'Torque'}",
                            'Color': folder_colors[legend_label]
                        }))
                else:
                    for sub_col in available_cols:
                        plot_data.append(pd.DataFrame({
                            'X': df['Speed'],
                            'Y': df[sub_col],
                            'Label': f"{legend_label} - {sub_col}",
                            'Color': folder_colors[legend_label]
                        }))
            else:
                if y_cols not in df.columns:
                    continue
                
                y_data = df[y_cols]
                
                if 'Battery power' in y_cols:
                    y_data = y_data[y_data >= Config.BATTERY_POWER_THRESHOLD]
                
                if len(y_data) > 0:
                    plot_data.append(pd.DataFrame({
                        'X': df['Speed'].loc[y_data.index],
                        'Y': y_data,
                        'Label': f"{legend_label} - {column}",
                        'Color': folder_colors[legend_label]
                    }))
    
    if not plot_data:
        return pd.DataFrame(), {}
    
    # Combine all plot data
    plot_df = pd.concat(plot_data, ignore_index=True)
    plot_df.dropna(subset=['X', 'Y'], inplace=True)
    
    # Create color map
    unique_labels = plot_df['Label'].unique()
    color_map = {label: folder_colors[label.split(" - ")[0]] for label in unique_labels}
    
    # Apply smoothing
    if smoothing_value > 0:
        for label in unique_labels:
            y_values = plot_df.loc[plot_df['Label'] == label, 'Y'].values
            if len(y_values) >= smoothing_value:
                smoothed_values = uniform_filter1d(y_values, size=smoothing_value)
                plot_df.loc[plot_df['Label'] == label, 'Y'] = smoothed_values
    
    return plot_df, color_map


if __name__ == "__main__":
    main()
