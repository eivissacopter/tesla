import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib.parse
import re
from io import StringIO

# Set page config
st.set_page_config(page_title="Tesla Performance Analysis", page_icon=":racing_car:", layout="wide")

# Function to scan the root folder and classify the subfolders
@st.cache_data(ttl=600)
def scan_and_classify_folders(base_url):
    def parse_directory(url):
        response = requests.get(url)
        if response.status_code != 200:
            st.error(f"Failed to access {url}")
            return []
        soup = BeautifulSoup(response.content, 'html.parser')
        dirs = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('/')]
        return dirs

    def classify_folder(folder_name):
        pattern = re.compile(r"(?P<manufacturer>[^_]+)_"
                             r"(?P<model>[^_]+)_"
                             r"(?P<variant>[^_]+)_"
                             r"(?P<model_year>\d+)_"
                             r"(?P<battery>[^_]+)_"
                             r"(?P<front_motor>[^_]+)_"
                             r"(?P<rear_motor>[^_]+)_"
                             r"(?P<tuning>[^/]+)")
        match = pattern.match(folder_name)
        if match:
            classified = match.groupdict()
            classified['tuning'] = urllib.parse.unquote(classified['tuning'])
            return classified
        else:
            return None

    classified_folders = []
    dirs = parse_directory(base_url)
    for d in dirs:
        full_path = urllib.parse.urljoin(base_url, d)
        classification = classify_folder(d.strip('/'))
        if classification:
            classification['path'] = full_path
            classified_folders.append(classification)
    return classified_folders

# Base URL for scanning the root folder
BASE_URL = "https://nginx.eivissacopter.com/smt/"

# Scan and classify folders
classified_folders = scan_and_classify_folders(BASE_URL)

# Check if any classified folders were found
if not classified_folders:
    st.error("The directory structure is empty. No options available.")
    st.stop()

# Create dynamic filters based on the classified information
def get_unique_values(classified_folders, key, filters={}):
    values = set()
    for folder in classified_folders:
        match = all(folder[k] in v for k, v in filters.items())
        if match:
            values.add(folder[key])
    return sorted(values)

selected_filters = {}

# Sidebar filters
st.sidebar.header("Filter Options")

# Model filter
models = get_unique_values(classified_folders, 'model')
selected_model = st.sidebar.multiselect("Model", models)
if selected_model:
    selected_filters['model'] = selected_model

# Variant filter
variants = get_unique_values(classified_folders, 'variant', selected_filters)
selected_variant = st.sidebar.multiselect("Version", variants)
if selected_variant:
    selected_filters['variant'] = selected_variant

# Model Year filter
model_years = get_unique_values(classified_folders, 'model_year', selected_filters)
selected_model_year = st.sidebar.multiselect("Model Year", model_years)
if selected_model_year:
    selected_filters['model_year'] = selected_model_year

# Battery filter
batteries = get_unique_values(classified_folders, 'battery', selected_filters)
selected_battery = st.sidebar.multiselect("Battery", batteries)
if selected_battery:
    selected_filters['battery'] = selected_battery

# Front Motor filter
front_motors = get_unique_values(classified_folders, 'front_motor', selected_filters)
selected_front_motor = st.sidebar.multiselect("Front Motor", front_motors)
if selected_front_motor:
    selected_filters['front_motor'] = selected_front_motor

# Rear Motor filter
rear_motors = get_unique_values(classified_folders, 'rear_motor', selected_filters)
selected_rear_motor = st.sidebar.multiselect("Rear Motor", rear_motors)
if selected_rear_motor:
    selected_filters['rear_motor'] = selected_rear_motor

# Tuning filter
tunings = get_unique_values(classified_folders, 'tuning', selected_filters)
selected_tuning = st.sidebar.multiselect("Tuning", tunings)
if selected_tuning:
    selected_filters['tuning'] = selected_tuning

# Function to fetch CSV headers and first valid values
def fetch_csv_headers_and_values(url):
    response = requests.get(url)
    content = response.content.decode('utf-8')
    df = pd.read_csv(StringIO(content))
    
    # Filter out implausible values before filling
    df = df[(df['SOC'].between(0, 100)) & (df['Cell temp mid'].between(-30, 70))]
    
    # Fill missing values
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    # Check if necessary columns exist
    if 'SOC' in df.columns and 'Cell temp mid' in df.columns:
        soc_value = df['SOC'].iloc[0] if not pd.isna(df['SOC'].iloc[0]) else None
        temp_value = df['Cell temp mid'].iloc[0] if not pd.isna(df['Cell temp mid'].iloc[0]) else None
    else:
        soc_value = None
        temp_value = None
    
    return df.columns.tolist(), soc_value, temp_value

# Collect SOC and Cell temp mid values
file_info = []
for folder in classified_folders:
    if all(folder[k] in v for k, v in selected_filters.items()):
        response = requests.get(folder['path'])
        soup = BeautifulSoup(response.content, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.csv')]
        for file in files:
            file_url = urllib.parse.urljoin(folder['path'], file)
            headers, soc_value, temp_value = fetch_csv_headers_and_values(file_url)
            if soc_value is not None and temp_value is not None:
                file_info.append({
                    'path': file_url,
                    'SOC': round(soc_value),
                    'Cell temp mid': round(temp_value)
                })

# Sidebar sliders for SOC and Cell temp mid
if file_info:
    min_soc = min(info['SOC'] for info in file_info)
    max_soc = max(info['SOC'] for info in file_info)
    min_temp = min(info['Cell temp mid'] for info in file_info)
    max_temp = max(info['Cell temp mid'] for info in file_info)

    selected_soc_range = st.sidebar.slider("Select SOC Range", min_soc, max_soc, (min_soc, max_soc))
    selected_temp_range = st.sidebar.slider("Select Cell Temp Range", min_temp, max_temp, (min_temp, max_temp))

    # Filter files based on selected ranges
    filtered_file_info = [
        info for info in file_info
        if selected_soc_range[0] <= info['SOC'] <= selected_soc_range[1]
        and selected_temp_range[0] <= info['Cell temp mid'] <= selected_temp_range[1]
    ]

    # Display filtered files
    if filtered_file_info:
        st.write("Filtered Files:")
        for info in filtered_file_info:
            st.write(f"File: {info['path']} | SOC: {info['SOC']} | Cell Temp: {info['Cell temp mid']}")
    else:
        st.write("No files match the selected SOC and Cell Temp range.")
else:
    st.write("No CSV files found in the filtered folders.")
