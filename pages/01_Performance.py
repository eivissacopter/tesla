"""Tesla Performance Analysis - Refactored Page."""
from typing import Dict, List, Optional, Tuple

import pandas as pd
from scipy.ndimage import uniform_filter1d
import streamlit as st

from src.config import Config
from src.data.performance_data import PerformanceDataClient
from src.models import PerformanceFileInfo, PerformanceFolder
from src.utils import AccelerationAnalyzer, PlotBuilder
from src.ui import UIComponents


st.set_page_config(
    page_title='Tesla Performance Analysis',
    page_icon=':racing_car:',
    layout='wide'
)

PLOT_COLUMN_MAP = {
    'Max Discharge Power [kW]': 'Max discharge power',
    'Battery Power [kW]': 'Battery power',
    'Battery Current [A]': 'Battery current',
    'Battery Voltage [V]': 'Battery voltage',
    'Front/Rear Motor Power [kW]': ['F power', 'R power'],
    'Combined Motor Power [kW]': ['F power', 'R power'],
    'Front/Rear Motor Torque [Nm]': ['F torque', 'R torque'],
    'Combined Motor Torque [Nm]': ['F torque', 'R torque'],
}
ACCELERATION_MODE_ORDER = ['Chill', 'Standard', 'Sport']


def main():
    """Main application entry point."""
    UIComponents.render_performance_header()
    perf_client = PerformanceDataClient()

    classified_folders = perf_client.scan_and_classify_folders()
    if not classified_folders:
        st.error('The directory structure is empty. No options available.')
        return

    selected_filters: Dict[str, List[str]] = {}

    col1, col2 = st.sidebar.columns(2)
    models = get_unique_values(classified_folders, 'model', selected_filters)
    selected_model = col1.multiselect('Model', models, default=models if len(models) == 1 else [])
    if selected_model:
        selected_filters['model'] = selected_model

    variants = get_unique_values(classified_folders, 'variant', selected_filters)
    selected_variant = col2.multiselect('Variant', variants, default=variants if len(variants) == 1 else [])
    if selected_variant:
        selected_filters['variant'] = selected_variant

    col3, col4 = st.sidebar.columns(2)
    model_years = get_unique_values(classified_folders, 'model_year', selected_filters)
    selected_model_year = col3.multiselect('Model Year', model_years, default=model_years if len(model_years) == 1 else [])
    if selected_model_year:
        selected_filters['model_year'] = selected_model_year

    batteries = get_unique_values(classified_folders, 'battery', selected_filters)
    selected_battery = col4.multiselect('Battery', batteries, default=batteries if len(batteries) == 1 else [])
    if selected_battery:
        selected_filters['battery'] = selected_battery

    col5, col6 = st.sidebar.columns(2)
    front_motors = get_unique_values(classified_folders, 'front_motor', selected_filters)
    selected_front_motor = col5.multiselect('Front Motor', front_motors, default=front_motors if len(front_motors) == 1 else [])
    if selected_front_motor:
        selected_filters['front_motor'] = selected_front_motor

    rear_motors = get_unique_values(classified_folders, 'rear_motor', selected_filters)
    selected_rear_motor = col6.multiselect('Rear Motor', rear_motors, default=rear_motors if len(rear_motors) == 1 else [])
    if selected_rear_motor:
        selected_filters['rear_motor'] = selected_rear_motor

    tunings = get_unique_values(classified_folders, 'tuning', selected_filters)
    selected_tuning = st.sidebar.multiselect('Tuning', tunings, default=tunings if len(tunings) == 1 else [])
    if selected_tuning:
        selected_filters['tuning'] = selected_tuning

    acceleration_modes = get_unique_values(classified_folders, 'acceleration_mode', selected_filters)
    ordered_modes = [mode for mode in ACCELERATION_MODE_ORDER if mode in acceleration_modes]
    ordered_modes.extend([mode for mode in acceleration_modes if mode not in ordered_modes])
    selected_acceleration_mode = st.sidebar.multiselect(
        'Acceleration Mode',
        ordered_modes,
        default=ordered_modes if len(ordered_modes) == 1 else []
    )
    if selected_acceleration_mode:
        selected_filters['acceleration_mode'] = selected_acceleration_mode

    filtered_folders = filter_folders(classified_folders, selected_filters)
    if not filtered_folders:
        st.warning('No folders found matching the selected criteria.')
        return

    file_info = perf_client.get_file_info(filtered_folders)
    if not file_info:
        st.warning('No data files found after applying the filters.')
        return

    soc_range, temp_range = create_soc_temp_sliders(file_info)
    filtered_file_info = [
        info for info in file_info
        if soc_range[0] <= info.soc <= soc_range[1]
        and temp_range[0] <= info.cell_temp_mid <= temp_range[1]
    ]
    if not filtered_file_info:
        st.warning('No data files match the selected SOC and temperature ranges.')
        return

    _render_dataset_metrics(filtered_folders, filtered_file_info)
    _render_run_catalog(filtered_file_info)

    selected_columns = create_column_selectors()
    if not selected_columns:
        st.warning('Please select at least one data column to plot.')
        return

    smoothing_value = st.sidebar.slider('Line Smoothing', min_value=0, max_value=20, value=6)

    st.sidebar.markdown('---')
    st.sidebar.markdown('### Acceleration Analysis')
    acceleration_mode = st.sidebar.checkbox(
        'Acceleration Run Mode',
        value=False,
        help='Analyze 0-100, 0-200 acceleration runs'
    )

    target_speed = 100
    show_metrics = True
    if acceleration_mode:
        target_speed = st.sidebar.selectbox(
            'Target Speed',
            [60, 100, 160, 200],
            index=1,
            help='Speed target for acceleration analysis (kph)'
        )
        show_metrics = st.sidebar.checkbox(
            'Show Acceleration Metrics',
            value=True,
            help='Display 0-60, 0-100, quarter mile times'
        )

    if acceleration_mode:
        plot_df, color_map, metrics = generate_acceleration_plot_data(
            filtered_file_info,
            selected_columns,
            perf_client,
            smoothing_value,
            target_speed,
            show_metrics
        )
    else:
        plot_df, color_map = generate_plot_data(
            filtered_file_info,
            selected_columns,
            perf_client,
            smoothing_value
        )
        metrics = None

    if plot_df.empty:
        st.write('No data available to plot with the selected options.')
        return

    fig = PlotBuilder.create_performance_line_plot(
        plot_df,
        'Time [s]' if acceleration_mode else 'Speed [kph]',
        'Values' if len(selected_columns) > 1 else selected_columns[0],
        color_map
    )

    for label in plot_df['Label'].unique():
        color_map[label] = st.sidebar.color_picker(f'Pick a color for {label}', color_map[label])

    fig.for_each_trace(
        lambda trace: trace.update(line_color=color_map.get(trace.name, trace.line.color))
    )

    st.plotly_chart(fig, width='stretch')

    if acceleration_mode and metrics:
        _render_acceleration_metrics(metrics)

    UIComponents.render_sidebar_footer()


