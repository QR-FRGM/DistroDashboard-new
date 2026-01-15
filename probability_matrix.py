import os
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from returns_main import folder_processed_pq

from views.plotting import plot_data


def GetMatrix(
    target_bps: float,
    target_hrs: int,
    interval: str,
    ticker_name: str,
    data_type: str,
    version: str = "NA",
):
    """
    Locate parquet data, build probability matrices, and generate plots.

    Args:
        target_bps (float): Target threshold in basis points (1 bp = 0.01%).
            Example: 2.0 means a 2 bps move.
        target_hrs (int): Target time horizon (hours) over which moves are measured.
        interval (str): Time interval of intraday data (e.g., '1h').
        ticker_name (str): Name of the ticker/symbol (e.g., 'ZN').
        data_type (str): Either 'Event' (event windows) or 'Non-Event' (regular times).
        version (str): Determines how returns are treated:
            - 'Absolute': Take absolute value of returns.
            - 'Up': Keep only upward moves.
            - 'Down': Keep only downward moves.
            - 'NA': Compute all three versions.

    Returns:
        dict: Mapping from version -> dict containing:
            - "<=%": Percentile stats for target threshold.
            - "Returns_Matrix": Probability matrix DataFrames.
            - "Plots": Distribution plots.
    """
    df = pd.DataFrame()  # Will hold parquet data once loaded

    # Regex pattern to match event parquet filenames
    pattern = re.compile(r"Intraday_data_ZN_1h_2022-12-20_to_(\d{4}-\d{2}-\d{2})\.parquet")

    # -------- Locate parquet file --------
    if data_type == "Non-Event":
        # Loop through folder for non-event data
        for file in os.scandir(folder_processed_pq):
            if not file.is_file():
                continue
            if (
                interval in file.name
                and ticker_name in file.name
                and "nonevents" in file.name
                and "target_tz" in file.name
                and file.name.endswith(".parquet")
            ):
                print("data used for Probabilty Matrix:", file.name)
                df = pd.read_parquet(os.path.join(folder_processed_pq, file.name))
                break
    else:
        # Look in event data folder
        for file in os.scandir("Intraday_data_files_pq"):
            if not file.is_file():
                continue
            if pattern.match(file.name):
                print("data used for Probabilty Matrix:", file.name)
                df = pd.read_parquet(os.path.join("Intraday_data_files_pq", file.name))
                break

    if df.empty:
        raise FileNotFoundError("No suitable parquet found for the Probability Matrix inputs.")

    # Decide which versions to compute
    if version == "NA":
        version_dic = {"Absolute": {}, "Up": {}, "Down": {}}
    else:
        version_dic = {version: {}}

    # Initialize ProbabilityMatrix object
    my_matrix = ProbabilityMatrix(df.reset_index(drop=True))
    graphs_dict = {}

    # Compute for each version
    for ver in list(version_dic.keys()):
        print("Computing:", ver)
        try:
            graphs_dict = my_matrix.calc_prob(target_bps, target_hrs, ver)
        except Exception as e:
            print(f"❌ Failed on {ver}: {type(e).__name__}: {e}")
            raise

        version_dic[ver]["<=%"] = my_matrix.less_than_equal_percentile_dict
        version_dic[ver]["Returns_Matrix"] = my_matrix.prob_matrix_dict
        version_dic[ver]["Plots"] = graphs_dict
        version_dic[ver]['Latest movt'] = my_matrix.latest_movt_data

    return version_dic


