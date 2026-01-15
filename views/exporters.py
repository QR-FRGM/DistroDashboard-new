"""
Export functions for DistroDashboard.
Functions moved here from core/utils.py.
"""

from io import BytesIO
import pandas as pd

# Defining function to download the data
def download_combined_excel(df_list, sheet_names, skip_index_sheet=[]):
    output = BytesIO()
 
    # Use xlsxwriter for styling
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        highlight_format = workbook.add_format({'bg_color': '#FFFF00', 'bold': True})

        for sheetname, df in zip(sheet_names, df_list):
            df.to_excel(writer, sheet_name=sheetname, index=(sheetname not in skip_index_sheet))
            worksheet = writer.sheets[sheetname]
            last_excel_row = len(df)
            worksheet.set_row(last_excel_row, None, highlight_format)

    output.seek(0)
    return output
