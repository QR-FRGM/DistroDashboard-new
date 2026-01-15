"""
Plotting utility functions for DistroDashboard.
Plotly implementation for use with Dash (migrated from matplotlib).
"""

import numpy as np
import plotly.graph_objects as go
from scipy.stats import gaussian_kde, percentileofscore


def plot_data(final_df, required_columns, graph_type='pdf', bool_hist=True, bool_custom_value=False, custom_value=0.0, bin_size = 1):
    """
    Generate Plotly distribution plots for specified columns.
    
    Args:
        final_df: DataFrame containing the data with 'Start_Date' column
        required_columns: List of column names to plot
        graph_type: 'pdf' for probability density or 'cdf' for cumulative distribution
        bool_hist: If True, show histogram with bin edge labels. If False, only show KDE/CDF curve.
        bool_custom_value: If True, use custom_value for the "current value" marker
        custom_value: Custom value to use if bool_custom_value is True
        
    Returns:
        dict: Dictionary mapping column names to Plotly Figure objects
    """
    figures = {}

    for col in required_columns:
        data = final_df[col].dropna()

        traces = []
        bin_edges = None  # Will be set only if bool_hist is True
        
        if bool_hist:
            # Match matplotlib binning: fixed bin width of 1
            min_value = int(data.min() // 1)
            max_value = int(np.ceil(data.max()))
            bin_edges = np.arange(min_value, max_value + bin_size + 1, bin_size)  # +2 to include right edge
            bin_size = bin_size

            hist = go.Histogram(
                x=data,
                histnorm='probability density',
                opacity=0.6,
                name='Histogram',
                marker=dict(color='skyblue', line=dict(color='black', width=1)),
                xbins=dict(
                    start=min_value,
                    end=max_value + 1,
                    size=bin_size
                )
            )
            traces.append(hist)

        if graph_type == 'pdf':
            kde = gaussian_kde(data)
            x_grid = np.linspace(data.min(), data.max(), 300)
            kde_trace = go.Scatter(
                x=x_grid,
                y=kde(x_grid),
                mode='lines',
                name='KDE',
                line=dict(color='darkblue', width=2)
            )
            traces.append(kde_trace)

        elif graph_type == 'cdf':
            kde = gaussian_kde(data)
            x_grid = np.linspace(data.min(), data.max(), 300)
            # Compute CDF by integrating KDE
            cdf_values = np.array([kde.integrate_box_1d(data.min(), x) for x in x_grid])
            cdf_trace = go.Scatter(
                x=x_grid,
                y=cdf_values,
                mode='lines',
                name='CDF',
                line=dict(color='green', width=2)
            )
            traces.append(cdf_trace)


        stats = data.describe()
        mean = stats['mean']
        std = stats['std']
        skew = final_df[col].skew()
        count = len(final_df[col])

        if bool_custom_value:
            current_value = custom_value
        else:
            current_value = data.iloc[-1]

        zscore = (current_value - mean) / std if std != 0 else 0
        percentile = percentileofscore(data, current_value, kind="rank").round(2)

        # Calculate appropriate y-values for red line and dot based on graph type
        if graph_type == 'cdf':
            # For CDF, position on the CDF curve
            cdf_at_current = kde.integrate_box_1d(data.min(), current_value)
            red_line_y_max = cdf_at_current
            red_dot_y = cdf_at_current
        else:
            # For PDF, position on the KDE curve
            red_line_y_max = kde(current_value).max()
            red_dot_y = kde(current_value).max()

        red_line = go.Scatter(
            x=[current_value, current_value],
            y=[0, red_line_y_max],
            mode='lines',
            line=dict(color='red', dash='dot'),
            name='Current Value'
        )

        red_dot = go.Scatter(
            x=[current_value],
            y=[red_dot_y],
            mode='markers',
            marker=dict(color='red', size=10),
            name='Current Point',
            showlegend=False
        )

        traces.append(red_dot)
        traces.append(red_line)

        stats_box = (
            f"Count: {count}<br>"
            f"Mean: {mean:.2f}<br>"
            f"Std: {std:.2f}<br>"
            f"Min: {stats['min']:.2f}<br>"
            f"25%: {stats['25%']:.2f}<br>"
            f"Median: {stats['50%']:.2f}<br>"
            f"75%: {stats['75%']:.2f}<br>"
            f"95%: {data.quantile(0.95):.2f}<br>"
            f"99%: {data.quantile(0.99):.2f}<br>"
            f"Max: {stats['max']:.2f}<br>"
            f"Skew: {skew:.2f}"
        )

        fig = go.Figure(data=traces)

        fig.add_annotation(
            xref="paper", yref="paper",
            x=1.02, y=0.75,  # Right side, below legend
            xanchor="left",
            yanchor="top",
            text=stats_box,
            showarrow=False,
            align="left",
            bordercolor="black",
            borderwidth=1,
            bgcolor="white",
            opacity=0.9,
            font=dict(size=12)
        )

        has_start_date = 'Start_Date' in final_df.columns
        current_date = final_df['Start_Date'].iloc[-1] if has_start_date else "N/A"

        # Current value box - positioned below stats box
        current_value_box = (
            f"<b>Latest Data Point</b><br>"
            f"Date: {current_date}<br>"
            f"Value: {current_value:.2f}<br>"
            f"Z-Score: {zscore:.2f}<br>"
            f"Percentile: {percentile}%"
        )

        fig.add_annotation(
            xref="paper", yref="paper",
            x=1.02, y=0.25,  # Below stats box
            xanchor="left",
            yanchor="top",
            text=current_value_box,
            showarrow=False,
            align="left",
            bordercolor="red",
            borderwidth=1,
            bgcolor="white",
            opacity=0.9,
            font=dict(size=12)
        )

        # ============================================================
        # BIN EDGE LABELLING - Only if histogram is shown
        # ============================================================
        if bool_hist and bin_edges is not None:
            tick_vals = list(bin_edges)
            tick_text = [f"{edge:.1f}" for edge in bin_edges]
            
            fig.update_layout(
                title=col,
                xaxis=dict(
                    title="Value",
                    tickmode='array',
                    tickvals=tick_vals,
                    ticktext=tick_text,
                    tickangle=45,
                    tickfont=dict(size=10),
                    dtick=1,
                ),
                yaxis_title="Density",
                barmode='overlay',
                height=600,
                template="plotly_white",
                legend=dict(
                    x=1.02,
                    y=1,
                    xanchor="left",
                    yanchor="top",
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="black",
                    borderwidth=1
                ),
                margin=dict(r=180)
            )
        else:
            # Simplified layout without bin edge labels
            fig.update_layout(
                title=col,
                xaxis_title="Value",
                yaxis_title="Density",
                height=600,
                template="plotly_white",
                legend=dict(
                    x=1.02,
                    y=1,
                    xanchor="left",
                    yanchor="top",
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="black",
                    borderwidth=1
                ),
                margin=dict(r=180)
            )

        figures[col] = fig

    return figures
