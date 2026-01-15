"""
Controller for Tab 2: Probability Matrix.
Handles business logic for probability matrix generation.
"""

import pandas as pd
from probability_matrix import GetMatrix
from views.exporters import download_combined_excel
from utils.helpers import sanitize_sheet_name


def process_probability_matrix(enter_bps, enter_hrs, x, y, data_type, version_value):
    """
    Process probability matrix calculations.
    
    Args:
        enter_bps: Number of basis points to analyze
        enter_hrs: Number of hours for the analysis window
        x: Selected interval
        y: Selected instrument
        data_type: Type of data to use ('Non-Event' or 'All data')
        version_value: Version type ('Absolute', 'Up', 'Down', 'No-Version')
    
    Returns:
        dict with keys:
            - 'prob_matrix_dic': Full probability matrix dictionary from GetMatrix
            - 'version': The version value used
    """
    prob_matrix_dic = GetMatrix(
        enter_bps, int(enter_hrs), x, y, data_type, version=version_value
    )
    
    return {
        'prob_matrix_dic': prob_matrix_dic,
        'version': version_value,
    }


def get_probability_display_data(prob_matrix_dic, version, enter_bps, enter_hrs, mode):
    """
    Extract display-ready data from probability matrix results.
    
    Args:
        prob_matrix_dic: Result from process_probability_matrix
        version: Version type
        enter_bps: Basis points value
        enter_hrs: Hours value
        mode: Display mode ('open-close', 'open-high/low', 'high-low')
    
    Returns:
        dict with:
            - 'prob_df': DataFrame with probability summary
            - 'plot': Matplotlib figure for the mode
            - 'matrix_styled': Styled DataFrame for matrix display
            - 'movt_df': Latest movements DataFrame
    """
    v = version
    
    # Create probability summary DataFrame
    prob_df = pd.DataFrame(
        columns=['Description', 'Value'],
        data=[[
            f'Probability of bps ({v})  > {abs(enter_bps)} bps within {enter_hrs} hrs',
            f"{round(100.0 - round(prob_matrix_dic[v]['<=%'][mode], 2), 2)}%"
        ]]
    )
    prob_df.loc[len(prob_df)] = [
        f'Probability of bps ({v})  <= {abs(enter_bps)} bps within {enter_hrs} hrs',
        f"{round(prob_matrix_dic[v]['<=%'][mode], 2)}%"
    ]
    
    # Get the plot
    plot = prob_matrix_dic[v]["Plots"][mode]
    
    # Process matrix for display
    raw = prob_matrix_dic[v]['Returns_Matrix'][mode].copy()
    raw.columns = [f"{int(c)} hr" for c in raw.columns]
    raw.index = [f"{idx} bps" for idx in raw.index]
    
    # Get movement data
    movt_df = prob_matrix_dic[v]['Latest movt'][mode]
    movt_df = movt_df.sort_values(by='Bps moved', ascending=False)
    
    return {
        'prob_df': prob_df,
        'plot': plot,
        'matrix_raw': raw,
        'movt_df': movt_df,
    }


def prepare_matrix_download(prob_matrix_dic):
    """
    Prepare Excel file with all probability matrices for download.
    
    Args:
        prob_matrix_dic: Full probability matrix dictionary
    
    Returns:
        BytesIO: Excel file ready for download
    """
    my_matrix_list = []
    my_matrix_ver = []

    for ver in list(prob_matrix_dic.keys()):
        for mode in ['open-close', 'open-high/low', 'high-low']:
            my_matrix_list.append(prob_matrix_dic[ver]['Returns_Matrix'][mode])
            sheet_name = sanitize_sheet_name(f'{mode}: {ver}')
            my_matrix_ver.append(sheet_name)

    excel_file = download_combined_excel(
        df_list=my_matrix_list,
        sheet_names=my_matrix_ver,
        skip_index_sheet=[]
    )
    
    return excel_file, my_matrix_ver
