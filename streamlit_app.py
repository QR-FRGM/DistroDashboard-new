import streamlit as st
import os
import pandas as pd
from io import BytesIO
from zipfile import ZipFile
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from probability_matrix import GetMatrix
import custom_filtering_dataframe
import requests
import re
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy.stats import percentileofscore, skew, kurtosis
from pandas.tseries.offsets import MonthEnd

# Import from MVC modules
from models.constants import (
    EVENTS as events,
    SUB_EVENT_DICT as sub_event_dict,
    PERCENTAGE_EVENTS as percentage_events,
)
from models.data_loader import get_data, get_price_movt
from models.event_processor import (
    add_start_end_ts,
    filter_event_df,
    month_end_filtering,
)

from models.pullback_analysis import (
    detect_moves,
    record_downtrend,
    record_uptrend,
)
from models.session_utils import get_session

from views.plotting import plot_data
from views.formatters import convert_decimal_to_ticks, convert_ticks_to_decimal
from views.table_builders import get_pivot_tables
from views.exporters import download_combined_excel

from utils.helpers import timeit, clean_text, sanitize_sheet_name

# Import controllers
from controllers.session_controller import process_session_analysis
from controllers.probability_controller import (
    process_probability_matrix,
    get_probability_display_data,
    prepare_matrix_download,
)
from controllers.custom_filter_controller import (
    get_filtered_dataframe,
    calculate_time_difference,
    process_custom_filter,
    prepare_custom_filter_download,
)
from controllers.event_distro_controller import (
    load_event_data,
    process_event_distro,
    prepare_event_distro_download,
)
from controllers.tagging_controller import (
    TAGS as tagging_tags,
    load_tagged_events,
    add_tagged_event,
    delete_tagged_event,
    get_price_data_for_event,
    filter_by_tag,
)
from controllers.library_controller import (
    LIBRARY_TAGS,
    get_matching_files,
    save_uploaded_file,
    read_file_for_download,
)

