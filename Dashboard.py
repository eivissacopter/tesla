import streamlit as st
import plotly.express as px
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Set page config as the first Streamlit command
st.set_page_config(page_title="Tesla Battery Analysis", page_icon=":battery:", layout="wide")

# Function to fetch data from Google Sheets
@st.cache
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

    # Fetch all data from the sheet, including the header row
    data = sheet.get_all_values()

    # Filter out columns with empty headers or headers starting with an underscore
    header = data[0]
    filtered_header = [col.strip() for col in header if col.strip() and not col.strip().startswith('_')]
    
    # Get the indices of the columns to keep
    keep_indices = [i for i, col in enumerate(header) if col.strip() in filtered_header]

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

    # Clean up the 'Age' column to remove " Months" and convert to float
    df['Age'] = df['Age'].str.replace(" Months", "").str.replace(",", ".").astype(float)

    # Clean up the 'Odometer' column to ensure it is numeric
    df['Odometer'] = df['Odometer'].str.replace(',', '').str.extract('(\d+)').astype(float)
    
    # Replace all commas with dots in all columns
    df = df.apply(lambda x: x.str.replace(',', '.') if x.dtype == "object" else x)

    # Add negative sign to specific columns if they exist
    columns_to_negate = ['Degradation', 'DegradationPerMonth', 'DegradationPerCycle']
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

    return df

# Fetch the data using the caching function
df = fetch_data()

# Streamlit app setup

# Add the link with animated arrows at the top
st.markdown(
    """
    <style>
        .link-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 1rem;
            font-size: 1.2rem;
            font-weight: bold;
        }
        .arrow {
            margin: 0 10px;
            display: inline-block;
            font-size: 1.5rem;
            animation: bounce 1s infinite;
        }
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {
                transform: translateY(0);
            }
            40% {
                transform: translateY(-10px);
            }
            60% {
                transform: translateY(-5px);
            }
        }
    </style>
    <div class="link-container">
        <span class="arrow">➡️</span>
        <a href="https://forms.gle/SnWNCmRnavyk7kmt5" target="_blank">Enter your data here!</a>
        <span class="arrow">⬅️</span>
    </div>
    """,
    unsafe_allow_html=True
)

# Add a JPG picture at the top as a header
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
            width: 80%;
            height: auto;
        }
        .header h1 {
            margin: 0;
            padding-top: 0rem;
            text-align: center;
        }
    </style>
    <div class="header">
        <img src="https://uploads.tff-forum.de/original/4X/e/c/7/ec7257041b0b9c87755b20a8c9dd267cb615ed82.jpeg" alt="Tesla Battery Analysis">
        <h1>Tesla Battery Analysis</h1>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

# Sidebar setup

# Initialize the filtered dataframe
filtered_df = df.copy()

# Create filter for Tesla
car_options = filtered_df["Tesla"].unique()
car = st.sidebar.multiselect("Tesla :red_car: ", car_options)

if car:
    filtered_df = filtered_df[filtered_df["Tesla"].isin(car)]

# Create filter for Version
version_options = filtered_df["Version"].unique()
version = st.sidebar.multiselect("Version :traffic_light: ", version_options)

if version:
    filtered_df = filtered_df[filtered_df["Version"].isin(version)]

# Create filter for Battery
battery_options = filtered_df["Battery"].unique()
battery = st.sidebar.multiselect("Battery :battery: ", battery_options)

if battery:
    filtered_df = filtered_df[filtered_df["Battery"].isin(battery)]

# Create filter for Minimum Age and Maximum Age side by side
col1, col2 = st.sidebar.columns(2)
min_age = col1.number_input("MIN Age (months)", min_value=0, value=int(filtered_df["Age"].min()))
max_age = col2.number_input("MAX Age (months)", min_value=0, value=int(filtered_df["Age"].max()))

# Create filter for Minimum ODO and Maximum ODO side by side
col3, col4 = st.sidebar.columns(2)
min_odo = col3.number_input("MIN ODO (km)", min_value=0, value=int(filtered_df["Odometer"].min()), step=10000)
max_odo = col4.number_input("MAX ODO (km)", min_value=0, value=int(filtered_df["Odometer"].max()), step=10000)

# Columns layout for Y-axis and X-axis selection
col5, col6 = st.sidebar.columns(2)

# Radio buttons for Y-axis data selection
y_axis_data = col5.radio("Y-axis Data", ['Degradation', 'Capacity', 'Rated Range'], index=0)

# Radio buttons for X-axis data selection
x_axis_data = col6.radio("X-axis Data", ['Age', 'Odometer', 'Cycles'], index=0)

# Apply filters for Age and Odometer
filtered_df = filtered_df[(filtered_df["Age"] >= min_age) & (filtered_df["Age"] <= max_age)]
filtered_df = filtered_df[(filtered_df["Odometer"] >= min_odo) & (filtered_df["Odometer"] <= max_odo)]

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

# Create scatterplot
fig = px.scatter(filtered_df, x=x_column, y=y_column, color='Battery',
                 labels={x_column: x_label, y_column: y_label})

# Plot the figure
st.plotly_chart(fig, use_container_width=True)

# Display the top 10 rows of the filtered data
st.write(filtered_df.head(10))

# Show number of rows in filtered data
st.sidebar.write(f"Filtered Data Rows: {filtered_df.shape[0]}")

# Reset filters button
# if st.sidebar.button("Reset Filters"):
#     # Reset all filter variables
#     car = []
#     version = []
#     battery = []
#     min_age = int(filtered_df["Age"].min())
#     max_age = int(filtered_df["Age"].max())
#     min_odo = int(filtered_df["Odometer"].min())
#     max_odo = int(filtered_df["Odometer"].max())
#     y_axis_data = 'Degradation'
#     x_axis_data = 'Age'

#     # Reset filtered_df to original df
#     filtered_df = df.copy()

#     st.sidebar.success("Filters have been reset.")

# Sidebar with logo and link
st.sidebar.markdown(
    """
    <style>
        .sidebar-content {
            display: flex;
            align-items: center;
            padding: 1rem;
        }
        .sidebar-content img {
            width: 230px;
            height: auto;
            margin-right: 1rem;
        }
        .sidebar-content a {
            color: black;
            text-decoration: none;
            font-weight: bold;
        }
    </style>
    <div class="sidebar-content">
        <a href="https://buymeacoffee.com/eivissa" target="_blank">
            <img src="https://media.giphy.com/media/o7RZbs4KAA6tvM4H6j/giphy.gif" alt="Buy Me a Coffee">
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
