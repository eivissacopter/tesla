"""Plotting utilities for battery analysis."""
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

from ..config import Config


class PlotBuilder:
    """Builder for creating plotly charts."""
    
    @staticmethod
    def create_scatter_plot(
        df: pd.DataFrame,
        x_column: str,
        y_column: str,
        x_label: str,
        y_label: str,
        color_column: Optional[str] = None,
        color_map: str = "RdBu_r"
    ) -> go.Figure:
        """Create a scatter plot.
        
        Args:
            df: DataFrame with plot data.
            x_column: X-axis column name.
            y_column: Y-axis column name.
            x_label: X-axis label.
            y_label: Y-axis label.
            color_column: Optional column for color mapping.
            color_map: Color map to use.
            
        Returns:
            Plotly Figure object.
        """
        if color_column and color_column in df.columns:
            df[color_column] = pd.to_numeric(df[color_column], errors='coerce')
            fig = px.scatter(
                df, x=x_column, y=y_column,
                color=color_column,
                color_continuous_scale=color_map,
                labels={x_column: x_label, y_column: y_label, color_column: color_column},
                symbol='Marker Symbol',
                symbol_map={'circle': 'circle', 'star': 'star'}
            )
        else:
            fig = px.scatter(
                df, x=x_column, y=y_column,
                color='Battery',
                symbol='Marker Symbol',
                labels={x_column: x_label, y_column: y_label},
                color_discrete_sequence=Config.COLOR_SEQUENCE,
                symbol_map={'circle': 'circle', 'star': 'star'}
            )
        
        # Hide marker symbol legend items (circle/star) - symbols already shown in legend
        for trace in fig.data:
            if trace.name in ['circle', 'star']:
                trace.showlegend = False
        
        PlotBuilder._add_watermark(fig)
        PlotBuilder._configure_legend(fig)
        
        return fig
    
    @staticmethod
    def add_trend_lines(
        fig: go.Figure,
        df: pd.DataFrame,
        batteries: List[str],
        x_column: str,
        y_column: str,
        trend_type: str
    ) -> go.Figure:
        """Add trend lines to the plot.
        
        Args:
            fig: Figure to add trend lines to.
            df: DataFrame with data.
            batteries: List of battery types.
            x_column: X-axis column name.
            y_column: Y-axis column name.
            trend_type: Type of trend line ('Linear Regression', 'Logarithmic Regression', etc.).
            
        Returns:
            Updated Figure object.
        """
        for battery_type in batteries:
            battery_df = df[df['Battery'] == battery_type]
            X = battery_df[x_column].values.reshape(-1, 1)
            y = battery_df[y_column].values.reshape(-1, 1)
            
            if len(X) < 2:
                continue
            
            if trend_type == 'Linear Regression':
                x_range, y_pred = PlotBuilder._linear_regression(X, y, df[x_column].min(), df[x_column].max())
            elif trend_type == 'Logarithmic Regression':
                x_range, y_pred = PlotBuilder._logarithmic_regression(X, y, df[x_column].min(), df[x_column].max())
            elif trend_type == 'Polynomial Regression (3rd Degree)':
                x_range, y_pred = PlotBuilder._polynomial_regression(X, y, df[x_column].min(), df[x_column].max())
            else:
                continue
            
            # Get battery color from existing traces
            battery_color = next(
                (trace.marker.color for trace in fig.data if trace.name == battery_type),
                None
            )
            
            trend_trace = go.Scatter(
                x=x_range.flatten(),
                y=y_pred.flatten(),
                mode='lines',
                name=f"{battery_type} Trendline",
                line=dict(color=battery_color)
            )
            fig.add_trace(trend_trace)
        
        return fig
    
    @staticmethod
    def add_tesla_retention_line(fig: go.Figure, odometer_km: np.ndarray, retention: np.ndarray) -> go.Figure:
        """Add Tesla's official retention line to the plot.
        
        Args:
            fig: Figure to add line to.
            odometer_km: Odometer values in km.
            retention: Battery retention percentages.
            
        Returns:
            Updated Figure object.
        """
        fig.add_trace(go.Scatter(
            x=odometer_km,
            y=retention,
            mode='lines',
            name='Tesla Battery Retention',
            line=dict(color='rgba(0, 0, 255, 0.6)', width=8)
        ))
        return fig
    
    @staticmethod
    def create_bar_chart(
        df: pd.DataFrame,
        x_column: str,
        y_column: str,
        x_label: str,
        orientation: str = 'h'
    ) -> go.Figure:
        """Create a horizontal bar chart.
        
        Args:
            df: DataFrame with data.
            x_column: X-axis column name.
            y_column: Y-axis column name.
            x_label: X-axis label.
            orientation: Chart orientation ('h' or 'v').
            
        Returns:
            Plotly Figure object.
        """
        fig = px.bar(
            df,
            x=x_column,
            y=y_column,
            orientation=orientation,
            labels={x_column: x_label, y_column: ''},
            color_discrete_sequence=Config.COLOR_SEQUENCE,
            text='custom_text'
        )
        
        # Invert x-axis for degradation
        fig.update_xaxes(autorange='reversed')
        
        # Position text inside bars
        fig.update_traces(
            textposition='inside',
            insidetextanchor='start',
            hovertemplate='<b>%{y}</b><br>Degradation: %{x:.2f}%<br>Count: %{text}<extra></extra>'
        )
        
        # Add annotations for average degradation
        for _, row in df.iterrows():
            fig.add_annotation(
                x=row[x_column],
                y=row[y_column],
                text=row['degradation_text'],
                showarrow=False,
                xshift=20
            )
        
        fig.update_layout(yaxis_title=None, showlegend=False)
        PlotBuilder._add_watermark(fig)
        
        return fig
    
    @staticmethod
    def create_performance_line_plot(
        plot_df: pd.DataFrame,
        x_label: str,
        y_label: str,
        color_map: Dict[str, str]
    ) -> go.Figure:
        """Create a line plot for performance data.
        
        Args:
            plot_df: DataFrame with plot data (must include 'File' column).
            x_label: X-axis label.
            y_label: Y-axis label.
            color_map: Mapping of labels to colors.
            
        Returns:
            Plotly Figure object.
        """
        fig = go.Figure()
        
        # Group by Label and File to create separate traces
        # This prevents lines from connecting between different files
        for label in plot_df['Label'].unique():
            label_df = plot_df[plot_df['Label'] == label]
            
            if 'File' in label_df.columns:
                # Create a trace for each file within this label
                for file_name in label_df['File'].unique():
                    file_df = label_df[label_df['File'] == file_name].sort_values('X')
                    
                    # Only show legend for first trace of each label
                    show_legend = (file_name == label_df['File'].iloc[0])
                    
                    fig.add_trace(go.Scatter(
                        x=file_df['X'],
                        y=file_df['Y'],
                        mode='lines',
                        name=label,
                        line=dict(color=color_map.get(label), width=3),
                        legendgroup=label,
                        showlegend=show_legend,
                        connectgaps=False
                    ))
            else:
                # Fallback for data without File column
                label_df = label_df.sort_values('X')
                fig.add_trace(go.Scatter(
                    x=label_df['X'],
                    y=label_df['Y'],
                    mode='lines',
                    name=label,
                    line=dict(color=color_map.get(label), width=3),
                    connectgaps=False
                ))
        
        # Configure layout
        fig.update_layout(
            showlegend=True,
            xaxis_title=x_label,
            yaxis_title=y_label,
            width=800,
            height=800,
            margin=dict(l=50, r=50, t=50, b=50),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=1.1,
                xanchor="center",
                x=0.5,
                title=None
            )
        )
        
        PlotBuilder._add_watermark(fig, opacity=0.15)
        
        return fig
    
    @staticmethod
    def _linear_regression(X: np.ndarray, y: np.ndarray, x_min: float, x_max: float):
        """Perform linear regression.
        
        Args:
            X: Input features.
            y: Target values.
            x_min: Minimum x value for prediction range.
            x_max: Maximum x value for prediction range.
            
        Returns:
            Tuple of (x_range, y_pred).
        """
        lin_reg = LinearRegression()
        lin_reg.fit(X, y)
        x_range = np.linspace(x_min, x_max, 100).reshape(-1, 1)
        y_pred = lin_reg.predict(x_range)
        return x_range, y_pred
    
    @staticmethod
    def _logarithmic_regression(X: np.ndarray, y: np.ndarray, x_min: float, x_max: float):
        """Perform logarithmic regression.
        
        Args:
            X: Input features.
            y: Target values.
            x_min: Minimum x value for prediction range.
            x_max: Maximum x value for prediction range.
            
        Returns:
            Tuple of (x_range, y_pred).
        """
        X_log = np.log(X)
        log_reg = LinearRegression()
        log_reg.fit(X_log, y)
        x_range = np.linspace(x_min, x_max, 100)
        y_pred = log_reg.predict(np.log(x_range).reshape(-1, 1))
        return x_range, y_pred
    
    @staticmethod
    def _polynomial_regression(X: np.ndarray, y: np.ndarray, x_min: float, x_max: float):
        """Perform polynomial regression (3rd degree).
        
        Args:
            X: Input features.
            y: Target values.
            x_min: Minimum x value for prediction range.
            x_max: Maximum x value for prediction range.
            
        Returns:
            Tuple of (x_range, y_pred).
        """
        poly = PolynomialFeatures(degree=3)
        X_poly = poly.fit_transform(X)
        poly_reg = LinearRegression()
        poly_reg.fit(X_poly, y)
        x_range = np.linspace(x_min, x_max, 100).reshape(-1, 1)
        x_range_poly = poly.transform(x_range)
        y_pred = poly_reg.predict(x_range_poly)
        return x_range, y_pred
    
    @staticmethod
    def _add_watermark(fig: go.Figure, opacity: float = 0.05) -> None:
        """Add watermark to the plot.
        
        Args:
            fig: Figure to add watermark to.
            opacity: Watermark opacity.
        """
        fig.add_annotation(
            text="@eivissacopter",
            font=dict(size=20, color="lightgrey"),
            align="center",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            opacity=opacity,
            showarrow=False
        )
    
    @staticmethod
    def _configure_legend(fig: go.Figure) -> None:
        """Configure legend appearance.
        
        Args:
            fig: Figure to configure.
        """
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
