import streamlit as st
import plotly.express as px
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import plotly.graph_objects as go
import plotly.io as pio
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Set page config as the first Streamlit command
st.set_page_config(page_title="Tesla Battery Analysis", page_icon=":battery:", layout="wide")

# Set default Plotly template and color sequence
pio.templates.default = "plotly"
color_sequence = [
    "#0068c9",
    "#83c9ff",
    "#ff2b2b",
    "#ffabab",
    "#29b09d",
    "#7defa1",
    "#ff8700",
    "#ffd16a",
    "#6d3fc0",
    "#d5dae5",
]

# Function to fetch data from Google Sheets
@st.cache_data(ttl=300)  # Cache data for 300 seconds
def fetch_data():
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

    # Fetch only necessary columns
    data = sheet.get_all_values()
    header = data[0]
    filtered_header = []
    keep_indices = []
    stop_index = None
    for i, col in enumerate(header):
        col = col.strip()
        if col and not col.startswith('_') and col not in ['B', 'G', 'H', 'I', 'J', 'O', 'P', 'W', 'X', 'Y', 'AB']:
            filtered_header.append(col)
            keep_indices.append(i)
        if col == "DC Ratio":
            stop_index = i
            break
    if stop_index is not None:
        keep_indices = keep_indices[:stop_index + 1]

    # Filter the data based on the kept indices
    filtered_data = [[row[i] for i in keep_indices] for row in data]

    # Fix duplicate headers
    unique_header = []
    for col in filtered_header:
        col = col.strip()  # Trim whitespace
        if col not in unique_header:
            unique_header.append(col)
        else:
            # Add a suffix to make the header unique
            suffix = 1
            new_col = f"{col}_{suffix}"
            while new_col in unique_header:
                suffix += 1
                new_col = f"{col}_{suffix}"
            unique_header.append(new_col)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data[1:], columns=unique_header)

    # Handle 'Age' column conversion
    df['Age'] = df['Age'].str.replace(" Months", "").str.replace(",", ".").replace('', np.nan).astype(float)

    # Clean up the 'Odometer' column to ensure it is numeric
    df['Odometer'] = df['Odometer'].str.replace(',', '').str.extract('(\d+)').astype(float)
    
    # Replace all commas with dots in all columns
    df = df.apply(lambda x: x.str.replace(',', '.') if x.dtype == "object" else x)

    # Add negative sign to specific columns if they exist
    columns_to_negate = ['Degradation']
    for col in columns_to_negate:
        if col in df.columns:
            df[col] = '-' + df[col]

    # Replace '0,0%' in 'Degradation' with NaN
    df['Degradation'] = df['Degradation'].replace('-0.0%', float('NaN'))

    # Clean 'Rated Range' and 'Capacity Net Now' columns
    df['Rated Range'] = df['Rated Range'].str.replace(' km', '')
    df['Rated Range'] = pd.to_numeric(df['Rated Range'], errors='coerce')

    df['Capacity Net Now'] = df['Capacity Net Now'].str.replace(' kWh', '').str.replace(',', '.')
    df['Capacity Net Now'] = pd.to_numeric(df['Capacity Net Now'], errors='coerce')

    # Convert Degradation to numeric
    df['Degradation'] = pd.to_numeric(df['Degradation'].str.replace('%', ''), errors='coerce')

    # Clean 'Daily SOC Limit' and 'DC Ratio' columns
    df['Daily SOC Limit'] = df['Daily SOC Limit'].str.replace('%', '').replace('', np.nan).astype(float)
    df['DC Ratio'] = df['DC Ratio'].str.replace('%', '').replace('', np.nan).astype(float)

    return df

# Fetch the data and timestamp
df = fetch_data()

# Define default values for the filters
default_tesla = []
default_version = []
default_battery = []
default_min_age = int(df["Age"].min())
default_max_age = int(df["Age"].max())
default_min_odo = int(df["Odometer"].min())
default_max_odo = int(df["Odometer"].max())
default_daily_soc_limit = False
default_dc_ratio = False

