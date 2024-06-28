import streamlit as st
import plotly.express as px
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.figure_factory as ff

# Set page config as the first Streamlit command
st.set_page_config(page_title="Tesla version Analysis", page_icon=":battery:", layout="wide")

# Function to fetch data from Google Sheets
@st.cache_data
def fetch_data():
    # Google Sheets API setup
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("/Users/mille/OneDrive/Tesla/STREAMLIT/tesla/.streamlit/credentials.json", scope)
    client = gspread.authorize(creds)

    # Define the URL of the Google Sheets
    url = "https://docs.google.com/spreadsheets/d/1LmyllKqJWBr8J_LKVIAimsOigT4-hpfi5NeFJR8qZhQ/edit?usp=sharing"
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

    # Clean up the 'Age' column to remove any non-numeric characters
    df['Age'] = df['Age'].str.extract('(\d+)').astype(float)

    # Clean up the 'Odometer' column to ensure it is numeric
    df['Odometer'] = df['Odometer'].str.replace(',', '').str.extract('(\d+)').astype(float)

    return df

# Fetch the data using the caching function
df = fetch_data()

# Streamlit app setup
st.title(" :battery: Tesla version Analysis")
st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

st.sidebar.header("Choose your filter: ")

# Create filter for Tesla
car = st.sidebar.multiselect("Tesla", df["Tesla"].unique())

# Create filter for Version
version = st.sidebar.multiselect("Version", df["Version"].unique())

# Create filter for Battery
battery = st.sidebar.multiselect("Battery", df["Battery"].unique())

# Create filter for Minimum Age
min_age = st.sidebar.number_input("Minimum Age (months)", min_value=0, value=int(df["Age"].min()))

# Create filter for Maximum Age
max_age = st.sidebar.number_input("Maximum Age (months)", min_value=0, value=int(df["Age"].max()))

# Create filter for Minimum ODO
min_odo = st.sidebar.number_input("Minimum ODO (km)", min_value=0, value=int(df["Odometer"].min()))

# Create filter for Maximum ODO
max_odo = st.sidebar.number_input("Maximum ODO (km)", min_value=0, value=int(df["Odometer"].max()))

# Apply filters
filtered_df = df.copy()

if car:
    filtered_df = filtered_df[filtered_df["Tesla"].isin(car)]

if version:
    filtered_df = filtered_df[filtered_df["Version"].isin(version)]

if battery:
    filtered_df = filtered_df[filtered_df["Battery"].isin(battery)]

filtered_df = filtered_df[(filtered_df["Age"] >= min_age) & (filtered_df["Age"] <= max_age)]
filtered_df = filtered_df[(filtered_df["Odometer"] >= min_odo) & (filtered_df["Odometer"] <= max_odo)]

category_df = filtered_df.groupby(by=["Version"], as_index=False)["Degradation"].sum()

# Select columns up to 'Result vs Fleet' for display
columns_to_display = list(filtered_df.columns[:filtered_df.columns.get_loc('Result vs fleet data') + 1])
filtered_df_to_display = filtered_df[columns_to_display]

st.write(filtered_df_to_display)  # Display the final filtered data

# Uncomment the following section to add plots if needed
# with col1:
#     st.subheader("Degradation per battery")
#     fig = px.bar(category_df, x="Battery", y="Degradation", text=['${:,.2f}'.format(x) for x in category_df["Degradation"]],
#                  template="seaborn")
#     st.plotly_chart(fig, use_container_width=True, height=200)

# with col2:
#     st.subheader("Degradation per version Type")
#     fig = px.pie(filtered_df, values="Degradation", names="version", hole=0.5)
#     fig.update_traces(text=filtered_df["version"], textposition="outside")
#     st.plotly_chart(fig, use_container_width=True)

