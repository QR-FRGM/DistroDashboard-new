"""
Controller for Tab 3: Custom Normalised Returns.
Handles business logic for custom filtering and analysis.
"""

import pandas as pd
import datetime
import custom_filtering_dataframe
from views.exporters import download_combined_excel


def get_filtered_dataframe(x, y, folder='Intraday_data_files_pq'):
    """
    Get the base dataframe for the selected interval and instrument.
    
    Args:
        x: Selected interval
        y: Selected instrument
        folder: Data folder path
    
    Returns:
        DataFrame: Raw data for the instrument/interval
    """
    return custom_filtering_dataframe.get_dataframe(x, y, folder)


def calculate_time_difference(start_date, start_time, end_date, end_time):
    """
    Calculate time difference between two datetime points.
    
    Args:
        start_date: Start date
        start_time: Start time
        end_date: End date
        end_time: End time
    
    Returns:
        dict with 'hours', 'minutes', 'approx_hours', 'approx_minutes'
    """
    start_datetime = datetime.datetime.combine(start_date, start_time)
    end_datetime = datetime.datetime.combine(end_date, end_time)
    
    time_diff = end_datetime - start_datetime
    hours, remainder = divmod(time_diff.total_seconds(), 3600)
    minutes = remainder / 60
    
    return {
        'hours': int(hours),
        'minutes': int(minutes),
        'approx_hours': round(hours + minutes/60, 1),
        'approx_minutes': int(hours * 60 + minutes),
        'display_text1': f"Time Difference: {int(hours)} hours and {int(minutes)} minutes",
        'display_text2': f"Approx Difference (Hrs): {round(hours + minutes/60, 1)} hours",
        'display_text3': f"Approx Difference (Mins): {int(hours * 60 + minutes)} minutes",
    }


def process_custom_filter(selected_df, filter_sessions, x, y, version_value, enter_bps, target_column):
    """
    Process custom filtering and calculate statistics.
    
    Args:
        selected_df: Base DataFrame
        filter_sessions: Filter configuration list or empty
        x: Interval
        y: Instrument
        version_value: Version type ('Absolute', 'Up', 'Down', 'No-Version')
        enter_bps: Basis points value to analyze
        target_column: Column to use for grouping
    
    Returns:
        dict with 'filtered_df', 'stats_plots_dict', 'date_range'
    """
    # Prepare the dataframe
    finalcsv = selected_df.copy()
    finalcsv.index = finalcsv[finalcsv.columns[-1]]
    finalcsv.drop_duplicates(inplace=True)
    finalcsv.dropna(inplace=True, how='all')
    finalcsv.sort_index(inplace=True)
    finalcsv = finalcsv.loc[~finalcsv.index.duplicated(keep='last')]
    
    finalstart = str(finalcsv.index.to_list()[0])[:10]
    finalend = str(finalcsv.index.to_list()[-1])[:10]
    
    if filter_sessions:
        # Filter the dataframe as per selections
        filtered_df = custom_filtering_dataframe.filter_dataframe(
            selected_df,
            filter_sessions,
            day_dict="",
            timezone_column='US/Eastern Timezone',
            target_timezone='US/Eastern',
            interval=x,
            ticker=y
        )
        actual_target_column = 'Group'
    else:
        filtered_df = custom_filtering_dataframe.filter_dataframe(
            selected_df,
            "",
            "",
            'US/Eastern Timezone',
            'US/Eastern',
            x,
            y
        )
        actual_target_column = target_column
    
    if filtered_df.empty:
        return {
            'filtered_df': filtered_df,
            'stats_plots_dict': None,
            'date_range': {'start': finalstart, 'end': finalend},
            'error': 'Empty filtered dataframe'
        }
    
    # Generate name for the analysis
    default_text = f'Distribution of bps ({version_value}) Returns {y} with returns calculated for every {x}'
    if filter_sessions:
        mysession = f'{filter_sessions[0][2]} {filter_sessions[0][0]} ET to {filter_sessions[0][0]} ET+{filter_sessions[0][1]}{x[-1]}'
        finalname = f'{default_text} for session:{mysession} for dates:{finalstart} to {finalend}'
    else:
        finalname = f'{default_text} for dates:{finalstart} to {finalend}'
    
    # Calculate stats and plots
    stats_plots_dict = custom_filtering_dataframe.calculate_stats_and_plots(
        filtered_df,
        finalname,
        version=version_value,
        check_movement=enter_bps,
        interval=x,
        ticker=y,
        target_column=actual_target_column
    )
    
    return {
        'filtered_df': filtered_df,
        'stats_plots_dict': stats_plots_dict,
        'date_range': {'start': finalstart, 'end': finalend},
        'name': finalname,
        'error': None
    }


def prepare_custom_filter_download(filtered_df, prob_df, stats_df, x, y, date_range):
    """
    Prepare Excel file for download.
    
    Args:
        filtered_df: Filtered DataFrame
        prob_df: Probability DataFrame
        stats_df: Statistics DataFrame
        x: Interval
        y: Instrument
        date_range: Dict with 'start' and 'end'
    
    Returns:
        BytesIO: Excel file ready for download
    """
    # Convert datetime columns to strings for Excel compatibility
    df_for_download = filtered_df.copy()
    if 'US/Eastern Timezone' in df_for_download.columns:
        df_for_download['US/Eastern Timezone'] = df_for_download['US/Eastern Timezone'].dt.tz_localize(None).astype(str)
    if 'Group' in df_for_download.columns:
        df_for_download['Group'] = df_for_download['Group'].dt.tz_localize(None).astype(str)
    
    my_matrix_list = [df_for_download, prob_df, stats_df]
    my_matrix_ver = [
        f'{x}_{y}_{date_range["start"]} to {date_range["end"]}',
        'Probability',
        'Descriptive Statistics'
    ]
    
    excel_file = download_combined_excel(
        df_list=my_matrix_list,
        sheet_names=my_matrix_ver,
        skip_index_sheet=[]
    )
    
    return excel_file