# Initialize filter states in session_state if not already present
if "filters" not in st.session_state:
    st.session_state.filters = {
        "tesla": default_tesla,
        "version": default_version,
        "battery": default_battery,
        "min_age": default_min_age,
        "max_age": default_max_age,
        "min_odo": default_min_odo,
        "max_odo": default_max_odo,
        "show_daily_soc_limit": default_daily_soc_limit,
        "show_dc_ratio": default_dc_ratio,
    }

# Initialize the filtered dataframe
if "filtered_df" not in st.session_state:
    st.session_state.filtered_df = df.copy()

####################################################################################################################

# Streamlit app setup

# Add the main header picture with emojis
st.markdown(
    """
    <style>
        .header {
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            padding: 0rem 0;
            margin-bottom: 0rem; /* Adjust the margin bottom to reduce space */
        }
        .header img {
            width: 100%;
            height: auto;
        }
        .header h1 {
            margin: 0;
            padding-top: 1rem;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
        }
        .header h1 span {
            margin: 0 10px;
        }
    </style>
    <div class="header">
        <img src="https://uploads.tff-forum.de/original/4X/5/2/3/52397973df71db6122c1eda4c5c558d2ca70686c.jpeg" alt="Tesla Battery Analysis">
        <h1><span>🔋</span> Tesla Battery Analysis <span>🔋</span></h1>
    </div>
    """,
    unsafe_allow_html=True
)

