import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from io import StringIO
import urllib.parse
import json
import os
import re
from matplotlib import colors as mcolors
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d

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

# Model and Variant filters
col1, col2 = st.sidebar.columns(2)
models = get_unique_values(classified_folders, 'model')
selected_model = col1.multiselect("Model", models, default=models if len(models) == 1 else [])
if selected_model:
    selected_filters['model'] = selected_model

variants = get_unique_values(classified_folders, 'variant', selected_filters)
selected_variant = col2.multiselect("Variant", variants, default=variants if len(variants) == 1 else [])
if selected_variant:
    selected_filters['variant'] = selected_variant

# Model Year and Battery filters
col3, col4 = st.sidebar.columns(2)
model_years = get_unique_values(classified_folders, 'model_year', selected_filters)
selected_model_year = col3.multiselect("Model Year", model_years, default=model_years if len(model_years) == 1 else [])
if selected_model_year:
    selected_filters['model_year'] = selected_model_year

batteries = get_unique_values(classified_folders, 'battery', selected_filters)
selected_battery = col4.multiselect("Battery", batteries, default=batteries if len(batteries) == 1 else [])
if selected_battery:
    selected_filters['battery'] = selected_battery

# Front Motor and Rear Motor filters
col5, col6 = st.sidebar.columns(2)
front_motors = get_unique_values(classified_folders, 'front_motor', selected_filters)
selected_front_motor = col5.multiselect("Front Motor", front_motors, default=front_motors if len(front_motors) == 1 else [])
if selected_front_motor:
    selected_filters['front_motor'] = selected_front_motor

rear_motors = get_unique_values(classified_folders, 'rear_motor', selected_filters)
selected_rear_motor = col6.multiselect("Rear Motor", rear_motors, default=rear_motors if len(rear_motors) == 1 else [])
if selected_rear_motor:
    selected_filters['rear_motor'] = selected_rear_motor

# Tuning filter
tunings = get_unique_values(classified_folders, 'tuning', selected_filters)
selected_tuning = st.sidebar.multiselect("Tuning", tunings, default=tunings if len(tunings) == 1 else [])
if selected_tuning:
    selected_filters['tuning'] = selected_tuning

# Acceleration Mode filter with custom order
acceleration_modes = get_unique_values(classified_folders, 'acceleration_mode', selected_filters)
acceleration_modes_ordered = ["Chill", "Standard", "Sport"]
selected_acceleration_mode = st.sidebar.multiselect("Acceleration Mode", acceleration_modes_ordered, default=acceleration_modes_ordered if len(acceleration_modes_ordered) == 1 else [])
if selected_acceleration_mode:
    selected_filters['acceleration_mode'] = selected_acceleration_mode

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
    
    # Scan entire DataFrame until valid values are found
    df['SOC'] = df['SOC'].ffill().bfill()
    df['Cell temp mid'] = df['Cell temp mid'].ffill().bfill()
    
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
                    'name': short_name,
                    'folder': folder  # Add folder info for legend
                })

# Save metadata cache
save_metadata_cache(metadata_cache)

# Sidebar sliders for SOC and Cell temp mid
if file_info:
    min_soc = min(info['SOC'] for info in file_info)
    max_soc = max(info['SOC'] for info in file_info)
    min_temp = min(info['Cell temp mid'] for info in file_info if info['Cell temp mid'] is not None)
    max_temp = max(info['Cell temp mid'] for info in file_info if info['Cell temp mid'] is not None)

    if min_soc == max_soc:
        st.sidebar.write(f"Only one SOC value available: {min_soc}")
        selected_soc_range = (min_soc, max_soc)
    else:
        selected_soc_range = st.sidebar.slider("Select SOC Range", min_soc, max_soc, (min_soc, max_soc))

    if min_temp == max_temp:
        st.sidebar.write(f"Only one Cell Temp value available: {min_temp}")
        selected_temp_range = (min_temp, max_temp)
    else:
        selected_temp_range = st.sidebar.slider("Select Cell Temp Range", min_temp, max_temp, (min_temp, max_temp))

    # Filter files based on selected ranges
    filtered_file_info = [
        info for info in file_info
        if selected_soc_range[0] <= info['SOC'] <= selected_soc_range[1]
        and (min_temp is None or selected_temp_range[0] <= info['Cell temp mid'] <= selected_temp_range[1])
    ]

# Y-Axis selection checkboxes
st.sidebar.subheader("Select Y-Axis")
columns_to_plot = {
    "Max Discharge Power [kW]": "Max discharge power",
    "Battery Power [kW]": "Battery power",
    "Battery Current [A]": "Battery current",
    "Battery Voltage [V]": "Battery voltage",
    "Front/Rear Motor Power [kW]": ["F power", "R power"],
    "Combined Motor Power [kW]": ["F power", "R power"],
    "Front/Rear Motor Torque [Nm]": ["F torque", "R torque"],
    "Combined Motor Torque [Nm]": ["F torque", "R torque"]
}
selected_columns = []
for label in columns_to_plot.keys():
    if st.sidebar.checkbox(label, key=f"y_{label}"):
        selected_columns.append(label)

