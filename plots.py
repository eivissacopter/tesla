"""
Plotting functions for the Tesla Battery Analysis Dashboard.
"""

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import plotly.graph_objects as go


def add_trend_lines(fig, batteries, filtered_df, x_column, y_column, trend_line_type):
    """
    Add trend lines to a plotly figure for each battery type.
    
    Parameters:
    -----------
    fig : plotly.graph_objects.Figure
        The figure to add trend lines to
    batteries : list
        List of battery types to add trend lines for
    filtered_df : pd.DataFrame
        The filtered DataFrame containing the data
    x_column : str
        Name of the column to use for X-axis
    y_column : str
        Name of the column to use for Y-axis
    trend_line_type : str
        Type of trend line ('Linear Regression', 'Logarithmic Regression', or 'Polynomial Regression (3rd Degree)')
    
    Returns:
    --------
    plotly.graph_objects.Figure
        The figure with trend lines added
    """
    for battery_type in batteries:
        battery_df = filtered_df[filtered_df['Battery'] == battery_type]
        X = battery_df[x_column].values.reshape(-1, 1)
        y = battery_df[y_column].values.reshape(-1, 1)
        
        # Skip if insufficient data for regression
        if len(battery_df) < 2:
            continue
        
        if trend_line_type == 'Linear Regression':
            lin_reg = LinearRegression()
            lin_reg.fit(X, y)
            x_range = np.linspace(filtered_df[x_column].min(), filtered_df[x_column].max(), 100).reshape(-1, 1)
            y_pred = lin_reg.predict(x_range)
        elif trend_line_type == 'Logarithmic Regression':
            # Skip if data contains zero or negative values (log domain error)
            if np.any(X <= 0):
                continue
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


def get_retention_curve_data():
    """
    Calculate the Tesla Battery Retention curve data (green line).
    
    This function creates a smooth logarithmic curve representing Tesla's
    expected battery retention over kilometers, based on converting the
    original miles-based data points to kilometers.
    
    Returns:
    --------
    tuple
        (odometer_km_smooth, battery_retention_smooth) - Arrays for X and Y coordinates
    """
    # Define the data points for the green line (converted from miles to kilometers)
    odometer_miles = np.array([0, 50000, 100000, 150000, 200000])
    battery_retention = np.array([0, -8, -12, -13.5, -15])  # Ensure the initial point starts at 100%
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
    
    return odometer_km_smooth, battery_retention_smooth