# Add Google Forms logo with text and correctly placed animated arrows with increased spacing
st.markdown(
    """
    <style>
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.05); opacity: 0.9; }
            100% { transform: scale(1); opacity: 1; }
        }
        .google-form-logo {
            display: block;
            margin: 0rem auto; /* Centers the logo horizontally below the header */
            width: 300px;  /* Adjust the width of the logo as necessary */
            height: auto;
            animation: pulse 2s infinite ease-in-out;
        }
        .arrow-text {
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 24px;
            font-weight: bold;
            margin-top: 20px;
        }
        .arrow {
            animation: blinker 3s linear infinite;
            font-size: 24px;
            margin: 0 20px; /* Increased spacing from text */
        }
        @keyframes blinker {
            50% {
                opacity: 0;
            }
        }
    </style>
    <div class="arrow-text">
        <span>Add your data here</span>
        <span class="arrow">🡢</span>
        <a href="https://forms.gle/WtFayqANSr9kwKv39" target="_blank">
            <img src="https://i.ibb.co/YZvSDRm/google-forms-400x182-removebg-preview.png" class="google-form-logo" alt="Google Forms Survey">
        </a>
        <span class="arrow">🡠</span>
        <span>Add your data here</span>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

# Get the latest row
latest_row = df.iloc[-3:][::-1]

# Display the latest row at the top
st.markdown(
    """
    <div>
        Latest Entries
    </div>
    """,
    unsafe_allow_html=True
)

st.write(latest_row)

####################################################################################################################

# Sidebar setup

# Create filter for Tesla
tesla = st.sidebar.multiselect(":red_car: Tesla", df["Tesla"].unique(), key="tesla")
if not tesla:
    df2 = df.copy()
else:
    df2 = df[df["Tesla"].isin(tesla)]

# Create filter for Version based on selected Tesla
version = st.sidebar.multiselect(":vertical_traffic_light: Version", df2["Version"].unique(), key="version")
if not version:
    df3 = df2.copy()
else:
    df3 = df2[df2["Version"].isin(version)]

# Create filter for Battery based on selected Tesla and Version
battery = st.sidebar.multiselect(":battery: Battery", df3["Battery"].unique(), key="battery")

# Apply filters based on selected Tesla, Version, and Battery
if not tesla and not version and not battery:
    st.session_state.filtered_df = df.copy()
else:
    conditions = []
    if tesla:
        conditions.append(df["Tesla"].isin(tesla))
    if version:
        conditions.append(df["Version"].isin(version))
    if battery:
        conditions.append(df["Battery"].isin(battery))
    
    condition = conditions[0]
    for cond in conditions[1:]:
        condition &= cond

    st.session_state.filtered_df = df[condition]

############################################################

# Create filter for Minimum Age and Maximum Age side by side
col3, col4 = st.sidebar.columns(2)
min_age = col3.number_input(":clock630: MIN Age (months)", min_value=1, value=max(1, int(st.session_state.filtered_df["Age"].min())))
max_age = col4.number_input(":clock12: MAX Age (months)", min_value=1, value=int(st.session_state.filtered_df["Age"].max()))

# Create filter for Minimum ODO and Maximum ODO side by side
col5, col6 = st.sidebar.columns(2)
min_odo = col5.number_input(":arrow_forward: MIN ODO (km)", min_value=1000, value=max(1000, int(st.session_state.filtered_df["Odometer"].min())), step=10000)
max_odo = col6.number_input(":fast_forward: MAX ODO (km)", min_value=1000, value=int(st.session_state.filtered_df["Odometer"].max()), step=10000)

# Columns layout for Y-axis and X-axis selection
col7, col8 = st.sidebar.columns(2)

# Radio buttons for Y-axis data selection
y_axis_data = col7.radio(":arrow_up_down: Y-axis Data", ['Degradation', 'Capacity', 'Rated Range'], index=0)

# Radio buttons for X-axis data selection
x_axis_data = col8.radio(":left_right_arrow: X-axis Data", ['Age', 'Odometer', 'Cycles'], index=0)

# Apply filters for Age and Odometer
st.session_state.filtered_df = st.session_state.filtered_df[(st.session_state.filtered_df["Age"] >= min_age) & (st.session_state.filtered_df["Age"] <= max_age)]
st.session_state.filtered_df = st.session_state.filtered_df[(st.session_state.filtered_df["Odometer"] >= min_odo) & (st.session_state.filtered_df["Odometer"] <= max_odo)]

# Determine Y-axis column name based on selection
if y_axis_data == 'Degradation':
    y_column = 'Degradation'
    y_label = 'Degradation [%]'
elif y_axis_data == 'Capacity':
    y_column = 'Capacity Net Now'  # This should match the original column name
    y_label = 'Capacity [kWh]'
else:  # 'Rated Range'
    y_column = 'Rated Range'
    y_label = 'Rated Range [km]'

# Determine X-axis label based on selection
if x_axis_data == 'Age':
    x_column = 'Age'
    x_label = 'Age [months]'
elif x_axis_data == 'Odometer':
    x_column = 'Odometer'
    x_label = 'Odometer [km]'
else:  # 'Cycles'
    x_column = 'Cycles'
    x_label = 'Cycles [n]'

# Toggle switch for trend line
add_trend_line = st.sidebar.checkbox(":chart_with_downwards_trend: Trend Line", value=False)

# Add a checkbox for Polynomial Regression in the sidebar
if add_trend_line:
    trend_line_type = st.sidebar.selectbox(
        "Trend Line Type", 
        ['Linear Regression', 'Logarithmic Regression', 'Polynomial Regression (3rd Degree)']
    )

# Add checkboxes for additional filters as a vertical switch
filter_option = st.sidebar.radio(
    "Nerdy Options",
    ["Off", "Daily SOC Limit", "AC/DC Ratio"],
    index=0
)

# Apply filters based on the selected option
if filter_option == "Daily SOC Limit":
    col1, col2 = st.sidebar.columns(2)
    daily_soc_limit_values = st.session_state.filtered_df["Daily SOC Limit"].dropna().astype(float)
    daily_soc_min = col1.number_input("Min SOC Limit", value=float(daily_soc_limit_values.min()), step=10.0, min_value=50.0, max_value=100.0, key="daily_soc_min")
    daily_soc_max = col2.number_input("Max SOC Limit", value=float(daily_soc_limit_values.max()), step=10.0, min_value=50.0, max_value=100.0, key="daily_soc_max")
    st.session_state.filtered_df = st.session_state.filtered_df[
        (st.session_state.filtered_df["Daily SOC Limit"].astype(float) >= daily_soc_min) & 
        (st.session_state.filtered_df["Daily SOC Limit"].astype(float) <= daily_soc_max)
    ]
elif filter_option == "AC/DC Ratio":
    col3, col4 = st.sidebar.columns(2)
    dc_ratio_values = st.session_state.filtered_df["DC Ratio"].dropna().astype(float)
    dc_ratio_min = col3.number_input("Min DC Ratio", value=float(dc_ratio_values.min()), step=25.0, min_value=0.0, max_value=100.0, key="dc_ratio_min")
    dc_ratio_max = col4.number_input("Max DC Ratio", value=float(dc_ratio_values.max()), step=25.0, min_value=0.0, max_value=100.0, key="dc_ratio_max")
    st.session_state.filtered_df = st.session_state.filtered_df[
        (st.session_state.filtered_df["DC Ratio"].astype(float) >= dc_ratio_min) & 
        (st.session_state.filtered_df["DC Ratio"].astype(float) <= dc_ratio_max)
    ]

# Filter the data based on the user-selected criteria
st.session_state.filtered_df = st.session_state.filtered_df[(st.session_state.filtered_df["Age"] >= min_age) & (st.session_state.filtered_df["Age"] <= max_age)]
st.session_state.filtered_df = st.session_state.filtered_df[(st.session_state.filtered_df["Odometer"] >= min_odo) & (st.session_state.filtered_df["Odometer"] <= max_odo)]

# Add a refresh button and reset button in the sidebar
refresh, reset = st.sidebar.columns(2)
if refresh.button("Refresh Data", key="refresh_data"):
    st.cache_data.clear()  # Clear the cache
    st.experimental_rerun()  # Rerun the app to refresh with new data

if reset.button("Reset Filters", key="reset_filters"):
    # Reset filters to default values
    st.session_state.filters = {
        "tesla": default_tesla,
        "version": default_version,
        "battery": default_battery,
        "min_age": default_min_age,
        "max_age": default_max_age,
        "min_odo": default_min_odo,
        "max_odo": default_max_odo,
        "show_daily_soc_limit": default_daily_soc_limit,
        "show_dc_ratio": default_dc_ratio,
    }
    st.experimental_rerun()  # Rerun the app to apply reset filters

# Show number of rows in filtered data
st.sidebar.write(f"Filtered Data Rows: {st.session_state.filtered_df.shape[0]}")

# Animated Banner with logo and link
st.sidebar.markdown(
    """
    <style>
        .sidebar-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0rem;
        }
        .sidebar-content img {
            height: auto;
        }
        .sidebar-content .akku-wiki {
            width: 90px;  /* Set specific width for Akku Wiki logo */
        }
        .sidebar-content .buy-me-coffee {
            width: 240px;  /* Set specific width for Buy Me a Coffee logo */
        }
        .sidebar-content .follow-on-x {
            width: 110px;  /* Set specific width for Follow on X logo */
        }
        .sidebar-content .text {
            text-align: center;
            font-size: 12px;  /* Default font size for text */
        }
        .sidebar-content a {
            color: white;
            text-decoration: none;
            font-weight: bold;
        }
    </style>
    <div class="sidebar-content">
        <a href="https://tff-forum.de/t/wiki-akkuwiki-model-3-model-y-cybertruck/107641?u=eivissa" target="_blank">
            <div>
                <img src="https://i.ibb.co/vBvVFTg/TFF-Logo-ohne-Schrift-removebg-preview.png" class="akku-wiki" alt="Akku Wiki">
                <div class="text">Akku Wiki</div>
            </div>
        </a>
        <a href="https://buymeacoffee.com/eivissa" target="_blank">
            <img src="https://media.giphy.com/media/o7RZbs4KAA6tvM4H6j/giphy.gif" class="buy-me-coffee" alt="Buy Me a Coffee">
        </a>
        <a href="https://x.com/eivissacopter" target="_blank">
            <img src="https://i.ibb.co/xLhFQNn/c23e7825a07e5e998bd361f9c991e12c-400x400-removebg-preview.png" class="follow-on-x" alt="Follow on X">
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

