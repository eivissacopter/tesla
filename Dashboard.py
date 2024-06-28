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

    # Fix duplicate headers
    header = data[0]
    unique_header = []
    for col in header:
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
    df = pd.DataFrame(data[1:], columns=unique_header)

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

# Add a JPG picture at the top as a header
st.markdown(
    """
    <style>
        .header {
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            padding: 2rem 0;
        }
        .header img {
            width: 100%;
            height: auto;
        }
        .header h1 {
            margin: 0;
            padding-top: 1rem;
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

st.sidebar.header("Choose your filter: ")

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

# Create filter for Minimum Age
min_age = st.sidebar.number_input("Minimum Age (months)", min_value=0, value=int(filtered_df["Age"].min()))

# Create filter for Maximum Age
max_age = st.sidebar.number_input("Maximum Age (months)", min_value=0, value=int(filtered_df["Age"].max()))

filtered_df = filtered_df[(filtered_df["Age"] >= min_age) & (filtered_df["Age"] <= max_age)]

# Create filter for Minimum ODO
min_odo = st.sidebar.number_input("Minimum ODO (km)", min_value=0, value=int(filtered_df["Odometer"].min()))

# Create filter for Maximum ODO
max_odo = st.sidebar.number_input("Maximum ODO (km)", min_value=0, value=int(filtered_df["Odometer"].max()))

filtered_df = filtered_df[(filtered_df["Odometer"] >= min_odo) & (filtered_df["Odometer"] <= max_odo)]

category_df = filtered_df.groupby(by=["Version"], as_index=False)["Degradation"].sum()

# Select columns up to 'Result vs Fleet' for display
columns_to_display = list(filtered_df.columns[:filtered_df.columns.get_loc('Result vs fleet data') + 1])
filtered_df_to_display = filtered_df[columns_to_display]

# Reverse the DataFrame
filtered_df_to_display = filtered_df_to_display.iloc[::-1]

# Drop columns where the header is empty or starts with '_'
filtered_df_to_display = filtered_df_to_display.loc[:, ~filtered_df_to_display.columns.str.match(r'(^$|^_)')]

# Display the top 5 rows
st.write(filtered_df_to_display.head(5))  # Display the final filtered data

####################################################################################################################

# Scatterplot
st.sidebar.subheader("Scatterplot Options")

# Radio buttons for Y-axis data selection
y_axis_data = st.sidebar.radio("Y-axis Data", ['Degradation', 'Capacity', 'Rated Range'], index=0)

# Radio buttons for X-axis data selection
x_axis_data = st.sidebar.radio("X-axis Data", ['Age', 'Odometer', 'Cycles'], index=0)

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
    x_label = 'Age [months]'
elif x_axis_data == 'Odometer':
    x_label = 'Odometer [km]'
else:  # 'Cycles'
    x_label = 'Cycles [n]'

# Create scatterplot
fig = px.scatter(filtered_df, x=x_axis_data, y=y_column, color='Battery', 
                 title=f'{y_label} vs {x_label}', labels={x_axis_data: x_label, y_column: y_label})

# Plot the figure
st.plotly_chart(fig, use_container_width=True)
