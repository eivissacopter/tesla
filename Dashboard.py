import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go
import plotly.io as pio

# Import from new modules
from styles import HEADER_HTML, GOOGLE_FORM_LOGO_HTML, SIDEBAR_BANNER_HTML, LATEST_ENTRIES_HTML
from utils import fetch_data, fetch_battery_info
from plots import add_trend_lines, get_retention_curve_data

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

# Add the main header picture with emojis
st.markdown(HEADER_HTML, unsafe_allow_html=True)

# Add Google Forms logo with text and correctly placed animated arrows with increased spacing
st.markdown(GOOGLE_FORM_LOGO_HTML, unsafe_allow_html=True)

# Add search field for username below the "Add your data here" section
username = st.text_input("Search by Username:", key="username")

# Fetch the data
df, battery_pack_col = fetch_data(username_filter=username)

# Get the latest row from the filtered DataFrame
latest_row = df.iloc[-3:][::-1]

# Display the latest entries at the top
st.markdown(LATEST_ENTRIES_HTML, unsafe_allow_html=True)

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

# Add the "Hide Replaced Packs" checkbox below the "Trend Line" checkbox
hide_replaced_packs = st.sidebar.checkbox(":star: Hide Replaced Packs", value=True)

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

# Apply the "Hide Replaced Packs" filter
if hide_replaced_packs and battery_pack_col and battery_pack_col in st.session_state.filtered_df.columns:
    st.session_state.filtered_df = st.session_state.filtered_df[st.session_state.filtered_df[battery_pack_col] != 'Replaced']

# Filter the data based on the user-selected criteria
st.session_state.filtered_df = st.session_state.filtered_df[(st.session_state.filtered_df["Age"] >= min_age) & (st.session_state.filtered_df["Age"] <= max_age)]
st.session_state.filtered_df = st.session_state.filtered_df[(st.session_state.filtered_df["Odometer"] >= min_odo) & (st.session_state.filtered_df["Odometer"] <= max_odo)]

# Add a refresh button in the sidebar
refresh = st.sidebar.button("Clear Cache", key="clear_cache_refresh")
if refresh:
    st.cache_data.clear()  # Clear the cache
    st.success("Cache cleared! Please rerun the app.")

# Show number of rows in filtered data
st.sidebar.write(f"Filtered Data Rows: {st.session_state.filtered_df.shape[0]}")

# Animated Banner with logo and link
st.sidebar.markdown(SIDEBAR_BANNER_HTML, unsafe_allow_html=True)

####################################################################################################################

from sklearn.linear_model import LinearRegression

# Ensure the 'Cycles' column is numeric
st.session_state.filtered_df[x_column] = pd.to_numeric(st.session_state.filtered_df[x_column], errors='coerce')

# Filter out non-positive values from the x_column and rows with NaNs in x_column or y_column
filtered_df = st.session_state.filtered_df[(st.session_state.filtered_df[x_column] > 0) & st.session_state.filtered_df[x_column].notna() & st.session_state.filtered_df[y_column].notna()]

# Sort the filtered_df by the x_column
filtered_df = filtered_df.sort_values(by=x_column)

##################################################

# Create 'Marker Symbol' column based on 'Battery Pack'
if battery_pack_col and battery_pack_col in filtered_df.columns:
    filtered_df['Marker Symbol'] = filtered_df[battery_pack_col].fillna('Original').apply(
        lambda x: 'star' if x.strip() == 'Replaced' else 'circle'
    )
else:
    filtered_df['Marker Symbol'] = 'circle'  # Default to circle if 'Battery Pack' is missing

# Define color map for colorbar and invert it
color_map = "RdBu_r"

# Check if only one battery is selected and if DC Ratio or SOC Limit filter is active
color_column = None
if len(battery) == 1 and filter_option != "Off":
    if filter_option == "Daily SOC Limit":
        color_column = "Daily SOC Limit"
    elif filter_option == "AC/DC Ratio":
        color_column = "DC Ratio"

####################################################################################

# Get the Tesla Battery Retention curve data (Green Line)
odometer_km_smooth, battery_retention_smooth = get_retention_curve_data()