####################################################################################################################

# Ensure the 'Cycles' column is numeric
st.session_state.filtered_df[x_column] = pd.to_numeric(st.session_state.filtered_df[x_column], errors='coerce')

# Filter out non-positive values from the x_column and rows with NaNs in x_column or y_column
filtered_df = st.session_state.filtered_df[(st.session_state.filtered_df[x_column] > 0) & st.session_state.filtered_df[x_column].notna() & st.session_state.filtered_df[y_column].notna()]

# Sort the filtered_df by the x_column
filtered_df = filtered_df.sort_values(by=x_column)

##################################################

# Define color map for colorbar and invert it
color_map = "RdBu_r"

# Check if only one battery is selected and if DC Ratio or SOC Limit filter is active
color_column = None
if len(battery) == 1 and filter_option != "Off":
    if filter_option == "Daily SOC Limit":
        color_column = "Daily SOC Limit"
    elif filter_option == "AC/DC Ratio":
        color_column = "DC Ratio"

# Add trend line if selected
def add_trend_lines(fig, batteries, filtered_df, x_column, y_column, trend_line_type):
    for battery_type in batteries:
        battery_df = filtered_df[filtered_df['Battery'] == battery_type]
        X = battery_df[x_column].values.reshape(-1, 1)
        y = battery_df[y_column].values.reshape(-1, 1)
        
        if trend_line_type == 'Linear Regression':
            lin_reg = LinearRegression()
            lin_reg.fit(X, y)
            x_range = np.linspace(filtered_df[x_column].min(), filtered_df[x_column].max(), 100).reshape(-1, 1)
            y_pred = lin_reg.predict(x_range)
        elif trend_line_type == 'Logarithmic Regression':
            X_log = np.log(X)
            log_reg = LinearRegression()
            log_reg.fit(X_log, y)
            x_range = np.linspace(filtered_df[x_column].min(), filtered_df[x_column].max(), 100)
            y_pred = log_reg.predict(np.log(x_range).reshape(-1, 1))
        elif trend_line_type == 'Polynomial Regression (3rd Degree)':
            poly = PolynomialFeatures(degree=3)
            X_poly = poly.fit_transform(X)
            poly_reg = LinearRegression()
            poly_reg.fit(X_poly, y)
            x_range = np.linspace(filtered_df[x_column].min(), filtered_df[x_column].max(), 100).reshape(-1, 1)
            x_range_poly = poly.transform(x_range)
            y_pred = poly_reg.predict(x_range_poly)
        
        # Extract the color of the battery type from the scatter plot
        battery_color = next(
            (trace.marker.color for trace in fig.data if trace.name == battery_type),
            None
        )
        
        # Add the trendline trace
        trend_trace = go.Scatter(
            x=x_range.flatten(), y=y_pred.flatten(), mode='lines', name=f"{battery_type} Trendline",
            line=dict(color=battery_color)
        )
        fig.add_trace(trend_trace)
    return fig

