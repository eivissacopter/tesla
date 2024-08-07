import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib.parse
import re
from io import StringIO
import matplotlib.pyplot as plt

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
def fetch_csv_headers_and_first_valid_values(url):
    response = requests.get(url)
    content = response.content.decode('utf-8')
    df = pd.read_csv(StringIO(content))
    
    # Check if the required columns are present
    if 'SOC' not in df.columns or 'Cell temp mid' not in df.columns:
        return df.columns.tolist(), None, None
    
    # Fill forward and backward to handle NaN values
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    # Filter invalid values
    df = df[(df['SOC'] >= -5) & (df['SOC'] <= 101) & (df['Cell temp mid'] >= -30) & (df['Cell temp mid'] <= 70)]
    
    # Find the first valid values
    for index, row in df.iterrows():
        soc_value = row['SOC']
        cell_temp_mid_value = row['Cell temp mid']
        if pd.notna(soc_value) and pd.notna(cell_temp_mid_value):
            return df.columns.tolist(), round(soc_value), round(cell_temp_mid_value)
    
    return df.columns.tolist(), None, None

# Filter folders based on selections
filtered_folders = [f for f in classified_folders if
                    all(f[k] in v for k, v in selected_filters.items())]

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

# Add the plotting options for X and Y axes in the sidebar
st.sidebar.header("Plotting Options")

# X-Axis selection with checkboxes
x_axis_options = ["Speed", "Time"]
selected_x_axis = st.sidebar.radio("Select X-Axis", x_axis_options)

# Y-Axis selection checkboxes
columns_to_plot = {
    "Max Discharge Power": "Max discharge power",
    "Battery Power": "Battery power",
    "Front Power": "F power",
    "Rear Power": "R power",
    "Combined Motor Power (F+R)": ["F power", "R power"],
    "Front Torque": "F torque",
    "Rear Torque": "R torque",
    "Combined Motor Torque (F+R)": ["F torque", "R torque"],
    "Battery Current": "Battery current",
    "Battery Voltage": "Battery voltage"
}
selected_columns = st.sidebar.multiselect("Select Columns to Plot (Y-Axis)", list(columns_to_plot.keys()))

# Show legend option
show_legend = st.sidebar.checkbox("Show Legend", value=True)

# Function to fetch and process data with caching
@st.cache_data(ttl=3600)
def fetch_and_process_data(url):
    response = requests.get(url)
    content = response.content.decode('utf-8')
    df = pd.read_csv(StringIO(content))
    df = df.fillna(method='ffill').fillna(method='bfill')
    df = df[(df['SOC'] >= -5) & (df['SOC'] <= 101) & (df['Cell temp mid'] >= -30) & (df['Cell temp mid'] <= 70)]
    return df

# Plotting the data
if selected_x_axis and selected_columns and filtered_file_info:
    fig, ax = plt.subplots(figsize=(10, 6))

    for info in filtered_file_info:
        df = fetch_and_process_data(info['path'])

        # Plot selected columns
        for col in selected_columns:
            y_col = columns_to_plot[col]
            if isinstance(y_col, list):
                df['Combined'] = df[y_col[0]] + df[y_col[1]]
                y_col = 'Combined'
            ax.plot(df[selected_x_axis], df[y_col], label=f"{info['name']} - {col}")

    ax.set_xlabel(selected_x_axis)
    ax.set_ylabel("Values")
    ax.set_title("Performance Data Plot")
    if show_legend:
        ax.legend(loc='best')
    ax.grid(True)
    st.pyplot(fig)
else:
    st.write("Please select an X-axis and at least one column to plot.")

