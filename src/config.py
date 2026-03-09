"""Configuration management for the Tesla Battery Analysis application."""
from typing import Dict, List, Any
import streamlit as st


class Config:
    """Application configuration constants and settings."""

    # Cache settings
    CACHE_TTL = 300  # seconds
    PERFORMANCE_CACHE_TTL = 900  # seconds
    REQUEST_TIMEOUT = 20  # seconds

    # Plotly settings
    PLOTLY_TEMPLATE = "plotly"
    COLOR_SEQUENCE = [
        "#0068c9", "#83c9ff", "#ff2b2b", "#ffabab", "#29b09d",
        "#7defa1", "#ff8700", "#ffd16a", "#6d3fc0", "#d5dae5",
    ]

    # Performance page colors
    PERFORMANCE_COLORS = [
        '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF',
        '#00FFFF', '#FFA500', '#800080', '#008000', '#000080',
        '#A52A2A', '#FFC0CB', '#808080', '#808000', '#00FFFF'
    ]

    # Data validation ranges
    SOC_MIN = -5
    SOC_MAX = 101
    CELL_TEMP_MIN = -30
    CELL_TEMP_MAX = 70
    SPEED_MIN = 0
    SPEED_MAX = 210

    # Filter thresholds
    MIN_AGE_MONTHS = 1
    MIN_ODOMETER_KM = 1000
    ODOMETER_STEP = 10000

    # Battery power thresholds
    BATTERY_POWER_THRESHOLD = 40  # kW
    COMBINED_MOTOR_POWER_THRESHOLD = 20  # kW

    # SOH projection settings
    SOH_70_DEGRADATION = -30  # %
    SOH_YEARS_MIN = 7
    SOH_YEARS_MAX = 20
    SOH_KM_MIN = 300000
    SOH_KM_MAX = 1500000
    MIN_PROJECTION_POINTS = 3

    # Columns to exclude from Google Sheets
    EXCLUDE_COLUMNS = ['B', 'G', 'H', 'I', 'J', 'O', 'P', 'W', 'X', 'Y']

    # Tesla battery retention data (for reference line)
    TESLA_RETENTION_MILES = [0, 50000, 100000, 150000, 200000]
    TESLA_RETENTION_PERCENT = [0, -8, -12, -13.5, -15]
    MILES_TO_KM = 1.60934

    # External URLs
    GOOGLE_FORMS_URL = "https://forms.gle/WtFayqANSr9kwKv39"
    PERFORMANCE_BASE_URL = "https://nginx.eivissacopter.com/smt/"

    # Images
    HEADER_IMAGE_URL = "https://uploads.tff-forum.de/original/4X/5/2/3/52397973df71db6122c1eda4c5c558d2ca70686c.jpeg"
    GOOGLE_FORMS_IMAGE_URL = "https://i.ibb.co/YZvSDRm/google-forms-400x182-removebg-preview.png"
    TESLA_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Tesla_T_symbol.svg/482px-Tesla_T_symbol.svg.png"
    COFFEE_IMAGE_URL = "https://media.giphy.com/media/o7RZbs4KAA6tvM4H6j/giphy.gif"
    X_LOGO_URL = "https://i.ibb.co/xLhFQNn/c23e7825a07e5e998bd361f9c991e12c-400x400-removebg-preview.png"

    # Social links
    REFERRAL_LINK = "https://www.tesla.com/referral/eivissa86753"
    COFFEE_LINK = "https://buymeacoffee.com/eivissa"
    X_LINK = "https://x.com/eivissacopter"

    @staticmethod
    def get_gcp_credentials() -> Dict[str, Any]:
        """Get Google Cloud Platform credentials from Streamlit secrets.

        Returns:
            Dictionary containing GCP service account credentials.
        """
        return {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace("\\n", "\n"),
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
        }

    @staticmethod
    def get_spreadsheet_url() -> str:
        """Get Google Sheets spreadsheet URL from Streamlit secrets.

        Returns:
            URL of the Google Sheets spreadsheet.
        """
        return st.secrets["connections"]["gsheets"]["spreadsheet"]

    @staticmethod
    def get_google_api_scope() -> List[str]:
        """Get Google API scope for authentication.

        Returns:
            List of API scope URLs.
        """
        return [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
