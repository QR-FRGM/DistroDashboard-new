"""
Controller for Tab 4: Event Specific Distro.
Handles business logic for event-specific distribution analysis.
"""

import re
import pandas as pd
from models.data_loader import get_data
from models.event_returns import calc_event_spec_returns
from models.event_processor import month_end_filtering
from models.constants import PERCENTAGE_EVENTS
from views.plotting import plot_data
from views.formatters import convert_decimal_to_ticks, convert_ticks_to_decimal
from views.table_builders import get_pivot_tables
from views.exporters import download_combined_excel
from utils.helpers import clean_text


def load_event_data(x, y):
    """
    Load and prepare event and OHLC data.
    
    Args:
        x: Selected interval
        y: Selected instrument
    
    Returns:
        dict with 'all_event_ts', 'ohcl_data', 'price_data_1m', 'latest_close_price'
    """
    # Load event timestamps
    all_event_ts = get_data("Intraday_data_files_processed_folder_pq", ['EconomicEventsSheet', 'target'], ".csv")
    
    # Clean event text
    all_event_ts['events'] = all_event_ts['events'].astype(str).apply(clean_text)
    
    # Group to get latest values for each event-datetime combo
    all_event_ts = (
        all_event_ts
        .sort_values(["datetime", "events"])
        .groupby(["datetime", "events"], as_index=False)
        .last()
    )
    
    # Handle percentage events scaling
    normalized = [re.escape(e.strip().lower().replace(" ", "")) for e in PERCENTAGE_EVENTS]
    pattern = r'^(?:' + '|'.join(normalized) + ')'
    event_clean = all_event_ts['events'].astype(str).str.strip().str.lower().str.replace(" ", "", regex=False)
    mask = event_clean.str.match(pattern, na=False)
    cols_to_scale = ['actual', 'consensus', 'forecast']
    all_event_ts.loc[mask, cols_to_scale] = all_event_ts.loc[mask, cols_to_scale].mul(100)
    
    # Load OHLC data
    ohcl_data = get_data("Intraday_data_files_pq", [x, y], ".parquet")
    
    # Convert timezone
    ohcl_data['US/Eastern Timezone'] = pd.to_datetime(ohcl_data.index, errors='coerce', utc=True)
    all_event_ts['datetime'] = pd.to_datetime(all_event_ts['datetime'], errors='coerce', utc=True)
    
    ohcl_data['US/Eastern Timezone'] = ohcl_data['US/Eastern Timezone'].dt.tz_convert('US/Eastern')
    all_event_ts['datetime'] = all_event_ts['datetime'].dt.tz_convert('US/Eastern')
    
    # Load 1m price data for latest price
    price_data_1m = get_data("Intraday_data_files_pq", [y, '1m'], ".parquet")
    latest_close_price = price_data_1m['Close'].iloc[-1]
    
    return {
        'all_event_ts': all_event_ts,
        'ohcl_data': ohcl_data,
        'price_data_1m': price_data_1m,
        'latest_close_price': latest_close_price,
    }


