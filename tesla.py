import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from streamlit_gsheets import GSheetsConnection

# Streamlit App
st.title('Battery State of Health Analysis')

# Google Sheets URL and connection
url = "https://docs.google.com/spreadsheets/d/1LmyllKqJWBr8J_LKVIAimsOigT4-hpfi5NeFJR8qZhQ/edit?usp=sharing"

# Create a connection object.
conn = st.connection("gsheets", type=GSheetsConnection)

# Fetch data from Google Sheets
data = conn.read(spreadsheet=url)

# Preprocess the data
data.fillna(method='ffill', inplace=True)

# Define the battery types to filter
battery_types = ['Panasonic 3']

# Filter data for specific battery types and degradation threshold
data = data[data['Battery'].isin(battery_types)]
data = data[data['Degradation'] >= 0.1]

data = data.sort_values(by='Age')

battery = data['Battery']
chemistry = data['Chemistry']
age = data['Age']
odometer = data['Odometer']
capacity = data['Capacity Net Now']
cycles = data['Cycles']
degradation = data['Degradation'] * (-1)
dailysoc = data['Daily SOC Limit']
dcratio = data['DC Ratio']
delivered = pd.to_datetime(data['Delivered'], format='%d.%m.%Y')  # Correct date format to 'DD.MM.YYYY'
date = pd.to_datetime(data['Date'], format='%d.%m.%Y')  # Correct date format to 'DD.MM.YYYY'

# Calculate the absolute difference in months between 'Date' and 'Delivered'
ageinmonths = abs((date - delivered) / np.timedelta64(1, 'M'))

# Plotting
plt.style.use('dark_background')
fig, ax = plt.subplots()

scatter = plt.scatter(ageinmonths, degradation, c=odometer, s=dailysoc, cmap='bwr', edgecolor='black', linewidth=1,
                      alpha=1.0, label='Battery')

# Fit a linear trend line
coefficients = np.polyfit(ageinmonths, degradation, 1)
trend_line = np.polyval(coefficients, ageinmonths)
plt.plot(ageinmonths, trend_line, color='orange', linestyle='--', label='Trend Line')

cbar = plt.colorbar()
cbar.set_label('Odometer [km]')

handles, labels = scatter.legend_elements(prop="sizes", alpha=1.0, color='white')
legend2 = ax.legend(reversed(handles), reversed(labels), loc="upper right", title="Daily SOC [%]")

plt.title(' / '.join(battery_types))
plt.xlabel('Age [Months]')
plt.ylabel('Degradation [%]')
# plt.ylim((-30, 0))
# plt.xlim((0, 96))

plt.grid(color='darkgrey', linestyle='-', linewidth=0.5)
plt.rcParams['figure.dpi'] = 500
plt.rcParams['savefig.dpi'] = 500
plt.tight_layout()

st.pyplot(fig)

print(data.columns)

