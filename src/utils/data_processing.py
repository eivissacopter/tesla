"""Data processing utilities for battery analysis."""
from typing import Tuple, Optional, List
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

from ..config import Config
from ..models import FilterCriteria, SOHProjection


class BatteryDataProcessor:
    """Processor for battery analysis data."""
    
    @staticmethod
    def apply_filters(df: pd.DataFrame, criteria: FilterCriteria, battery_pack_col: Optional[str]) -> pd.DataFrame:
        """Apply filter criteria to DataFrame.
        
        Args:
            df: DataFrame to filter.
            criteria: Filter criteria to apply.
            battery_pack_col: Name of battery pack column.
            
        Returns:
            Filtered DataFrame.
        """
        filtered_df = df.copy()
        
        # Apply Tesla model filter
        if criteria.tesla_models:
            filtered_df = filtered_df[filtered_df["Tesla"].isin(criteria.tesla_models)]
        
        # Apply version filter
        if criteria.versions:
            filtered_df = filtered_df[filtered_df["Version"].isin(criteria.versions)]
        
        # Apply battery filter
        if criteria.batteries:
            filtered_df = filtered_df[filtered_df["Battery"].isin(criteria.batteries)]
        
        # Apply age filter
        filtered_df = filtered_df[
            (filtered_df["Age"] >= criteria.min_age) &
            (filtered_df["Age"] <= criteria.max_age)
        ]
        
        # Apply odometer filter
        filtered_df = filtered_df[
            (filtered_df["Odometer"] >= criteria.min_odo) &
            (filtered_df["Odometer"] <= criteria.max_odo)
        ]
        
        # Apply SOC limit filter
        if criteria.daily_soc_min is not None and criteria.daily_soc_max is not None:
            filtered_df = filtered_df[
                (filtered_df["Daily SOC Limit"].astype(float) >= criteria.daily_soc_min) &
                (filtered_df["Daily SOC Limit"].astype(float) <= criteria.daily_soc_max)
            ]
        
        # Apply DC ratio filter
        if criteria.dc_ratio_min is not None and criteria.dc_ratio_max is not None:
            filtered_df = filtered_df[
                (filtered_df["DC Ratio"].astype(float) >= criteria.dc_ratio_min) &
                (filtered_df["DC Ratio"].astype(float) <= criteria.dc_ratio_max)
            ]
        
        # Hide replaced packs
        if criteria.hide_replaced_packs and battery_pack_col and battery_pack_col in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[battery_pack_col] != 'Replaced']
        
        return filtered_df
    
    @staticmethod
    def prepare_plot_data(df: pd.DataFrame, x_column: str, y_column: str, battery_pack_col: Optional[str]) -> pd.DataFrame:
        """Prepare data for plotting.
        
        Args:
            df: Source DataFrame.
            x_column: X-axis column name.
            y_column: Y-axis column name.
            battery_pack_col: Battery pack column name.
            
        Returns:
            Filtered and sorted DataFrame ready for plotting.
        """
        # Convert to numeric
        plot_df = df.copy()
        plot_df[x_column] = pd.to_numeric(plot_df[x_column], errors='coerce')
        
        # Filter out invalid values
        plot_df = plot_df[
            (plot_df[x_column] > 0) &
            plot_df[x_column].notna() &
            plot_df[y_column].notna()
        ]
        
        # Sort by x column
        plot_df = plot_df.sort_values(by=x_column)
        
        # Add marker symbols based on battery pack status
        if battery_pack_col and battery_pack_col in plot_df.columns:
            plot_df['Marker Symbol'] = plot_df[battery_pack_col].fillna('Original').apply(
                lambda x: 'star' if x.strip() == 'Replaced' else 'circle'
            )
        else:
            plot_df['Marker Symbol'] = 'circle'
        
        return plot_df
    
    @staticmethod
    def calculate_degradation_per_x(df: pd.DataFrame, x_column: str, divisor: float = 1.0) -> pd.DataFrame:
        """Calculate degradation per X-axis unit.
        
        Args:
            df: DataFrame with degradation data.
            x_column: Column to use for calculation.
            divisor: Divisor to apply to X values.
            
        Returns:
            DataFrame with DegradationPerX column added.
        """
        result_df = df.copy()
        
        # Convert to numeric
        result_df['Degradation'] = pd.to_numeric(result_df['Degradation'], errors='coerce')
        result_df[x_column] = pd.to_numeric(result_df[x_column], errors='coerce')
        
        # Drop rows with NaN
        result_df = result_df.dropna(subset=['Degradation', x_column])
        
        # Calculate degradation per X
        result_df['DegradationPerX'] = result_df['Degradation'] / (result_df[x_column] / divisor)
        
        # Filter out invalid values
        result_df = result_df.replace([np.inf, -np.inf], np.nan).dropna(subset=['DegradationPerX'])
        result_df = result_df[result_df['DegradationPerX'] != 0]
        
        return result_df
    
    @staticmethod
    def predict_soh_70(batteries: List[str], df: pd.DataFrame, x_axis_data: str) -> List[SOHProjection]:
        """Predict when batteries will reach 70% SOH.
        
        Args:
            batteries: List of battery types to analyze.
            df: DataFrame with battery data.
            x_axis_data: X-axis selection ('Age', 'Odometer', or 'Cycles').
            
        Returns:
            List of SOHProjection objects.
        """
        projections = []
        
        for battery_type in batteries:
            battery_df = df[df["Battery"] == battery_type]
            
            # Clean data
            battery_df = battery_df.replace([np.inf, -np.inf], np.nan)
            battery_df = battery_df.dropna(subset=['Degradation'])
            
            if len(battery_df) <= 1:
                projections.append(SOHProjection(battery_type=battery_type))
                continue
            
            years_text = None
            kilometers_text = None
            
            # Calculate based on current x-axis
            if x_axis_data == 'Age' and 'Age' in battery_df.columns:
                years_text = BatteryDataProcessor._predict_years(battery_df)
            elif x_axis_data == 'Odometer' and 'Odometer' in battery_df.columns:
                kilometers_text = BatteryDataProcessor._predict_kilometers(battery_df, 'Odometer')
            elif x_axis_data == 'Cycles' and 'Cycles' in battery_df.columns:
                kilometers_text = BatteryDataProcessor._predict_kilometers(battery_df, 'Cycles')
            
            # Always try to calculate both if not already done
            if not years_text and 'Age' in battery_df.columns:
                years_text = BatteryDataProcessor._predict_years(battery_df)
            
            if not kilometers_text and 'Odometer' in battery_df.columns:
                kilometers_text = BatteryDataProcessor._predict_kilometers(battery_df, 'Odometer')
            
            projections.append(SOHProjection(
                battery_type=battery_type,
                years=years_text,
                kilometers=kilometers_text
            ))
        
        return projections
    
    @staticmethod
    def _predict_years(df: pd.DataFrame) -> str:
        """Predict years to 70% SOH.
        
        Args:
            df: DataFrame with Age and Degradation columns.
            
        Returns:
            Prediction string or "unknown".
        """
        clean_df = df[['Age', 'Degradation']].dropna()
        if len(clean_df) <= 1:
            return "unknown"
        
        X = clean_df['Age'].values.reshape(-1, 1)
        y = clean_df['Degradation'].values.reshape(-1, 1)
        
        lin_reg = LinearRegression()
        lin_reg.fit(X, y)
        
        predicted_months = (Config.SOH_70_DEGRADATION - lin_reg.intercept_) / lin_reg.coef_
        predicted_years = predicted_months / 12
        
        if Config.SOH_YEARS_MIN <= predicted_years[0][0] <= Config.SOH_YEARS_MAX:
            return f"{predicted_years[0][0]:.0f} years"
        
        return "unknown"
    
    @staticmethod
    def _predict_kilometers(df: pd.DataFrame, column: str) -> str:
        """Predict kilometers to 70% SOH.
        
        Args:
            df: DataFrame with column and Degradation.
            column: Column name to use for prediction.
            
        Returns:
            Prediction string or "unknown".
        """
        clean_df = df[[column, 'Degradation']].dropna()
        if len(clean_df) <= 1:
            return "unknown"
        
        X = clean_df[column].values.reshape(-1, 1)
        y = clean_df['Degradation'].values.reshape(-1, 1)
        
        lin_reg = LinearRegression()
        lin_reg.fit(X, y)
        
        predicted_km = (Config.SOH_70_DEGRADATION - lin_reg.intercept_) / lin_reg.coef_
        
        if Config.SOH_KM_MIN <= predicted_km[0][0] <= Config.SOH_KM_MAX:
            rounded_km = round(predicted_km[0][0] / 100000) * 100000
            return f"{rounded_km:.0f} kilometers"
        
        return "unknown"
    
    @staticmethod
    def get_tesla_retention_line() -> Tuple[np.ndarray, np.ndarray]:
        """Get Tesla's official battery retention line data.
        
        Returns:
            Tuple of (odometer_km, battery_retention) arrays.
        """
        odometer_miles = np.array(Config.TESLA_RETENTION_MILES)
        battery_retention = np.array(Config.TESLA_RETENTION_PERCENT)
        odometer_km = odometer_miles * Config.MILES_TO_KM
        
        # Create smooth line using logarithmic fitting
        odometer_km_log = np.log(odometer_km[1:])
        battery_retention_log = battery_retention[1:]
        
        log_reg = LinearRegression()
        log_reg.fit(odometer_km_log.reshape(-1, 1), battery_retention_log)
        
        odometer_km_smooth = np.linspace(odometer_km[1:].min(), odometer_km.max(), 500)
        battery_retention_smooth = log_reg.predict(np.log(odometer_km_smooth).reshape(-1, 1))
        
        # Insert initial point
        odometer_km_smooth = np.insert(odometer_km_smooth, 0, odometer_km[0])
        battery_retention_smooth = np.insert(battery_retention_smooth, 0, battery_retention[0])
        
        return odometer_km_smooth, battery_retention_smooth
