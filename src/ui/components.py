"""UI components for the Tesla Battery Analysis application."""
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from ..config import Config
from ..data.range_constants import RangeConstantClient
from ..utils.data_processing import BatteryDataProcessor


class UIComponents:
    """Reusable UI components."""

    @staticmethod
    def _get_container(container: Any = None):
        """Resolve the target Streamlit container."""
        return container if container is not None else st.sidebar

    @staticmethod
    def render_header() -> None:
        """Render the application header with logo and title."""
        st.markdown(
            f"""
            <style>
                .header {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    flex-direction: column;
                    padding: 0rem 0;
                    margin-bottom: 0rem;
                }}
                .header img {{
                    width: 100%;
                    height: auto;
                }}
                .header h1 {{
                    margin: 0;
                    padding-top: 1rem;
                    text-align: center;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 32px;
                }}
                .header h1 span {{
                    margin: 0 10px;
                }}
            </style>
            <div class="header">
                <img src="{Config.HEADER_IMAGE_URL}" alt="Tesla Battery Analysis">
                <h1><span>&#128267;</span> Tesla Battery Analysis <span>&#128267;</span></h1>
            </div>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def render_performance_header() -> None:
        """Render the performance analysis header."""
        st.markdown(
            f"""
            <style>
                .header {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    flex-direction: column;
                    padding: 0rem 0;
                    margin-bottom: 0rem;
                }}
                .header img {{
                    width: 100%;
                    height: auto;
                }}
                .header h1 {{
                    margin: 0;
                    padding-top: 1rem;
                    text-align: center;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 32px;
                }}
                .header h1 span {{
                    margin: 0 10px;
                }}
            </style>
            <div class="header">
                <img src="{Config.HEADER_IMAGE_URL}" alt="Tesla Performance Analysis">
                <h1><span>&#128640;</span> Tesla Performance Analysis <span>&#128640;</span></h1>
            </div>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def render_google_forms_banner() -> None:
        """Render the Google Forms banner with animated arrows."""
        st.markdown(
            f"""
            <style>
                @keyframes pulse {{
                    0% {{ transform: scale(1); opacity: 1; }}
                    50% {{ transform: scale(1.05); opacity: 0.9; }}
                    100% {{ transform: scale(1); opacity: 1; }}
                }}
                .google-form-logo {{
                    display: block;
                    margin: 0rem auto;
                    width: 300px;
                    height: auto;
                    animation: pulse 2s infinite ease-in-out;
                }}
                .arrow-text {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-size: 24px;
                    font-weight: bold;
                    margin-top: 20px;
                }}
                .arrow {{
                    animation: blinker 3s linear infinite;
                    font-size: 24px;
                    margin: 0 20px;
                }}
                @keyframes blinker {{
                    50% {{ opacity: 0; }}
                }}
            </style>
            <div class="arrow-text">
                <span>Add your data here</span>
                <span class="arrow">&rarr;</span>
                <a href="{Config.GOOGLE_FORMS_URL}" target="_blank">
                    <img src="{Config.GOOGLE_FORMS_IMAGE_URL}" class="google-form-logo" alt="Google Forms Survey">
                </a>
                <span class="arrow">&larr;</span>
                <span>Add your data here</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def render_sidebar_footer() -> None:
        """Render the sidebar footer with social links."""
        st.sidebar.markdown(
            f"""
            <style>
                .sidebar-content {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0rem;
                }}
                .sidebar-content img {{
                    height: auto;
                }}
                .sidebar-content .akku-wiki {{
                    width: 90px;
                }}
                .sidebar-content .buy-me-coffee {{
                    width: 240px;
                }}
                .sidebar-content .follow-on-x {{
                    width: 110px;
                }}
                .sidebar-content .text {{
                    text-align: center;
                    font-size: 12px;
                    margin-top: 5px;
                }}
            </style>
            <div class="sidebar-content">
                <a href="{Config.REFERRAL_LINK}" target="_blank">
                    <div>
                        <img src="{Config.TESLA_LOGO_URL}" class="akku-wiki" alt="Tesla Referral">
                        <div class="text">Referral</div>
                    </div>
                </a>
                <a href="{Config.COFFEE_LINK}" target="_blank">
                    <img src="{Config.COFFEE_IMAGE_URL}" class="buy-me-coffee" alt="Buy Me a Coffee">
                </a>
                <a href="{Config.X_LINK}" target="_blank">
                    <img src="{Config.X_LOGO_URL}" class="follow-on-x" alt="Follow on X">
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def render_username_search() -> str:
        """Render username search field.

        Returns:
            Username search string.
        """
        return st.text_input("Search by Username:", key="username")

    @staticmethod
    def render_latest_entries(df: pd.DataFrame) -> None:
        """Render latest entries table.

        Args:
            df: DataFrame with latest entries.
        """
        st.subheader("Latest Entries")
        preferred_columns = [
            column for column in [
                'Username', 'Tesla', 'Version', 'Battery', 'Chronology Pack', 'Chronology Chemistry',
                'SOH', 'Degradation', 'Age', 'Odometer'
            ] if column in df.columns
        ]
        display_df = df[preferred_columns] if preferred_columns else df
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    @staticmethod
    def create_model_filters(
        df: pd.DataFrame,
        container: Any = None,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Create Tesla model, version, and battery filters.

        Args:
            df: DataFrame to extract filter options from.

        Returns:
            Tuple of (tesla_models, versions, batteries).
        """
        target = UIComponents._get_container(container)
        tesla_options = sorted(df['Tesla'].dropna().unique().tolist()) if 'Tesla' in df.columns else []
        tesla = target.multiselect(':red_car: Tesla', tesla_options, key='tesla')

        if tesla and 'Tesla' in df.columns:
            df_filtered = df[df['Tesla'].isin(tesla)]
        else:
            df_filtered = df.copy()

        version_options = sorted(df_filtered['Version'].dropna().unique().tolist()) if 'Version' in df_filtered.columns else []
        version = target.multiselect(':vertical_traffic_light: Version', version_options, key='version')

        if version and 'Version' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Version'].isin(version)]

        battery_options = sorted(df_filtered['Battery'].dropna().unique().tolist()) if 'Battery' in df_filtered.columns else []
        battery = target.multiselect(':battery: Battery', battery_options, key='battery')

        return tesla, version, battery

    @staticmethod
    def create_chronology_filters(
        df: pd.DataFrame,
        container: Any = None,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Create Akkuchronik-derived filters."""
        if df.empty:
            return [], [], []

        target = UIComponents._get_container(container)
        target.markdown('#### Akkuchronik')
        filtered_df = df.copy()

        chemistry_options = sorted(filtered_df['Chronology Chemistry'].dropna().unique().tolist()) if 'Chronology Chemistry' in filtered_df.columns else []
        chemistries = target.multiselect(':test_tube: Chemistry', chemistry_options, key='chronology_chemistry')
        if chemistries and 'Chronology Chemistry' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Chronology Chemistry'].isin(chemistries)]

        plant_options = sorted(filtered_df['Chronology Plant'].dropna().unique().tolist()) if 'Chronology Plant' in filtered_df.columns else []
        plants = target.multiselect(':factory: Plant', plant_options, key='chronology_plant')
        if plants and 'Chronology Plant' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Chronology Plant'].isin(plants)]

        code_options = sorted(filtered_df['Chronology Code'].dropna().unique().tolist()) if 'Chronology Code' in filtered_df.columns else []
        codes = target.multiselect(':hash: Akku-Code', code_options, key='chronology_code')

        return chemistries, plants, codes

    @staticmethod
    def create_age_odo_filters(
        df: pd.DataFrame,
        container: Any = None,
    ) -> Tuple[int, int, int, int]:
        """Create age and odometer range filters.

        Args:
            df: DataFrame to extract ranges from.

        Returns:
            Tuple of (min_age, max_age, min_odo, max_odo).
        """
        target = UIComponents._get_container(container)
        age_values = pd.to_numeric(df.get('Age'), errors='coerce').dropna() if 'Age' in df.columns else pd.Series(dtype=float)
        odo_values = pd.to_numeric(df.get('Odometer'), errors='coerce').dropna() if 'Odometer' in df.columns else pd.Series(dtype=float)

        age_min = max(Config.MIN_AGE_MONTHS, int(age_values.min())) if not age_values.empty else Config.MIN_AGE_MONTHS
        age_max = max(age_min, int(np.ceil(age_values.max()))) if not age_values.empty else age_min
        odo_min = max(Config.MIN_ODOMETER_KM, int(odo_values.min())) if not odo_values.empty else Config.MIN_ODOMETER_KM
        odo_max = max(odo_min, int(odo_values.max())) if not odo_values.empty else odo_min

        age_range = target.slider(
            'Age [months]',
            min_value=age_min,
            max_value=age_max,
            value=(age_min, age_max)
        )
        odo_range = target.slider(
            'Odometer [km]',
            min_value=odo_min,
            max_value=odo_max,
            value=(odo_min, odo_max),
            step=Config.ODOMETER_STEP
        )

        return age_range[0], age_range[1], odo_range[0], odo_range[1]

    @staticmethod
    def create_axis_selectors(container: Any = None) -> Tuple[str, str]:
        """Create Y-axis and X-axis data selectors.

        Returns:
            Tuple of (y_axis_data, x_axis_data).
        """
        target = UIComponents._get_container(container)
        col7, col8 = target.columns(2)

        y_axis_data = col7.radio(
            ':arrow_up_down: Y-axis Data',
            ['Degradation', 'Capacity', 'Rated Range'],
            index=0
        )

        x_axis_data = col8.radio(
            ':left_right_arrow: X-axis Data',
            ['Age', 'Odometer', 'Cycles'],
            index=0
        )

        return y_axis_data, x_axis_data

    @staticmethod
    def create_trend_line_selector(container: Any = None) -> Tuple[bool, Optional[str]]:
        """Create trend line selector.

        Returns:
            Tuple of (add_trend_line, trend_line_type).
        """
        target = UIComponents._get_container(container)
        add_trend_line = target.checkbox(':chart_with_downwards_trend: Trend Line', value=False)

        trend_line_type = None
        if add_trend_line:
            trend_line_type = target.selectbox(
                'Trend Line Type',
                ['Linear Regression', 'Logarithmic Regression', 'Polynomial Regression (3rd Degree)']
            )

        return add_trend_line, trend_line_type

    @staticmethod
    def create_hide_replaced_packs_filter(container: Any = None) -> bool:
        """Create hide replaced packs filter.

        Returns:
            Boolean indicating whether to hide replaced packs.
        """
        target = UIComponents._get_container(container)
        return target.checkbox(':star: Hide Replaced Packs', value=True)

    @staticmethod
    def create_nerdy_options(
        df: pd.DataFrame,
        container: Any = None,
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Create advanced filtering options.

        Args:
            df: DataFrame for range calculation.

        Returns:
            Tuple of (daily_soc_min, daily_soc_max, dc_ratio_min, dc_ratio_max).
        """
        target = UIComponents._get_container(container)
        filter_option = target.radio(
            'Nerdy Options',
            ['Off', 'Daily SOC Limit', 'DC Ratio'],
            index=0
        )

        daily_soc_min = daily_soc_max = dc_ratio_min = dc_ratio_max = None

        if filter_option == 'Daily SOC Limit' and 'Daily SOC Limit' in df.columns:
            daily_soc_values = pd.to_numeric(df['Daily SOC Limit'], errors='coerce').dropna()
            if daily_soc_values.empty:
                target.info('No Daily SOC Limit data available in the current slice.')
            else:
                soc_range = target.slider(
                    'Daily SOC Limit [%]',
                    min_value=float(daily_soc_values.min()),
                    max_value=float(daily_soc_values.max()),
                    value=(float(daily_soc_values.min()), float(daily_soc_values.max())),
                    step=5.0
                )
                daily_soc_min, daily_soc_max = soc_range

        elif filter_option == 'DC Ratio' and 'DC Ratio' in df.columns:
            dc_ratio_values = pd.to_numeric(df['DC Ratio'], errors='coerce').dropna()
            if dc_ratio_values.empty:
                target.info('No DC ratio data available in the current slice.')
            else:
                ratio_range = target.slider(
                    'DC Fast-Charge Ratio [%]',
                    min_value=float(dc_ratio_values.min()),
                    max_value=float(dc_ratio_values.max()),
                    value=(float(dc_ratio_values.min()), float(dc_ratio_values.max())),
                    step=5.0
                )
                dc_ratio_min, dc_ratio_max = ratio_range

        return daily_soc_min, daily_soc_max, dc_ratio_min, dc_ratio_max

    @staticmethod
    def render_cache_refresh_button(container: Any = None) -> bool:
        """Render cache refresh button.

        Returns:
            True if button was clicked.
        """
        target = UIComponents._get_container(container)
        if target.button('Clear Cache', key='clear_cache_refresh'):
            st.cache_data.clear()
            st.cache_resource.clear()
            target.success('Cache cleared! Please rerun the app.')
            return True
        return False

    @staticmethod
    def render_energy_monitor_calculator(container: Any = None) -> None:
        """Render an Energy app calculator for usable battery and rated range."""
        target = UIComponents._get_container(container)
        target.markdown('#### Energy Monitor')
        target.caption(
            'Use your Energy app average consumption, projected range, and current SoC '
            'to estimate usable battery and your rated-range constant.'
        )

        preset_options = RangeConstantClient.list_labels()
        selected_preset = target.selectbox(
            'Car model / preset',
            preset_options,
            index=0,
            key='energy_monitor_preset',
        )
        reference = RangeConstantClient.get_reference(selected_preset)

        rated_constant = target.number_input(
            'Rated constant [Wh/km]',
            min_value=80.0,
            max_value=250.0,
            value=float(reference['constant_wh_km']),
            step=0.1,
            key='energy_monitor_constant',
            help='Prefilled from the selected model, but editable for your own snapshot.',
        )

        avg_consumption = target.number_input(
            'Energy app consumption [Wh/km]',
            min_value=50.0,
            max_value=400.0,
            value=160.0,
            step=1.0,
            key='energy_monitor_consumption',
        )
        projected_range = target.number_input(
            'Energy app range [km]',
            min_value=1.0,
            max_value=1000.0,
            value=250.0,
            step=1.0,
            key='energy_monitor_range',
        )
        soc_percent = target.number_input(
            'Current SoC [%]',
            min_value=1.0,
            max_value=100.0,
            value=80.0,
            step=1.0,
            key='energy_monitor_soc',
        )
        current_rated_range = target.number_input(
            'Displayed rated range [km] (optional)',
            min_value=0.0,
            max_value=1000.0,
            value=0.0,
            step=1.0,
            key='energy_monitor_rated_range',
            help='Optional battery-indicator range at the same SoC to infer your personal constant.',
        )

        snapshot = BatteryDataProcessor.analyze_energy_monitor_snapshot(
            average_consumption_wh_km=avg_consumption,
            projected_range_km=projected_range,
            soc_percent=soc_percent,
            rated_constant_wh_km=rated_constant,
            current_rated_range_km=current_rated_range if current_rated_range > 0 else None,
        )

        target.metric('Usable battery', f"{snapshot['usable_battery_kwh']:.1f} kWh")
        if snapshot['estimated_rated_range_100_km'] is not None:
            target.metric('Estimated rated range @100%', f"{snapshot['estimated_rated_range_100_km']:.0f} km")
        if snapshot['implied_rated_range_100_km'] is not None:
            target.metric('Implied rated range @100%', f"{snapshot['implied_rated_range_100_km']:.0f} km")

        if snapshot['inferred_constant_wh_km'] is not None:
            target.metric('Inferred constant', f"{snapshot['inferred_constant_wh_km']:.1f} Wh/km")
            if snapshot['constant_delta_wh_km'] is not None:
                target.caption(
                    f"Delta vs selected constant: {snapshot['constant_delta_wh_km']:+.1f} Wh/km"
                )
        else:
            target.caption('Add your displayed rated range to infer your current personal constant.')

        if selected_preset != 'Custom / Manual':
            target.info(
                f"Reference: {reference['label']} | {reference['constant_wh_km']:.1f} Wh/km. "
                f"{reference['notes']}"
            )

        target.caption('Formula: consumption x projected range / SoC = usable battery capacity')

    @staticmethod
    def render_soh_projections(projections: list, batteries: list) -> None:
        """Render SOH 70% projections.

        Args:
            projections: List of SOHProjection objects.
            batteries: List of battery types being analyzed.
        """
        if not batteries:
            return

        st.markdown(
            """
            <div style="text-align:center; font-size:16px; padding:10px; margin-top:20px;">
                With these filter settings, the:
            </div>
            """,
            unsafe_allow_html=True
        )

        for projection in projections:
            st.markdown(
                f"""
                <div style="text-align:center; font-size:16px; padding:5px; margin-top:5px;">
                    {projection.get_display_text()}
                </div>
                """,
                unsafe_allow_html=True
            )