####################################################################################

# Define the data points for the green line (converted from miles to kilometers)
odometer_miles = np.array([0, 50000, 100000, 150000, 200000])
battery_retention = np.array([0, -8, -12, -15, -18])  # Ensure the initial point starts at 100%
odometer_km = odometer_miles * 1.60934  # Convert miles to kilometers

# Create a smooth line for the green line using logarithmic fitting
odometer_km_log = np.log(odometer_km[1:])  # Remove the zero value for log transformation
battery_retention_log = battery_retention[1:]  # Corresponding y-values

log_reg = LinearRegression()
log_reg.fit(odometer_km_log.reshape(-1, 1), battery_retention_log)

odometer_km_smooth = np.linspace(odometer_km[1:].min(), odometer_km.max(), 500)
battery_retention_smooth = log_reg.predict(np.log(odometer_km_smooth).reshape(-1, 1))

# Insert the initial point back into the smooth curve
odometer_km_smooth = np.insert(odometer_km_smooth, 0, odometer_km[0])
battery_retention_smooth = np.insert(battery_retention_smooth, 0, battery_retention[0])

####################################################################################

# Ensure the selected color column is numeric
if color_column:
    filtered_df[color_column] = pd.to_numeric(filtered_df[color_column], errors='coerce')

# Create the scatter plot
if color_column:
    fig = px.scatter(
        filtered_df, x=x_column, y=y_column, color=color_column, color_continuous_scale=color_map,
        labels={x_column: x_label, y_column: y_label, color_column: color_column},
    )
