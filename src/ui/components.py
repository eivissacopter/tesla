"""UI components for the Tesla Battery Analysis application."""
import streamlit as st
from typing import List, Optional, Tuple
import pandas as pd

from ..config import Config


class UIComponents:
    """Reusable UI components."""
    
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
                <h1><span>🔋</span> Tesla Battery Analysis <span>🔋</span></h1>
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
                <h1><span>🚀</span> Tesla Performance Analysis <span>🚀</span></h1>
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
                <span class="arrow">🡢</span>
                <a href="{Config.GOOGLE_FORMS_URL}" target="_blank">
                    <img src="{Config.GOOGLE_FORMS_IMAGE_URL}" class="google-form-logo" alt="Google Forms Survey">
                </a>
                <span class="arrow">🡠</span>
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
        st.markdown(
            """
            <div>
                Latest Entries
            </div>
            """,
            unsafe_allow_html=True
        )
        st.write(df)
    
    @staticmethod
    def create_model_filters(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
        """Create Tesla model, version, and battery filters.
        
        Args:
            df: DataFrame to extract filter options from.
            
        Returns:
            Tuple of (tesla_models, versions, batteries).
        """
        tesla = st.sidebar.multiselect(
            ":red_car: Tesla",
            df["Tesla"].unique(),
            key="tesla"
        )
        
        if tesla:
            df_filtered = df[df["Tesla"].isin(tesla)]
        else:
            df_filtered = df.copy()
        
        version = st.sidebar.multiselect(
            ":vertical_traffic_light: Version",
            df_filtered["Version"].unique(),
            key="version"
        )
        
        if version:
            df_filtered = df_filtered[df_filtered["Version"].isin(version)]
        
        battery = st.sidebar.multiselect(
            ":battery: Battery",
            df_filtered["Battery"].unique(),
            key="battery"
        )
        
        return tesla, version, battery
    
    @staticmethod
    def create_age_odo_filters(df: pd.DataFrame) -> Tuple[int, int, int, int]:
        """Create age and odometer range filters.
        
        Args:
            df: DataFrame to extract ranges from.
            
        Returns:
            Tuple of (min_age, max_age, min_odo, max_odo).
        """
        col3, col4 = st.sidebar.columns(2)
        
        min_age = col3.number_input(
            ":clock630: MIN Age (months)",
            min_value=1,
            value=max(1, int(df["Age"].min()))
        )
        
        max_age = col4.number_input(
            ":clock12: MAX Age (months)",
            min_value=1,
            value=int(df["Age"].max())
        )
        
        col5, col6 = st.sidebar.columns(2)
        
        min_odo = col5.number_input(
            ":arrow_forward: MIN ODO (km)",
            min_value=1000,
            value=max(1000, int(df["Odometer"].min())),
            step=10000
        )
        
        max_odo = col6.number_input(
            ":fast_forward: MAX ODO (km)",
            min_value=1000,
            value=int(df["Odometer"].max()),
            step=10000
        )
        
        return min_age, max_age, min_odo, max_odo
    
    @staticmethod
    def create_axis_selectors() -> Tuple[str, str]:
        """Create Y-axis and X-axis data selectors.
        
        Returns:
            Tuple of (y_axis_data, x_axis_data).
        """
        col7, col8 = st.sidebar.columns(2)
        
        y_axis_data = col7.radio(
            ":arrow_up_down: Y-axis Data",
            ['Degradation', 'Capacity', 'Rated Range'],
            index=0
        )
        
        x_axis_data = col8.radio(
            ":left_right_arrow: X-axis Data",
            ['Age', 'Odometer', 'Cycles'],
            index=0
        )
        
        return y_axis_data, x_axis_data
    
    @staticmethod
    def create_trend_line_selector() -> Tuple[bool, Optional[str]]:
        """Create trend line selector.
        
        Returns:
            Tuple of (add_trend_line, trend_line_type).
        """
        add_trend_line = st.sidebar.checkbox(
            ":chart_with_downwards_trend: Trend Line",
            value=False
        )
        
        trend_line_type = None
        if add_trend_line:
            trend_line_type = st.sidebar.selectbox(
                "Trend Line Type",
                ['Linear Regression', 'Logarithmic Regression', 'Polynomial Regression (3rd Degree)']
            )
        
        return add_trend_line, trend_line_type
    
    @staticmethod
    def create_hide_replaced_packs_filter() -> bool:
        """Create hide replaced packs filter.
        
        Returns:
            Boolean indicating whether to hide replaced packs.
        """
        return st.sidebar.checkbox(":star: Hide Replaced Packs", value=True)
    
    @staticmethod
    def create_nerdy_options(df: pd.DataFrame) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Create advanced filtering options.
        
        Args:
            df: DataFrame for range calculation.
            
        Returns:
            Tuple of (daily_soc_min, daily_soc_max, dc_ratio_min, dc_ratio_max).
        """
        filter_option = st.sidebar.radio(
            "Nerdy Options",
            ["Off", "Daily SOC Limit", "AC/DC Ratio"],
            index=0
        )
        
        daily_soc_min = daily_soc_max = dc_ratio_min = dc_ratio_max = None
        
        if filter_option == "Daily SOC Limit":
            col1, col2 = st.sidebar.columns(2)
            daily_soc_limit_values = df["Daily SOC Limit"].dropna().astype(float)
            daily_soc_min = col1.number_input(
                "Min SOC Limit",
                value=float(daily_soc_limit_values.min()),
                step=10.0,
                min_value=50.0,
                max_value=100.0,
                key="daily_soc_min"
            )
            daily_soc_max = col2.number_input(
                "Max SOC Limit",
                value=float(daily_soc_limit_values.max()),
                step=10.0,
                min_value=50.0,
                max_value=100.0,
                key="daily_soc_max"
            )
        
        elif filter_option == "AC/DC Ratio":
            col3, col4 = st.sidebar.columns(2)
            dc_ratio_values = df["DC Ratio"].dropna().astype(float)
            dc_ratio_min = col3.number_input(
                "Min DC Ratio",
                value=float(dc_ratio_values.min()),
                step=25.0,
                min_value=0.0,
                max_value=100.0,
                key="dc_ratio_min"
            )
            dc_ratio_max = col4.number_input(
                "Max DC Ratio",
                value=float(dc_ratio_values.max()),
                step=25.0,
                min_value=0.0,
                max_value=100.0,
                key="dc_ratio_max"
            )
        
        return daily_soc_min, daily_soc_max, dc_ratio_min, dc_ratio_max
    
    @staticmethod
    def render_cache_refresh_button() -> bool:
        """Render cache refresh button.
        
        Returns:
            True if button was clicked.
        """
        if st.sidebar.button("Clear Cache", key="clear_cache_refresh"):
            st.cache_data.clear()
            st.success("Cache cleared! Please rerun the app.")
            return True
        return False
    
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
            text = projection.get_display_text()
            st.markdown(
                f"""
                <div style="text-align:center; font-size:16px; padding:5px; margin-top:5px;">
                    {text}
                </div>
                """,
                unsafe_allow_html=True
            )
