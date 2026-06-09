"""Data processing utilities for battery analysis."""
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
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
        if df.empty:
            return df.copy()

        mask = pd.Series(True, index=df.index)

        if criteria.tesla_models and 'Tesla' in df.columns:
            mask &= df['Tesla'].isin(criteria.tesla_models)

        if criteria.versions and 'Version' in df.columns:
            mask &= df['Version'].isin(criteria.versions)

        if criteria.batteries and 'Battery' in df.columns:
            mask &= df['Battery'].isin(criteria.batteries)

        if criteria.chronology_chemistries and 'Chronology Chemistry' in df.columns:
            mask &= df['Chronology Chemistry'].isin(criteria.chronology_chemistries)

        if criteria.chronology_plants and 'Chronology Plant' in df.columns:
            mask &= df['Chronology Plant'].isin(criteria.chronology_plants)

        if criteria.chronology_codes and 'Chronology Code' in df.columns:
            mask &= df['Chronology Code'].isin(criteria.chronology_codes)

        if 'Age' in df.columns:
            age = pd.to_numeric(df['Age'], errors='coerce')
            mask &= age.between(criteria.min_age, criteria.max_age, inclusive='both')

        if 'Odometer' in df.columns:
            odometer = pd.to_numeric(df['Odometer'], errors='coerce')
            mask &= odometer.between(criteria.min_odo, criteria.max_odo, inclusive='both')

        if (
            criteria.daily_soc_min is not None
            and criteria.daily_soc_max is not None
            and 'Daily SOC Limit' in df.columns
        ):
            daily_soc = pd.to_numeric(df['Daily SOC Limit'], errors='coerce')
            mask &= daily_soc.between(criteria.daily_soc_min, criteria.daily_soc_max, inclusive='both')

        if (
            criteria.dc_ratio_min is not None
            and criteria.dc_ratio_max is not None
            and 'DC Ratio' in df.columns
        ):
            dc_ratio = pd.to_numeric(df['DC Ratio'], errors='coerce')
            mask &= dc_ratio.between(criteria.dc_ratio_min, criteria.dc_ratio_max, inclusive='both')

        if criteria.hide_replaced_packs and battery_pack_col and battery_pack_col in df.columns:
            mask &= df[battery_pack_col].fillna('Original').ne('Replaced')

        return df.loc[mask].copy()

    @staticmethod
    def prepare_plot_data(
        df: pd.DataFrame,
        x_column: str,
        y_column: str,
        battery_pack_col: Optional[str]
    ) -> pd.DataFrame:
        """Prepare data for plotting.

        Args:
            df: Source DataFrame.
            x_column: X-axis column name.
            y_column: Y-axis column name.
            battery_pack_col: Battery pack column name.

        Returns:
            Filtered and sorted DataFrame ready for plotting.
        """
        if df.empty or x_column not in df.columns or y_column not in df.columns:
            return pd.DataFrame()

        plot_df = df.copy()
        plot_df[x_column] = pd.to_numeric(plot_df[x_column], errors='coerce')
        plot_df[y_column] = pd.to_numeric(plot_df[y_column], errors='coerce')

        plot_df = plot_df[
            plot_df[x_column].gt(0)
            & plot_df[x_column].notna()
            & plot_df[y_column].notna()
        ].sort_values(by=x_column)

        if battery_pack_col and battery_pack_col in plot_df.columns:
            marker_source = plot_df[battery_pack_col].fillna('Original').astype(str).str.strip()
            plot_df['Marker Symbol'] = np.where(marker_source.eq('Replaced'), 'star', 'circle')
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
        if df.empty or x_column not in df.columns or 'Degradation' not in df.columns:
            return pd.DataFrame()

        result_df = df.copy()
        result_df['Degradation'] = pd.to_numeric(result_df['Degradation'], errors='coerce')
        result_df[x_column] = pd.to_numeric(result_df[x_column], errors='coerce')
        result_df = result_df.dropna(subset=['Degradation', x_column])
        result_df = result_df[result_df[x_column].gt(0)]

        result_df['DegradationPerX'] = result_df['Degradation'] / (result_df[x_column] / divisor)
        result_df = result_df.replace([np.inf, -np.inf], np.nan).dropna(subset=['DegradationPerX'])
        return result_df[result_df['DegradationPerX'].ne(0)]

    @staticmethod
    def degradation_rate_by_group(
        df: pd.DataFrame,
        group_column: str,
        denominator_column: str,
        divisor: float = 1.0,
        min_samples: int = 5,
        confidence: float = 0.95,
    ) -> pd.DataFrame:
        """Mean degradation rate per group with a 95% confidence interval.

        Groups (e.g. chemistries or packs) are only reported when they clear
        `min_samples`, so the comparison reflects statistically meaningful
        cohorts rather than one-off submissions.
        """
        rates = BatteryDataProcessor.calculate_degradation_per_x(df, denominator_column, divisor)
        if rates.empty or group_column not in rates.columns:
            return pd.DataFrame()

        labels = rates[group_column].astype(str).str.strip()
        rates = rates[labels.ne('') & labels.ne('nan') & labels.ne('None')]
        if rates.empty:
            return pd.DataFrame()

        rows = []
        for group_value, chunk in rates.groupby(group_column):
            values = chunk['DegradationPerX'].dropna()
            n = int(values.size)
            if n < min_samples:
                continue
            mean = float(values.mean())
            std = float(values.std(ddof=1)) if n > 1 else 0.0
            standard_error = std / np.sqrt(n) if n > 0 else 0.0
            t_value = float(stats.t.ppf(0.5 + confidence / 2.0, n - 1)) if n > 1 else 0.0
            margin = t_value * standard_error
            rows.append({
                'Group': str(group_value),
                'Rate': mean,
                'CI': margin,
                'Lower': mean - margin,
                'Upper': mean + margin,
                'Samples': n,
            })

        result = pd.DataFrame(rows)
        return result.sort_values('Rate') if not result.empty else result

    @staticmethod
    def calendar_vs_cycle_aging(df: pd.DataFrame, min_samples: int = 20) -> Optional[Dict[str, float]]:
        """Decompose degradation into calendar (per month) and cycle components.

        Fits Degradation ~ Age + Cycles and reports each coefficient plus the
        standardized share of variation each driver explains, so users can see
        whether a pack ages mostly from time or from use.
        """
        required = {'Degradation', 'Age', 'Cycles'}
        if not required.issubset(df.columns):
            return None

        frame = df[['Degradation', 'Age', 'Cycles']].apply(pd.to_numeric, errors='coerce')
        frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
        frame = frame[(frame['Age'] > 0) & (frame['Cycles'] > 0)]
        n = int(len(frame))
        if n < min_samples:
            return None

        features = frame[['Age', 'Cycles']].to_numpy()
        target = frame['Degradation'].to_numpy()
        model = LinearRegression().fit(features, target)

        age_std = float(frame['Age'].std(ddof=1))
        cycle_std = float(frame['Cycles'].std(ddof=1))
        age_weight = abs(float(model.coef_[0]) * age_std)
        cycle_weight = abs(float(model.coef_[1]) * cycle_std)
        total_weight = age_weight + cycle_weight
        calendar_share = (age_weight / total_weight) if total_weight > 0 else None

        return {
            'n': n,
            'r2': float(model.score(features, target)),
            'calendar_per_month': float(model.coef_[0]),
            'cycle_per_1000': float(model.coef_[1]) * 1000.0,
            'calendar_share': calendar_share,
        }

    @staticmethod
    def calculate_overview_metrics(df: pd.DataFrame) -> Dict[str, Optional[float]]:
        """Calculate headline metrics for the currently filtered fleet."""
        if df.empty:
            return {
                'entries': 0,
                'users': 0,
                'batteries': 0,
                'median_degradation': None,
                'median_soh': None,
                'median_odometer': None,
            }

        return {
            'entries': int(len(df)),
            'users': int(df['Username'].nunique()) if 'Username' in df.columns else 0,
            'batteries': int(df['Battery'].nunique()) if 'Battery' in df.columns else 0,
            'median_degradation': float(df['Degradation'].median()) if 'Degradation' in df.columns else None,
            'median_soh': float(df['SOH'].median()) if 'SOH' in df.columns else None,
            'median_odometer': float(df['Odometer'].median()) if 'Odometer' in df.columns else None,
        }

    @staticmethod
    def analyze_energy_monitor_snapshot(
        average_consumption_wh_km: float,
        projected_range_km: float,
        soc_percent: float,
        rated_constant_wh_km: Optional[float] = None,
        current_rated_range_km: Optional[float] = None,
    ) -> Dict[str, Optional[float]]:
        """Estimate usable battery and rated-range behavior from an Energy app snapshot."""
        soc_fraction = float(soc_percent) / 100.0
        if soc_fraction <= 0:
            raise ValueError('SOC must be greater than 0%.')

        usable_battery_kwh = (
            float(average_consumption_wh_km) * float(projected_range_km) / soc_fraction / 1000.0
        )

        estimated_rated_range_100_km = None
        if rated_constant_wh_km is not None and rated_constant_wh_km > 0:
            estimated_rated_range_100_km = usable_battery_kwh * 1000.0 / float(rated_constant_wh_km)

        implied_rated_range_100_km = None
        inferred_constant_wh_km = None
        constant_delta_wh_km = None
        if current_rated_range_km is not None and current_rated_range_km > 0:
            implied_rated_range_100_km = float(current_rated_range_km) / soc_fraction
            if implied_rated_range_100_km > 0:
                inferred_constant_wh_km = usable_battery_kwh * 1000.0 / implied_rated_range_100_km

        if rated_constant_wh_km is not None and inferred_constant_wh_km is not None:
            constant_delta_wh_km = inferred_constant_wh_km - float(rated_constant_wh_km)

        return {
            'usable_battery_kwh': usable_battery_kwh,
            'estimated_rated_range_100_km': estimated_rated_range_100_km,
            'implied_rated_range_100_km': implied_rated_range_100_km,
            'inferred_constant_wh_km': inferred_constant_wh_km,
            'constant_delta_wh_km': constant_delta_wh_km,
        }

    @staticmethod
    def build_battery_summary(df: pd.DataFrame) -> pd.DataFrame:
        """Build a compact battery summary table for the filtered dataset."""
        if df.empty or 'Battery' not in df.columns:
            return pd.DataFrame()

        group_columns = ['Battery']
        if 'Version' in df.columns:
            group_columns.append('Version')

        aggregation = {
            'Samples': ('Battery', 'size'),
            'Users': ('Username', pd.Series.nunique) if 'Username' in df.columns else ('Battery', 'size'),
            'MedianSOH': ('SOH', 'median') if 'SOH' in df.columns else ('Degradation', 'median'),
            'MedianDegradation': ('Degradation', 'median') if 'Degradation' in df.columns else ('Battery', 'size'),
            'MedianAge': ('Age', 'median') if 'Age' in df.columns else ('Battery', 'size'),
            'MedianOdometer': ('Odometer', 'median') if 'Odometer' in df.columns else ('Battery', 'size'),
        }

        for source_column, target_column in [
            ('Chronology Pack', 'Chronology Pack'),
            ('Chronology Chemistry', 'Chemistry'),
            ('Chronology Plant', 'Plant'),
            ('Chronology Code', 'Code'),
            ('Chronology Confidence', 'Chronology Confidence'),
        ]:
            if source_column in df.columns:
                aggregation[target_column] = (source_column, BatteryDataProcessor._mode_or_first)

        summary = df.groupby(group_columns, dropna=False).agg(**aggregation).reset_index()

        rename_map = {
            'MedianSOH': 'Median SOH [%]',
            'MedianDegradation': 'Median Degradation [%]',
            'MedianAge': 'Median Age [months]',
            'MedianOdometer': 'Median ODO [km]',
        }
        summary = summary.rename(columns=rename_map)

        for column in ['Median SOH [%]', 'Median Degradation [%]', 'Median Age [months]', 'Median ODO [km]']:
            if column in summary.columns:
                summary[column] = pd.to_numeric(summary[column], errors='coerce').round(1)

        if 'Users' in summary.columns and 'Username' not in df.columns:
            summary = summary.drop(columns=['Users'])

        return summary.sort_values(by='Samples', ascending=False)

    @staticmethod
    def _mode_or_first(series: pd.Series):
        """Return the most common non-empty value in a series."""
        cleaned = series.dropna().astype(str).str.strip()
        cleaned = cleaned[cleaned.ne('') & cleaned.ne('nan') & cleaned.ne('None')]
        if cleaned.empty:
            return None
        return cleaned.mode().iloc[0]

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
            battery_df = df[df['Battery'] == battery_type].replace([np.inf, -np.inf], np.nan)
            battery_df = battery_df.dropna(subset=['Degradation'])

            if len(battery_df) < Config.MIN_PROJECTION_POINTS:
                projections.append(SOHProjection(battery_type=battery_type))
                continue

            years_text = BatteryDataProcessor._predict_years(battery_df) if 'Age' in battery_df.columns else 'unknown'
            kilometers_text = (
                BatteryDataProcessor._predict_distance_like_value(
                    battery_df,
                    'Odometer',
                    Config.SOH_KM_MIN,
                    Config.SOH_KM_MAX,
                    lambda value: f"{round(value / 100000) * 100000:.0f} kilometers"
                )
                if 'Odometer' in battery_df.columns else 'unknown'
            )
            cycles_text = (
                BatteryDataProcessor._predict_distance_like_value(
                    battery_df,
                    'Cycles',
                    1000,
                    10000,
                    lambda value: f"{round(value / 100) * 100:.0f} cycles"
                )
                if 'Cycles' in battery_df.columns else 'unknown'
            )

            if x_axis_data == 'Odometer':
                cycles_text = 'unknown'
            elif x_axis_data == 'Cycles':
                kilometers_text = 'unknown'

            projections.append(SOHProjection(
                battery_type=battery_type,
                years=years_text,
                kilometers=kilometers_text,
                cycles=cycles_text
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
        clean_df = df[['Age', 'Degradation']].dropna().drop_duplicates(subset=['Age']).sort_values('Age')
        if len(clean_df) < Config.MIN_PROJECTION_POINTS:
            return 'unknown'

        X = clean_df['Age'].to_numpy().reshape(-1, 1)
        y = clean_df['Degradation'].to_numpy()

        lin_reg = LinearRegression()
        lin_reg.fit(X, y)

        slope = float(lin_reg.coef_[0])
        if slope >= 0:
            return 'unknown'

        predicted_months = (Config.SOH_70_DEGRADATION - float(lin_reg.intercept_)) / slope
        predicted_years = predicted_months / 12

        if np.isfinite(predicted_years) and Config.SOH_YEARS_MIN <= predicted_years <= Config.SOH_YEARS_MAX:
            return f"{predicted_years:.0f} years"

        return 'unknown'

    @staticmethod
    def _predict_distance_like_value(
        df: pd.DataFrame,
        column: str,
        minimum: float,
        maximum: float,
        formatter
    ) -> str:
        """Predict a threshold crossing for odometer- or cycle-based views."""
        clean_df = df[[column, 'Degradation']].dropna().drop_duplicates(subset=[column]).sort_values(column)
        if len(clean_df) < Config.MIN_PROJECTION_POINTS:
            return 'unknown'

        X = clean_df[column].to_numpy().reshape(-1, 1)
        y = clean_df['Degradation'].to_numpy()

        lin_reg = LinearRegression()
        lin_reg.fit(X, y)

        slope = float(lin_reg.coef_[0])
        if slope >= 0:
            return 'unknown'

        predicted_value = (Config.SOH_70_DEGRADATION - float(lin_reg.intercept_)) / slope
        if not np.isfinite(predicted_value) or not minimum <= predicted_value <= maximum:
            return 'unknown'

        return formatter(predicted_value)

    @staticmethod
    def get_tesla_retention_line() -> Tuple[np.ndarray, np.ndarray]:
        """Get Tesla's official battery retention line data.

        Returns:
            Tuple of (odometer_km, battery_retention) arrays.
        """
        odometer_miles = np.array(Config.TESLA_RETENTION_MILES)
        battery_retention = np.array(Config.TESLA_RETENTION_PERCENT)
        odometer_km = odometer_miles * Config.MILES_TO_KM

        odometer_km_log = np.log(odometer_km[1:])
        battery_retention_log = battery_retention[1:]

        log_reg = LinearRegression()
        log_reg.fit(odometer_km_log.reshape(-1, 1), battery_retention_log)

        odometer_km_smooth = np.linspace(odometer_km[1:].min(), odometer_km.max(), 500)
        battery_retention_smooth = log_reg.predict(np.log(odometer_km_smooth).reshape(-1, 1))

        odometer_km_smooth = np.insert(odometer_km_smooth, 0, odometer_km[0])
        battery_retention_smooth = np.insert(battery_retention_smooth, 0, battery_retention[0])

        return odometer_km_smooth, battery_retention_smooth
