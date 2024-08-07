import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib.parse
import re
from io import StringIO
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d
import os
import json

# Set page config
st.set_page_config(page_title="Tesla Performance Analysis", page_icon=":racing_car:", layout="wide")

# Metadata cache file
METADATA_FILE = "metadata_cache.json"

# Load metadata cache
def load_metadata_cache():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Save metadata cache
def save_metadata_cache(metadata):
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f)

metadata_cache = load_metadata_cache()

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
                             r"(?P<tuning>[^_]+)_"
                             r"(?P<acceleration_mode>[^/]+)")
        match = pattern.match(folder_name)
        if match:
            classified = match.groupdict()
            classified['tuning'] = urllib.parse.unquote(classified['tuning'])
            classified['acceleration_mode'] = urllib.parse.unquote(classified['acceleration_mode'])
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
        match = all(folder[k] in v for k, v in filters.items() if k in folder)
        if match and key in folder:
            values.add(folder[key])
    return sorted(values)

selected_filters = {}

###################################################################################

# Sidebar filters
st.sidebar.header("Filter Options")

# Prefill function
def prefill_filter(options, label):
    if len(options) == 1:
        return st.sidebar.multiselect(label, options, default=options)
    return st.sidebar.multiselect(label, options)

# Model filter
models = get_unique_values(classified_folders, 'model')
selected_model = prefill_filter(models, "Model")
if selected_model:
    selected_filters['model'] = selected_model

# Variant filter
variants = get_unique_values(classified_folders, 'variant', selected_filters)
selected_variant = prefill_filter(variants, "Variant")
if selected_variant:
    selected_filters['variant'] = selected_variant

# Model Year filter
model_years = get_unique_values(classified_folders, 'model_year', selected_filters)
selected_model_year = prefill_filter(model_years, "Model Year")
if selected_model_year:
    selected_filters['model_year'] = selected_model_year

# Battery filter
batteries = get_unique_values(classified_folders, 'battery', selected_filters)
selected_battery = prefill_filter(batteries, "Battery")
if selected_battery:
    selected_filters['battery'] = selected_battery

# Rear Motor filter
rear_motors = get_unique_values(classified_folders, 'rear_motor', selected_filters)
selected_rear_motor = prefill_filter(rear_motors, "Rear Motor")
if selected_rear_motor:
    selected_filters['rear_motor'] = selected_rear_motor

# Tuning filter
tunings = get_unique_values(classified_folders, 'tuning', selected_filters)
selected_tuning = prefill_filter(tunings, "Tuning")
if selected_tuning:
    selected_filters['tuning'] = selected_tuning

# Acceleration Mode filter
acceleration_modes = get_unique_values(classified_folders, 'acceleration_mode', selected_filters)
selected_acceleration_mode = prefill_filter(acceleration_modes, "Acceleration Mode")
if selected_acceleration_mode:
    selected_filters['acceleration_mode'] = selected_acceleration_mode

#################################################################################################

# Function to fetch CSV headers and first valid values
def fetch_csv_headers_and_first_valid_values(url):
    # Use cached metadata if available
    if url in metadata_cache:
        return metadata_cache[url]['headers'], metadata_cache[url]['SOC'], metadata_cache[url]['Cell temp mid']
    
    response = requests.get(url)
    content = response.content.decode('utf-8')
    df = pd.read_csv(StringIO(content))
    
    # Check if the required columns are present
    if 'SOC' not in df.columns or 'Cell temp mid' not in df.columns:
        headers = df.columns.tolist()
        metadata_cache[url] = {'headers': headers, 'SOC': None, 'Cell temp mid': None}
        return headers, None, None
    
    # Fill forward and backward to handle NaN values
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    # Filter invalid values
    df = df[(df['SOC'] >= -5) & (df['SOC'] <= 101) & (df['Cell temp mid'] >= -30) & (df['Cell temp mid'] <= 70)]
    
    # Find the first valid values
    for index, row in df.iterrows():
        soc_value = row['SOC']
        cell_temp_mid_value = row['Cell temp mid']
        if pd.notna(soc_value) and pd.notna(cell_temp_mid_value):
            headers = df.columns.tolist()
            metadata_cache[url] = {'headers': headers, 'SOC': round(soc_value), 'Cell temp mid': round(cell_temp_mid_value)}
            return headers, round(soc_value), round(cell_temp_mid_value)
    
    headers = df.columns.tolist()
    metadata_cache[url] = {'headers': headers, 'SOC': None, 'Cell temp mid': None}
    return headers, None, None

# Filter folders based on selections
filtered_folders = [f for f in classified_folders if
                    all(f[k] in v for k, v in selected_filters.items() if k in f)]

# Initialize an empty list to collect file information
file_info = []

