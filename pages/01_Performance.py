import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

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
            return match.groupdict()
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

# Filter folders based on selections
filtered_folders = [f for f in classified_folders if
                    all(f[k] in v for k, v in selected_filters.items())]

# Display filtered paths and list files
if filtered_folders:
    st.write("Filtered Directories and Files:")
    for folder in filtered_folders:
        st.write(f"**Directory**: {folder['path']}")
        response = requests.get(folder['path'])
        soup = BeautifulSoup(response.content, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.csv')]
        for file in files:
            file_url = urllib.parse.urljoin(folder['path'], file)
            st.write(f"- {file_url}")
else:
    st.write("No directories match the selected filters.")
