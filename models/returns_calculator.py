"""
Returns calculation functions for DistroDashboard.
Calculation methods moved here from returns.py.
Plotting methods moved to views/returns_plotter.py.
"""

import os
import pandas as pd
from datetime import datetime


class ReturnsCalculator:
    def __init__(
        self, output_folder="stats_and_plots_folder", dataframe=pd.DataFrame()
    ):
        self.colors = {
            "deep_black": "#000000",
            "golden_yellow": "#FFD700",
            "dark_slate_gray": "#2F4F4F",
            "ivory": "#FFFFF0",
            "fibonacci_blue": "#0066CC",
            "sage_green": "#8FBC8F",
            "light_gray": "#D3D3D3",
        }
        self.sessions = [
            "London 0-7 ET",
            "US Open 7-10 ET",
            "US Mid 10-15 ET",
            "US Close 15-17 ET",
            "Asia 18-24 ET",
            "All day",
        ]
        self.output_folder = output_folder
        self.dataframe = dataframe
        os.makedirs(self.output_folder, exist_ok=True)

    def get_session(self, timestamp):
        hour = timestamp.hour
        # minute = timestamp.minute
        if 18 <= hour < 24:
            return "Asia 18-24 ET"
        elif 0 <= hour < 7:  # or (hour == 6 and minute < 30):
            return "London 0-7 ET"
        elif 7 <= hour < 10:  # or (hour == 6 and minute >= 30):
            return "US Open 7-10 ET"
        elif 10 <= hour < 15:
            return "US Mid 10-15 ET"
        elif 15 <= hour < 17:
            return "US Close 15-17 ET"
        else:
            return "Other"


    def filter_date(
        self,
        filter_df,
        start_date="",
        end_date="",
        month_day_filter=[],
        to_sessions=True,
    ):
        self.month_day_filter=month_day_filter
        df = filter_df.copy()
        if to_sessions == True:
            df["session"] = df["timestamp"].apply(self.get_session)

        if month_day_filter == []:
            if start_date == end_date == "":
                finaldf = df
            elif start_date == "" and end_date != "":
                end_date = pd.to_datetime(end_date).date()
                finaldf = df[(df["timestamp"].dt.date <= end_date)]
            elif start_date != "" and end_date == "":
                start_date = pd.to_datetime(start_date).date()
                finaldf = df[(df["timestamp"].dt.date >= start_date)]
            else:
                start_date = pd.to_datetime(start_date).date()
                end_date = pd.to_datetime(end_date).date()
                finaldf = df[
                    (df["timestamp"].dt.date >= start_date)
                    & (df["timestamp"].dt.date <= end_date)
                ]

        else:
            month = month_day_filter[0]
            day1 = month_day_filter[1]
            day2 = month_day_filter[2]
            finaldf = df[
                (df["timestamp"].dt.month == month)
                & (df["timestamp"].dt.day >= day1)
                & (df["timestamp"].dt.day <= day2)
            ]
        finaldf["year"] = (finaldf["timestamp"].dt.year).astype("Int64")
        finaldf = finaldf.sort_values("timestamp")
        

        return finaldf
    
    def get_descriptive_stats(self,target_csv,target_column):
        
        stats_csv=target_csv[target_column].describe(percentiles=[0.1,0.25,0.5,0.75,0.95,0.99])

        # Add additional statistics to the DataFrame
        stats_csv.loc['mean'] = target_csv[target_column].mean()
        stats_csv.loc['skewness'] = target_csv[target_column].skew()
        stats_csv.loc['kurtosis'] = target_csv[target_column].kurtosis()

        stats_csv.index.name = 'Volatility of Returns Statistic'
        return stats_csv

    # Close Price when the session ended - Open Price when the session started
    def _calculate_return_bps(self, group,bps_factor):
        return abs(group["Close"].iloc[-1]-group["Open"].iloc[0]) * bps_factor
    def _calculate_return_bps2(self, group,bps_factor):
        return (group["Close"].iloc[-1]-group["Open"].iloc[0]) * bps_factor

    def get_daily_session_returns(self, df,bps_factor,target_column='timestamp',columns='NA'):
        
        if columns=='NA':
            returns = (
                df.groupby([df[target_column].dt.date, "session"], group_keys=False)
                .apply(self._calculate_return_bps, bps_factor=bps_factor,include_groups=False)
                .reset_index()
            )
            returns.columns = ["date", "session", "return"]
        else:
            returns.columns=columns
        return returns

    def get_daily_returns(self, df, bps_factor,target_column='timestamp',columns='NA'):
        
        if columns=='NA':
            daily_returns_all = (
            df.groupby(df[target_column].dt.date)
            .apply(self._calculate_return_bps,bps_factor)
            .reset_index()
        )
            daily_returns_all.columns = ["date", "return"]
        else:
            daily_returns_all = (
            df.groupby(df[target_column])
                .apply(self._calculate_return_bps2,bps_factor)
                .reset_index()
            )
             
            daily_returns_all.columns = columns

        return daily_returns_all

    def get_daily_session_volatility_returns(self, df,bps_factor , target_col = 'timestamp'):
        
        session_volatility_df = df.groupby([df[target_col].dt.date, "session"]).agg(
            {"High": ["max"], "Low": ["min"]}
        )
        session_volatility_df["return"] = bps_factor * (
            session_volatility_df["High"]["max"] - session_volatility_df["Low"]["min"]
        )
        session_volatility_df = session_volatility_df.reset_index()
        session_volatility_df.columns = ["date", "session", "high", "low", "return"]
        session_volatility_df = session_volatility_df.sort_values(["date", "session"])
        return session_volatility_df

    def get_daily_volatility_returns(self, df,bps_factor , target_col = 'timestamp'):
        all_df = df.groupby([df[target_col].dt.date]).agg(
            {"High": ["max"], "Low": ["min"]}
        )
        all_df["return"] = bps_factor * (all_df["High"]["max"] - all_df["Low"]["min"])
        all_df = all_df.reset_index()
        all_df.columns = ["date", "high", "low", "return"]
        all_df = all_df.sort_values(["date"])
        return all_df

    def tag_events(self, ev, pc):
        events_df = ev.copy()
        price_df = pc.copy()

        # Prepare events DataFrame
        events_df["timestamp"] = events_df["datetime"]
       

        # Prepare price DataFrame
        price_df.index.name = None
        price_df.reset_index(inplace=True)
        price_df["timestamp"] = price_df["timestamp"]
        price_df = price_df.sort_values("timestamp")
        events_df = events_df.sort_values("timestamp")

        # Outer merge based on timestamp
        # print('pricedf',price_df)
        # print('events_df',events_df)
        price_df["timestamp"] = price_df["timestamp"].dt.tz_localize(None)
        events_df['timestamp'] = events_df["timestamp"].dt.tz_localize(None)
        
        final_df = pd.merge(price_df, events_df, on="timestamp", how="outer")

        # Sort the final DataFrame by timestamp
        final_df = final_df.sort_values("timestamp")
        final_df.dropna(how="all", inplace=True)
        final_df.index = final_df["index"]
        final_df.index.name = pc.index.name
        final_df.drop("index", axis=1, inplace=True)

        final_df["year"] = (final_df["timestamp"].dt.year).astype("Int64")
        final_df = final_df.sort_values("timestamp")

        common_columns = ["timestamp", "year", "session"]
        # Separate the columns of the two DataFrames
        events_columns = [col for col in events_df.columns if col not in common_columns]
        price_columns = [col for col in price_df.columns if col not in common_columns]
        remove_columns = ["datetime", "index"]

        # Combine the desired order
        ordered_columns = common_columns + events_columns + price_columns
        ordered_columns = [i for i in ordered_columns if i not in remove_columns]
        final_df = final_df.reindex(columns=ordered_columns, fill_value="na")
        return final_df