# cl1, cl2 = st.columns((2))
# with cl1:
#     with st.expander("Category_ViewData"):
#         st.write(category_df.style.background_gradient(cmap="Blues"))
#         csv = category_df.to_csv(index=False).encode('utf-8')
#         st.download_button("Download Data", data=csv, file_name="Category.csv", mime="text/csv",
#                            help='Click here to download the data as a CSV file')

# with cl2:
#     with st.expander("version_ViewData"):
#         version = filtered_df.groupby(by="version", as_index=False)["Sales"].sum()
#         st.write(version.style.background_gradient(cmap="Oranges"))
#         csv = version.to_csv(index=False).encode('utf-8')
#         st.download_button("Download Data", data=csv, file_name="version.csv", mime="text/csv",
#                            help='Click here to download the data as a CSV file')

# filtered_df["month_year"] = filtered_df["Order Date"].dt.to_period("M")
# st.subheader('Time Series Analysis')

# linechart = pd.DataFrame(filtered_df.groupby(filtered_df["month_year"].dt.strftime("%Y : %b"))["Sales"].sum()).reset_index()
# fig2 = px.line(linechart, x="month_year", y="Sales", labels={"Sales": "Amount"}, height=500, width=1000, template="gridon")
# st.plotly_chart(fig2, use_container_width=True)

# with st.expander("View Data of TimeSeries:"):
#     st.write(linechart.T.style.background_gradient(cmap="Blues"))
#     csv = linechart.to_csv(index=False).encode("utf-8")
#     st.download_button('Download Data', data=csv, file_name="TimeSeries.csv", mime='text/csv')

# Create a tree map based on version, Category, Sub-Category
# st.subheader("Hierarchical view of Sales using TreeMap")
# fig3 = px.treemap(filtered_df, path=["version", "Category", "Sub-Category"], values="Sales", hover_data=["Sales"],
#                   color="Sub-Category")
# fig3.update_layout(width=800, height=650)
# st.plotly_chart(fig3, use_container_width=True)

# chart1, chart2 = st.columns((2))
# with chart1:
#     st.subheader('Segment wise Sales')
#     fig = px.pie(filtered_df, values="Sales", names="Segment", template="plotly_dark")
#     fig.update_traces(text=filtered_df["Segment"], textposition="inside")
#     st.plotly_chart(fig, use_container_width=True)

# with chart2:
#     st.subheader('Category wise Sales')
#     fig = px.pie(filtered_df, values="Sales", names="Category", template="gridon")
#     fig.update_traces(text=filtered_df["Category"], textposition="inside")
#     st.plotly_chart(fig, use_container_width=True)

# st.subheader(":point_right: Month wise Sub-Category Sales Summary")
# with st.expander("Summary_Table"):
#     df_sample = df[0:5][["version", "formfactor", "battery", "Category", "Sales", "Profit", "Quantity"]]
#     fig = ff.create_table(df_sample, colorscale="Cividis")
#     st.plotly_chart(fig, use_container_width=True)

#     st.markdown("Month wise sub-Category Table")
#     filtered_df["month"] = filtered_df["Order Date"].dt.month_name()
#     sub_category_Year = pd.pivot_table(data=filtered_df, values="Sales", index=["Sub-Category"], columns="month")
#     st.write(sub_category_Year.style.background_gradient(cmap="Blues"))

# Create a scatter plot
# data1 = px.scatter(filtered_df, x="Sales", y="Profit", size="Quantity")
# data1['layout'].update(title="Relationship between Sales and Profits using Scatter Plot.",
#                        titlefont=dict(size=20), xaxis=dict(title="Sales", titlefont=dict(size=19)),
#                        yaxis=dict(title="Profit", titlefont=dict(size=19)))
# st.plotly_chart(data1, use_container_width=True)

# with st.expander("View Data"):
#     st.write(filtered_df.iloc[:500, 1:20:2].style.background_gradient(cmap="Oranges"))

# Download original DataSet
# csv = df.to_csv(index=False).encode('utf-8')
# st.download_button('Download Data', data=csv, file_name="Data.csv", mime="text/csv")