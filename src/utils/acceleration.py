"""Performance analysis utilities for acceleration runs."""
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np


class AccelerationAnalyzer:
    """Analyzer for acceleration run data."""
    
    @staticmethod
    def detect_acceleration_runs(df: pd.DataFrame, speed_threshold: float = 10.0) -> List[pd.DataFrame]:
        """Detect individual acceleration runs in a performance CSV.
        
        Handles files with a single acceleration run that may have positioning
        data before and after the actual run. Identifies the main acceleration
        segment by finding the maximum speed achieved.
        
        Args:
            df: DataFrame with Speed column.
            speed_threshold: Minimum speed to consider active run (kph).
            
        Returns:
            List of DataFrames, one per acceleration run.
        """
        if 'Speed' not in df.columns or df.empty:
            return []
        
        # Find the maximum speed achieved
        max_speed = df['Speed'].max()
        max_speed_idx = df['Speed'].idxmax()
        
        # Find where the run starts (first time speed crosses threshold before max)
        before_max = df.loc[:max_speed_idx]
        above_threshold_before = before_max['Speed'] >= speed_threshold
        
        if above_threshold_before.any():
            start_idx = before_max[above_threshold_before].index[0]
        else:
            start_idx = df.index[0]
        
        # Find where the run ends (last time speed is above threshold after max)
        after_max = df.loc[max_speed_idx:]
        above_threshold_after = after_max['Speed'] >= speed_threshold
        
        if above_threshold_after.any():
            end_idx = after_max[above_threshold_after].index[-1]
        else:
            end_idx = max_speed_idx
        
        # Extract the main acceleration run
        run_df = df.loc[start_idx:end_idx].copy()
        
        if len(run_df) > 5:  # Minimum 5 points for a valid run
            return [run_df]
        
        return []
    
    @staticmethod
    def get_best_run(runs: List[pd.DataFrame], target_speed: float = 100.0) -> Optional[pd.DataFrame]:
        """Get the best (fastest) acceleration run to a target speed.
        
        Args:
            runs: List of acceleration run DataFrames.
            target_speed: Target speed in kph.
            
        Returns:
            DataFrame of the best run, or None if no valid runs.
        """
        if not runs:
            return None
        
        best_run = None
        best_time = float('inf')
        
        for run in runs:
            # Check if run reaches target speed
            max_speed = run['Speed'].max()
            if max_speed >= target_speed:
                # Find time to reach target speed
                target_rows = run[run['Speed'] >= target_speed]
                if not target_rows.empty:
                    time_to_target = target_rows.iloc[0]['Time'] - run.iloc[0]['Time']
                    if time_to_target < best_time:
                        best_time = time_to_target
                        best_run = run
        
        return best_run
    
    @staticmethod
    def calculate_acceleration_metrics(df: pd.DataFrame) -> dict:
        """Calculate key acceleration metrics from a run.
        
        Args:
            df: DataFrame with Time and Speed columns.
            
        Returns:
            Dictionary with acceleration metrics.
        """
        if df.empty or 'Time' not in df.columns or 'Speed' not in df.columns:
            return {}
        
        metrics = {}
        start_time = df.iloc[0]['Time']
        
        # 0-60 kph
        speed_60 = df[df['Speed'] >= 60]
        if not speed_60.empty:
            metrics['0-60_kph'] = speed_60.iloc[0]['Time'] - start_time
        
        # 0-100 kph
        speed_100 = df[df['Speed'] >= 100]
        if not speed_100.empty:
            metrics['0-100_kph'] = speed_100.iloc[0]['Time'] - start_time
        
        # 0-200 kph
        speed_200 = df[df['Speed'] >= 200]
        if not speed_200.empty:
            metrics['0-200_kph'] = speed_200.iloc[0]['Time'] - start_time
        
        # Quarter mile (402.336 meters)
        # Approximate distance from speed data (integrate speed over time)
        if len(df) > 1:
            df_sorted = df.sort_values('Time').copy()
            # Convert kph to m/s and calculate distance
            df_sorted['Speed_ms'] = df_sorted['Speed'] / 3.6
            df_sorted['Time_diff'] = df_sorted['Time'].diff()
            df_sorted['Distance'] = df_sorted['Speed_ms'] * df_sorted['Time_diff']
            df_sorted['Cumulative_Distance'] = df_sorted['Distance'].cumsum()
            
            quarter_mile = df_sorted[df_sorted['Cumulative_Distance'] >= 402.336]
            if not quarter_mile.empty:
                metrics['quarter_mile_time'] = quarter_mile.iloc[0]['Time'] - start_time
                metrics['quarter_mile_speed'] = quarter_mile.iloc[0]['Speed']
        
        # Max speed achieved
        metrics['max_speed'] = df['Speed'].max()
        
        # Average power during run
        if 'Battery power' in df.columns:
            metrics['avg_battery_power'] = df['Battery power'].mean()
        
        return metrics
    
    @staticmethod
    def filter_run_by_speed_range(df: pd.DataFrame, start_speed: float = 0, end_speed: float = 200) -> pd.DataFrame:
        """Filter a run to only show data within a speed range.
        
        Args:
            df: DataFrame with Speed column.
            start_speed: Minimum speed to include (kph).
            end_speed: Maximum speed to include (kph).
            
        Returns:
            Filtered DataFrame.
        """
        if df.empty or 'Speed' not in df.columns:
            return df
        
        # Find first point at or above start speed
        start_idx = df[df['Speed'] >= start_speed].index
        if start_idx.empty:
            return pd.DataFrame()
        
        # Find last point at or below end speed
        end_idx = df[df['Speed'] <= end_speed].index
        if end_idx.empty:
            return df.loc[start_idx[0]:]
        
        # Return data from start to end
        return df.loc[start_idx[0]:end_idx[-1]]
    
    @staticmethod
    def interpolate_acceleration_data(df: pd.DataFrame, interval: float = 0.1) -> pd.DataFrame:
        """Interpolate acceleration data to regular time intervals.
        
        Useful for smoothing sparse data and creating consistent plots.
        
        Args:
            df: DataFrame with Time and Speed columns.
            interval: Time interval for interpolation (seconds).
            
        Returns:
            Interpolated DataFrame.
        """
        if df.empty or 'Time' not in df.columns:
            return df
        
        # Create regular time series
        time_min = df['Time'].min()
        time_max = df['Time'].max()
        new_times = np.arange(time_min, time_max, interval)
        
        # Interpolate all numeric columns
        interpolated_data = {'Time': new_times}
        
        for col in df.select_dtypes(include=[np.number]).columns:
            if col != 'Time':
                interpolated_data[col] = np.interp(
                    new_times,
                    df['Time'].values,
                    df[col].values
                )
        
        return pd.DataFrame(interpolated_data)
