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
    PLOTLY_TEMPLATE = "plotly_dark"
    # Opaque chart background, matching .streamlit/config.toml backgroundColor, so
    # in-app charts blend in AND exported PNGs keep the dark background (a
    # transparent export shows black in the app but white on sites like X).
    CHART_BACKGROUND = "#0B0E14"
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

    # Default lower bound preselected on the range sliders when the app loads
    DEFAULT_MIN_AGE_MONTHS = 24
    DEFAULT_MIN_ODOMETER_KM = 30000

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

    # Physically plausible ranges. Values outside become NaN so a single bad
    # submission (e.g. a 9.9-billion-km odometer) can't break sliders or skew stats.
    SANITY_BOUNDS = {
        'Age': (0, 220),               # months (~18 years)
        'Odometer': (0, 1_500_000),    # km
        'Rated Range': (0, 800),       # km
        'Capacity Net Now': (0, 130),  # kWh
        'Cycles': (0, 6000),
        'Daily SOC Limit': (0, 100),   # %
        'DC Ratio': (0, 100),          # %
        'Degradation': (-60, 0.0001),  # %, already non-positive
    }

    # Manufacturing origin (reported in the sheet) -> Tesla factory code
    ORIGIN_TO_FACTORY = {
        'China': 'MIC',     # Shanghai
        'Germany': 'MIG',   # Berlin-Brandenburg (Grünheide)
        'USA': 'MIA',       # Fremont / Austin
    }

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
    def has_service_account() -> bool:
        """Return True if Google service-account credentials are configured.

        When absent (e.g. local/dev runs without secrets), the data layer reads
        the link-viewable spreadsheet directly instead of authenticating.
        """
        try:
            return "gcp_service_account" in st.secrets
        except Exception:
            return False

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
    def normalize_chemistry(value: Any) -> Any:
        """Canonicalize a reported chemistry to NCA / NMC / LFP (or None).

        The sheet mixes spellings and plant suffixes (e.g. 'NCM', 'NCA MIC').
        """
        if value is None:
            return None
        text = str(value).strip().upper()
        if not text or text == 'NAN':
            return None
        if 'LFP' in text or 'LIFEPO' in text:
            return 'LFP'
        if 'NCA' in text:
            return 'NCA'
        if 'NMC' in text or 'NCM' in text:
            return 'NMC'
        return None

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