# Setting up page configuration
st.set_page_config(
    page_title="FR Live Plots",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

tab = st.radio('Select a Tab' , ["Session and Volatility Returns for all sessions",
                                "Probability Matrix",
                                "Custom Normalised Returns",
                                "Event Specific Distro",
                                "Non-Economic Event Tagging",
                                "Analysis Library",
                                "Pull back analysis"])

# Storing unique lists to be used later in separate drop-downs
unique_intervals = ['1m' , '15m' , '1h' , '1d'] #Interval drop-down (1hr,15min,etc)
unique_instruments = ['ZN' , 'ZF' , 'ZT' , 'ZB'] #Instrument/ticker drop-down (ZN, ZB,etc)
unique_sessions = ['London 0-7 ET' , 'US Open 7-10 ET' , 'US Mid 10-15 ET' , 'US Close 15-17 ET' , 'Asia 18-24 ET'] #Session drop-downs (US Mid,US Open,etc)
unique_versions=['Absolute','Up','Down','No-Version']#Version drop-downs for Probability Matrix
data_type = ['Non-Event' , 'All data']  #type of data to use when forming the Probability Matrix

# The  default option when opening the app
desired_interval = '1h'
desired_instrument='ZN'
desired_version='Absolute'

# Set the desired values in respective drop-downs.
# Interval drop-down
if desired_interval in unique_intervals:
    default_interval_index = unique_intervals.index(desired_interval)  # Get its index
else:
    default_interval_index = 0  # Default to the first element

# Instrument drop-down
if desired_instrument in unique_instruments:
    default_instrument_index = unique_instruments.index(desired_instrument)  # Get its index
else:
    default_instrument_index = 0  # Default to the first element

# Version drop-down
if desired_version in unique_versions:
    default_version_index = unique_versions.index(desired_version)  # Get its index
else:
    default_version_index = 0 # Default to the first element

# Create drop-down and display it on the left permanantly
x= st.sidebar.selectbox("Select Interval",unique_intervals,index=default_interval_index)
y= st.sidebar.selectbox("Select Instrument",unique_instruments,index=default_instrument_index)

st.session_state.x = x
st.session_state.y = y

#Define tabs:
if tab == "Session and Volatility Returns for all sessions":

    st.title("Session-wise Analysis")

    # ------- USER INTERFACE ---------
    selected_sessions = st.multiselect("Select Session", unique_sessions)

    last_x_obs = None
    last_x_obs_bool = st.checkbox("Analyze last x instances of the selected sessions")
    if(last_x_obs_bool):
        last_x_obs = st.number_input("Enter the number of most recent instances to analyse" , min_value = 1)

    custom_pivot_price = None
    custom_pivot_price_bool = st.checkbox("Generate pivot tables about a custom pivot price")
    if(custom_pivot_price_bool):
        num = st.text_input("Enter custom pivot price")
        integer,frac = num.split("'")
        custom_pivot_price = int(integer) + (float(frac)/32)

    # go button
    execute = st.button("Go")

    # ------- BACKEND FUNCTION CALLS VIA CONTROLLER ----------
    if(execute):
        # Call controller to process data
        results = process_session_analysis(
            x, y, selected_sessions, 
            last_x_obs=last_x_obs if last_x_obs_bool else None,
            custom_pivot_price=custom_pivot_price if custom_pivot_price_bool else None
        )
        
        # Display plots
        st.title("Distribution Analysis")
        fig_dict = results['fig_dict']
        n = len(fig_dict)
        cols = st.columns(n)

        for col, (name, fig) in zip(cols, fig_dict.items()):
            with col:
                st.markdown(name)
                st.plotly_chart(fig, use_container_width=True)

        # Display metadata
        metadata = results['metadata']
        st.write(f"Distribution generated using data from {metadata['date_start']} to {metadata['date_end']}")
        st.write(f"Total number of instances for the selected sessions: {metadata['total_instances']}")
        st.write(f"Latest close price of {metadata['latest_close_price_formatted']} at: ", metadata['latest_price_timestamp'])
        st.write(f"The below tables are pivoted about {metadata['pivot_price_formatted']}")
                
        # Display pivot tables
        col1, col2, col3 = st.columns(3)
        pivot_tables_list = results['pivot_tables']

        with col1:
            st.markdown("Based on Absolute Return")
            st.table(pivot_tables_list[0])

        with col2:
            st.markdown("Based on Return")
            st.table(pivot_tables_list[1])

        with col3:
            st.markdown("Based on Volatility Return")
            st.table(pivot_tables_list[2])
        
        # Download button
        file_name_str = '_'.join(selected_sessions)
        st.download_button(
            label = "Download Returns Data",
            data = results['download_data'],
            file_name=f'Session_returns_{file_name_str}.xlsx',
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.text("Click the Go button to generate output")
        
elif tab == "Probability Matrix":
    try:
        st.title("Probability Matrix (Unconditional)")

        # Use stored values from session state
        x = st.session_state.get("x", list(unique_intervals)[0])
        y = st.session_state.get("y", list(unique_instruments)[0])

        if 'h' in x:
            # --- Inputs ---
            version_value = st.selectbox("Select Version", unique_versions, index=default_version_index)
            data_type_selected = st.selectbox("Select type of data to use", data_type, index=default_version_index)

            enter_bps = st.number_input(label="Enter the number of bps:", min_value=0.0, step=0.5, format="%.1f")
            st.caption("Note: The value must be a float and increases in steps of 0.5. Eg 1, 1.5, 2, 2.5, etc")
            st.caption("The probability matrix rounds offs any other bps value into this format in the output.")

            enter_hrs = st.number_input(label="Enter the number of hours:", min_value=1, step=1)
            st.caption("Note: The value must be an integer and increase in steps of 1. Eg 1, 2, 3, 4, etc.")

            v = version_value

            # ============================================================
            # 1) CALL CONTROLLER TO GET PROBABILITY MATRIX DATA
            # ============================================================
            results = process_probability_matrix(
                enter_bps, enter_hrs, x, y, data_type_selected, version_value
            )
            prob_matrix_dic_plots = results['prob_matrix_dic']

            mode = st.selectbox("Select the mode:", ['open-close', 'open-high/low', 'high-low'])

            # Get display data from controller
            display_data = get_probability_display_data(
                prob_matrix_dic_plots, v, enter_bps, enter_hrs, mode
            )

            # ============================================================
            # 2) DISPLAY PROBABILITY SUMMARY & GRAPH
            # ============================================================
            st.subheader(f"Probability of bps ({v})  > {abs(enter_bps)} bps within {enter_hrs} hrs")
            st.dataframe(display_data['prob_df'], use_container_width=True)

            st.subheader(f"Probability Plot for {enter_bps} bps ({v}) movement in {enter_hrs} hrs")
            st.plotly_chart(display_data['plot'])

            # ============================================================
            # 3) DISPLAY MATRIX TABLE WITH HIGHLIGHTING
            # ============================================================
            raw = display_data['matrix_raw']
            main_col = f"{enter_hrs} hr"

            def _highlight_main(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                if main_col in df.columns:
                    styles.loc[:, main_col] = (
                        "background-color: #808000; font-weight: 700; "
                        "border-left: 2px solid #888; border-right: 2px solid #888;"
                    )
                return styles

            styled = raw.style.apply(lambda _: _highlight_main(raw), axis=None)

            st.subheader(f"Probability Matrix of Pr(bps ({v}) >) — window {max(enter_hrs-10, 1)} to {enter_hrs + 10} hrs")
            st.text(f"Mode: {mode}")
            st.dataframe(styled, use_container_width=False)

            # ============================================================
            # 4) DISPLAY LARGEST MOVES DATA
            # ============================================================
            movt_df = display_data['movt_df']
            st.subheader(f"Latest bps values for {mode}, version = {v}, hours = {enter_hrs}")
            st.text(f'Total observations: {len(movt_df)}')
            st.dataframe(movt_df.head(10), use_container_width=True)

            # ============================================================
            # 5) DOWNLOADS VIA CONTROLLER
            # ============================================================
            excel_file, my_matrix_ver = prepare_matrix_download(prob_matrix_dic_plots)

            valid_keys = [ver for ver in prob_matrix_dic_plots.keys()]
            st.download_button(
                label=f"Download the Probability Matrices for version(s): bps {', bps '.join(list(valid_keys))}",
                data=excel_file,
                file_name=f"Probability Matrix_{'_'.join(my_matrix_ver)}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        else:
            st.write("Please select 1h interval.")
            
    except Exception as e:
        display_text = f'1h interval data unavailable for the current ticker. ({e})'
        st.markdown(f"<p style='color:red;'>{display_text}</p>", unsafe_allow_html=True)

elif tab == "Custom Normalised Returns":
    try:
        # Protected tab
        PASSWORD = "distro" 

        # Initialize authentication state
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False

        if not st.session_state.authenticated:
            st.header("This tab is Password Protected🔒")
            password = st.text_input("Enter Password:", type="password")
            
            if st.button("Login"):
                if password == PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Try again.")
        else:
            st.header("Authorised ✅")
            st.write("This tab contains sensitive information.")
            
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.rerun()

        if st.session_state.authenticated == True:
            # Use stored values from session state
            x = st.session_state.get("x", list(unique_intervals)[0])
            y = st.session_state.get("y", list(unique_instruments)[0])

            st.title("Custom Filtering")

            # Show the version dropdown
            version_value = st.selectbox("Select Version", unique_versions.copy(), index=default_version_index, key='tab4_v')

            # Select bps to analyse
            enter_bps = st.number_input(label="Enter the Observed movement in bps:", min_value=0.00, key='tab4_bps')

            # Add custom session via button
            default_text = f'Distribution of bps ({version_value}) Returns {y} with returns calculated for every {x}'
            finalname = default_text
            filter_sessions = False
            
            # Not include intervals
            if 'd' not in x:
                st.subheader('Add Custom Session')
                tab4check = st.checkbox(label='Add Custom Session', key='tab4check')

                if tab4check:
                    # Add Checkbox to filter by starting day
                    tab4check1 = st.checkbox(label='Calculate Custom Time Difference', key='tab4check1')
                    if tab4check1:
                        # Date inputs
                        start_date = st.date_input(label="Start Date (YYYY/MM/DD)", value=datetime.today().date())
                        end_date = st.date_input(label="End Date (YYYY/MM/DD)", value=datetime.today().date())

                        # Time inputs
                        start_time = st.time_input(label="Start Time (HH:MM)", value='now', help='Directly Type Time in HH:MM')
                        end_time = st.time_input(label="End Time (HH:MM)", value='now', help='Directly Type Time in HH:MM')
                    
                        # Use controller to calculate time difference
                        time_info = calculate_time_difference(start_date, start_time, end_date, end_time)
                        st.markdown(f"<p style='color:red; font-size:14px;'>{time_info['display_text1']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='color:red; font-size:14px;'>{time_info['display_text2']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='color:red; font-size:14px;'>{time_info['display_text3']}</p>", unsafe_allow_html=True)

                    # 1. Select Start time in ET
                    enter_start = st.number_input(label="Enter the start time in ET", min_value=0, max_value=23, step=1)
                    st.caption("Note: The value must be an integer and increase in steps of 1. Eg 1, 2, 3, 4, etc.")

                    # 2. Select number of hours to analyse post the start time
                    enter_hrs = st.number_input(label=f"Enter the time (multiple of {x}) to be searched post the selected time", min_value=0, step=1)
                    st.caption("Note: The value must be an integral multiple of the interval selected")

                    # Add Checkbox to filter by starting day
                    tab4check2 = st.checkbox(label='Filter by Starting Day', key='tab4check2')
                    day_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    
                    # Add Selectbox to select the starting day
                    if tab4check2 == True:
                        enter_start_day = st.selectbox("Select Starting Day", day_list, index=0, key='tab4_sd')
                    else:
                        enter_start_day = ""

                    # Build filter sessions
                    filter_sessions = [(enter_start, enter_hrs, enter_start_day)]

            # Use controller to get filtered dataframe
            selected_df = get_filtered_dataframe(x, y)

            # Determine target column based on filter_sessions
            target_column = 'Group' if filter_sessions else 'US/Eastern Timezone'

            # Use controller to process the custom filter
            results = process_custom_filter(
                selected_df=selected_df,
                filter_sessions=filter_sessions if filter_sessions else None,
                x=x,
                y=y,
                version_value=version_value,
                enter_bps=enter_bps,
                target_column=target_column
            )

            if results.get('error'):
                st.error(results['error'])
            else:
                filtered_df = results['filtered_df']
                stats_plots_dict = results['stats_plots_dict']
                date_range = results['date_range']
                finalname = results.get('name', finalname)

                # Display Filtered Dataframe
                st.subheader('Filtered Dataframe')
                st.text(f'Ticker: {y}')
                st.text(f'Interval: {x}')
                st.text(f'Dates: {date_range["start"]} to {date_range["end"]}')
                st.dataframe(filtered_df, use_container_width=True)

                # Display stats dataframe
                stats_df = stats_plots_dict['stats']
                st.dataframe(stats_df, use_container_width=True)

                # Store probability data in a dataframe
                prob_df = pd.DataFrame(columns=['Description', 'Value'],
                            data=[[f'Probability of bps ({version_value})  > {abs(enter_bps)}',
                                str(round(stats_plots_dict['%>'], 2)) + '%']])

                prob_df.loc[len(prob_df)] = [f'Probability of bps ({version_value})  <= {abs(enter_bps)}',
                                str(round(stats_plots_dict['%<='], 2)) + '%']
                
                prob_df.loc[len(prob_df)] = [f'ZScore for ({version_value}) bps <=  {enter_bps} bps',
                                str((stats_plots_dict['zscore<=']))]

                # Display the probability dataframe
                st.dataframe(prob_df, use_container_width=True)

                # Display the probability plot
                st.subheader(f"Probability Plot for {enter_bps} bps ({version_value}) movement")
                st.pyplot(stats_plots_dict['plot'])

                # Prepare download via controller
                excel_file = prepare_custom_filter_download(
                    filtered_df, prob_df, stats_df, x, y, date_range
                )

                st.download_button(
                    label="Download Excels",
                    data=excel_file,
                    file_name=f"Probability_Stats_Excel_{finalname}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except UnboundLocalError as uble:
        display_text = f'{y} Data unavailable for {x} interval.'
        st.markdown(f"<p style='color:red;'>{display_text}</p>", unsafe_allow_html=True)

    except Exception as e:
        display_text = 'Some error occured. Please try some other parameters and re-run.'
        st.text(e)
        st.markdown(f"<p style='color:red;'>{display_text}</p>", unsafe_allow_html=True)

elif tab == "Event Specific Distro":

    ################################## USER INTERFACE #####################################################
    
    selected_event = st.selectbox("Select an event:", events)

    month_end_days = None
    if(selected_event == 'Month End'):
        month_end_days = st.number_input("Enter the number of days to consider at the end of each month:",
        min_value=1,
        max_value=3,
        step=1,
        value=1
    )

    st.text("Choose filters: ")

    ## ISOLATING EVENT FILTER
    filter_isolated = st.checkbox(
    "Exclude events when there is another event announced x hours prior. (only events in the dropdown)",
    help="Only include event instances that have no other events in the surrounding time window."
    )
    # which tiers to consider when isolating en event.
    filter_tier_list = None
    filter_tiers = [1, 2, 3, 4]
    if(filter_isolated):
        window_hrs = st.number_input(label="Choose x:", min_value=1)
        st.text('x only takes on integer values')
        filter_tier_list = st.multiselect("Choose which tiers to filter", filter_tiers)

    ## GROUPING EVENT FILTER
    group_events = st.checkbox(
    "Group events",
    help="Only consider those event instances when there has been a tier 1 event within +- x hours of it"
    )
    # number of hours to check before and after for the isolation/grouping of event.
    window_hrs = 0
    selected_group_event = ""
     
    # consider event only if there is a tier 1 event within +- window_hrs of the selected event
    if(group_events):
        window_hrs = st.number_input("Enter the window hours")
        st.text("Only integer input is valid")
        selected_group_event = st.selectbox("Choose which events to group", events)

    ## SUB-EVENT FILTER
    sub_event_filter = st.checkbox("Filter based on specific sub-event data", help="Hotter: actual > expected | Colder: actual < expected")
    sub_event_filtering_dict = {}
    if(sub_event_filter):
        selected_sub_events = st.multiselect("Select a sub-event to condition it on:", sub_event_dict[selected_event])

        if(not selected_event in ['Fed Speeches', 'FOMC Minutes', 'Fed Press Conference', 'Month End']):
            for sub_event in selected_sub_events:
                col1, col2 = st.columns([2, 2])
                upper_bound = None
                lower_bound = None

                with col1:
                    lower_bound = st.number_input(f"Lower bound for Actual - Expected for {sub_event}", step=0.0001, format="%.4f")
                with col2:
                    upper_bound = st.number_input(f"Upper bound for Actual - Expected for {sub_event}", step=0.0001, format="%.4f")

                sub_event_filtering_dict[sub_event] = [lower_bound, upper_bound]
        else:
            for sub_event in selected_sub_events:
                sub_event_filtering_dict[sub_event] = []

    ## LAST x OBSERVATIONS FILTER
    last_x_obs = None
    if st.checkbox('Analyze last x instances'):
        last_x_obs = st.number_input('Enter the number of lastest instances to analyze', min_value=2)

    # For analysis of custom hours before or after an event.
    delta1 = st.number_input("Enter the total number of hours:", min_value=-1000, max_value=1000, value=1, step=1,
                          help="Enter custom number of integer hours to analyse. Positive input will analyze after the event and negative input will analyze before the event.")
    
    delta2 = st.number_input("Enter the number of hours to omit immediately before/after:", min_value=-1000, max_value=1000, value=0, step=1,
                          help="Enter custom number of integer hours to omit immediately before/after an event. Positive input will analyze after the event and negative input will analyze before the event.")
    
    st.text("It is benenficial to remove some part of the data from the distro immediately before/after an event so that we can remove the drift caused by initial jerk reaction in the market.")

    # Load event data via controller
    event_data = load_event_data(x, y)
    latest_close_price = event_data['latest_close_price']
    price_data_1m = event_data['price_data_1m']

    if(st.checkbox("Custom pivot price", help='if not used, the pivot price is taken as the latest availabe close price')):
        num = st.text_input("Enter custom pivot price")
        custom_price = convert_ticks_to_decimal(num)
        if custom_price is not None:
            latest_close_price = custom_price
        else:
            st.warning("Please enter a valid value")

    # Custom bin size input
    bin_size = 1
    if(st.checkbox("Custom bin size input")):
        bin_size = st.number_input("Enter the custom bin size" , value = 1)
    
    #execute button
    execute = st.button('Go')
    
    ####################################### BACK-END FUNCTION CALLS VIA CONTROLLER ############################################

    if(execute):
        # Call controller to process event distribution
        results = process_event_distro(
            selected_event=selected_event,
            all_event_ts=event_data['all_event_ts'],
            ohcl_data=event_data['ohcl_data'],
            sub_event_dict=sub_event_dict,
            delta1=delta1,
            delta2=delta2,
            filter_isolated=filter_isolated,
            window_hrs=window_hrs,
            filter_tier_list=filter_tier_list,
            group_events=group_events,
            selected_group_event=selected_group_event,
            sub_event_filter=sub_event_filter,
            sub_event_filtering_dict=sub_event_filtering_dict,
            last_x_obs=last_x_obs,
            month_end_days=month_end_days,
            latest_close_price=latest_close_price,
            bin_size = bin_size
        )

        # Check for errors
        if results.get('error'):
            st.text(results['error'])
        else:
            final_df = results['final_df']
            
            # Display price movement plots
            st.title("Distribution Analysis")
            fig_dict = results['fig_dict']
            n = len(fig_dict)
            cols = st.columns(n)

            for col, (name, fig) in zip(cols, fig_dict.items()):
                with col:
                    st.markdown(name)
                    st.plotly_chart(fig, use_container_width=True)
            
            # Display sub-event deviation distributions (if not month end)
            # Layout: 3 columns x 2 rows grid
            if selected_event != 'Month End' and results.get('deviation_distro_dict'):
                st.header("Sub-event Deviation distribution")
                deviation_distro_dict = results['deviation_distro_dict']
                items = list(deviation_distro_dict.items())
                
                if len(items) > 0:
                    # Create 3x2 grid layout
                    num_cols = 3
                    for row_start in range(0, len(items), num_cols):
                        row_items = items[row_start:row_start + num_cols]
                        cols = st.columns(num_cols)
                        for col, (name, fig) in zip(cols, row_items):
                            with col:
                                st.markdown(name)
                                st.plotly_chart(fig, use_container_width=True)

            # Display pivot tables
            st.write(f"Pivot tables generated about {results['latest_close_price_formatted']}")
            st.write(f"Latest 1m data availabe: {convert_decimal_to_ticks(price_data_1m['Close'].iloc[-1])} at: ", price_data_1m['US/Eastern Timezone'].iloc[-1], 'ET')

            col1, col2, col3 = st.columns(3)
            pivot_tables = results['pivot_tables']

            with col1:
                st.markdown("Based on Absolute Return")
                st.table(pivot_tables[0])

            with col2:
                st.markdown("Based on Return")
                st.table(pivot_tables[1])

            with col3:
                st.markdown("Based on Volatility Return")
                st.table(pivot_tables[2])

            # Download button via controller
            downloadable_excel = prepare_event_distro_download(final_df)

            st.download_button(
                label=f"📥 Download Data",
                data=downloadable_excel,
                file_name='EventSpecificData.xlsx',
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.text('The above file is for:')
            text_output = f"Event: {selected_event} when actual - expected of the sub-events satisfy:\n"
            for event, bounds in sub_event_filtering_dict.items():
                text_output += f"{event}: {bounds}\n"
            st.text(text_output)

            st.text(f'Latest number of such instances being considered: {len(final_df["Start_Date"].unique().tolist())}')
            st.text(f'Time: {delta1-delta2} hrs relative to the event after removing interval of {delta2} hours before/after event')

            if(filter_isolated):
                st.text(f'Event instances where there are other events in a window of ± {window_hrs} hours around it are excluded.')
            if(group_events):
                st.text(f"Only those event instances are considered which have a tier 1 event withiin +- {window_hrs} hours of it")

            st.text('''We use hourly data to plot ZN reaction graphs, with 8:00 ET serving as the standard reference point for how each event hour is treated.
            For events released between 8:01 ET and 8:56 ET, the immediate reaction is measured using the 8:00-9:00 ET candle. Since the event occurs partway through that hour, the post-release price action captured reflects less than a full hour of reaction. If the pre-event window covers the 8 hours prior to the release, it spans 12:00-8:00 ET, which excludes a portion of the hour immediately preceding the release.
            For events released between 8:56 ET and 8:59 ET, the immediate reaction is captured using the 9:00-10:00 ET candle. Any price movement in the final seconds before 9:00—such as a release at 8:59:50 ET—is not reflected in the immediate reaction distribution, as it falls outside the defined post-event window. If the pre-event window again covers the 8 hours prior to the release, it would still span 12:00-8:00 ET, thereby also excluding some of the time immediately before the release.

            Once a sufficient amount of 1-minute data is available, we will transition to that granularity to more accurately capture market reactions to economic releases.''')

    else:
        st.write("Press 'Go' to generate output")

elif tab == "Non-Economic Event Tagging":
    non_eco_event = st.text_input('Enter name of the event')
    tags = ['Market Shift', "Geo", 'Tariff', 'Positioning', 'Election']
    tag = st.selectbox('Select tag', tags)

    comment = st.text_input('Enter Comments')
    name_input = st.text_input("Enter the name of the person entering the event")

    start_date, end_date = st.date_input("Pick a date range", [datetime.date(2024, 1, 1), datetime.date(2025, 1, 15)])

    start_time = st.time_input("Enter the start time in ET")
    end_time = st.time_input("Enter the end time in ET")

    start_timestamp = datetime.datetime.combine(start_date, start_time)
    start_timestamp = pd.Timestamp(start_timestamp).tz_localize('US/Eastern')
    end_timestamp = datetime.datetime.combine(end_date, end_time)
    end_timestamp = pd.Timestamp(end_timestamp).tz_localize('US/Eastern')

    # Get price data via controller
    price_info = get_price_data_for_event(start_timestamp, end_timestamp, x, y)

    # Load existing tagged events via controller
    data = load_tagged_events()

    if st.button("Add Tag"):
        event_info = {
            'event': non_eco_event,
            'tag': tag,
            'comment': comment,
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
            'open': price_info['open'],
            'high': price_info['high'],
            'close': price_info['close'],
            'low': price_info['low'],
            'name': name_input,
        }
        data = add_tagged_event(data, event_info)
        st.success("Event tagged successfully!")
    elif st.button("Delete Tagged Event"):
        event_info = {
            'event': non_eco_event,
            'tag': tag,
            'comment': comment,
            'start_timestamp': str(start_timestamp),
            'end_timestamp': str(end_timestamp),
            'name': name_input,
        }
        data = delete_tagged_event(data, event_info)
        st.success("Record deleted successfully!")

    st.dataframe(data, use_container_width=True)

    if(st.checkbox('Filter for a specific tag')):
        selected_tag = st.selectbox("Select a tag to analyze", tags)
        # Use controller to filter and calculate returns
        filter_results = filter_by_tag(data, selected_tag)
        filter_df = filter_results['filtered_df']
        
        if filter_results['plots']:
            for col_name, fig in filter_results['plots'].items():
                st.plotly_chart(fig, use_container_width=True)
        
        st.text("Records for the selected tag: ")
        st.dataframe(filter_df, use_container_width=True)

elif tab == "Analysis Library":
    # Use tags from controller
    selected_event_tags = st.multiselect("Enter the tag", LIBRARY_TAGS)
    
    # Get matching files via controller
    matching_files = get_matching_files(selected_event_tags)
    
    for file_info in matching_files:
        file_data = read_file_for_download(file_info['path'])
        st.download_button(
            label=f"Download {file_info['name']}",
            data=file_data,
            file_name=file_info['name']
        )
    
    st.subheader("Upload a File")
    uploaded_file = st.file_uploader("Choose a file to upload", type=None)  

    if uploaded_file is not None:
        file_tag = st.multiselect("Enter a tag for the file", LIBRARY_TAGS)
        
        # Preview the filename
        cleaned_tags = [t.lower().replace(" ", "") for t in file_tag]
        tag_str = "_".join(cleaned_tags) if file_tag else ""
        name_part, ext = os.path.splitext(uploaded_file.name)
        new_filename = f"{name_part}_{tag_str}{ext}" if tag_str else uploaded_file.name
        st.text(f"File will be saved as: {new_filename}")

        if st.button("Save File"):
            # Use controller to save file
            result = save_uploaded_file(uploaded_file, file_tag)
            if result['success']:
                st.success(f"File saved as {result['filename']}")
            else:
                st.error(f"Error saving file: {result.get('error', 'Unknown error')}")

elif tab == "Pull back analysis":
    tier1_events = ["CPI" , "Non Farm Payrolls" , "JOLTs" , "PPI" , 'FOMC Minutes' , '20-Year Note Auction']
    event_selected = st.selectbox("Select an event" , tier1_events)

    col1, col2 = st.columns(2)
    with col1:
        trend_establish_threshold = st.number_input("Trend Establish Threshold (bps)", value=3, min_value=1)
    with col2:
        trend_reverse_threshold = st.number_input("Trend Reverse Threshold (bps)", value=5, min_value=1)

    bin_size = 1
    if(st.checkbox("Custom bin size input")):
        bin_size = st.number_input("Enter custom bin size" , value = 1)

    if st.button("Run Pullback Analysis"):
        with st.spinner("Processing..."):
            ohcl = pd.read_csv("/Users/siddhartha/Desktop/CODES/FRGM Codes/ZN1minute_DataBento_1min.csv")
            ohcl['timestamp'] = pd.to_datetime(ohcl['timestamp'])
            ohcl['timestamp'] = ohcl['timestamp'].dt.tz_localize('US/Eastern')

            event_data = get_data("Intraday_data_files_processed_folder_pq", ['EconomicEventsSheet', 'target'], ".csv")
            event_data["events"] = event_data["events"].astype(str)
            event_data = event_data.dropna(subset=["events"])
            event_data = event_data.drop_duplicates(subset=["datetime", "events"], keep="last")
            event_data["cleaned_events"] = event_data["events"].str.strip().str.lower().str.replace(" ", "")
            event_data['datetime'] = pd.to_datetime(event_data['datetime'] , utc = True , errors='coerce')
            event_data['datetime'] = event_data['datetime'].dt.tz_convert('US/Eastern')

            df_list = detect_moves(event_data , trend_establish_threshold , trend_reverse_threshold , event_selected , ohcl)
            df_list = [
                df.drop_duplicates(subset=["timestamp"], keep="last")
                for df in df_list
            ]

            initial_moves_df = df_list[0]
            pullback_moves_df = df_list[1]

            # Save CSVs
            for i in range(2):
                df_list[i].to_csv(f"/Users/siddhartha/Desktop/CODES/FRGM Codes/df_list_{i}.csv")

            st.success(f"Analysis complete! Initial moves: {len(initial_moves_df)}, Pullbacks: {len(pullback_moves_df)}")

            # Display DataFrames
            st.subheader(f"Results for {event_selected}")
            
            tab1, tab2 = st.tabs(["Initial Moves", "Pullbacks"])
            
            with tab1:
                if len(initial_moves_df) > 0 and 'Initial_Move' in initial_moves_df.columns:

                    # Plot PDF for Initial Moves
                    moves_data = initial_moves_df['Initial_Move'].dropna()
                    if len(moves_data) > 1:
                        initial_moves_df['Start_Date'] = initial_moves_df['timestamp']
                        fig_dict = plot_data(initial_moves_df , ['Initial_Move'] , bin_size = bin_size)

                        n = len(fig_dict)
                        cols = st.columns(n)

                        for col, (name, fig) in zip(cols, fig_dict.items()):
                            with col:
                                st.markdown(name)
                                st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(initial_moves_df, use_container_width=True)
                else:
                    st.warning("No initial moves found")
            
            with tab2:
                if len(pullback_moves_df) > 0 and 'Pullback' in pullback_moves_df.columns:
                    # Plot PDF for Pullbacks
                    fig2, ax2 = plt.subplots(figsize=(10, 6))
                    moves_data = pullback_moves_df['Pullback'].dropna()
                    
                    if len(moves_data) > 1:
                        pullback_moves_df['Start_Date'] = pullback_moves_df['timestamp']
                        fig_dict = plot_data(pullback_moves_df , ['Pullback'] , bin_size = bin_size)

                        n = len(fig_dict)
                        cols = st.columns(n)

                        for col, (name, fig) in zip(cols, fig_dict.items()):
                            with col:
                                st.markdown(name)
                                st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(pullback_moves_df, use_container_width=True)
                else:
                    st.warning("No pullbacks found")


