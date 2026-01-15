"""
Event processing functions for DistroDashboard.
Functions moved here from core/event_filters.py.
"""

import pandas as pd
from pandas.tseries.offsets import MonthEnd


# =============================================================================
# Event timestamp helper
# =============================================================================

#5.1.2 helper function for 5.1
def add_start_end_ts(all_event_ts , delta1 , delta2):

    if(delta1 < 0):  # pre event + custom with delta < 0

        all_event_ts['end'] = all_event_ts['datetime'].apply(lambda x: x.replace(minute=0, second=0, microsecond=0)) 
        all_event_ts['start'] = all_event_ts['end'] + pd.Timedelta(hours = delta1)
        all_event_ts['end'] = all_event_ts['end'] + pd.Timedelta(hours = delta2)

    else:   # immediate reaction + custom with delta > 0

        all_event_ts['start'] = all_event_ts['datetime'].apply(lambda x: x.replace(minute=0, second=0, microsecond=0))
        all_event_ts['end'] = all_event_ts['start'] + pd.Timedelta(hours = delta1)
        all_event_ts['start'] = all_event_ts['start'] + pd.Timedelta(hours = delta2)
    
    return all_event_ts


# =============================================================================
# Event filtering logic
# =============================================================================

#5.1.3 helper function for 5.1 (isolates / groups events as per requirement)
def filter_event_df(event_ts, selected_event, sub_event_dic, window_size,
                    isolate_event=False, filter_tier_list=[],
                    group_events=False, selected_group_event=""):

    df = event_ts.copy()

    # Cleaned event labels
    df["cleaned_events"] = df["events"].astype(str).str.strip().str.lower().str.replace(" ", "")

    # Sub-events for the selected event
    sub_events_cleaned = [s.strip().lower().replace(" ", "") for s in sub_event_dic[selected_event]]

    # Keep only rows that are part of the selected sub-event set
    mask_selected = df["cleaned_events"].str.startswith(tuple(sub_events_cleaned))
    df_selected = df[mask_selected].copy()
    print("LEN df_selected: " , len(df_selected))
    if df_selected.empty:
        return pd.DataFrame()

    # Prepare time window boundaries
    df_selected["t_minus"] = df_selected["datetime"] - pd.Timedelta(hours=window_size)
    df_selected["t_plus"] = df_selected["datetime"] + pd.Timedelta(hours=window_size)

    # Merge with all events to see what's in each window
    merged = df_selected.merge(
            df[["datetime", "cleaned_events", "tier"]],
            how="cross",
            suffixes=("", "_nearby")
        )

    # Check if nearby event falls into the window
    cond_in_window = (merged["datetime_nearby"] >= merged["t_minus"]) & (merged["datetime_nearby"] <= merged["t_plus"])
    merged = merged[cond_in_window]

    print("LEN merged: " , len(merged))

    # Logic for filtering
    include_mask = pd.Series(True, index=merged.index)

    if isolate_event:
        # Exclude if any unwanted tier appears nearby
        bad_mask = merged["tier"].isin(filter_tier_list)
        # mark those selected events as False
        bad_ids = merged.loc[bad_mask, "datetime"].unique()
        include_mask &= ~merged["datetime"].isin(bad_ids)

    elif group_events:
        # Require presence of chosen sub-event in the window
        specific_sub_events = [s.strip().lower().replace(" ", "") for s in sub_event_dic[selected_group_event]]
        has_required = merged["cleaned_events_nearby"].str.startswith(tuple(specific_sub_events))
        good_ids = merged.loc[has_required, "datetime"].unique()
        include_mask &= merged["datetime"].isin(good_ids)

    # Final filtered set
    filtered_times = merged.loc[include_mask, "datetime"].unique()
    filtered_df = df[df["datetime"].isin(filtered_times)]
                        
    return filtered_df


# =============================================================================
# Month-end filtering
# =============================================================================

# 5.4 for month-end filtering
def month_end_filtering(num_days , ohcl_data):
    return_df = pd.DataFrame()

    df = ohcl_data.copy()
    df["month_end"] = (df["US/Eastern Timezone"] + MonthEnd(0)).dt.normalize()
    mask = (df["month_end"].dt.normalize() - df["US/Eastern Timezone"].dt.normalize()) <= pd.Timedelta(days=num_days-1)
    df_month_end = df[mask]
    
    vol_ret = []
    abs_ret = []
    ret = []
    start_date = []
    end_date = []
    start_price = []
    end_price = []
    high = []
    low = []


    for _, g in df_month_end.groupby(df_month_end['month_end']):
        open_price = g['Open'].iloc[0]
        close_price = g['Close'].iloc[-1]
        maxi = g['High'].max()
        mini = g['Low'].min()
        vol_ret.append((maxi-mini)*16)
        abs_ret.append(abs(close_price-open_price) * 16)
        ret.append((close_price-open_price) * 16)
        start_date.append(g['US/Eastern Timezone'].iloc[0])
        end_date.append(g['US/Eastern Timezone'].iloc[-1])
        start_price.append(open_price)
        end_price.append(close_price)
        high.append(maxi)
        low.append(mini)
    
    return_df['Volatility Return'] = vol_ret
    return_df['Absolute Return'] = abs_ret
    return_df['Return'] = ret
    return_df['Start_Date'] = start_date
    return_df['End_Date'] = end_date
    return_df['Entry_Price'] = start_price
    return_df['Exit_Price'] = end_price
    return_df['High'] = high
    return_df['Low'] = low

    return return_df


