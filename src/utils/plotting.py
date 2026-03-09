"""Plotting utilities for battery analysis."""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
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
        color_map: str = 'RdBu_r'
    ) -> go.Figure:
        """Create a scatter plot."""
        plot_df = df.copy()
        hover_data = {
            column: True
            for column in ['Tesla', 'Version', 'Battery', 'Username', 'Age', 'Odometer', 'SOH', 'Daily SOC Limit', 'DC Ratio']
            if column in plot_df.columns and column not in {x_column, y_column, color_column}
        }

        common_kwargs = dict(
            data_frame=plot_df,
            x=x_column,
            y=y_column,
            symbol='Marker Symbol',
            symbol_map={'circle': 'circle', 'star': 'star'},
            hover_data=hover_data,
            opacity=0.82,
        )

        if color_column and color_column in plot_df.columns:
            plot_df[color_column] = pd.to_numeric(plot_df[color_column], errors='coerce')
            fig = px.scatter(
                color=color_column,
                color_continuous_scale=color_map,
                labels={x_column: x_label, y_column: y_label, color_column: color_column},
                **common_kwargs,
            )
        elif 'Battery' in plot_df.columns:
            fig = px.scatter(
                color='Battery',
                color_discrete_sequence=Config.COLOR_SEQUENCE,
                labels={x_column: x_label, y_column: y_label},
                **common_kwargs,
            )
        else:
            fig = px.scatter(
                labels={x_column: x_label, y_column: y_label},
                **common_kwargs,
            )

        for trace in fig.data:
            if trace.name in ['circle', 'star']:
                trace.showlegend = False
            trace.marker.update(size=9, line=dict(width=0.5, color='rgba(255,255,255,0.45)'))

        fig.update_layout(hovermode='closest', margin=dict(l=20, r=20, t=40, b=20))
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
        """Add trend lines to the plot."""
        for battery_index, battery_type in enumerate(batteries):
            battery_df = df[df['Battery'] == battery_type].copy()
            if battery_df.empty:
                continue

            battery_df[x_column] = pd.to_numeric(battery_df[x_column], errors='coerce')
            battery_df[y_column] = pd.to_numeric(battery_df[y_column], errors='coerce')
            battery_df = battery_df.dropna(subset=[x_column, y_column]).sort_values(x_column)

            if len(battery_df) < 3:
                continue

            X = battery_df[x_column].to_numpy().reshape(-1, 1)
            y = battery_df[y_column].to_numpy()
            x_min = float(battery_df[x_column].min())
            x_max = float(battery_df[x_column].max())

            if trend_type == 'Linear Regression':
                x_range, y_pred = PlotBuilder._linear_regression(X, y, x_min, x_max)
            elif trend_type == 'Logarithmic Regression':
                positive_df = battery_df[battery_df[x_column] > 0]
                if len(positive_df) < 3:
                    continue
                x_range, y_pred = PlotBuilder._logarithmic_regression(
                    positive_df[x_column].to_numpy().reshape(-1, 1),
                    positive_df[y_column].to_numpy(),
                    float(positive_df[x_column].min()),
                    float(positive_df[x_column].max())
                )
            elif trend_type == 'Polynomial Regression (3rd Degree)':
                if len(battery_df) < 4:
                    continue
                x_range, y_pred = PlotBuilder._polynomial_regression(X, y, x_min, x_max)
            else:
                continue

            battery_color = PlotBuilder._get_trace_color(fig, battery_type, battery_index)
            fig.add_trace(go.Scatter(
                x=np.asarray(x_range).flatten(),
                y=np.asarray(y_pred).flatten(),
                mode='lines',
                name=f'{battery_type} Trendline',
                line=dict(color=battery_color, width=3, dash='dash'),
                hovertemplate=f'{battery_type} trend<br>X: %{{x:.2f}}<br>Y: %{{y:.2f}}<extra></extra>',
            ))

        return fig

    @staticmethod
    def add_tesla_retention_line(fig: go.Figure, odometer_km: np.ndarray, retention: np.ndarray) -> go.Figure:
        """Add Tesla's official retention line to the plot."""
        fig.add_trace(go.Scatter(
            x=odometer_km,
            y=retention,
            mode='lines',
            name='Tesla Battery Retention',
            line=dict(color='rgba(0, 0, 255, 0.6)', width=5),
            hovertemplate='Tesla reference<br>Odometer: %{x:.0f} km<br>Retention: %{y:.2f}%<extra></extra>',
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
        """Create a horizontal bar chart."""
        fig = px.bar(
            df,
            x=x_column,
            y=y_column,
            orientation=orientation,
            labels={x_column: x_label, y_column: ''},
            color=x_column,
            color_continuous_scale='RdYlGn',
            text='custom_text',
        )

        fig.update_xaxes(autorange='reversed')
        fig.update_traces(
            textposition='inside',
            insidetextanchor='start',
            hovertemplate='<b>%{y}</b><br>Value: %{x:.2f}%<br>%{text}<extra></extra>',
        )

        for _, row in df.iterrows():
            fig.add_annotation(
                x=row[x_column],
                y=row[y_column],
                text=row['degradation_text'],
                showarrow=False,
                xshift=22,
            )

        fig.update_layout(yaxis_title=None, showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
        PlotBuilder._add_watermark(fig)
        return fig

    @staticmethod
    def create_performance_line_plot(
        plot_df: pd.DataFrame,
        x_label: str,
        y_label: str,
        color_map: Dict[str, str]
    ) -> go.Figure:
        """Create a line plot for performance data."""
        fig = go.Figure()

        for label in plot_df['Label'].unique():
            label_df = plot_df[plot_df['Label'] == label]
            if 'File' in label_df.columns:
                first_file = label_df['File'].iloc[0]
                for file_name in label_df['File'].unique():
                    file_df = label_df[label_df['File'] == file_name].sort_values('X')
                    fig.add_trace(go.Scatter(
                        x=file_df['X'],
                        y=file_df['Y'],
                        mode='lines',
                        name=label,
                        line=dict(color=color_map.get(label), width=3),
                        legendgroup=label,
                        showlegend=(file_name == first_file),
                        connectgaps=False,
                        customdata=np.array([[file_name]] * len(file_df)),
                        hovertemplate='Trace: %{name}<br>X: %{x:.2f}<br>Y: %{y:.2f}<br>File: %{customdata[0]}<extra></extra>',
                    ))
            else:
                label_df = label_df.sort_values('X')
                fig.add_trace(go.Scatter(
                    x=label_df['X'],
                    y=label_df['Y'],
                    mode='lines',
                    name=label,
                    line=dict(color=color_map.get(label), width=3),
                    connectgaps=False,
                ))

        fig.update_layout(
            showlegend=True,
            xaxis_title=x_label,
            yaxis_title=y_label,
            height=760,
            margin=dict(l=20, r=20, t=60, b=20),
            hovermode='x unified',
            legend=dict(
                orientation='h',
                yanchor='top',
                y=1.12,
                xanchor='center',
                x=0.5,
                title=None,
            )
        )

        PlotBuilder._add_watermark(fig, opacity=0.15)
        return fig

    @staticmethod
    def _linear_regression(X: np.ndarray, y: np.ndarray, x_min: float, x_max: float):
        """Perform linear regression."""
        lin_reg = LinearRegression()
        lin_reg.fit(X, y)
        x_range = np.linspace(x_min, x_max, 120).reshape(-1, 1)
        y_pred = lin_reg.predict(x_range)
        return x_range, y_pred

    @staticmethod
    def _logarithmic_regression(X: np.ndarray, y: np.ndarray, x_min: float, x_max: float):
        """Perform logarithmic regression."""
        X_log = np.log(X)
        log_reg = LinearRegression()
        log_reg.fit(X_log, y)
        x_range = np.linspace(x_min, x_max, 120)
        y_pred = log_reg.predict(np.log(x_range).reshape(-1, 1))
        return x_range, y_pred

    @staticmethod
    def _polynomial_regression(X: np.ndarray, y: np.ndarray, x_min: float, x_max: float):
        """Perform polynomial regression (3rd degree)."""
        poly = PolynomialFeatures(degree=3)
        X_poly = poly.fit_transform(X)
        poly_reg = LinearRegression()
        poly_reg.fit(X_poly, y)
        x_range = np.linspace(x_min, x_max, 120).reshape(-1, 1)
        y_pred = poly_reg.predict(poly.transform(x_range))
        return x_range, y_pred

    @staticmethod
    def _get_trace_color(fig: go.Figure, label: str, fallback_index: int) -> str:
        """Resolve the plotted color for a label."""
        for trace in fig.data:
            if trace.name == label:
                marker = getattr(trace, 'marker', None)
                if marker and getattr(marker, 'color', None):
                    return marker.color
                line = getattr(trace, 'line', None)
                if line and getattr(line, 'color', None):
                    return line.color
        return Config.COLOR_SEQUENCE[fallback_index % len(Config.COLOR_SEQUENCE)]

    @staticmethod
    def _add_watermark(fig: go.Figure, opacity: float = 0.05) -> None:
        """Add watermark to the plot."""
        fig.add_annotation(
            text='@eivissacopter',
            font=dict(size=20, color='lightgrey'),
            align='center',
            xref='paper',
            yref='paper',
            x=0.5,
            y=0.5,
            opacity=opacity,
            showarrow=False,
        )

    @staticmethod
    def _configure_legend(fig: go.Figure) -> None:
        """Configure legend appearance."""
        fig.update_layout(
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='left',
                x=0,
                title=None,
            )
        )