# X-Axis selection
selected_x_axis = "Speed"

# Additional options
st.sidebar.subheader("Options")
show_legend = st.sidebar.checkbox("Show Legend", value=True)

####################################################################################################

# Plotting the data using Plotly
if selected_x_axis and selected_columns and filtered_file_info:
    plot_data = []

    # Define a function to get the color based on SOC
    def get_color(value, min_val, max_val, base_color):
        norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
        cmap = plt.get_cmap(base_color)
        return mcolors.to_hex(cmap(norm(value)))

    min_soc = min(info['SOC'] for info in file_info)
    max_soc = max(info['SOC'] for info in file_info)

    # Base colors for different folders
    base_colors = ['Blues', 'Reds', 'Oranges', 'Greens', 'Purples']

    # Prepare plot data
    folder_colors = {}
    for i, info in enumerate(filtered_file_info):
        folder_path = info['folder']['path']
        if folder_path not in folder_colors:
            folder_colors[folder_path] = base_colors[i % len(base_colors)]
        
        response = requests.get(info['path'])
        content = response.content.decode('utf-8')
        df = pd.read_csv(StringIO(content))

        # Fill forward and backward to handle NaN values
        df = df.ffill().bfill()

        # Filter invalid values
        df = df[(df['SOC'] >= 0) & (df['SOC'] <= 101) & (df['Cell temp mid'] >= 0) & (df['Cell temp mid'] <= 70)]

        # Filter rows where speed is not increasing
        if 'Speed' in df.columns:
            df = df[df['Speed'].diff() > 0]

        # Prepare the legend format
        legend_label = f"{info['folder']['model']} {info['folder']['variant']} {info['folder']['model_year']} {info['folder']['battery']} {info['folder']['rear_motor']} {info['folder']['acceleration_mode']} / {info['SOC']}% / {info['Cell temp mid']}°C"

        # Plot selected columns
        for column in selected_columns:
            y_col = columns_to_plot[column]
            if isinstance(y_col, list):
                for sub_col in y_col:
                    smoothed_y = uniform_filter1d(df[sub_col], size=15)
                    plot_data.append(pd.DataFrame({
                        'X': df[selected_x_axis],
                        'Y': smoothed_y,
                        'Label': f"{legend_label} - {sub_col}",
                        'Color': get_color(info['SOC'], min_soc, max_soc, folder_colors[folder_path])
                    }))
            else:
                smoothed_y = uniform_filter1d(df[y_col], size=15)
                plot_data.append(pd.DataFrame({
                    'X': df[selected_x_axis],
                    'Y': smoothed_y,
                    'Label': f"{legend_label} - {column}",
                    'Color': get_color(info['SOC'], min_soc, max_soc, folder_colors[folder_path])
                }))

    if plot_data:
        plot_df = pd.concat(plot_data)
        fig = px.line(plot_df, x='X', y='Y', color='Label', labels={'X': selected_x_axis, 'Y': 'Values'})
        
        # Apply the colors and make the lines wider with a glow effect
        for trace in fig.data:
            trace.update(line=dict(width=2))  # Make lines wider
            color = trace.line.color
            fig.add_trace(go.Scatter(
                x=trace.x, y=trace.y,
                mode='lines',
                line=dict(color=color, width=3),  # Outer glow
                showlegend=False,
                hoverinfo='skip'
            ))
            fig.add_trace(go.Scatter(
                x=trace.x, y=trace.y,
                mode='lines',
                line=dict(color=color, width=4),  # Inner glow
                showlegend=False,
                hoverinfo='skip'
            ))

        # Add watermark
        fig.add_annotation(
            text="@eivissacopter",
            font=dict(size=20, color="lightgrey"),
            align="center",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            opacity=0.05,
            showarrow=False
        )

        fig.update_layout(
            title="Performance Data Plot",
            xaxis_title=selected_x_axis,
            yaxis_title="Values" if len(selected_columns) > 1 else selected_columns[0],
            width=800,  # Adjust width as needed
            height=800,  # Adjust height as needed
            margin=dict(l=50, r=50, t=50, b=150),  # Add margin to the bottom for legend
            legend=dict(
                orientation="h",  # Horizontal legend
                yanchor="top",
                y=-0.3,  # Position the legend below the plot
                xanchor="center",
                x=0.5
            )
        )

        st.plotly_chart(fig, use_container_width=True)
else:
    st.write("Please select an X-axis and at least one column to plot.")
