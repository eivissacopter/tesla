"""Google Sheets data access layer."""
from typing import Optional, Tuple
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

from ..config import Config


class GoogleSheetsClient:
    """Client for accessing Google Sheets data."""
    
    def __init__(self):
        """Initialize the Google Sheets client."""
        self._client = None
    
    def _get_client(self) -> gspread.Client:
        """Get authenticated Google Sheets client.
        
        Returns:
            Authenticated gspread client.
        """
        if self._client is None:
            scope = Config.get_google_api_scope()
            creds_dict = Config.get_gcp_credentials()
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            self._client = gspread.authorize(creds)
        return self._client
    
    @st.cache_data(ttl=Config.CACHE_TTL)
    def fetch_battery_data(_self, username_filter: Optional[str] = None) -> Tuple[pd.DataFrame, Optional[str]]:
        """Fetch battery data from Google Sheets.
        
        Args:
            username_filter: Optional username to filter results.
            
        Returns:
            Tuple of (DataFrame with battery data, battery pack column name).
        """
        try:
            client = _self._get_client()
            url = Config.get_spreadsheet_url()
            spreadsheet = client.open_by_url(url)
            sheet = spreadsheet.worksheet("Database")
            
            # Fetch all values
            data = sheet.get_all_values()
            header = data[0]
            
            # Validate header
            if 'Username' not in header:
                st.error("The 'Username' column is missing from the Google Sheets data.")
                return pd.DataFrame(), None
            
            # Filter columns
            filtered_header = [
                col for col in header 
                if col and not col.startswith('_') and col not in Config.EXCLUDE_COLUMNS
            ]
            
            # Get column indices
            keep_indices = [header.index(col) for col in filtered_header if col in header]
            
            # Filter data
            filtered_data = [[row[i] for i in keep_indices] for row in data]
            
            # Handle duplicate headers
            unique_header = _self._make_unique_headers(filtered_header)
            
            # Create DataFrame
            df = pd.DataFrame(filtered_data[1:], columns=unique_header)
            
            # Process the data
            df = _self._process_dataframe(df)
            
            # Find battery pack column
            battery_pack_col = _self._find_battery_pack_column(df)
            
            # Apply username filter if provided
            if username_filter:
                df = df[df["Username"].str.contains(username_filter, case=False, na=False)]
            
            return df, battery_pack_col
            
        except Exception as e:
            st.error(f"Error fetching data from Google Sheets: {str(e)}")
            return pd.DataFrame(), None
    
    @st.cache_data(ttl=Config.CACHE_TTL)
    def fetch_battery_info(_self) -> pd.DataFrame:
        """Fetch battery pack information from Backend worksheet.
        
        Returns:
            DataFrame with battery pack specifications.
        """
        try:
            client = _self._get_client()
            url = Config.get_spreadsheet_url()
            spreadsheet = client.open_by_url(url)
            sheet = spreadsheet.worksheet("Backend")
            
            data = sheet.get("O1:W22")
            header = data[0]
            battery_info = pd.DataFrame(data[1:], columns=header)
            
            # Drop unnecessary columns
            battery_info.drop(battery_info.columns[[6, 7]], axis=1, inplace=True)
            
            # Replace commas with dots
            battery_info = battery_info.applymap(
                lambda x: x.replace(',', '.') if isinstance(x, str) else x
            )
            
            # Reorder columns
            cols = list(battery_info.columns)
            if "Capacity (new)" in cols and "Nominal Capacity" in cols:
                nominal_idx = cols.index("Nominal Capacity")
                cols.pop(nominal_idx)
                cols.insert(cols.index("Capacity (new)") + 1, "Nominal Capacity")
                battery_info = battery_info[cols]
            
            # Add units
            battery_info["Capacity (new)"] = battery_info["Capacity (new)"] + " kWh"
            battery_info["Nominal Capacity"] = battery_info["Nominal Capacity"] + " Ah"
            if len(battery_info.columns) > 6:
                battery_info.iloc[:, 6] = battery_info.iloc[:, 6] + " km"
            
            return battery_info
            
        except Exception as e:
            st.error(f"Error fetching battery info: {str(e)}")
            return pd.DataFrame()
    
    @staticmethod
    def _make_unique_headers(headers: list) -> list:
        """Make column headers unique by adding suffixes to duplicates.
        
        Args:
            headers: List of column headers.
            
        Returns:
            List of unique headers.
        """
        unique_header = []
        duplicate_counts = {}
        
        for col in headers:
            col = col.strip()
            if col not in unique_header:
                unique_header.append(col)
                duplicate_counts[col] = 1
            else:
                duplicate_counts[col] += 1
                new_col = f"{col}_{duplicate_counts[col]}"
                unique_header.append(new_col)
        
        return unique_header
    
    @staticmethod
    def _find_battery_pack_column(df: pd.DataFrame) -> Optional[str]:
        """Find the battery pack column in the DataFrame.
        
        Args:
            df: DataFrame to search.
            
        Returns:
            Name of the battery pack column, or None if not found.
        """
        battery_pack_cols = [col for col in df.columns if col.startswith('Battery Pack')]
        return battery_pack_cols[0] if battery_pack_cols else None
    
    @staticmethod
    def _process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean the DataFrame.
        
        Args:
            df: Raw DataFrame from Google Sheets.
            
        Returns:
            Processed DataFrame.
        """
        # Handle Age column
        df['Age'] = (df['Age'].str.replace(" Months", "")
                              .str.replace(",", ".")
                              .replace('', np.nan)
                              .astype(float))
        
        # Clean Odometer column
        df['Odometer'] = (df['Odometer'].str.replace(',', '')
                                        .str.extract(r'(\d+)')
                                        .astype(float))
        
        # Replace commas with dots in object columns (except Battery Pack)
        battery_pack_col = GoogleSheetsClient._find_battery_pack_column(df)
        columns_to_replace = df.select_dtypes(include='object').columns.tolist()
        if battery_pack_col and battery_pack_col in columns_to_replace:
            columns_to_replace.remove(battery_pack_col)
        
        for col in columns_to_replace:
            df[col] = df[col].str.replace(',', '.')
        
        # Add negative sign to degradation
        if 'Degradation' in df.columns:
            df['Degradation'] = '-' + df['Degradation']
            df['Degradation'] = df['Degradation'].replace('-0.0%', float('NaN'))
        
        # Clean Rated Range
        if 'Rated Range' in df.columns:
            df['Rated Range'] = df['Rated Range'].str.replace(' km', '')
            df['Rated Range'] = pd.to_numeric(df['Rated Range'], errors='coerce')
        
        # Clean Capacity Net Now
        if 'Capacity Net Now' in df.columns:
            df['Capacity Net Now'] = (df['Capacity Net Now'].str.replace(' kWh', '')
                                                             .str.replace(',', '.'))
            df['Capacity Net Now'] = pd.to_numeric(df['Capacity Net Now'], errors='coerce')
        
        # Convert Degradation to numeric
        if 'Degradation' in df.columns:
            df['Degradation'] = pd.to_numeric(
                df['Degradation'].str.replace('%', ''), 
                errors='coerce'
            )
        
        # Clean Daily SOC Limit and DC Ratio
        if 'Daily SOC Limit' in df.columns:
            df['Daily SOC Limit'] = (df['Daily SOC Limit'].str.replace('%', '')
                                                          .replace('', np.nan)
                                                          .astype(float))
        
        if 'DC Ratio' in df.columns:
            df['DC Ratio'] = (df['DC Ratio'].str.replace('%', '')
                                           .replace('', np.nan)
                                           .astype(float))
        
        return df