else:
    fig = px.scatter(
        filtered_df, x=x_column, y=y_column, color='Battery',
        labels={x_column: x_label, y_column: y_label},
        color_discrete_sequence=color_sequence,
    )

# Add battery traces to ensure they appear first in the legend
batteries = filtered_df['Battery'].unique()
for battery_type in batteries:
    battery_color = next(
        (trace.marker.color for trace in fig.data if trace.name == battery_type),
        None
    )
    if not any(trace.name == battery_type for trace in fig.data):
        battery_trace = go.Scatter(
            x=[None], y=[None], mode='markers', marker=dict(color=battery_color),
            showlegend=True, name=battery_type
        )
        fig.add_trace(battery_trace)

# Add trend line if selected
if add_trend_line:
    fig = add_trend_lines(fig, batteries, filtered_df, x_column, y_column, trend_line_type)

# Add the green line to the scatter plot if Odometer is selected
if x_axis_data == 'Odometer':
    fig.add_trace(go.Scatter(
        x=odometer_km_smooth, y=battery_retention_smooth,
        mode='lines', name='Tesla Battery Retention',
        line=dict(color='rgba(0, 0, 255, 0.6)', width=8)  # Adjust the color to be semi-transparent
    ))

# Ensure the legend always appears
fig.update_layout(
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0
    )
)

# Add watermark to the plot
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

# Plot the figure
st.plotly_chart(fig, use_container_width=True)

####################################################################################################################

# Determine the denominator column based on the X-axis selection
if x_axis_data == 'Age':
    denominator_column = 'Age'
    x_label = 'Month'
    divisor = 1  # No additional scaling
elif x_axis_data == 'Odometer':
    denominator_column = 'Odometer'
    x_label = '1000km]'
    divisor = 1000  # Scale Odometer to 1,000 km
else:  # 'Cycles'
    denominator_column = 'Cycles'
    x_label = 'Cycle'
    divisor = 1  # No additional scaling

# Convert Degradation and the selected denominator column to numeric, coerce errors to NaN and drop rows with NaN values
st.session_state.filtered_df['Degradation'] = pd.to_numeric(st.session_state.filtered_df['Degradation'], errors='coerce')
st.session_state.filtered_df[denominator_column] = pd.to_numeric(st.session_state.filtered_df[denominator_column], errors='coerce')
st.session_state.filtered_df = st.session_state.filtered_df.dropna(subset=['Degradation', denominator_column])

# Ensure the 'Cycles' column is numeric
st.session_state.filtered_df[x_column] = pd.to_numeric(st.session_state.filtered_df[x_column], errors='coerce')

