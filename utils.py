"""
Utility functions for data fetching and cleaning.
"""

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np


def clean_numeric_col(series, remove_unit=None):
    """
    Clean a pandas Series for numeric conversion.
    
    Args:
        series: pandas Series to clean
        remove_unit: Optional string unit to remove (e.g., ' km', ' kWh', '%')
    
    Returns:
        pandas Series converted to numeric with errors coerced to NaN
    """
    result = series.copy()
    
    # Remove specific unit if provided
    if remove_unit:
        result = result.str.replace(remove_unit, '', regex=False)
    
    # Replace commas with dots
    result = result.str.replace(',', '.')
    
    # Convert to numeric with errors='coerce'
    result = pd.to_numeric(result, errors='coerce')
    
    return result


# Function to fetch data from Google Sheets
@st.cache_data(ttl=3600)  # Cache data for 3600 seconds (1 hour)
def fetch_data(username_filter=None):
    """Fetch data from Google Sheets and clean it."""
    # Google Sheets API setup
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Fetching credentials from Streamlit secrets
    creds_dict = {
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

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    # Define the URL of the Google Sheets
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    spreadsheet = client.open_by_url(url)
    sheet = spreadsheet.worksheet("Database")  # Open the 'Database' worksheet

    # Fetch all values from the sheet
    data = sheet.get_all_values()
    header = data[0]

    # Check if 'Username' is in the header
    if 'Username' not in header:
        st.error("The 'Username' column is missing from the Google Sheets data.")
        return pd.DataFrame(), None  # Return an empty DataFrame to avoid further errors

    # Columns to exclude
    exclude_columns = ['B', 'G', 'H', 'I', 'J', 'O', 'P', 'W', 'X', 'Y']

    # Include all columns except the excluded ones
    filtered_header = [col for col in header if col and not col.startswith('_') and col not in exclude_columns]

    # Get indices of the filtered columns
    keep_indices = [header.index(col) for col in filtered_header if col in header]

    # Filter the data based on the kept indices
    filtered_data = [[row[i] for i in keep_indices] for row in data]

    # Fix duplicate headers
    unique_header = []
    duplicate_counts = {}
    for col in filtered_header:
        col = col.strip()  # Trim whitespace
        if col not in unique_header:
            unique_header.append(col)
            duplicate_counts[col] = 1
        else:
            # Add a suffix to make the header unique
            duplicate_counts[col] += 1
            new_col = f"{col}_{duplicate_counts[col]}"
            unique_header.append(new_col)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data[1:], columns=unique_header)

    # Identify the 'Battery Pack' column
    battery_pack_cols = [col for col in df.columns if col.startswith('Battery Pack')]
    if battery_pack_cols:
        battery_pack_col = battery_pack_cols[0]  # Use the first match
    else:
        battery_pack_col = None  # Handle missing column

    # Handle 'Age' column conversion
    df['Age'] = df['Age'].str.replace(" Months", "").str.replace(",", ".").replace('', np.nan).astype(float)

    # Clean up the 'Odometer' column to ensure it is numeric - Fix regex with raw string
    df['Odometer'] = df['Odometer'].str.replace(',', '').str.extract(r'(\d+)').astype(float)
    
    # Replace all commas with dots in all columns except 'Battery Pack'
    columns_to_replace = df.select_dtypes(include='object').columns.tolist()
    if battery_pack_col and battery_pack_col in columns_to_replace:
        columns_to_replace.remove(battery_pack_col)
    df[columns_to_replace] = df[columns_to_replace].apply(lambda x: x.str.replace(',', '.'))

    # Add negative sign to specific columns if they exist
    columns_to_negate = ['Degradation']
    for col in columns_to_negate:
        if col in df.columns:
            df[col] = '-' + df[col]

    # Replace '0,0%' in 'Degradation' with NaN
    df['Degradation'] = df['Degradation'].replace('-0.0%', float('NaN'))

    # Clean numeric columns using the helper function
    df['Rated Range'] = clean_numeric_col(df['Rated Range'], remove_unit=' km')
    df['Capacity Net Now'] = clean_numeric_col(df['Capacity Net Now'], remove_unit=' kWh')
    df['Degradation'] = clean_numeric_col(df['Degradation'], remove_unit='%')
    df['Daily SOC Limit'] = clean_numeric_col(df['Daily SOC Limit'], remove_unit='%')
    df['DC Ratio'] = clean_numeric_col(df['DC Ratio'], remove_unit='%')

    if username_filter:
        df = df[df["Username"].str.contains(username_filter, case=False, na=False)]

    return df, battery_pack_col  # Return the DataFrame and the 'Battery Pack' column name


# Function to fetch additional battery data from the "Backend" worksheet
@st.cache_data(ttl=3600)  # Cache data for 3600 seconds (1 hour)
def fetch_battery_info():
    """Fetch battery information from the Backend worksheet."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = {
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
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    spreadsheet = client.open_by_url(url)
    sheet = spreadsheet.worksheet("Backend")
    data = sheet.get("O1:W22")
    header = data[0]
    battery_info = pd.DataFrame(data[1:], columns=header)
    battery_info.drop(battery_info.columns[[6, 7]], axis=1, inplace=True)
    # Fix Deprecation: Replace applymap with map for Pandas 2.1.0+ compatibility
    battery_info = battery_info.map(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
    cols = list(battery_info.columns)
    if "Capacity (new)" in cols and "Nominal Capacity" in cols:
        cols.insert(cols.index("Capacity (new)") + 1, cols.pop(cols.index("Nominal Capacity")))
    battery_info = battery_info[cols]
    battery_info["Capacity (new)"] = battery_info["Capacity (new)"] + " kWh"
    battery_info["Nominal Capacity"] = battery_info["Nominal Capacity"] + " Ah"
    if len(battery_info.columns) > 6:
        battery_info.iloc[:, 6] = battery_info.iloc[:, 6] + " km"
    return battery_info
