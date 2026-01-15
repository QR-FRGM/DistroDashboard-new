"""
Table building functions for DistroDashboard.
Functions moved here from core/utils.py.
"""

import pandas as pd
from .formatters import convert_decimal_to_ticks

# used for generating the pivot tables.    
def get_pivot_tables(final_df , custom_percentiles , required_columns , latest_close_price):
    my_df_list = []
    for col_name in required_columns:
        pct_values = final_df[col_name].quantile(custom_percentiles)

        df = pd.DataFrame({
            "Percentile": [f"{p*100:.2f}%" for p in pct_values.index],
            "Upside": [convert_decimal_to_ticks(v/16 + latest_close_price) for v in pct_values.values],
            "Downside": [convert_decimal_to_ticks(latest_close_price - v/16) for v in pct_values.values]
        })

        my_df_list.append(df)
    return my_df_list


