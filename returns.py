"""
Returns module for DistroDashboard.
This is a backward-compatible wrapper that combines:
- models/returns_calculator.py (calculation methods)
- views/returns_plotter.py (plotting methods)

For new code, prefer importing directly from:
- from models.returns_calculator import ReturnsCalculator
- from views.returns_plotter import ReturnsPlotter
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from events import Events
from scipy.stats import percentileofscore
from datetime import datetime

# Import from new MVC structure
from models.returns_calculator import ReturnsCalculator
from views.returns_plotter import ReturnsPlotter


class Returns:
    """
    Backward-compatible Returns class that combines calculation and plotting functionality.
    Delegates to ReturnsCalculator and ReturnsPlotter internally.
    """
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
        
        # Internal delegates
        self._calculator = ReturnsCalculator(output_folder=output_folder, dataframe=dataframe)
        self._plotter = ReturnsPlotter(output_folder=output_folder, dataframe=dataframe)
        
        # Keep month_day_filter for backward compatibility
        self.month_day_filter = []

    def get_session(self, timestamp):
        return self._calculator.get_session(timestamp)

    def filter_date(
        self,
        filter_df,
        start_date="",
        end_date="",
        month_day_filter=[],
        to_sessions=True,
    ):
        result = self._calculator.filter_date(filter_df, start_date, end_date, month_day_filter, to_sessions)
        self.month_day_filter = self._calculator.month_day_filter
        return result
    
    def get_descriptive_stats(self, target_csv, target_column):
        return self._calculator.get_descriptive_stats(target_csv, target_column)

    def _calculate_return_bps(self, group, bps_factor):
        return self._calculator._calculate_return_bps(group, bps_factor)
    
    def _calculate_return_bps2(self, group, bps_factor):
        return self._calculator._calculate_return_bps2(group, bps_factor)

    def get_daily_session_returns(self, df, bps_factor, target_column='timestamp', columns='NA'):
        return self._calculator.get_daily_session_returns(df, bps_factor, target_column, columns)

    def get_daily_returns(self, df, bps_factor, target_column='timestamp', columns='NA'):
        return self._calculator.get_daily_returns(df, bps_factor, target_column, columns)

    def plot_daily_session_returns(self, filtered_df, tickersymbol_val, interval_val, bps_factor):
        return self._plotter.plot_daily_session_returns(
            filtered_df, tickersymbol_val, interval_val, bps_factor, 
            self._calculator, self.month_day_filter
        )

    def get_daily_session_volatility_returns(self, df, bps_factor, target_col='timestamp'):
        return self._calculator.get_daily_session_volatility_returns(df, bps_factor, target_col)

    def get_daily_volatility_returns(self, df, bps_factor, target_col='timestamp'):
        return self._calculator.get_daily_volatility_returns(df, bps_factor, target_col)

    def plot_daily_session_volatility_returns(
        self, filtered_df, tickersymbol_val, interval_val, bps_factor
    ):
        return self._plotter.plot_daily_session_volatility_returns(
            filtered_df, tickersymbol_val, interval_val, bps_factor,
            self._calculator, self.month_day_filter
        )

    def tag_events(self, ev, pc):
        return self._calculator.tag_events(ev, pc)