# Filter out non-positive values from the x_column and rows with NaNs in x_column or y_column
filtered_df = st.session_state.filtered_df[(st.session_state.filtered_df[x_column] > 0) & st.session_state.filtered_df[x_column].notna() & st.session_state.filtered_df[y_column].notna()]

# Sort the filtered_df by the x_column
filtered_df = filtered_df.sort_values(by=x_column)

# Calculate degradation per selected X-axis value
st.session_state.filtered_df['DegradationPerX'] = st.session_state.filtered_df['Degradation'] / (st.session_state.filtered_df[denominator_column] / divisor)

# Filter out rows where DegradationPerX is NaN, 0, or infinite
st.session_state.filtered_df = st.session_state.filtered_df.replace([np.inf, -np.inf], np.nan).dropna(subset=['DegradationPerX'])
st.session_state.filtered_df = st.session_state.filtered_df[st.session_state.filtered_df['DegradationPerX'] != 0]

# Group by the appropriate column and calculate mean and count
if len(battery) == 1:
    selected_battery = battery[0]
    version_avg_degradation = st.session_state.filtered_df[st.session_state.filtered_df['Battery'] == selected_battery].groupby('Version')['DegradationPerX'].agg(['mean', 'count']).reset_index()
    version_avg_degradation['custom_text'] = version_avg_degradation.apply(lambda row: f"{row['mean']:.2f}% (n={row['count']})", axis=1)
    bar_fig = px.bar(
        version_avg_degradation, x='mean', y='Version', orientation='h',
        labels={'mean': f'Average Degradation / {x_label}', 'Version': ''},
        color_discrete_sequence=color_sequence,
        text='custom_text'  # Add custom text to bars
    )
else:
    avg_degradation_per_x = st.session_state.filtered_df.groupby('Battery')['DegradationPerX'].agg(['mean', 'count']).reset_index()
    avg_degradation_per_x['custom_text'] = avg_degradation_per_x.apply(lambda row: f"{row['mean']:.2f}% (n={row['count']})", axis=1)
    bar_fig = px.bar(
        avg_degradation_per_x, x='mean', y='Battery', orientation='h',
        labels={'mean': f'Average Degradation / {x_label}', 'Battery': ''},
        color_discrete_sequence=color_sequence,
        text='custom_text'  # Add custom text to bars
    )

# Invert the x-axis
bar_fig.update_xaxes(autorange='reversed')

# Position the text inside the bar
bar_fig.update_traces(textposition='inside')

# Remove the y-axis title
bar_fig.update_layout(yaxis_title=None)

# Add watermark to the bar chart
bar_fig.add_annotation(
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

# Remove the legend title
bar_fig.update_layout(showlegend=False)

# Plot the bar chart
st.plotly_chart(bar_fig, use_container_width=True)

########################

# Function to fetch additional battery data from the "Backend" worksheet
@st.cache_data(ttl=300)
def fetch_battery_info():
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
    battery_info = battery_info.applymap(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
    cols = list(battery_info.columns)
    if "Capacity (new)" in cols and "Nominal Capacity" in cols:
        cols.insert(cols.index("Capacity (new)") + 1, cols.pop(cols.index("Nominal Capacity")))
    battery_info = battery_info[cols]
    battery_info["Capacity (new)"] = battery_info["Capacity (new)"] + " kWh"
    battery_info["Nominal Capacity"] = battery_info["Nominal Capacity"] + " Ah"
    if len(battery_info.columns) > 6:
        battery_info.iloc[:, 6] = battery_info.iloc[:, 6] + " km"
    return battery_info

battery_info = fetch_battery_info()

# Filter the battery info data based on the selected batteries
if not battery:
    selected_battery_info = battery_info
else:
    selected_battery_info = battery_info[battery_info['Battery'].isin(battery)]

# Display the selected battery information as a table at the bottom of the app
st.markdown("### Battery Pack Information")
st.table(selected_battery_info.style.hide(axis='index'))

#############################################################
