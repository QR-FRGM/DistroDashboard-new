"""
Returns plotting functions for DistroDashboard.
Plotting methods moved here from returns.py.
Calculation methods are in models/returns_calculator.py.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import percentileofscore
from datetime import datetime


class ReturnsPlotter:
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
        if 18 <= hour < 24:
            return "Asia 18-24 ET"
        elif 0 <= hour < 7:
            return "London 0-7 ET"
        elif 7 <= hour < 10:
            return "US Open 7-10 ET"
        elif 10 <= hour < 15:
            return "US Mid 10-15 ET"
        elif 15 <= hour < 17:
            return "US Close 15-17 ET"
        else:
            return "Other"

    def plot_daily_session_returns(self, filtered_df, tickersymbol_val, interval_val, bps_factor, 
                                    returns_calculator, month_day_filter=[]):

        start_date = (filtered_df["timestamp"].dt.date.tolist())[0]
        end_date = (filtered_df["timestamp"].dt.date.tolist())[-1]
      
        sessions = self.sessions

        #fetching the intraday data to make the red dot.
        intraday_data = self.dataframe.copy()
        intraday_data['session'] = intraday_data['timestamp'].apply(self.get_session)
        intraday_data['date'] = intraday_data['timestamp'].dt.date

        plt.figure(figsize=(24, 18))
        sns.set_style("darkgrid")
        list_stats = []

        if 'd' in interval_val:
            sessions=['All day']

        for i, session in enumerate(sessions, 1):

            plt.subplot(3, 2, i)

            latest_return = -1
            latest_date = None

            if session != "All day":
                daily_session_returns = returns_calculator.get_daily_session_returns(filtered_df,bps_factor)
                session_returns = daily_session_returns[daily_session_returns["session"] == session]["return"]

                # take unfiltered intraday day for the red dot so that actual movement is compared to non-evemt distro.
                session_ret_intraday = returns_calculator.get_daily_session_returns(intraday_data , bps_factor)
                session_ret_intraday = session_ret_intraday[session_ret_intraday['session'] == session]
                latest_return = session_ret_intraday['return'].iloc[-1]
                latest_date = session_ret_intraday['date'].iloc[-1]
                print('latest date for red dot' , latest_date)


            else:

                daily_returns_all = returns_calculator.get_daily_returns(filtered_df,bps_factor)
                session_returns = daily_returns_all["return"]

                daily_ret_intraday = returns_calculator.get_daily_returns(intraday_data ,bps_factor)
                latest_return = session_returns.iloc[-1]
                latest_date = daily_returns_all["date"].iloc[-1]
                print('latest date for red dot' , latest_date)

            # Calculate the percentile of the latest return
            latest_percentile = percentileofscore(
                session_returns.squeeze(), latest_return, kind="rank"
            )

            # Calculate descriptive stats
            mean = session_returns.mean()
            median = session_returns.median()
            perc95 = session_returns.quantile(0.95)
            perc99 = session_returns.quantile(0.99)
            std = session_returns.std()
            skew = session_returns.skew()
            kurt = session_returns.kurtosis()
            zscore=(latest_return-mean)/std
            latest_zscore=round(zscore,2)

            sns.histplot(
                session_returns, kde=True, stat="density", linewidth=0, color="skyblue"
            )
            sns.kdeplot(session_returns, color="darkblue", linewidth=2)

           
            # Add the latest return as a red point
            plt.scatter(latest_return, 0, color="red", s=150, zorder=5)
            plt.annotate(
                f"({latest_date}, Return:{latest_return:.2f}, Zscore: {latest_zscore}, %ile:{latest_percentile:.1f}%)",
                (latest_return, 0),
                xytext=(10, 10),  # Offset text slightly more for clarity
                textcoords="offset points",
                color="red",
                fontweight="bold",
                fontsize=14,  # Increased font size for readability
            )

            # Add a red dotted vertical line to highlight the latest return
            plt.axvline(
                x=latest_return,
                color="red",
                linestyle="--",
                linewidth=1.5,
                alpha=0.7,
                label="Latest Return",
            )
            plt.title(f"{session}", fontsize=18)
            plt.xlabel("Session return in TV bps", fontsize=16)
            plt.ylabel("Density", fontsize=16)

           
            stats_text = f"Mean: {mean:.2f}\nMedian: {median:.2f}\nStd: {std:.1f}\n95%ile: {perc95:.1f}\n99%ile: {perc99:.1f}\nSkew: {skew:.1f}\nKurt: {kurt:.1f}"
            plt.text(
                0.95,
                0.95,
                stats_text,
                transform=plt.gca().transAxes,
                verticalalignment="top",
                horizontalalignment="right",
                bbox=dict(
                    boxstyle="round",
                    facecolor=self.colors["ivory"],
                    edgecolor=self.colors["dark_slate_gray"],
                    alpha=0.8,
                ),
                color=self.colors["dark_slate_gray"],
                fontsize=20,
            )

            list_stats.append(
                session_returns.describe(
                    percentiles=[0.05, 0.25, 0.5, 0.68, 0.90, 0.95, 0.99, 0.997]
                )
            )
        plt.tight_layout()
        month_to_name = (lambda a, b, c: f"Dates filtered: {datetime.strptime(str(a), '%m').strftime('%B')}: {b}-{c}")
        if month_day_filter==[]:
            filtered_string=""
        else:
            filtered_string = month_to_name(month_day_filter[0],month_day_filter[1], month_day_filter[2])
        plt.suptitle(
            f"Distribution of Returns {tickersymbol_val} with interval of {interval_val}: ABS(End - Start) across trading sessions: {start_date} to {end_date}.{filtered_string}",
            fontsize=20,
            y=1.02,
            x=0.01,
            ha='left'
        )
        plt.savefig(
            os.path.join(
                self.output_folder,
                f"{tickersymbol_val}_{interval_val}_Returns_Distribution.png", #_{start_date}_{end_date}
            ),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

        df_stats = pd.concat(list_stats, axis=1)
        df_stats.columns = sessions
        df_stats.index.name=f'(Return Stats:- Interval:{interval_val}, Symbol:{tickersymbol_val})'
        df_stats.to_csv(
            os.path.join(
                self.output_folder,
                f"{tickersymbol_val}_{interval_val}_Returns_stats.csv",
            )
        )
        #print(df_stats.round(1))

    def get_descriptive_stats(self,target_csv,target_column):
        
        stats_csv=target_csv[target_column].describe(percentiles=[0.1,0.25,0.5,0.75,0.95,0.99])

        # Add additional statistics to the DataFrame
        stats_csv.loc['mean'] = target_csv[target_column].mean()
        stats_csv.loc['skewness'] = target_csv[target_column].skew()
        stats_csv.loc['kurtosis'] = target_csv[target_column].kurtosis()

        stats_csv.index.name = 'Volatility of Returns Statistic'
        return stats_csv

    def plot_daily_session_volatility_returns(
        self, filtered_df, tickersymbol_val, interval_val, bps_factor,
        returns_calculator, month_day_filter=[]
    ):
                
        start_date = (filtered_df["timestamp"].dt.date.tolist())[0]
        end_date = (filtered_df["timestamp"].dt.date.tolist())[-1]

        #fetching intraday data for the red dot.
        intraday_data = self.dataframe.copy()
        intraday_data['session'] = intraday_data['timestamp'].apply(self.get_session)
        intraday_data['date'] = intraday_data['timestamp'].dt.date

        latest_return = -1
        latest_date = None
        
        # Analyze distributions
        list_stats = []
        plt.figure(figsize=(24, 18))
        sns.set_style("darkgrid")

        skip_sessions=False
        if 'd' in interval_val:
            sessions=['All day']
            skip_sessions=True
        else:
            sessions = self.sessions
            
        for i, session in enumerate(sessions, 1):

            if skip_sessions==False:
                plt.subplot(3, 2, i)

            if session == "All day":

                all_volatility_df = returns_calculator.get_daily_volatility_returns(filtered_df,bps_factor=bps_factor)
                session_returns = all_volatility_df["return"]
                latest_custom_days_return = all_volatility_df.iloc[:].loc[  #-15
                    :, ["date", "return"]
                ]

                latest_custom_days_return['ZScore wrt All Days']=(latest_custom_days_return['return']-session_returns.mean())/session_returns.std()
                latest_custom_days_return['ZScore wrt Given Days']=(latest_custom_days_return['return']-latest_custom_days_return['return'].mean())/latest_custom_days_return['return'].std()
                
                latest_custom_days_return_stats=self.get_descriptive_stats(latest_custom_days_return,'return')
                latest_custom_days_return_stats.name=f'(Session:{session}, Interval:{interval_val}, Symbol:{tickersymbol_val})'

                latest_custom_days_return.rename(columns={'date':'Date','return':f'Volatility of Returns (Session:{session}, Interval:{interval_val}, Symbol:{tickersymbol_val})'},inplace=True)
                latest_custom_days_return.to_csv(os.path.join(self.output_folder,
                    f"{"_".join(str(session).split())}_latest_custom_days_Volatility_Returns_{interval_val}_{tickersymbol_val}.csv"),index=False
                )
                latest_custom_days_return_stats.to_csv(os.path.join(self.output_folder,
                    f"{"_".join(str(session).split())}_latest_custom_days_Volatility_Returns_{interval_val}_{tickersymbol_val}_stats.csv")
                )
                
                # data for the red dot.
                vol_ret_all_day_intraday = returns_calculator.get_daily_volatility_returns(intraday_data , bps_factor)
                latest_date = vol_ret_all_day_intraday['date'].iloc[-1]
                latest_return = vol_ret_all_day_intraday['return'].iloc[-1]

                # latest_return = session_returns.iloc[-1]
                latest_zscore=latest_custom_days_return['ZScore wrt All Days'].iloc[-1]
                # latest_date = all_volatility_df["date"].iloc[-1]
                
            else:

                session_volatility_df = returns_calculator.get_daily_session_volatility_returns(filtered_df,bps_factor)
                
                # distribution is a plot of session_returns.
                session_returns = session_volatility_df.loc[session_volatility_df["session"] == session, ["return"]]
                
                latest_custom_days_return = session_volatility_df.loc[session_volatility_df['session']==session].iloc[:].loc[ 
                    :, ["date", "return"]
                ] #-15
               
                latest_custom_days_return['ZScore wrt All Days']=(latest_custom_days_return['return']-session_returns['return'].mean())/session_returns['return'].std()
                latest_custom_days_return['ZScore wrt Given Days']=(latest_custom_days_return['return']-latest_custom_days_return['return'].mean())/latest_custom_days_return['return'].std()

                latest_custom_days_return_stats=self.get_descriptive_stats(latest_custom_days_return,'return')
                latest_custom_days_return_stats.name=f'(Session:{session}, Interval:{interval_val}, Symbol:{tickersymbol_val})'
                
                latest_custom_days_return.rename(columns={'date':'Date','return':f'Volatility of Returns (Session:{session}, Interval:{interval_val}, Symbol:{tickersymbol_val})'},inplace=True)
                latest_custom_days_return.to_csv(os.path.join(self.output_folder,
                    f"{"_".join(str(session).split())}_latest_custom_days_Volatility_Returns_{interval_val}_{tickersymbol_val}.csv"),index=False
                )

                latest_custom_days_return_stats.to_csv(os.path.join(self.output_folder,
                    f"{"_".join(str(session).split())}_latest_custom_days_Volatility_Returns_{interval_val}_{tickersymbol_val}_stats.csv")
                )

                latest_zscore=latest_custom_days_return['ZScore wrt All Days'].iloc[-1]
                
                # Data for the red dot.
                session_vol_ret_intraday = returns_calculator.get_daily_session_volatility_returns(intraday_data , bps_factor)
                session_vol_ret_intraday = session_vol_ret_intraday[session_vol_ret_intraday['session'] == session]
                latest_return = session_vol_ret_intraday['return'].iloc[-1]
                latest_date = session_vol_ret_intraday['date'].iloc[-1]

            # Calculate the percentile of the latest return
            latest_percentile = percentileofscore(session_returns.squeeze(), latest_return, kind="rank")

            # Descriptive Statistics
            mean = session_returns.mean()
            median = session_returns.median()
            std = session_returns.std()
            perc95 = session_returns.quantile(0.95)
            perc99 = session_returns.quantile(0.99)
            skew = session_returns.skew()
            kurt = session_returns.kurtosis()

            # zscore=(session_returns-mean)/std
            latest_zscore=round(latest_zscore,2)

            sns.histplot(
                session_returns, kde=True,stat="density",linewidth=0, color="skyblue"
            )
            sns.kdeplot(session_returns, color="darkblue", linewidth=2)
            # Add the latest return as a red point
            plt.scatter(latest_return, 0, color="red", s=150, zorder=5)
            #plt.scatter(mean,0,color='black',s=150,zorder=5)

            plt.annotate(
                f"({latest_date}, VoltyReturn:{latest_return:.2f}, Zscore:{latest_zscore}, {latest_percentile:.1f}%ile)",
                (latest_return, 0),
                xytext=(10, 10),  # Offset text slightly more for clarity
                textcoords="offset points",
                color="red",
                fontweight="bold",
                fontsize=14,  # Increased font size for readability
            )
            # Add a red dotted vertical line to highlight the latest return
            plt.axvline(
                x=latest_return,
                color="red",
                linestyle="--",
                linewidth=1.5,
                alpha=0.7,
                label="Latest Volty. Return",
            )


            plt.title(f"{session}", fontsize=18)
            plt.xlabel("Session return in TV bps", fontsize=16)
            plt.ylabel("Density", fontsize=16)
            plt.legend("", frameon=False)

            


            if isinstance(session_returns, pd.DataFrame):
                mean, median, std, perc95, perc99, skew, kurt = [
                    x.iloc[0] for x in [mean, median, std, perc95, perc99, skew, kurt]
                ]

            list_stats.append(
                session_returns.describe(
                    percentiles=[0.05, 0.25, 0.5, 0.68, 0.90, 0.95, 0.99, 0.997]
                )
            )

            stats_text = f"Mean: {mean:.2f}\nMedian: {median:.2f}\nStd: {std:.1f}\n95%ile: {perc95:.1f}\n99%ile: {perc99:.1f}\nSkew: {skew:.1f}\nKurt: {kurt:.1f}\n"
            plt.text(
                0.95,
                0.95,
                stats_text,
                transform=plt.gca().transAxes,
                verticalalignment="top",
                horizontalalignment="right",
                bbox=dict(
                    boxstyle="round",
                    facecolor=self.colors["ivory"],
                    edgecolor=self.colors["dark_slate_gray"],
                    alpha=0.8,
                ),
                color=self.colors["dark_slate_gray"],
                fontsize=20,
            )

        
        plt.tight_layout()
        month_to_name = lambda a, b, c: f"Dates filtered: {datetime.strptime(str(a), '%m').strftime('%B')}: {b}-{c}"
        if month_day_filter==[]:
            filtered_string=""
        else:
            filtered_string = month_to_name(month_day_filter[0],month_day_filter[1], month_day_filter[2])
        plt.suptitle(
            f"Distribution of Volatility {tickersymbol_val} with interval of {interval_val}: (High - Low) across trading sessions: {start_date} to {end_date}.{filtered_string}",
            fontsize=20,
            y=1.02,
            x=0.01,
            ha='left'
        )

        
        plt.savefig(
            os.path.join(
                self.output_folder,
                f"{tickersymbol_val}_{interval_val}_Volatility_Distribution.png",
            ),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

        df_stats = pd.concat(list_stats, axis=1)
        df_stats.columns = sessions
        df_stats.index.name=f'(Vol Return Stats:- Interval:{interval_val}, Symbol:{tickersymbol_val})'
        df_stats.to_csv(
            os.path.join(
                self.output_folder,
                f"{tickersymbol_val}_{interval_val}_Volatility_Returns_stats.csv",
            )
        )
        #print(df_stats.round(1))