# Collect SOC and Cell temp mid values
if filtered_folders:
    for folder in filtered_folders:
        response = requests.get(folder['path'])
        soup = BeautifulSoup(response.content, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.csv')]
        for file in files:
            file_url = urllib.parse.urljoin(folder['path'], file)
            headers, soc_value, cell_temp_mid_value = fetch_csv_headers_and_first_valid_values(file_url)
            if 'SOC' not in headers or 'Cell temp mid' not in headers:
                continue  # Skip the file if it doesn't have the required columns
            if soc_value is not None and cell_temp_mid_value is not None:
                # Create a short name for the file
                short_name = file.split('/')[-1].replace('.csv', '')
                file_info.append({
                    'path': file_url,
                    'SOC': soc_value,
                    'Cell temp mid': cell_temp_mid_value,
                    'name': short_name  # Add short name here
                })

# Save metadata cache
save_metadata_cache(metadata_cache)

# Sidebar sliders for SOC and Cell temp mid
if file_info:
    min_soc = min(info['SOC'] for info in file_info)
    max_soc = max(info['SOC'] for info in file_info)
    min_temp = min(info['Cell temp mid'] for info in file_info)
    max_temp = max(info['Cell temp mid'] for info in file_info)

    selected_soc_range = st.sidebar.slider("Select SOC Range", min_soc, max_soc, (min_soc, max_soc))

    # Ensure min_temp and max_temp are not None
    if min_temp is None or max_temp is None:
        st.error("Error: Unable to determine the min and max temperature for slider.")
    else:
        selected_temp_range = st.sidebar.slider("Select Cell Temp Range", min_temp, max_temp, (min_temp, max_temp))

    # Filter files based on selected ranges
    filtered_file_info = [
        info for info in file_info
        if selected_soc_range[0] <= info['SOC'] <= selected_soc_range[1]
        and selected_temp_range[0] <= info['Cell temp mid'] <= selected_temp_range[1]
    ]

# Set the dark mode style
plt.style.use('dark_background')

# Add the plotting options for X and Y axes in the sidebar
st.sidebar.header("Plotting Options")

# Y-Axis selection checkboxes
st.sidebar.subheader("Select Y-Axis")
columns_to_plot = {
    "Max Discharge Power": "Max discharge power",
    "Battery Power": "Battery power",
    "Battery Current": "Battery current",
    "Battery Voltage": "Battery voltage",
    "Front/Rear Motor Power": ["F power", "R power"],
    "Combined Motor Power": ["F power", "R power"],
    "Front/Rear Motor Torque": ["F torque", "R torque"],
    "Combined Motor Torque": ["F torque", "R torque"]
}
selected_columns = []
for label in columns_to_plot.keys():
    if st.sidebar.checkbox(label, key=f"y_{label}"):
        selected_columns.append(label)

# X-Axis selection with radio buttons with a label
st.sidebar.subheader("Select X-Axis")
x_axis_options = ["Speed", "Time"]
selected_x_axis = st.sidebar.radio("", x_axis_options, index=0)

# Additional options
st.sidebar.subheader("Additional Options")
show_legend = st.sidebar.checkbox("Show Legend", value=False)

# Plotting the data
if selected_x_axis and selected_columns and filtered_file_info:
    fig, ax = plt.subplots(figsize=(10, 6))

    for info in filtered_file_info:
        response = requests.get(info['path'])
        content = response.content.decode('utf-8')
        df = pd.read_csv(StringIO(content))

        # Fill forward and backward to handle NaN values
        df = df.fillna(method='ffill').fillna(method='bfill')

        # Filter invalid values
        df = df[(df['SOC'] >= -5) & (df['SOC'] <= 101) & (df['Cell temp mid'] >= -30) & (df['Cell temp mid'] <= 70)]

        # Filter rows where Accelerator Pedal is not 100 if the column exists
        if 'Accelerator Pedal' in df.columns:
            df = df[df['Accelerator Pedal'] == 100]

        # Plot selected columns
        for column in selected_columns:
            y_col = columns_to_plot[column]
            if isinstance(y_col, list):
                for sub_col in y_col:
                    smoothed_y = uniform_filter1d(df[sub_col], size=15)
                    ax.plot(df[selected_x_axis], smoothed_y, label=f"{info['name']} - {sub_col}")
            else:
                smoothed_y = uniform_filter1d(df[y_col], size=15)
                ax.plot(df[selected_x_axis], smoothed_y, label=f"{info['name']} - {column}")

    ax.set_xlabel(selected_x_axis)
    ax.set_ylabel("Values" if len(selected_columns) > 1 else selected_columns[0])
    ax.set_title("Performance Data Plot")
    if show_legend:
        ax.legend(loc='best')
    ax.grid(True)
    st.pyplot(fig)
else:
    st.write("Please select an X-axis and at least one column to plot.")
