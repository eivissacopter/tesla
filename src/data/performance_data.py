"""Performance data access from remote server."""
import re
import json
import os
from typing import List, Dict, Optional, Tuple
from io import StringIO
import urllib.parse

import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st

from ..config import Config
from ..models import PerformanceFolder, PerformanceFileInfo


class PerformanceDataClient:
    """Client for accessing performance test data."""
    
    METADATA_FILE = "metadata_cache.json"
    
    def __init__(self, base_url: str = Config.PERFORMANCE_BASE_URL):
        """Initialize the performance data client.
        
        Args:
            base_url: Base URL for performance data.
        """
        self.base_url = base_url
        self.metadata_cache = self._load_metadata_cache()
    
    def _load_metadata_cache(self) -> Dict:
        """Load metadata cache from file.
        
        Returns:
            Dictionary containing cached metadata.
        """
        if os.path.exists(self.METADATA_FILE):
            try:
                with open(self.METADATA_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_metadata_cache(self) -> None:
        """Save metadata cache to file."""
        try:
            with open(self.METADATA_FILE, "w") as f:
                json.dump(self.metadata_cache, f)
        except Exception as e:
            st.warning(f"Could not save metadata cache: {e}")
    
    @st.cache_data(ttl=600)
    def scan_and_classify_folders(_self) -> List[PerformanceFolder]:
        """Scan the base URL and classify subfolders.
        
        Returns:
            List of PerformanceFolder objects.
        """
        classified_folders = []
        
        try:
            dirs = _self._parse_directory(_self.base_url)
            
            for d in dirs:
                full_path = urllib.parse.urljoin(_self.base_url, d)
                folder = _self._classify_folder(d.strip('/'))
                
                if folder:
                    folder.path = full_path
                    classified_folders.append(folder)
                    
        except Exception as e:
            st.error(f"Error scanning performance folders: {e}")
        
        return classified_folders
    
    @staticmethod
    def _parse_directory(url: str) -> List[str]:
        """Parse directory listing from URL.
        
        Args:
            url: URL to parse.
            
        Returns:
            List of directory paths.
        """
        response = requests.get(url)
        if response.status_code != 200:
            st.error(f"Failed to access {url}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        dirs = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('/')]
        return dirs
    
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
        if match:
            data = match.groupdict()
            data['tuning'] = urllib.parse.unquote(data['tuning'])
            data['acceleration_mode'] = urllib.parse.unquote(data['acceleration_mode'])
            return PerformanceFolder(**data, path="")
        
        return None
    
    def fetch_csv_headers_and_values(self, url: str) -> Tuple[List[str], Optional[int], Optional[int]]:
        """Fetch CSV headers and first valid SOC and Cell temp mid values.
        
        Args:
            url: URL of the CSV file.
            
        Returns:
            Tuple of (headers, SOC value, Cell temp mid value).
        """
        # Check cache first
        if url in self.metadata_cache:
            cached = self.metadata_cache[url]
            return cached['headers'], cached['SOC'], cached['Cell temp mid']
        
        try:
            response = requests.get(url)
            content = response.content.decode('utf-8')
            df = pd.read_csv(StringIO(content))
            
            # Check for required columns
            if 'SOC' not in df.columns or 'Cell temp mid' not in df.columns:
                headers = df.columns.tolist()
                self.metadata_cache[url] = {'headers': headers, 'SOC': None, 'Cell temp mid': None}
                return headers, None, None
            
            # Fill missing values and filter
            df['SOC'] = df['SOC'].ffill().bfill()
            df['Cell temp mid'] = df['Cell temp mid'].ffill().bfill()
            
            df = df[
                (df['SOC'] >= Config.SOC_MIN) & 
                (df['SOC'] <= Config.SOC_MAX) &
                (df['Cell temp mid'] >= Config.CELL_TEMP_MIN) & 
                (df['Cell temp mid'] <= Config.CELL_TEMP_MAX)
            ]
            
            # Find first valid values
            for _, row in df.iterrows():
                soc_value = row['SOC']
                cell_temp_mid_value = row['Cell temp mid']
                
                if pd.notna(soc_value) and pd.notna(cell_temp_mid_value):
                    headers = df.columns.tolist()
                    self.metadata_cache[url] = {
                        'headers': headers,
                        'SOC': round(soc_value),
                        'Cell temp mid': round(cell_temp_mid_value)
                    }
                    return headers, round(soc_value), round(cell_temp_mid_value)
            
            headers = df.columns.tolist()
            self.metadata_cache[url] = {'headers': headers, 'SOC': None, 'Cell temp mid': None}
            return headers, None, None
            
        except Exception as e:
            st.warning(f"Error fetching CSV from {url}: {e}")
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
                response = requests.get(folder.path)
                soup = BeautifulSoup(response.content, 'html.parser')
                files = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.csv')]
                
                for file in files:
                    file_url = urllib.parse.urljoin(folder.path, file)
                    headers, soc_value, cell_temp_mid_value = self.fetch_csv_headers_and_values(file_url)
                    
                    if 'SOC' not in headers or 'Cell temp mid' not in headers:
                        continue
                    
                    if soc_value is not None and cell_temp_mid_value is not None:
                        short_name = file.split('/')[-1].replace('.csv', '')
                        file_info.append(PerformanceFileInfo(
                            path=file_url,
                            soc=soc_value,
                            cell_temp_mid=cell_temp_mid_value,
                            name=short_name,
                            folder=folder
                        ))
                        
            except Exception as e:
                st.warning(f"Error processing folder {folder.path}: {e}")
        
        # Save cache
        self._save_metadata_cache()
        
        return file_info
    
    @staticmethod
    def fetch_csv_data(url: str) -> Optional[pd.DataFrame]:
        """Fetch and process CSV data from URL.
        
        Args:
            url: URL of the CSV file.
            
        Returns:
            Processed DataFrame or None if error.
        """
        try:
            response = requests.get(url)
            content = response.content.decode('utf-8')
            df = pd.read_csv(StringIO(content))
            
            # Fill missing values
            df = df.ffill().bfill()
            
            # Filter invalid values
            df = df[
                (df['SOC'] >= 0) & (df['SOC'] <= 101) &
                (df['Cell temp mid'] >= 0) & (df['Cell temp mid'] <= 70)
            ]
            
            # Filter speed if present
            if 'Speed' in df.columns:
                df = df[(df['Speed'] >= Config.SPEED_MIN) & (df['Speed'] <= Config.SPEED_MAX)]
                # Ensure speed is strictly increasing
                df = df[df['Speed'].diff().fillna(1) > 0]
            
            return df
            
        except Exception as e:
            st.warning(f"Error fetching CSV data from {url}: {e}")
            return None
