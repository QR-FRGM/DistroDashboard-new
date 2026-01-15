"""
Event-specific returns calculation for DistroDashboard.
Moved from streamlit_app.py calc_event_spec_returns() function.
"""

import re
import pandas as pd
import numpy as np
from models.event_processor import add_start_end_ts, filter_event_df


def calc_event_spec_returns(
    selected_event,
    all_event_ts,
    ohcl_1h,
    delta1=1,
    delta2=0,
    filter_out_other_events=False,
    window_size=2,
    group_events=False,
    selected_group_event="",
    sub_event_filter=False,
    sub_event_filtering_dict={},
    sub_event_dict={},
    last_x_obs=None,
    filter_tier_list=[]
):
    """
    Computes event-specific returns from OHLC data based on economic event filters and sub-event conditions.
    
    Returns:
        tuple: (final_df, sub_event_deviation) or (pd.DataFrame(), None) if no data
        Also returns a message string if there's an issue (can be displayed by UI)
    """
    
    # --- EVENT PREPROCESSING ---
    event_ts = all_event_ts.copy()
    event_ts["events"] = event_ts["events"].astype(str)
    event_ts = event_ts.dropna(subset=["events"])
    event_ts = event_ts.drop_duplicates(subset=["datetime", "events"], keep="last")

    cutoff_time = pd.to_datetime("2022-12-20 00:00:00-05:00", errors="coerce")
    event_ts = event_ts[event_ts["datetime"] >= cutoff_time]

    # add start/end times
    event_ts = add_start_end_ts(event_ts, delta1, delta2)

    # --- EVENT ISOLATION/GROUPING ---
    if filter_out_other_events or group_events:
        filtered_event_df = filter_event_df(
            event_ts,
            selected_event,
            sub_event_dict,
            window_size,
            filter_out_other_events,
            filter_tier_list,
            group_events,
            selected_group_event,
        )
    else:
        filtered_event_df = event_ts

    if filtered_event_df.empty:
        # Return empty dataframe and a message
        return pd.DataFrame(), None, "None of the instances of the selected event satisfy the event filtering conditions."

    # ---SUB-EVENT FILTERING---
    cleaned_sub_events = [s.replace(" ", "").strip().lower() for s in sub_event_dict[selected_event]]
    cleaned_sub_event_filtering_dict = {
        re.sub(r"\s+", "", k).strip().lower(): v for k, v in sub_event_filtering_dict.items()
    }

    # 2. Keep only relevant sub-events
    event_df = filtered_event_df.loc[
        filtered_event_df["events"]
        .astype(str)
        .str.replace(" ", "")
        .str.strip()
        .str.lower()
        .apply(lambda x: any(x.startswith(sub) for sub in cleaned_sub_events))
    ].copy()
    if event_df.empty:
        return pd.DataFrame(), None, None

    # 3. Clean names and compute deviation
    event_df["cleaned_events"] = event_df["events"].str.strip().str.lower().str.replace(" ", "")
    event_df["cons_or_forecast"] = event_df["consensus"].where(
        ~event_df["consensus"].isna(), event_df["forecast"]
    )
    event_df["deviation"] = event_df["actual"] - event_df["cons_or_forecast"]

    sub_event_filtered_df = None
    if sub_event_filter:

        # 4. Create per-row validity for sub-events
        def check_bounds(row):
            bounds = None
            months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
            for key in cleaned_sub_event_filtering_dict.keys():
                event = row["cleaned_events"].lower()

                # Match if event starts with key AND next 3 chars (if present) are a month
                if event.startswith(key):
                    suffix = event[len(key):len(key)+3].lower()

                    # check month condition: either no extra chars OR starts with a valid month
                    if len(suffix) < 3 or suffix in months:
                        bounds = cleaned_sub_event_filtering_dict[key]
                        break

            if not bounds:
                return True  
            
            lower, upper = bounds
            if pd.isna(lower) or pd.isna(upper):
                return False
            return lower <= row["deviation"] <= upper

        event_df["pass_bounds"] = event_df.apply(check_bounds, axis=1)

        # 5. Only keep timestamps where all sub-events pass
        pass_counts = event_df.groupby("datetime")["pass_bounds"].agg(list)
        valid_timestamps = [
            dt for dt, lst in pass_counts.items()
            if len(lst) == len(cleaned_sub_events) and all(lst)
        ]

        sub_event_filtered_df = event_df[event_df["datetime"].isin(valid_timestamps)]
        print("LEN event_df: " , len(event_df))

    else:
        sub_event_filtered_df = event_df

    sub_event_deviation = sub_event_filtered_df.loc[:, ['datetime', 'cleaned_events', 'deviation']]
    sub_event_deviation['Start_Date'] = sub_event_deviation['datetime']

    # ---RETURN CALCULATIONS---

    final_df = []
    for start, end in zip(sub_event_filtered_df["start"], sub_event_filtered_df["end"]):
        temp_df = ohcl_1h[(ohcl_1h["US/Eastern Timezone"] >= start) & (ohcl_1h["US/Eastern Timezone"] < end)]

        if temp_df.empty:
            final_df.append([np.nan]*9)
        else:
            entry_price = temp_df["Open"].iloc[0]
            exit_price = temp_df["Close"].iloc[-1]
            maxi = temp_df["High"].max()
            mini = temp_df["Low"].min()

            vol_ret = (maxi - mini) * 16
            abs_ret = abs(exit_price - entry_price) * 16
            ret = (exit_price - entry_price) * 16
            final_df.append([vol_ret, abs_ret, ret,
                             temp_df["US/Eastern Timezone"].iloc[0],
                             temp_df["US/Eastern Timezone"].iloc[-1],
                             entry_price, exit_price, maxi, mini])

    final_df = pd.DataFrame(
        final_df,
        columns=["Volatility Return", "Absolute Return", "Return",
                 "Start_Date", "End_Date", "Entry_Price", "Exit_Price", "High", "Low"]
    )

    final_df.dropna(inplace=True)
    final_df.drop_duplicates(subset=["Start_Date"], keep="first", inplace=True)

    if last_x_obs:
        final_df = final_df.tail(last_x_obs)

    return final_df, sub_event_deviation, None


