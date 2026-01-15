import pandas as pd
import numpy as np
from typing import Optional, Tuple, List, Dict

def record_uptrend(price_data: pd.DataFrame,
                   moves_list: List[Dict],
                   trend_reverse_threshold: float,
                   start_checking_from: int = 1) -> Optional[pd.Timestamp]:
    """
    Given a price_data DataFrame already filtered to rows >= start timestamp,
    detect the uptrend pivot (where a reverse exceeds trend_reverse_threshold).
    Append the initial up-move to moves_list as a dict {'timestamp', 'Move'}.
    Returns the timestamp to use as pivot for the next search (or None if not found).
    Expects columns: ['timestamp','Open','High','Low','Close'].
    """
    if price_data.empty:
        return None

    max_ind = 0
    running_high = price_data['high'].iloc[0]
    low = price_data['open'].iloc[0]

    for i in range(1, len(price_data)):

        if price_data['high'].iloc[i] >= running_high:
            running_high = price_data['high'].iloc[i]
            max_ind = i

        if i >= start_checking_from:
            if (running_high - price_data['low'].iloc[i]) * 16 >= trend_reverse_threshold:
                moves_list.append({
                    'timestamp': price_data['timestamp'].iloc[max_ind],
                    'Move': (running_high - low) * 16,
                    'Trend': 'up'
                })
                # return the timestamp at the running-high index (max_ind)
                return price_data['timestamp'].iloc[max_ind]

    # no pivot found
    return None


def record_downtrend(price_data: pd.DataFrame,
                     moves_list: List[Dict],
                     trend_reverse_threshold: float,
                     start_checking_from: int = 1) -> Optional[pd.Timestamp]:
    """
    Analogous to record_uptrend but for a downtrend --> looks for upward reversal.
    Appends initial down move to moves_list and returns timestamp of pivot (or None).
    """
    if price_data.empty:
        return None

    min_ind = 0
    running_low = price_data['low'].iloc[0]
    high = price_data['high'].iloc[0]

    for i in range(1, len(price_data)):

        if price_data['low'].iloc[i] <= running_low:
            running_low = price_data['low'].iloc[i]
            min_ind = i

        if i >= start_checking_from:
            if (price_data['high'].iloc[i] - running_low) * 16 >= trend_reverse_threshold:
                moves_list.append({
                    'timestamp': price_data['timestamp'].iloc[min_ind],
                    'Move': (running_low - high) * 16,
                    'Trend': 'down'
                })
                return price_data['timestamp'].iloc[min_ind]

    return None


def detect_moves(event_df: pd.DataFrame,
                 trend_establish_threshold: float,
                 trend_reverse_threshold: float,
                 selected_event: str,
                 price_data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    For each event timestamp in event_df where events == selected_event,
    find the initial trend (by running_body_sum * 16 crossing threshold),
    then record the initial move and the pullback move.
    Returns (initial_moves_df, pullback_moves_df) — both DataFrames with columns ['timestamp','Move'].
    Expects:
      - event_df has columns ['timestamp','events'].
      - price_data has columns ['timestamp','Open','High','Low','Close'] and is sorted ascending by timestamp.
    """
    cleaned_selected_event = selected_event.replace(" " ,"").lower().strip()
    df = event_df[event_df['cleaned_events'].astype(str).str.startswith(cleaned_selected_event)]
    initial_moves_list: List[Dict] = []
    pullback_moves_list: List[Dict] = []

    # ensure timestamps are of datetime type and price_data sorted
    price_data = price_data.sort_values('timestamp').reset_index(drop=True)

    for j in range(len(df)):
        start_ts = df['datetime'].iloc[j]

        # filtered OHLC starting from the event timestamp
        ohcl = price_data[price_data['timestamp'] >= start_ts].reset_index(drop=True)

        if ohcl.empty:
            continue

        # determine initial trend using running_body_sum
        running_body_sum = 0.0
        initial_trend = None
        trend_established_index = None
        for i in range(len(ohcl)):
            running_body_sum += (ohcl['close'].iloc[i] - ohcl['open'].iloc[i]) * 16
            if running_body_sum > trend_establish_threshold:
                initial_trend = 'up'
                trend_established_index = i
                break
            elif running_body_sum < -trend_establish_threshold:
                initial_trend = 'down'
                trend_established_index = i
                break

        # if no initial trend established, skip this event
        if initial_trend is None:
            continue

        if initial_trend == 'up':
            pivot_ts = record_uptrend(ohcl, initial_moves_list, trend_reverse_threshold , trend_established_index)
            if pivot_ts is not None:
                # when searching pullback, start from pivot timestamp (inclusive)
                ohcl_after_pivot = ohcl[ohcl['timestamp'] >= pivot_ts].reset_index(drop=True)
                _ = record_downtrend(ohcl_after_pivot, pullback_moves_list, trend_reverse_threshold)
        else: 
            pivot_ts = record_downtrend(ohcl, initial_moves_list, trend_reverse_threshold , trend_established_index)
            if pivot_ts is not None:
                ohcl_after_pivot = ohcl[ohcl['timestamp'] >= pivot_ts].reset_index(drop=True)
                _ = record_uptrend(ohcl_after_pivot, pullback_moves_list, trend_reverse_threshold)

    initial_moves_df = pd.DataFrame(initial_moves_list)
    pullback_moves_df = pd.DataFrame(pullback_moves_list)
    initial_moves_df.rename(columns = {"Move": "Initial_Move"} , inplace= True)
    pullback_moves_df.rename(columns = {"Move": "Pullback"} , inplace = True)
    return initial_moves_df, pullback_moves_df

def conditional_filtering(initial_moves, pullback_moves, lb, ub):
    mask = (
        (initial_moves['Initial_Move'] >= lb) &
        (initial_moves['Initial_Move'] <= ub)
    )

    df1 = initial_moves.loc[
        mask, ['timestamp', 'Initial_Move', 'Trend']
    ].reset_index(drop=True)

    df2 = pullback_moves.loc[
        mask, ['timestamp', 'Pullback', 'Trend']
    ].reset_index(drop=True)

    return df1, df2