####################################################################################

# Ensure the selected color column is numeric
if color_column:
    filtered_df[color_column] = pd.to_numeric(filtered_df[color_column], errors='coerce')

# Create the scatter plot
if color_column:
    fig = px.scatter(
        filtered_df, x=x_column, y=y_column, color=color_column, color_continuous_scale=color_map,
        labels={x_column: x_label, y_column: y_label, color_column: color_column},
        symbol='Marker Symbol',
        symbol_map={'circle': 'circle', 'star': 'star'}
    )
else:
    fig = px.scatter(
        filtered_df, x=x_column, y=y_column, color='Battery', symbol='Marker Symbol',
        labels={x_column: x_label, y_column: y_label},
        color_discrete_sequence=color_sequence,
        symbol_map={'circle': 'circle', 'star': 'star'}
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
if x_axis_data == 'Odometer' and y_axis_data == 'Degradation':
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

from sklearn.linear_model import LinearRegression

# Function to predict SOH 70% projection
def predict_soh_70(X, y, soh_70_degradation=-30):
    if len(X) > 1 and len(y) > 1:
        lin_reg = LinearRegression()
        lin_reg.fit(X, y)
        predicted_x_value = (soh_70_degradation - lin_reg.intercept_) / lin_reg.coef_
        return predicted_x_value
    return None

# Perform SOH 70% projection for each selected battery
result_texts = []

if battery:  # Check if any battery filter is applied
    for battery_type in battery:
        selected_battery_df = filtered_df[filtered_df["Battery"] == battery_type]
        
        # Clean data: drop rows with NaN or infinite values
        selected_battery_df = selected_battery_df.replace([np.inf, -np.inf], np.nan).dropna(subset=[x_column, "Degradation"])

        X = selected_battery_df[x_column].values.reshape(-1, 1)
        y = selected_battery_df["Degradation"].values.reshape(-1, 1)

        # Only proceed if there is sufficient data to fit the model
        if len(X) > 1 and len(y) > 1:
            # Fit a Linear Regression model
            lin_reg = LinearRegression()
            lin_reg.fit(X, y)

            # Predict when degradation will reach -30%
            soh_70_degradation = -30
            predicted_x_value = (soh_70_degradation - lin_reg.intercept_) / lin_reg.coef_

            years_text = None
            kilometers_text = None

            if x_axis_data == 'Age':
                predicted_years = predicted_x_value / 12  # Convert months to years
                if 7 <= predicted_years[0][0] <= 20:
                    years_text = f"{predicted_years[0][0]:.0f} years"
                else:
                    years_text = "unknown"
            elif x_axis_data == 'Odometer':
                predicted_kilometers = predicted_x_value
                if 300000 <= predicted_kilometers[0][0] <= 1500000:
                    rounded_kilometers = round(predicted_kilometers[0][0] / 100000) * 100000
                    kilometers_text = f"{rounded_kilometers:.0f} kilometers"
                else:
                    kilometers_text = "unknown"
            elif x_axis_data == 'Cycles':
                predicted_cycles = predicted_x_value
                if 300000 <= predicted_cycles[0][0] <= 1500000:
                    rounded_kilometers = round(predicted_cycles[0][0] / 100000) * 100000
                    kilometers_text = f"{rounded_kilometers:.0f} kilometers"
                else:
                    kilometers_text = "unknown"

            # Calculate projection for years if x_axis_data is not 'Age'
            if x_axis_data != 'Age' and 'Age' in selected_battery_df.columns:
                X_age = selected_battery_df['Age'].values.reshape(-1, 1)
                lin_reg.fit(X_age, y)
                predicted_age_value = (soh_70_degradation - lin_reg.intercept_) / lin_reg.coef_
                predicted_years_value = predicted_age_value / 12  # Convert months to years
                if 7 <= predicted_years_value[0][0] <= 20:
                    years_text = f"{predicted_years_value[0][0]:.0f} years"
                else:
                    years_text = "unknown"

            # Calculate projection for kilometers regardless of x_axis_data
            if 'Odometer' in selected_battery_df.columns:
                X_odo = selected_battery_df['Odometer'].values.reshape(-1, 1)
                lin_reg.fit(X_odo, y)
                predicted_odo_value = (soh_70_degradation - lin_reg.intercept_) / lin_reg.coef_
                if 300000 <= predicted_odo_value[0][0] <= 1500000:
                    rounded_kilometers = round(predicted_odo_value[0][0] / 100000) * 100000
                    kilometers_text = f"{rounded_kilometers:.0f} kilometers"
                else:
                    kilometers_text = "unknown"

            # Prepare the display text
            display_text = f"<span style='color:orange; font-weight:bold;'>{battery_type}</span> is expected to reach <span style='color:orange; font-weight:bold;'>70% SOH</span> after "
            if years_text != "unknown" and kilometers_text != "unknown":
                display_text += f"<span style='color:orange; font-weight:bold;'>{years_text}</span> or <span style='color:orange; font-weight:bold;'>{kilometers_text}</span>."
            elif years_text != "unknown":
                display_text += f"<span style='color:orange; font-weight:bold;'>{years_text}</span>."
            elif kilometers_text != "unknown":
                display_text += f"<span style='color:orange; font-weight:bold;'>{kilometers_text}</span>."

            result_texts.append(display_text)
        else:
            # Display a message if there is insufficient data
            result_texts.append(
                f"There is insufficient data to project the 70% SOH for the <span style='color:orange; font-weight:bold;'>{battery_type}</span>."
            )

    # Display the results below the scatterplot with reduced spacing
    st.markdown(
        """
        <div style="text-align:center; font-size:16px; padding:10px; margin-top:20px;">
            With these filter settings, the:
        </div>
        """,
        unsafe_allow_html=True
    )

    for text in result_texts:
        st.markdown(
            f"""
            <div style="text-align:center; font-size:16px; padding:5px; margin-top:5px;">
                {text}
            </div>
            """,
            unsafe_allow_html=True
        )

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
    version_avg_degradation['custom_text'] = version_avg_degradation.apply(lambda row: f"n={row['count']}", axis=1)
    version_avg_degradation['degradation_text'] = version_avg_degradation.apply(lambda row: f"{row['mean']:.2f}%", axis=1)
    version_avg_degradation = version_avg_degradation.sort_values(by='mean', ascending=True)
    bar_fig = px.bar(
        version_avg_degradation, x='mean', y='Version', orientation='h',
        labels={'mean': f'Average Degradation / {x_label}', 'Version': ''},
        color_discrete_sequence=color_sequence,
        text='custom_text'  # Add custom text to bars
    )
else:
    avg_degradation_per_x = st.session_state.filtered_df.groupby('Battery')['DegradationPerX'].agg(['mean', 'count']).reset_index()
    avg_degradation_per_x['custom_text'] = avg_degradation_per_x.apply(lambda row: f"n={row['count']}", axis=1)
    avg_degradation_per_x['degradation_text'] = avg_degradation_per_x.apply(lambda row: f"{row['mean']:.2f}%", axis=1)
    avg_degradation_per_x = avg_degradation_per_x.sort_values(by='mean', ascending=True)
    bar_fig = px.bar(
        avg_degradation_per_x, x='mean', y='Battery', orientation='h',
        labels={'mean': f'Average Degradation / {x_label}', 'Battery': ''},
        color_discrete_sequence=color_sequence,
        text='custom_text'  # Add custom text to bars
    )

# Invert the x-axis
bar_fig.update_xaxes(autorange='reversed')

# Position the text inside the bar for counts and outside for average degradation
bar_fig.update_traces(
    textposition='inside',
    insidetextanchor='start',
    hovertemplate='<b>%{y}</b><br>Degradation: %{x:.2f}%<br>Count: %{text}<extra></extra>',
)

# Add custom annotations for the average degradation outside the bars
for i, row in version_avg_degradation.iterrows() if len(battery) == 1 else avg_degradation_per_x.iterrows():
    bar_fig.add_annotation(
        x=row['mean'],
        y=row['Version'] if len(battery) == 1 else row['Battery'],
        text=row['degradation_text'],
        showarrow=False,
        xshift=20
    )

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
