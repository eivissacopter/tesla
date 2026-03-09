"""Performance analysis utilities for acceleration runs."""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


class AccelerationAnalyzer:
    """Analyzer for acceleration run data."""

    @staticmethod
    def detect_acceleration_runs(df: pd.DataFrame, speed_threshold: float = 10.0) -> List[pd.DataFrame]:
        """Detect one or more acceleration runs inside a telemetry file."""
        prepared_df = AccelerationAnalyzer._prepare_run_dataframe(df)
        if prepared_df.empty:
            return []

        active = prepared_df['Speed'] >= speed_threshold
        if not active.any():
            return []

        active_values = active.to_numpy()
        start_positions = np.flatnonzero(active_values & ~np.roll(active_values, 1))
        end_positions = np.flatnonzero(active_values & ~np.roll(active_values, -1))
        if active_values[0]:
            start_positions[0] = 0
        if active_values[-1]:
            end_positions[-1] = len(active_values) - 1

        runs: List[pd.DataFrame] = []
        for start_position, end_position in zip(start_positions, end_positions):
            extended_start = AccelerationAnalyzer._extend_start(prepared_df, start_position)
            extended_end = AccelerationAnalyzer._extend_end(prepared_df, end_position, speed_threshold)
            run_df = prepared_df.iloc[extended_start:extended_end + 1].copy()

            if len(run_df) < 6:
                continue
            if run_df['Speed'].max() < speed_threshold + 20:
                continue

            runs.append(run_df.reset_index(drop=True))

        return runs

    @staticmethod
    def get_best_run(runs: List[pd.DataFrame], target_speed: float = 100.0) -> Optional[pd.DataFrame]:
        """Get the fastest run to a target speed using interpolated crossing times."""
        best_run = None
        best_time = float('inf')

        for run in runs:
            time_to_target = AccelerationAnalyzer._time_at_speed(run, target_speed)
            if time_to_target is None:
                continue
            if time_to_target < best_time:
                best_time = time_to_target
                best_run = run

        return best_run

    @staticmethod
    def calculate_acceleration_metrics(df: pd.DataFrame) -> Dict[str, float]:
        """Calculate key acceleration metrics from a run."""
        prepared_df = AccelerationAnalyzer._prepare_run_dataframe(df)
        if prepared_df.empty:
            return {}

        metrics: Dict[str, float] = {}
        for speed, key in [(60, '0-60_kph'), (100, '0-100_kph'), (160, '0-160_kph'), (200, '0-200_kph')]:
            crossing_time = AccelerationAnalyzer._time_at_speed(prepared_df, speed)
            if crossing_time is not None:
                metrics[key] = crossing_time

        distance_df = prepared_df.copy()
        distance_df['Speed_ms'] = distance_df['Speed'] / 3.6
        distance_df['Delta_t'] = distance_df['Time'].diff().fillna(0)
        distance_df['SegmentDistance'] = (
            (distance_df['Speed_ms'] + distance_df['Speed_ms'].shift(1).fillna(distance_df['Speed_ms']))
            / 2
        ) * distance_df['Delta_t']
        distance_df['CumulativeDistance'] = distance_df['SegmentDistance'].cumsum()

        quarter_mile = distance_df[distance_df['CumulativeDistance'] >= 402.336]
        if not quarter_mile.empty:
            first_row = quarter_mile.iloc[0]
            metrics['quarter_mile_time'] = float(first_row['Time']) - float(distance_df.iloc[0]['Time'])
            metrics['quarter_mile_speed'] = float(first_row['Speed'])

        metrics['max_speed'] = float(prepared_df['Speed'].max())

        if 'Battery power' in prepared_df.columns:
            battery_power = pd.to_numeric(prepared_df['Battery power'], errors='coerce').dropna()
            if not battery_power.empty:
                metrics['avg_battery_power'] = float(battery_power.mean())
                metrics['peak_battery_power'] = float(battery_power.max())

        return metrics

    @staticmethod
    def filter_run_by_speed_range(df: pd.DataFrame, start_speed: float = 0, end_speed: float = 200) -> pd.DataFrame:
        """Filter a run to the region between start and end speed crossings."""
        prepared_df = AccelerationAnalyzer._prepare_run_dataframe(df)
        if prepared_df.empty:
            return prepared_df

        start_candidates = prepared_df.index[prepared_df['Speed'] >= start_speed]
        if len(start_candidates) == 0:
            return pd.DataFrame()
        start_idx = int(start_candidates[0])

        end_candidates = prepared_df.index[prepared_df['Speed'] >= end_speed]
        end_idx = int(end_candidates[0]) if len(end_candidates) else int(prepared_df.index[-1])
        return prepared_df.loc[start_idx:end_idx].reset_index(drop=True)

    @staticmethod
    def interpolate_acceleration_data(df: pd.DataFrame, interval: float = 0.1) -> pd.DataFrame:
        """Interpolate acceleration data to regular time intervals."""
        prepared_df = AccelerationAnalyzer._prepare_run_dataframe(df)
        if prepared_df.empty:
            return prepared_df

        time_min = prepared_df['Time'].min()
        time_max = prepared_df['Time'].max()
        new_times = np.arange(time_min, time_max + interval, interval)

        interpolated_data = {'Time': new_times}
        for column in prepared_df.select_dtypes(include=[np.number]).columns:
            if column == 'Time':
                continue
            interpolated_data[column] = np.interp(new_times, prepared_df['Time'].values, prepared_df[column].values)

        return pd.DataFrame(interpolated_data)

    @staticmethod
    def _prepare_run_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize and sort telemetry data for run analytics."""
        required_columns = {'Time', 'Speed'}
        if df.empty or not required_columns.issubset(df.columns):
            return pd.DataFrame()

        prepared_df = df.copy()
        prepared_df['Time'] = pd.to_numeric(prepared_df['Time'], errors='coerce')
        prepared_df['Speed'] = pd.to_numeric(prepared_df['Speed'], errors='coerce')
        prepared_df = prepared_df.dropna(subset=['Time', 'Speed']).sort_values('Time').reset_index(drop=True)
        prepared_df = prepared_df[prepared_df['Time'].diff().fillna(0).ge(0)]
        return prepared_df

    @staticmethod
    def _extend_start(df: pd.DataFrame, start_position: int, launch_speed: float = 3.0, window: int = 25) -> int:
        """Extend a run backwards to include the launch roll-in."""
        lower_bound = max(0, start_position - window)
        for position in range(start_position, lower_bound - 1, -1):
            if df.iloc[position]['Speed'] <= launch_speed:
                return position
        return lower_bound

    @staticmethod
    def _extend_end(df: pd.DataFrame, end_position: int, speed_threshold: float, window: int = 25) -> int:
        """Extend a run forward until the car is clearly out of the pull."""
        upper_bound = min(len(df) - 1, end_position + window)
        for position in range(end_position, upper_bound + 1):
            if df.iloc[position]['Speed'] < speed_threshold:
                return position
        return upper_bound

    @staticmethod
    def _time_at_speed(df: pd.DataFrame, target_speed: float) -> Optional[float]:
        """Estimate crossing time for a target speed using linear interpolation."""
        prepared_df = AccelerationAnalyzer._prepare_run_dataframe(df)
        if prepared_df.empty or prepared_df['Speed'].max() < target_speed:
            return None

        speeds = prepared_df['Speed'].to_numpy()
        times = prepared_df['Time'].to_numpy()
        base_time = float(times[0])

        for index in range(1, len(prepared_df)):
            previous_speed = speeds[index - 1]
            current_speed = speeds[index]
            if previous_speed <= target_speed <= current_speed:
                previous_time = times[index - 1]
                current_time = times[index]
                if current_speed == previous_speed:
                    return float(current_time - base_time)
                ratio = (target_speed - previous_speed) / (current_speed - previous_speed)
                interpolated_time = previous_time + ratio * (current_time - previous_time)
                return float(interpolated_time - base_time)

        return None
