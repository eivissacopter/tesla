"""Performance data access from remote server."""
import re
import urllib.parse
from io import StringIO
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
import pandas as pd
import requests
import streamlit as st

from ..config import Config
from ..models import PerformanceFileInfo, PerformanceFolder


class PerformanceDataClient:
    """Client for accessing performance test data."""

    def __init__(self, base_url: str = Config.PERFORMANCE_BASE_URL):
        """Initialize the performance data client.

        Args:
            base_url: Base URL for performance data.
        """
        self.base_url = base_url.rstrip('/') + '/'

    @staticmethod
    @st.cache_resource
    def _get_session() -> requests.Session:
        """Create a cached requests session for remote downloads."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": "TeslaTechBeta/2.1 (+https://teslatechbeta.streamlit.app/)"
        })
        return session

    @staticmethod
    @st.cache_data(ttl=Config.PERFORMANCE_CACHE_TTL)
    def _fetch_text(url: str) -> str:
        """Fetch and cache raw text content from a URL."""
        response = PerformanceDataClient._get_session().get(url, timeout=Config.REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = response.encoding or 'utf-8'
        return response.text

    @staticmethod
    @st.cache_data(ttl=Config.PERFORMANCE_CACHE_TTL)
    def _fetch_csv_frame(url: str) -> pd.DataFrame:
        """Fetch and cache raw CSV content from a URL."""
        response = PerformanceDataClient._get_session().get(url, timeout=Config.REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = response.encoding or 'utf-8'
        return pd.read_csv(StringIO(response.text))

    @st.cache_data(ttl=Config.PERFORMANCE_CACHE_TTL)
    def scan_and_classify_folders(_self) -> List[PerformanceFolder]:
        """Scan the base URL and classify subfolders.

        Returns:
            List of PerformanceFolder objects.
        """
        classified_folders = []

        try:
            for directory in _self._parse_directory(_self.base_url):
                folder = _self._classify_folder(directory.strip('/'))
                if folder:
                    folder.path = urllib.parse.urljoin(_self.base_url, directory)
                    classified_folders.append(folder)
        except Exception as exc:
            st.error(f"Error scanning performance folders: {exc}")

        return classified_folders

    @staticmethod
    def _parse_directory(url: str) -> List[str]:
        """Parse directory listing from URL.

        Args:
            url: URL to parse.

        Returns:
            List of directory paths.
        """
        html = PerformanceDataClient._fetch_text(url)
        soup = BeautifulSoup(html, 'html.parser')
        return [anchor['href'] for anchor in soup.find_all('a', href=True) if anchor['href'].endswith('/')]

    @staticmethod
    def _classify_folder(folder_name: str) -> Optional[PerformanceFolder]:
        """Classify a folder based on its name.

        Args:
            folder_name: Name of the folder.

        Returns:
            PerformanceFolder object or None if classification fails.
        """
        pattern = re.compile(
            r"(?P<manufacturer>[^_]+)_"
            r"(?P<model>[^_]+)_"
            r"(?P<variant>[^_]+)_"
            r"(?P<model_year>\d+)_"
            r"(?P<battery>[^_]+)_"
            r"(?P<front_motor>[^_]+)_"
            r"(?P<rear_motor>[^_]+)_"
            r"(?P<tuning>[^_]+)_"
            r"(?P<acceleration_mode>[^/]+)"
        )

        match = pattern.match(folder_name)
        if not match:
            return None

        data = match.groupdict()
        data['tuning'] = urllib.parse.unquote(data['tuning'])
        data['acceleration_mode'] = urllib.parse.unquote(data['acceleration_mode'])
        return PerformanceFolder(**data, path="")

    def fetch_csv_headers_and_values(self, url: str) -> Tuple[List[str], Optional[int], Optional[int]]:
        """Fetch CSV headers and first valid SOC and Cell temp mid values.

        Args:
            url: URL of the CSV file.

        Returns:
            Tuple of (headers, SOC value, Cell temp mid value).
        """
        try:
            df = self._prepare_dataframe(self._fetch_csv_frame(url))
            headers = df.columns.tolist()
            if 'SOC' not in headers or 'Cell temp mid' not in headers:
                return headers, None, None

            filtered_df = df[
                df['SOC'].between(Config.SOC_MIN, Config.SOC_MAX)
                & df['Cell temp mid'].between(Config.CELL_TEMP_MIN, Config.CELL_TEMP_MAX)
            ]

            if filtered_df.empty:
                return headers, None, None

            first_valid_row = filtered_df.iloc[0]
            return headers, round(first_valid_row['SOC']), round(first_valid_row['Cell temp mid'])

        except Exception as exc:
            st.warning(f"Error fetching CSV from {url}: {exc}")
            return [], None, None

    def get_file_info(self, folders: List[PerformanceFolder]) -> List[PerformanceFileInfo]:
        """Get file information for all CSV files in folders.

        Args:
            folders: List of PerformanceFolder objects.

        Returns:
            List of PerformanceFileInfo objects.
        """
        file_info = []

        for folder in folders:
            try:
                html = self._fetch_text(folder.path)
                soup = BeautifulSoup(html, 'html.parser')
                files = [anchor['href'] for anchor in soup.find_all('a', href=True) if anchor['href'].endswith('.csv')]

                for file_name in files:
                    file_url = urllib.parse.urljoin(folder.path, file_name)
                    headers, soc_value, cell_temp_mid_value = self.fetch_csv_headers_and_values(file_url)

                    if 'SOC' not in headers or 'Cell temp mid' not in headers:
                        continue

                    if soc_value is None or cell_temp_mid_value is None:
                        continue

                    short_name = file_name.split('/')[-1].replace('.csv', '')
                    file_info.append(PerformanceFileInfo(
                        path=file_url,
                        soc=soc_value,
                        cell_temp_mid=cell_temp_mid_value,
                        name=short_name,
                        folder=folder
                    ))

            except Exception as exc:
                st.warning(f"Error processing folder {folder.path}: {exc}")

        file_info.sort(key=lambda info: (info.folder.get_legend_label(), info.soc, info.cell_temp_mid, info.name))
        return file_info

    @staticmethod
    def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize numeric telemetry fields before filtering."""
        prepared_df = df.copy()

        for column in ['SOC', 'Cell temp mid', 'Speed', 'Time']:
            if column in prepared_df.columns:
                prepared_df[column] = pd.to_numeric(prepared_df[column], errors='coerce')

        numeric_columns = prepared_df.select_dtypes(include='number').columns
        if len(numeric_columns) > 0:
            prepared_df[numeric_columns] = prepared_df[numeric_columns].ffill().bfill()

        return prepared_df

    @staticmethod
    @st.cache_data(ttl=Config.PERFORMANCE_CACHE_TTL, show_spinner=False)
    def fetch_csv_data(url: str) -> Optional[pd.DataFrame]:
        """Fetch and process CSV data from URL.

        Cached on the URL: the raw download is already cached, but the cleaning
        (_prepare_dataframe copy + ffill/bfill) and filtering re-ran for every
        file on each rerun (e.g. color-picker and smoothing changes).

        Args:
            url: URL of the CSV file.

        Returns:
            Processed DataFrame or None if error.
        """
        try:
            df = PerformanceDataClient._prepare_dataframe(PerformanceDataClient._fetch_csv_frame(url))

            required_columns = {'SOC', 'Cell temp mid'}
            if not required_columns.issubset(df.columns):
                return None

            filtered_df = df[
                df['SOC'].between(0, 101)
                & df['Cell temp mid'].between(0, 70)
            ].copy()

            if 'Speed' in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df['Speed'].between(Config.SPEED_MIN, Config.SPEED_MAX)
                ]
                filtered_df = filtered_df[filtered_df['Speed'].diff().fillna(1) > 0]

            return filtered_df.reset_index(drop=True)

        except Exception as exc:
            st.warning(f"Error fetching CSV data from {url}: {exc}")
            return None