def get_unique_values(folders: List[PerformanceFolder], key: str, filters: Optional[Dict] = None) -> List[str]:
    """Get unique values for a specific key from folders."""
    filters = filters or {}
    values = set()
    for folder in folders:
        folder_dict = folder.to_dict()
        if all(folder_dict[filter_key] in selected for filter_key, selected in filters.items() if filter_key in folder_dict):
            values.add(folder_dict[key])
    return sorted(values)


def filter_folders(folders: List[PerformanceFolder], filters: Dict) -> List[PerformanceFolder]:
    """Filter folders based on criteria."""
    return [
        folder for folder in folders
        if all(folder.to_dict()[key] in values for key, values in filters.items() if key in folder.to_dict())
    ]


def create_soc_temp_sliders(file_info: List[PerformanceFileInfo]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Create SOC and temperature range sliders."""
    min_soc = min(info.soc for info in file_info)
    max_soc = max(info.soc for info in file_info)
    min_temp = min(info.cell_temp_mid for info in file_info)
    max_temp = max(info.cell_temp_mid for info in file_info)

    if min_soc == max_soc:
        st.sidebar.write(f'Only one SOC value available: {min_soc}')
        soc_range = (min_soc, max_soc)
    else:
        soc_range = st.sidebar.slider('State Of Charge [%]', min_soc, max_soc, (min_soc, max_soc))

    if min_temp == max_temp:
        st.sidebar.write(f'Only one Cell Temp value available: {min_temp}')
        temp_range = (min_temp, max_temp)
    else:
        temp_range = st.sidebar.slider('Battery Temperature [C]', min_temp, max_temp, (min_temp, max_temp))

    return soc_range, temp_range


def create_column_selectors() -> List[str]:
    """Create column selection checkboxes."""
    selected_columns = []
    for index, label in enumerate(PLOT_COLUMN_MAP.keys()):
        if st.sidebar.checkbox(label, key=f'y_{label}', value=index == 0):
            selected_columns.append(label)
    return selected_columns


def generate_plot_data(
    file_info: List[PerformanceFileInfo],
    selected_columns: List[str],
    perf_client: PerformanceDataClient,
    smoothing_value: int
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Generate plot data from selected files and columns."""
    folder_colors: Dict[str, str] = {}
    plot_frames: List[pd.DataFrame] = []

    for info in file_info:
        legend_label = info.folder.get_legend_label()
        folder_colors.setdefault(
            legend_label,
            Config.PERFORMANCE_COLORS[len(folder_colors) % len(Config.PERFORMANCE_COLORS)]
        )

        df = perf_client.fetch_csv_data(info.path)
        if df is None or df.empty or 'Speed' not in df.columns:
            continue

        plot_frames.extend(
            _build_plot_frames(
                df=df,
                x_series=df['Speed'],
                selected_columns=selected_columns,
                legend_label=legend_label,
                folder_color=folder_colors[legend_label],
                file_name=info.name,
            )
        )

    return _finalize_plot_data(plot_frames, folder_colors, smoothing_value)


def generate_acceleration_plot_data(
    file_info: List[PerformanceFileInfo],
    selected_columns: List[str],
    perf_client: PerformanceDataClient,
    smoothing_value: int,
    target_speed: int,
    show_metrics: bool
) -> Tuple[pd.DataFrame, Dict[str, str], Dict]:
    """Generate plot data for acceleration runs."""
    folder_colors: Dict[str, str] = {}
    plot_frames: List[pd.DataFrame] = []
    metrics_dict: Dict[str, Dict] = {}

    for info in file_info:
        legend_label = info.folder.get_legend_label()
        folder_colors.setdefault(
            legend_label,
            Config.PERFORMANCE_COLORS[len(folder_colors) % len(Config.PERFORMANCE_COLORS)]
        )

        df = perf_client.fetch_csv_data(info.path)
        if df is None or df.empty:
            continue

        runs = AccelerationAnalyzer.detect_acceleration_runs(df, speed_threshold=10.0)
        best_run = AccelerationAnalyzer.get_best_run(runs, target_speed=target_speed)
        if best_run is None or best_run.empty:
            continue

        if show_metrics:
            metrics_dict[info.name] = AccelerationAnalyzer.calculate_acceleration_metrics(best_run)

        best_run = AccelerationAnalyzer.filter_run_by_speed_range(best_run, 0, target_speed)
        if best_run.empty or 'Time' not in best_run.columns:
            continue

        best_run = best_run.copy().sort_values('Time')
        best_run['Time'] = best_run['Time'] - best_run['Time'].min()

        plot_frames.extend(
            _build_plot_frames(
                df=best_run,
                x_series=best_run['Time'],
                selected_columns=selected_columns,
                legend_label=legend_label,
                folder_color=folder_colors[legend_label],
                file_name=info.name,
            )
        )

    plot_df, color_map = _finalize_plot_data(plot_frames, folder_colors, smoothing_value)
    return plot_df, color_map, metrics_dict


def _build_plot_frames(
    df: pd.DataFrame,
    x_series: pd.Series,
    selected_columns: List[str],
    legend_label: str,
    folder_color: str,
    file_name: str,
) -> List[pd.DataFrame]:
    """Create individual plot series for the selected telemetry columns."""
    plot_frames: List[pd.DataFrame] = []
    x_values = pd.to_numeric(x_series, errors='coerce')

    for selected_column in selected_columns:
        source_columns = PLOT_COLUMN_MAP.get(selected_column)
        if source_columns is None:
            continue

        if isinstance(source_columns, list):
            available_columns = [column for column in source_columns if column in df.columns]
            if not available_columns:
                continue

            if selected_column in ['Combined Motor Power [kW]', 'Combined Motor Torque [Nm]']:
                combined = df[available_columns].apply(pd.to_numeric, errors='coerce').sum(axis=1, skipna=True)
                if selected_column == 'Combined Motor Power [kW]':
                    combined = combined[combined >= Config.COMBINED_MOTOR_POWER_THRESHOLD]
                plot_frames.append(_create_plot_frame(
                    x_values.loc[combined.index],
                    combined,
                    f"{legend_label} - Combined Motor {'Power' if 'Power' in selected_column else 'Torque'}",
                    folder_color,
                    file_name,
                ))
            else:
                for source_column in available_columns:
                    plot_frames.append(_create_plot_frame(
                        x_values,
                        pd.to_numeric(df[source_column], errors='coerce'),
                        f'{legend_label} - {source_column}',
                        folder_color,
                        file_name,
                    ))
        else:
            if source_columns not in df.columns:
                continue

            y_values = pd.to_numeric(df[source_columns], errors='coerce')
            if source_columns == 'Battery power':
                y_values = y_values[y_values >= Config.BATTERY_POWER_THRESHOLD]
                x_subset = x_values.loc[y_values.index]
            else:
                x_subset = x_values

            plot_frames.append(_create_plot_frame(
                x_subset,
                y_values,
                f'{legend_label} - {selected_column}',
                folder_color,
                file_name,
            ))

    return plot_frames


def _create_plot_frame(
    x_values: pd.Series,
    y_values: pd.Series,
    label: str,
    color: str,
    file_name: str,
) -> pd.DataFrame:
    """Create a normalized plot frame and drop invalid rows."""
    frame = pd.DataFrame({
        'X': pd.to_numeric(x_values, errors='coerce'),
        'Y': pd.to_numeric(y_values, errors='coerce'),
        'Label': label,
        'Color': color,
        'File': file_name,
    })
    return frame.dropna(subset=['X', 'Y'])


def _finalize_plot_data(
    plot_frames: List[pd.DataFrame],
    folder_colors: Dict[str, str],
    smoothing_value: int,
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Combine, sort and smooth plot data."""
    if not plot_frames:
        return pd.DataFrame(), {}

    plot_df = pd.concat(plot_frames, ignore_index=True)
    plot_df = plot_df.sort_values(['Label', 'File', 'X']).reset_index(drop=True)
    plot_df = _smooth_plot_df(plot_df, smoothing_value)

    color_map = {
        label: folder_colors[label.split(' - ')[0]]
        for label in plot_df['Label'].unique()
    }
    return plot_df, color_map


def _smooth_plot_df(plot_df: pd.DataFrame, smoothing_value: int) -> pd.DataFrame:
    """Apply smoothing per trace so different files never bleed into each other."""
    if smoothing_value <= 1 or plot_df.empty:
        return plot_df

    smoothed_df = plot_df.copy()

    def smooth_group(series: pd.Series) -> pd.Series:
        if len(series) < 3:
            return series
        size = min(smoothing_value, len(series))
        return pd.Series(uniform_filter1d(series.to_numpy(), size=size), index=series.index)

    smoothed_df['Y'] = smoothed_df.groupby(['Label', 'File'], sort=False)['Y'].transform(smooth_group)
    return smoothed_df


def _render_dataset_metrics(filtered_folders: List[PerformanceFolder], filtered_file_info: List[PerformanceFileInfo]) -> None:
    """Render overview metrics for the current performance slice."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Folders', len(filtered_folders))
    col2.metric('Files', len(filtered_file_info))
    col3.metric('Median SOC', f"{pd.Series([info.soc for info in filtered_file_info]).median():.0f}%")
    col4.metric('Median Cell Temp', f"{pd.Series([info.cell_temp_mid for info in filtered_file_info]).median():.0f} C")


def _render_run_catalog(filtered_file_info: List[PerformanceFileInfo]) -> None:
    """Show the currently filtered run catalog for quick inspection."""
    with st.expander('Run Catalog'):
        catalog = pd.DataFrame([
            {
                'Label': info.folder.get_legend_label(),
                'File': info.name,
                'SOC [%]': info.soc,
                'Cell Temp [C]': info.cell_temp_mid,
                'Model': info.folder.model,
                'Variant': info.folder.variant,
                'Battery': info.folder.battery,
                'Rear Motor': info.folder.rear_motor,
                'Tuning': info.folder.tuning,
                'Mode': info.folder.acceleration_mode,
            }
            for info in filtered_file_info
        ])
        st.dataframe(catalog, use_container_width=True, hide_index=True)


def _render_acceleration_metrics(metrics: Dict[str, Dict]) -> None:
    """Render acceleration metrics in both card and table form."""
    st.markdown('### Acceleration Metrics')

    summary_rows = []
    for file_name, file_metrics in metrics.items():
        summary_rows.append({
            'File': file_name,
            '0-60 kph [s]': file_metrics.get('0-60_kph'),
            '0-100 kph [s]': file_metrics.get('0-100_kph'),
            '0-160 kph [s]': file_metrics.get('0-160_kph'),
            '0-200 kph [s]': file_metrics.get('0-200_kph'),
            'Quarter Mile [s]': file_metrics.get('quarter_mile_time'),
            'Quarter Mile Speed [kph]': file_metrics.get('quarter_mile_speed'),
            'Max Speed [kph]': file_metrics.get('max_speed'),
            'Avg Battery Power [kW]': file_metrics.get('avg_battery_power'),
            'Peak Battery Power [kW]': file_metrics.get('peak_battery_power'),
        })

        with st.expander(file_name):
            cols = st.columns(3)
            if '0-60_kph' in file_metrics:
                cols[0].metric('0-60 kph', f"{file_metrics['0-60_kph']:.2f}s")
            if '0-100_kph' in file_metrics:
                cols[1].metric('0-100 kph', f"{file_metrics['0-100_kph']:.2f}s")
            if '0-160_kph' in file_metrics:
                cols[2].metric('0-160 kph', f"{file_metrics['0-160_kph']:.2f}s")

            cols_extra = st.columns(2)
            if '0-200_kph' in file_metrics:
                cols_extra[0].metric('0-200 kph', f"{file_metrics['0-200_kph']:.2f}s")
            if 'peak_battery_power' in file_metrics:
                cols_extra[1].metric('Peak Battery Power', f"{file_metrics['peak_battery_power']:.1f} kW")

            cols2 = st.columns(3)
            if 'quarter_mile_time' in file_metrics:
                cols2[0].metric('Quarter Mile', f"{file_metrics['quarter_mile_time']:.2f}s")
            if 'quarter_mile_speed' in file_metrics:
                cols2[1].metric('QM Speed', f"{file_metrics['quarter_mile_speed']:.1f} kph")
            if 'max_speed' in file_metrics:
                cols2[2].metric('Max Speed', f"{file_metrics['max_speed']:.1f} kph")

            if 'avg_battery_power' in file_metrics:
                st.metric('Avg Battery Power', f"{file_metrics['avg_battery_power']:.1f} kW")

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows).sort_values(by='0-100 kph [s]', na_position='last')
        st.dataframe(summary_df, use_container_width=True, hide_index=True)


if __name__ == '__main__':
    main()