class ProbabilityMatrix:
    """
    Builds distributions of intraday bps moves, probability matrices,
    and visualizations for different measurement modes:
        - open-close
        - open-high/low
        - high-low
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with intraday OHLC dataframe.

        Args:
            df (pd.DataFrame): Intraday data containing columns:
                ['US/Eastern Timezone', 'Open', 'High', 'Low', 'Close']
        """
        self.df = df
        self.N = len(df)  # Number of rows in dataframe
        self.less_than_equal_percentile_list = None  # Stores computed <= percentiles
        self.prob_matrix_dict = None  # Stores probability matrices for each mode
        self.latest_movt_data = None
 
    # ---------------------- helpers ----------------------

    def round_off(self, bps_move):
        """
        Round float to nearest 0.5 bps.
        Works with negatives too.

        Args:
            bps_move (float): Input basis point movement.

        Returns:
            float: Rounded movement.
        """
        return np.round(bps_move * 2) / 2

    def plot_prob(
        self,
        returns_dict,
        percentile: float,
        target_bps: float,
        target_hrs: int,
        version: str,
        mode: str,
    ):
        """
        Plot cumulative probability distribution for a given mode.

        Args:
            returns_dict (dict): Dict of returns by mode and hour.
            percentile (float): Probability (<= target_bps).
            target_bps (float): Target basis points threshold.
            target_hrs (int): Hour window.
            version (str): Version label ('Absolute'/'Up'/'Down').
            mode (str): Mode ('open-close', 'open-high/low', 'high-low').

        Returns:
            matplotlib.figure.Figure: Distribution plot.
        """
        # Array of returns for given mode and hour window
        arr = np.array(returns_dict[mode][target_hrs], dtype=float)

        # New plot
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.kdeplot(arr, color="blue", fill=True, cumulative=True, ax=ax)

        # Titles & labels
        ax.set_title(f"Probability Distribution for {mode} ({version}): {target_bps} bps in {target_hrs} hrs")
        ax.set_xlabel("Basis Points (bps)")
        ax.set_ylabel("Cumulative Probability")

        # Horizontal line at percentile
        y_value = percentile / 100.0

        # Add reference lines and annotations
        ax.axvline(x=target_bps, color="blue", linestyle="--", label=f"Target bps: {abs(target_bps)}")
        ax.axhline(
            y=y_value,
            xmin=0,
            xmax=1,
            color="green",
            linestyle="--",
            label=f"Pr(bps ({version}) > {abs(target_bps)}) = {100 - percentile:.2f}%",
        )
        ax.annotate(
            f"Pr(bps ({version}) <= {abs(target_bps)}) = {percentile:.2f}%",
            xy=(abs(target_bps), y_value),
            xytext=(target_bps + 2, y_value + 0.03),
            color="red",
            arrowprops=dict(facecolor="red", arrowstyle="->"),
        )
        ax.scatter(x=target_bps, y=y_value, color="red", alpha=1)

        # Show descriptive stats box
        desc = pd.Series(arr).describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.95, 0.99])
        stats_text = (
            f"Mean: {desc['mean']:.2f} bps\n"
            f"Std: {desc['std']:.1f} bps\n"
            f"0%ile (Min): {desc['min']:.2f} bps\n"
            f"10%ile: {desc['10%']:.2f} bps\n"
            f"25%ile: {desc['25%']:.2f} bps\n"
            f"50%ile (Median): {desc['50%']:.2f} bps\n"
            f"75%ile: {desc['75%']:.2f} bps\n"
            f"95%ile: {desc['95%']:.1f} bps\n"
            f"99%ile: {desc['99%']:.1f} bps\n"
            f"100%ile (Max): {desc['max']:.2f} bps"
        )

        ax.text(
            0.95,
            0.75,
            stats_text,
            transform=ax.transAxes,
            va="top",
            ha="right",
            bbox=dict(boxstyle="round", facecolor="#FFFFF0", edgecolor="#2F4F4F", alpha=0.8),
            color="#000000",
            fontsize=10,
        )

        ax.legend()
        fig.tight_layout()
        return fig 

    # ---------------------- main ----------------------
    def calc_prob(self, target_bps, target_hrs, version):
        """
        Compute probability matrices and plots for a version.

        Args:
            target_bps (float): Target threshold in bps.
            target_hrs (int): Time horizon in hours.
            version (str): 'Absolute', 'Up', 'Down'.

        Returns:
            dict: mode -> matplotlib Figure plot.
        """
        if version not in ["Absolute", "Up", "Down", "No-Version"]:
            raise ValueError("Invalid version. Use 'Down', 'Absolute', 'Up' or 'No-Version'.")

        # --- helper to filter returns by version ---
        def apply_version_filter(arr, ver) -> np.ndarray:
            arr = np.array(arr, dtype=float)
            if ver == "Down":
                arr = arr[arr <= 0]  # keep non-positives
                arr = -1 * arr[arr < 0]  # flip sign of negatives (so moves are positive numbers)
            elif ver == "Up":
                arr = arr[arr >= 0]  # keep non-negatives
            elif ver == "Absolute":
                arr = np.abs(arr)  # take absolute values
            return arr

        data = self.df
        # "gap" groups contiguous hourly segments, resets when gap > 1h
        data['gap'] = data['US/Eastern Timezone'].diff().gt(pd.Timedelta('1h')).cumsum()

        # Dict of returns by mode & hour window
        returns_dict = {'open-close': {}, 'open-high/low': {}, 'high-low': {}}

        # Dict of all movements across hours (used for matrix building)
        all_movt_dict = {'open-close': [], 'open-high/low': [], 'high-low': []}

        #dict storing the latest for target_hrs for the 3 modes
        latest_moves_dict = {}
        df1 = pd.DataFrame(columns=["Datetime", "Bps moved"])
        df2 = pd.DataFrame(columns=["Datetime", "Bps moved"])
        df3 = pd.DataFrame(columns=["Datetime", "Bps moved"])

        # Iterate over window sizes (target_hrs ± 10)
        for hrs in range(max(1, target_hrs-10), target_hrs + 11):

            # Ensure lists exist
            for mode in returns_dict:
                if hrs not in returns_dict[mode]:
                    returns_dict[mode][hrs] = []

            # Process each contiguous segment separately
            for _, segment in data.groupby('gap'):
                n = len(segment)
                full_blocks = n // hrs  # number of complete blocks of length hrs

                if full_blocks == 0:
                    # Not enough data for this segment
                    for mode in returns_dict:
                        returns_dict[mode][hrs].append(np.nan)
                else:
                    # Process each block
                    for i in range(full_blocks):
                        block = segment.iloc[i*hrs:(i+1)*hrs]

                        open_price = block['Open'].iloc[0]
                        close_price = block['Close'].iloc[-1]
                        block_high = block['High'].max()
                        block_low = block['Low'].min()

                        # Convert moves into bps (multiplied by 16)
                        ret1 = self.round_off((close_price - open_price) * 16)
                        ret2 = self.round_off(max(block_high-open_price, open_price-block_low) * 16)
                        ret3 = self.round_off((block_high - block_low) * 16)

                        returns_dict['open-close'][hrs].append(ret1)
                        returns_dict['open-high/low'][hrs].append(ret2)
                        returns_dict['high-low'][hrs].append(ret3)

                        if(hrs == target_hrs):
                            r1 = pd.DataFrame([{"Datetime": block['US/Eastern Timezone'].iloc[0] , "Bps moved": ret1}])
                            r2 = pd.DataFrame([{"Datetime": block['US/Eastern Timezone'].iloc[0] , "Bps moved": ret2}])
                            r3 = pd.DataFrame([{"Datetime": block['US/Eastern Timezone'].iloc[0] , "Bps moved": ret3}])
                            df1 = pd.concat([df1, r1], ignore_index=True)
                            df2 = pd.concat([df2, r2], ignore_index=True)
                            df3 = pd.concat([df3, r3], ignore_index=True)

            # Apply version filters + clean nans
            for mode in ['open-close', 'open-high/low', 'high-low']:
                returns_dict[mode][hrs] = apply_version_filter(returns_dict[mode][hrs], version)
                cleaned_arr = returns_dict[mode][hrs][~np.isnan(returns_dict[mode][hrs])]
                returns_dict[mode][hrs] = cleaned_arr

                # Collect all movements for this mode
                all_movt_dict[mode].extend(returns_dict[mode][hrs])

        latest_moves_dict['open-close'] = df1
        latest_moves_dict['open-high/low'] = df2
        latest_moves_dict['high-low'] = df3

        self.latest_movt_data = latest_moves_dict

        # Compute <= percentile for target bps in target_hrs
        percentile_dict = {}
        for mode in ['open-close', 'open-high/low', 'high-low']:
            percentile_dict[mode] = ((np.array(returns_dict[mode][target_hrs], dtype=float) <= target_bps).mean() * 100.0)

        # Build probability matrices
        matrix_dict = self._calc_prob_matrix(returns_dict, all_movt_dict, version)

        # Save results to object
        self.less_than_equal_percentile_dict = percentile_dict
        self.prob_matrix_dict = matrix_dict

        # Build plots
        graphs_dict = {}
        for mode in ['open-close', 'open-high/low', 'high-low']:
            temp_df = pd.DataFrame(returns_dict[mode][target_hrs], columns=["Moves"])
            fig_dict = plot_data(temp_df, ['Moves'] , graph_type='cdf' , bool_custom_value= True , custom_value=target_bps)
            graphs_dict[mode] = fig_dict['Moves']

        return graphs_dict

    # ---------------------- matrix builders ----------------------
    def _calc_prob_matrix_helper(self, prob_matrix_dict, unique_bps_array):
        """
        Construct cumulative probability distributions across ordered hours.

        Args:
            prob_matrix_dict (dict): Mapping hour -> list of bps values.
            unique_bps_array (array-like): Sorted array of thresholds.

        Returns:
            tuple: (list of np.ndarrays with probabilities, ordered hours).
        """
        unique_bps_array = np.sort(np.array(unique_bps_array))

        # Sorted list of hour windows
        ordered_hours = sorted({h for h in prob_matrix_dict.keys()})

        percentile_bps_array_for_all_hours = []
        for h in ordered_hours:
            if len(prob_matrix_dict[h]) > 0:
                bps_values = np.array(prob_matrix_dict[h], dtype=float)

                # Probability of exceeding each threshold
                pr_gt = 100.0 - np.array([np.mean(bps_values <= tb) * 100.0 for tb in unique_bps_array])
                pr_fmt = np.char.add(np.round(pr_gt, 2).astype(str), '%')
                percentile_bps_array_for_all_hours.append(pr_fmt)
            else:
                percentile_bps_array_for_all_hours.append(np.nan)

        return percentile_bps_array_for_all_hours, ordered_hours

    def _calc_prob_matrix(self, returns_dict, all_movt_dict, version):
        """
        Build probability matrix DataFrames for each mode.

        Args:
            returns_dict (dict): Hour -> returns mapping (key = mode, hrs & val = movements).
            all_movt_dict (dict): Mode -> list of all moves.
            version (str): Version label.

        Returns:
            dict: Mode -> DataFrame probability matrix.
        """
        matrix_dict = {}

        for mode in ['open-close', 'open-high/low', 'high-low']:
            unique_bps = sorted(list(set(all_movt_dict[mode])))

            percentile_bps_array, ordered_hours = self._calc_prob_matrix_helper(returns_dict[mode], unique_bps)

            # Create matrix indexed by thresholds (bps) vs hours
            prob_matrix = pd.DataFrame(index=unique_bps, columns=ordered_hours, dtype=object)
            for i, hr in enumerate(ordered_hours):
                prob_matrix[hr] = percentile_bps_array[i]

            prob_matrix.index.name = f"bps Pr(bps ({version}) > )"
            prob_matrix.columns.name = "hrs"

            matrix_dict[mode] = prob_matrix

        return matrix_dict


if __name__ == "__main__":
    # Example run
    target_bps = 2.0     # 2 basis points
    target_hrs = 6       # 6-hour window
    interval = "1h"      # intraday data at 1-hour frequency
    ticker_name = "ZN"   # ticker symbol
    data_type = "Non-Event"

    out = GetMatrix(
        target_bps,
        target_hrs,
        interval,
        ticker_name,
        data_type,
        version="Absolute",
    )
    print("Versions:", [k for k in out.keys() if k != "OH_OL_plot"])