def process_event_distro(
    selected_event,
    all_event_ts,
    ohcl_data,
    sub_event_dict,
    delta1=1,
    delta2=0,
    filter_isolated=False,
    window_hrs=0,
    filter_tier_list=None,
    group_events=False,
    selected_group_event="",
    sub_event_filter=False,
    sub_event_filtering_dict=None,
    last_x_obs=None,
    month_end_days=None,
    latest_close_price=None,
    bin_size = 1,
    remove_outliers_bool = False
):
    """
    Process event-specific distribution analysis.
    
    Args:
        selected_event: The event to analyze
        all_event_ts: Event timestamps DataFrame
        ohcl_data: OHLC price data
        sub_event_dict: Dictionary of sub-events for each event
        delta1: Total hours to analyze
        delta2: Hours to omit before/after event
        filter_isolated: Whether to isolate events
        window_hrs: Window hours for filtering
        filter_tier_list: Tiers to filter
        group_events: Whether to group events
        selected_group_event: Event to group with
        sub_event_filter: Whether to apply sub-event filtering
        sub_event_filtering_dict: Sub-event filter bounds
        last_x_obs: Limit to last x observations
        month_end_days: Days for month-end analysis (if month end selected)
        latest_close_price: Latest close price for pivot tables
    
    Returns:
        dict with analysis results or error message
    """
    if filter_tier_list is None:
        filter_tier_list = []
    if sub_event_filtering_dict is None:
        sub_event_filtering_dict = {}
    
    # Check for conflicting options
    if group_events and filter_isolated:
        return {
            'error': "Please select either isolation or grouping. Both can't be selected together.",
            'final_df': pd.DataFrame(),
        }
    
    # Handle month-end separately
    if selected_event == 'Month End':
        final_df = month_end_filtering(month_end_days, ohcl_data)
        sub_event_deviation = None
        message = None
    else:
        result = calc_event_spec_returns(
            selected_event,
            all_event_ts,
            ohcl_data,
            delta1,
            delta2,
            filter_isolated,
            window_hrs,
            group_events,
            selected_group_event,
            sub_event_filter,
            sub_event_filtering_dict,
            sub_event_dict,
            last_x_obs,
            filter_tier_list
        )
        
        # Handle the 3-tuple return (final_df, sub_event_deviation, message)
        if len(result) == 3:
            final_df, sub_event_deviation, message = result
        else:
            final_df, sub_event_deviation = result
            message = None
    
    if message:
        return {'error': message, 'final_df': pd.DataFrame()}
    
    if final_df.empty or len(final_df) == 0:
        return {'error': "No data available for the specified filters", 'final_df': pd.DataFrame()}
    
    if(remove_outliers_bool):
        final_df , outlier_info = filter_outliers(final_df , ['Absolute Return', 'Return', 'Volatility Return'])
    
    print("LEN final_df:", len(final_df))
    
    # Generate plots for price moves
    fig_dict = plot_data(final_df, ['Absolute Return', 'Return', 'Volatility Return'] , bin_size = bin_size)
    
    # Generate deviation distribution plots for sub-events
    deviation_distro_dict = {}
    if selected_event != 'Month End' and sub_event_deviation is not None:
        for event in sub_event_dict[selected_event]:
            mask = sub_event_deviation['cleaned_events'].str.startswith(event.strip().lower().replace(" ", ""))
            temp_df = sub_event_deviation[mask].copy()
            temp_df.dropna(subset=['deviation'], inplace=True)
            if not temp_df.empty:
                print(temp_df.head())
                # Use bool_hist=False to skip histogram and bin labels (prevents hanging on large ranges)
                graph_dict = plot_data(temp_df, ['deviation'], bool_hist=False)
                deviation_distro_dict[event] = graph_dict['deviation']
    
    # Generate pivot tables
    custom_percentiles = [
        0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90,
        0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99,
        0.995, 0.996, 0.997, 0.998, 0.999, 1
    ]
    required_columns = ['Absolute Return', 'Return', 'Volatility Return']
    pivot_tables = get_pivot_tables(final_df, custom_percentiles, required_columns, latest_close_price)
    
    return {
        'final_df': final_df,
        'sub_event_deviation': sub_event_deviation,
        'fig_dict': fig_dict,
        'deviation_distro_dict': deviation_distro_dict,
        'pivot_tables': pivot_tables,
        'latest_close_price_formatted': convert_decimal_to_ticks(latest_close_price),
        'error': None,
    }

def filter_outliers(final_df , required_columns):
    for col in required_columns:
        temp_df = final_df[col]
        



def prepare_event_distro_download(final_df):
    """
    Prepare event distribution data for download.
    
    Args:
        final_df: Final DataFrame with returns
    
    Returns:
        BytesIO: Excel file ready for download
    """
    df_for_download = final_df.copy()
    df_for_download['Start_Date'] = df_for_download['Start_Date'].dt.tz_localize(None).astype(str)
    df_for_download['End_Date'] = df_for_download['End_Date'].dt.tz_localize(None).astype(str)
    
    return download_combined_excel(df_list=[df_for_download], sheet_names=['Price Movt'])


