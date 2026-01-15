"""
Controller for Tab 1: Session and Volatility Returns for all sessions.
Handles business logic and data processing for session analysis.
"""

import pandas as pd
from models.data_loader import get_data
from views.plotting import plot_data
from views.formatters import convert_decimal_to_ticks
from views.table_builders import get_pivot_tables
from views.exporters import download_combined_excel


def process_session_analysis(x, y, selected_sessions, last_x_obs=None, custom_pivot_price=None):
    """
    Process session analysis data and generate results.
    
    Args:
        x: Selected interval (e.g., '1h', '1m')
        y: Selected instrument (e.g., 'ZN', 'ZB')
        selected_sessions: List of selected trading sessions
        last_x_obs: Number of recent observations to analyze (optional)
        custom_pivot_price: Custom pivot price for tables (optional)
    
    Returns:
        dict with keys:
            - 'final_df': Processed DataFrame with returns
            - 'fig_dict': Dictionary of matplotlib figures
            - 'pivot_tables': List of pivot table DataFrames
            - 'metadata': Dict with latest_close_price, pivot_price, date_range, etc.
            - 'download_data': BytesIO Excel file for download
    """
    # Load data
    intraday_data = get_data('Intraday_data_files_processed_folder_pq', [x, y, 'nonevents'], '.parquet')
    intraday_data = intraday_data[['timestamp', 'session', 'Adj Close', 'Close', 'High', 'Low', 'Open', 'Volume', 'US/Eastern Timezone']]

    # Get latest price for pivot
    price_data_1m = get_data('Intraday_data_files_pq', ['1m', y], '.parquet')
    latest_close_price = price_data_1m['Close'].iloc[-1]
    latest_price_timestamp = price_data_1m['US/Eastern Timezone'].iloc[-1]

    # Determine pivot price
    pivot_price = custom_pivot_price if custom_pivot_price else latest_close_price

    # Filter by selected sessions
    filtered_intraday_data = intraday_data[intraday_data['session'].isin(selected_sessions)]
    filtered_intraday_data['date'] = filtered_intraday_data['US/Eastern Timezone'].dt.date

    # Aggregate by date
    final_df = (
        filtered_intraday_data
        .groupby('date')
        .agg(
            open_price=('Open', 'first'),
            close_price=('Close', 'last'),
            high_price=('High', 'max'),
            low_price=('Low', 'min')
        )
    )

    # Calculate returns
    final_df['Return'] = (final_df['close_price'] - final_df['open_price']) * 16
    final_df['Volatility Return'] = (final_df['high_price'] - final_df['low_price']) * 16
    final_df['Absolute Return'] = ((final_df['close_price'] - final_df['open_price']).abs()) * 16
    final_df = final_df.reset_index()

    # Apply last_x_obs filter if specified
    if last_x_obs:
        final_df = final_df.tail(last_x_obs)

    # Prepare for plotting
    final_df['Start_Date'] = final_df['date']
    
    # Generate plots
    fig_dict = plot_data(final_df, ['Absolute Return', 'Return', 'Volatility Return'])

    # Generate pivot tables
    custom_percentiles = [
        0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90,
        0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99,
        0.995, 0.996, 0.997, 0.998, 0.999, 1
    ]
    required_columns = ['Absolute Return', 'Return', 'Volatility Return']
    pivot_tables = get_pivot_tables(final_df, custom_percentiles, required_columns, pivot_price)

    # Prepare download data
    download_data = download_combined_excel([final_df], ["Session wise analysis"])

    # Compile metadata
    metadata = {
        'latest_close_price': latest_close_price,
        'latest_close_price_formatted': convert_decimal_to_ticks(latest_close_price),
        'latest_price_timestamp': latest_price_timestamp,
        'pivot_price': pivot_price,
        'pivot_price_formatted': convert_decimal_to_ticks(pivot_price),
        'date_start': final_df['date'].iloc[0],
        'date_end': final_df['date'].iloc[-1],
        'total_instances': len(final_df),
    }

    return {
        'final_df': final_df,
        'fig_dict': fig_dict,
        'pivot_tables': pivot_tables,
        'metadata': metadata,
        'download_data': download_data,
    }


