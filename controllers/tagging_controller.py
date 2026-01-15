"""
Controller for Tab 5: Non-Economic Event Tagging.
Handles business logic for event tagging operations.
"""

import os
import pandas as pd
from models.data_loader import get_price_movt
from views.formatters import convert_decimal_to_ticks, convert_ticks_to_decimal
from views.plotting import plot_data


# Default file path for tagged events
DEFAULT_FILE_PATH = "/mnt/non_eco_events/tagged_non_eco_events.csv"
# DEFAULT_FILE_PATH = "/Users/siddhartha/Desktop/CODES/FRGM Codes/test_tab_5.csv"

# Available tags
TAGS = ['Market Shift', 'Geo', 'Tariff', 'Positioning', 'Election']


def load_tagged_events(file_path=DEFAULT_FILE_PATH):
    """
    Load existing tagged events from CSV file.
    
    Args:
        file_path: Path to the CSV file
    
    Returns:
        DataFrame: Tagged events data (timestamps stored as tz-aware strings)
    """
    if os.path.exists(file_path):
        # Keep Start_Date and End_Date as strings (stored with offset, e.g., "2025-11-04 00:00:00-05:00")
        data = pd.read_csv(file_path)
    else:
        data = pd.DataFrame(columns=[
            'Event', 'Tag', 'Comments', 'Start_Date', 'End_Date',
            'Open', 'High', 'Close', 'Low', 'Name'
        ])
    return data


def add_tagged_event(data, event_info, file_path=DEFAULT_FILE_PATH):
    """
    Add a new tagged event to the data.
    
    Args:
        data: Existing DataFrame
        event_info: Dict with event details
        file_path: Path to save the CSV
    
    Returns:
        DataFrame: Updated data
    """
    new_row = pd.DataFrame([{
        "Event": event_info['event'],
        "Tag": event_info['tag'],
        "Comments": event_info['comment'],
        "Start_Date": event_info['start_timestamp'],
        "End_Date": event_info['end_timestamp'],
        "Open": event_info['open'],
        "High": event_info['high'],
        "Close": event_info['close'],
        "Low": event_info['low'],
        "Name": event_info['name']
    }])
    
    data = pd.concat([data, new_row], ignore_index=True)
    data = data.sort_values(by='Tag').reset_index(drop=True)
    data.to_csv(file_path, index=False)
    
    return data


def delete_tagged_event(data, event_info, file_path=DEFAULT_FILE_PATH):
    """
    Delete a tagged event from the data.
    
    Args:
        data: Existing DataFrame
        event_info: Dict with event details to match
        file_path: Path to save the CSV
    
    Returns:
        DataFrame: Updated data
    """
    data = data[
        ~(
            (data['Event'] == event_info['event']) &
            (data['Tag'] == event_info['tag']) &
            (data['Comments'] == event_info['comment']) &
            (data['Start_Date'] == event_info['start_timestamp']) &
            (data['End_Date'] == event_info['end_timestamp']) &
            (data['Name'] == event_info['name'])
        )
    ]
    data.to_csv(file_path, index=False)
    
    return data


def get_price_data_for_event(start_timestamp, end_timestamp, x, y, folder='Intraday_data_files_pq'):
    """
    Get OHLC price data for a specific time range.
    
    Args:
        start_timestamp: Start timestamp (timezone-aware)
        end_timestamp: End timestamp (timezone-aware)
        x: Interval
        y: Instrument
        folder: Data folder
    
    Returns:
        dict with 'open', 'high', 'close', 'low' as formatted tick strings
    """
    ohcl = get_price_movt(start_timestamp, end_timestamp, x, y, folder)
    
    return {
        'open': convert_decimal_to_ticks(ohcl[0]),
        'high': convert_decimal_to_ticks(ohcl[1]),
        'close': convert_decimal_to_ticks(ohcl[2]),
        'low': convert_decimal_to_ticks(ohcl[3]),
    }


def filter_by_tag(data, selected_tag):
    """
    Filter tagged events by a specific tag and calculate returns.
    
    Args:
        data: Tagged events DataFrame
        selected_tag: Tag to filter by
    
    Returns:
        dict with 'filtered_df' and 'plots' (if data available)
    """
    filter_df = data[data['Tag'] == selected_tag].copy()
    
    if filter_df.empty:
        return {'filtered_df': filter_df, 'plots': None}
    
    # Convert prices back to decimal for calculations
    for col in ['Open', 'High', 'Low', 'Close']:
        filter_df[col] = filter_df[col].apply(convert_ticks_to_decimal)
    
    # Calculate returns
    filter_df['Abs Returns'] = abs((filter_df['Close']) - (filter_df['Open'])) * 16
    filter_df['Returns'] = (filter_df['Close'] - filter_df['Open']) * 16
    filter_df['Vol Returns'] = ((filter_df['High']) - (filter_df['Low'])) * 16
    filter_df['Open-High/Low'] = (pd.DataFrame({
        'A': (filter_df['Open'] - filter_df['Low']),
        'B': (filter_df['High'] - filter_df['Open'])
    }).max(axis=1)) * 16
    
    # Generate plots
    plots_dict = plot_data(filter_df, ['Abs Returns', 'Returns', 'Vol Returns', 'Open-High/Low'])
    
    return {
        'filtered_df': filter_df,
        'plots': plots_dict,
    }


