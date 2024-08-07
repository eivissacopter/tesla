import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests
from bs4 import BeautifulSoup
import os
from io import StringIO
import urllib.parse

# Set page config
st.set_page_config(page_title="Tesla Performance Analysis", page_icon=":racing_car:", layout="wide")

# Function to fetch directory structure from the given URL
@st.cache_data(ttl=600)
def fetch_directory_structure(base_url):
    def parse_directory(url):
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        dirs = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('/')]
        files = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.csv')]
        return dirs, files

    directory_structure = {}

    def build_structure(url, parent_structure):
        dirs, files = parse_directory(url)
        for d in dirs:
            full_path = urllib.parse.urljoin(url, d)
            parent_structure[d] = {}
            build_structure(full_path, parent_structure[d])
        for f in files:
            full_path = urllib.parse.urljoin(url, f)
            parent_structure[f] = full_path

    base_url = base_url if base_url.endswith('/') else base_url + '/'
    build_structure(base_url, directory_structure)
    return directory_structure

# Base URL for CSV files
BASE_URL = "https://nginx.eivissacopter.com/smt/"

# Fetch directory structure
directory_structure = fetch_directory_structure(BASE_URL)

# Sidebar filters
st.sidebar.header("Filter Options")

def get_options_from_structure(structure, keys=[]):
    options = list(structure.keys())
    selected_option = st.sidebar.selectbox("Select " + " > ".join(keys), options)
    if isinstance(structure[selected_option], dict):
        return get_options_from_structure(structure[selected_option], keys + [selected_option])
    else:
        return structure[selected_option], keys + [selected_option]

# Fetch the CSV file based on user's selection
csv_file_url, selected_keys = get_options_from_structure(directory_structure)

# Display the selected path
st.sidebar.write("Selected Path: " + " / ".join(selected_keys))

# Function to read CSV file from URL
@st.cache_data(ttl=600)
def load_csv_from_url(url):
    response = requests.get(url)
    csv_content = response.content.decode('utf-8')
    return pd.read_csv(StringIO(csv_content))

# Load the selected CSV file
data = load_csv_from_url(csv_file_url)

# Display the data
st.write(data.head())

# Sidebar filters for plotting
y_axis_data = st.sidebar.multiselect("Y-axis Data", data.columns, default=["Battery power", "Speed"])
x_axis_data = st.sidebar.selectbox("X-axis Data", ["Time", "Speed"], index=0)

# Plot the data
fig = px.line(data, x=x_axis_data, y=y_axis_data, labels={"value": "Value", "variable": "Parameter"})
st.plotly_chart(fig, use_container_width=True)

# Placeholder for performance meter screenshots
st.sidebar.header("Performance Meter Screenshots")
performance_meter_images = st.sidebar.file_uploader("Upload Performance Meter Screenshots", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

# Display performance meter screenshots
if performance_meter_images:
    st.header("Performance Meter Screenshots")
    cols = st.columns(len(performance_meter_images))
    for i, image in enumerate(performance_meter_images):
        with cols[i]:
            st.image(image, use_column_width=True)