from dash import Dash, dash_table, html, dcc, callback, ctx, Output, Input, State,ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os
from scipy.stats import gaussian_kde, percentileofscore
from probability_matrix import GetMatrix
from io import BytesIO
from datetime import datetime , date
import re
import base64
import custom_filtering_dataframe


from models.data_loader import (
    get_data
)

from models.constants import (
    EVENTS,
    SUB_EVENT_DICT,
    NON_ECO_EVENT_TAGS
)

from views.formatters import (
    convert_decimal_to_ticks,
    convert_ticks_to_decimal
)

from views.exporters import (
    download_combined_excel,
)

from views.table_builders import(
    get_pivot_tables
)

from views.plotting import plot_data

from controllers.probability_controller import (
    process_probability_matrix,
    get_probability_display_data,
    prepare_matrix_download
)

from controllers.event_distro_controller import (
    load_event_data,
    process_event_distro,
    filter_outliers,
    prepare_event_distro_download,
)

from controllers.tagging_controller import (
    load_tagged_events,
    add_tagged_event,
    delete_tagged_event,
    get_price_data_for_event,
    filter_by_tag
)

from controllers.library_controller import (
    LIBRARY_TAGS,
    get_matching_files,
    save_uploaded_file,
    read_file_for_download,
)

from models.pullback_analysis import (
    detect_moves,
    conditional_filtering
)

# ------------ MULTI-TAB LAYOUT SETUP -----------

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# ============ TAB 1 LAYOUT ============
def tab1_layout():
    return html.Div([
        html.H4('Session wise Analysis'),

        dcc.Dropdown(
            options=['London 0-7 ET', 'US Open 7-10 ET', 'US Mid 10-15 ET',
                     'US Close 15-17 ET', 'Asia 18-24 ET'],
            value=['London 0-7 ET'], 
            multi=True,
            placeholder='Select sessions',
            id='selected-sessions'
        ),

        dcc.Checklist(['Analyze last x instances'], id='last_x_instances_bool'),

        dcc.Input(id="last_x_instances_val", type="number",
                  style={"display": "none"}),

        dcc.Checklist(['Generate Pivot Tables about a custom price'],
                      id='custom_pivot_price_bool'),

        dcc.Input(id="custom_pivot_price", type="text",
                  style={"display": "none"}, placeholder="112'23"),

        html.Button('Go', id='exec_bool_tab_1', n_clicks=0),

        html.Div(id='output_space_tab_1')
    ], style={"margin": "20px"})

# ============ TAB 2 LAYOUT ============
def tab2_layout():
    return html.Div([

        html.H4("Probability Matrix (Unconditional)"),

        dcc.Dropdown(
            options=['Absolute' , 'Up' , 'Down' , 'No-version'],
            value='Absolute',
            multi=False,
            placeholder='Select version',
            id='selected_version_tab_2',
            style={"marginBottom": "20px"}
        ),

        dcc.Dropdown(
            options=['Non-Event' , 'All Data'],
            value='Non-Event',
            multi=False,
            placeholder='Select type of data',
            id='data_type',
            style={"marginBottom": "20px"}
        ),

        # ----- BPS Input -----
        html.Div([
            html.P("Enter the number of bps:", style={"marginBottom": "2px"}),
            dcc.Input(id="enter_bps_tab_2", type="number", step="any", style={"marginBottom": "10px"}),
            html.P("Note: Must be a float in steps of 0.5 (1, 1.5, 2, 2.5, etc)."),
            html.P("Other values will be rounded to the nearest 0.5.")
        ], style={"marginBottom": "20px"}),

        # ----- HOURS Input -----
        html.Div([
            html.P("Enter the number of hrs:", style={"marginBottom": "2px"}),
            dcc.Input(id="enter_hrs", type="number", style={"marginBottom": "10px"}),
            html.P("Note: Must be an integer (1, 2, 3, 4, etc).")
        ], style={"marginBottom": "20px"}),

        dcc.Dropdown(
            options = ['open-close' , 'high-low' , 'open-high/low'],
            value = 'open-close',
            placeholder="Select mode",
            id="mode",
        ),

        html.Button('Go', id='exec_bool_tab_2', n_clicks=0, style={"marginTop": "10px"}),

        # ----- Output -----
        html.Div(id="output_space_tab_2")

    ], style={"margin": "20px"})

# ============ TAB 3 LAYOUT ============
def tab3_layout():
    return html.Div([
        html.H4("Custom Normalised Returns"),

        dcc.Dropdown(
            options=['Absolute' , 'Up' , 'Down' , 'No-version'],
            value=['Absolute'],
            multi=False,
            placeholder='Select version',
            id='selected_version_tab_3',
            style={"marginBottom": "20px"}
        ),

        # ----- BPS Input -----
        html.Div([
            html.P("Enter the number of bps:", style={"marginBottom": "2px"}),
            dcc.Input(id="enter_bps_tab_3", type="number", step="any", style={"marginBottom": "10px"}),
        ], style={"marginBottom": "10px"}),

        dcc.Checklist(['Add a custom session'], id='custom_session_bool_tab_3'),

        html.Div([
            html.P("Enter the start time in ET"),
            dcc.Input(id="enter_hrs_tab_3", type="number", step=1, style={"marginBottom": "10px"}),
            html.P("Note: The value must be an integer and increase in steps of 1. Eg 1, 2, 3, 4, etc."),
            html.P("Enter the time (multiple of 1h) to be searched post the selected time"),
            dcc.Input(id="delta_hrs_tab_3", type="number", step=1, style={"marginBottom": "10px"}),
            html.P("Note: The value must be an integral multiple of the interval selected"),

            dcc.Checklist(["Filter by Starting Day"] , id = "custom_day_bool_tab_3"),
            html.Div([
                html.P("Select a starting day"),
                dcc.Dropdown(
                    options = ['Monday' , 'Tuesday' , 'Wednesday' , 'Thursday' , 'Friday' , 'Saturday' , 'Sunday'],
                    value = ['Monday'],
                    id = "starting_day_tab_3",
                    placeholder='Select a sarting day',
                )
            ],style={"display": "none"} , id = "custom_day_tab_3")
            
        ],style={"display": "none"}, id = "custom_session"),

        html.Button('Go' , id = "exec_bool_tab_3" , n_clicks=0),

        html.Div(id="output_space_tab_3")
    ], style={"margin": "20px"})

# ============ TAB 4 LAYOUT ============
def tab4_layout():
    return html.Div([
        html.H3("Event Specific Distribution"),

        # Event Selection
        html.Div([
            html.P("Select an event:"),
            dcc.Dropdown(
                id="selected_event_tab_4",
                options=[{"label": e, "value": e} for e in EVENTS],
                value="CPI",
                clearable=False,
                style={"marginBottom": "15px"}
            ),
        ]),

        # Month End Days (conditional)
        html.Div(
            id="month_end_container_tab_4",
            children=[
                html.P("Enter the number of days to consider at the end of each month:"),
                dcc.Input(id="month_end_days_tab_4", type="number", min=1, max=3, step=1, value=1),
            ],
            style={"display": "none", "marginBottom": "15px"}
        ),

        html.P("Choose filters:", style={"fontWeight": "bold", "marginTop": "20px"}),

        # Isolate Event Filter
        dcc.Checklist(
            id="filter_isolated_bool_tab_4",
            options=[{"label": " Exclude events when there is another event announced x hours prior", "value": True}],
            value=[],
            style={"marginBottom": "10px"}
        ),

        # Isolate Event Inputs (conditional)
        html.Div(
            id="filter_isolated_inputs_tab_4",
            children=[
                html.P("Choose x (window hours):"),
                dcc.Input(id="window_hrs_isolated_tab_4", type="number", min=1, step=1, value=4),
                html.P("x only takes on integer values", style={"fontSize": "12px", "color": "gray"}),
                html.P("Choose which tiers to filter:"),
                dcc.Dropdown(
                    id="filter_tier_list_tab_4",
                    options=[{"label": str(t), "value": t} for t in [1, 2, 3, 4]],
                    multi=True,
                    placeholder="Select tiers..."
                ),
            ],
            style={"display": "none", "marginLeft": "20px", "marginBottom": "15px"}
        ),

        # Group Events Filter
        dcc.Checklist(
            id="group_events_bool_tab_4",
            options=[{"label": " Group events (consider only when tier 1 event within ± x hours)", "value": True}],
            value=[],
            style={"marginBottom": "10px"}
        ),

        # Group Events Inputs (conditional)
        html.Div(
            id="group_events_inputs_tab_4",
            children=[
                html.P("Enter the window hours:"),
                dcc.Input(id="window_hrs_group_tab_4", type="number", min=1, step=1, value=4),
                html.P("Only integer input is valid", style={"fontSize": "12px", "color": "gray"}),
                html.P("Choose which events to group:"),
                dcc.Dropdown(
                    id="selected_group_event_tab_4",
                    options=[{"label": e, "value": e} for e in EVENTS],
                    value="CPI",
                    clearable=False
                ),
            ],
            style={"display": "none", "marginLeft": "20px", "marginBottom": "15px"}
        ),

        # Sub-Event Filter
        dcc.Checklist(
            id="sub_event_filter_bool_tab_4",
            options=[{"label": " Filter based on specific sub-event data (Hotter: actual > expected | Colder: actual < expected)", "value": True}],
            value=[],
            style={"marginBottom": "10px"}
        ),

        # Sub-Event Inputs (conditional)
        html.Div(
            id="sub_event_filter_inputs_tab_4",
            children=[
                html.P("Select sub-events to condition on:"),
                dcc.Dropdown(
                    id="selected_sub_events_tab_4",
                    options=[],  # Populated dynamically based on selected_event
                    multi=True,
                    placeholder="Select sub-events..."
                ),
                html.Div(id="sub_event_bounds_container_tab_4"),  # Dynamic bounds inputs
            ],
            style={"display": "none", "marginLeft": "20px", "marginBottom": "15px"}
        ),

        # Last X Instances Filter
        dcc.Checklist(
            id="last_x_obs_bool_tab_4",
            options=[{"label": " Analyze last x instances", "value": True}],
            value=[],
            style={"marginBottom": "10px"}
        ),

        # Last X Instances Input (conditional)
        html.Div(
            id="last_x_obs_input_tab_4",
            children=[
                html.P("Enter the number of latest instances to analyze:"),
                dcc.Input(id="last_x_obs_val_tab_4", type="number", min=2, step=1, value=10),
            ],
            style={"display": "none", "marginLeft": "20px", "marginBottom": "15px"}
        ),

        html.Hr(),

        # Delta1 - Hours to analyze
        html.Div([
            html.P("Enter the total number of hours to analyze:"),
            dcc.Input(id="delta1_tab_4", type="number", min=-1000, max=1000, step=1, value=1),
            html.P("Positive = after event, Negative = before event", style={"fontSize": "12px", "color": "gray"}),
        ], style={"marginBottom": "15px"}),

        # Delta2 - Hours to omit
        html.Div([
            html.P("Enter the number of hours to omit immediately before/after:"),
            dcc.Input(id="delta2_tab_4", type="number", min=-1000, max=1000, step=1, value=0),
            html.P("Removes initial jerk reaction from the distribution", style={"fontSize": "12px", "color": "gray"}),
        ], style={"marginBottom": "15px"}),

        # Custom Pivot Price
        dcc.Checklist(
            id="custom_pivot_bool_tab_4",
            options=[{"label": " Use custom pivot price (default: latest close)", "value": True}],
            value=[],
            style={"marginBottom": "10px"}
        ),

        # Custom Pivot Price Input (conditional)
        html.Div(
            id="custom_pivot_input_tab_4",
            children=[
                html.P("Enter custom pivot price (e.g., 112'23):"),
                dcc.Input(id="custom_pivot_val_tab_4", type="text", placeholder="112'23"),
            ],
            style={"display": "none", "marginLeft": "20px", "marginBottom": "15px"}
        ),

        # Custom bin size input
        dcc.Checklist(
            id = "bool_custom_bin_size_tab_4",
            options=[{"label": " Use custom bin size (default: 1)", "value": True}],
            value=[],
            style={"marginBottom": "10px"}
        ),
        html.Div(
            id = "custom_bin_size_input",
            children = [
                dcc.Input(id="custom_bin_size_tab_4", type="number"),
            ],
            style={"display": "none", "marginLeft": "20px", "marginBottom": "15px"}
        ),

        # Handling outliers
        dcc.Checklist(
            id = "remove_outliers_bool_tab_4",
            options = [{"label": "Remove outliers", "value": False}],
            value = [],
            style={"marginBottom": "10px"}
        ),

        # Go Button
        html.Button("Go", id="exec_bool_tab_4", n_clicks=0, 
                    style={"marginTop": "20px", "padding": "10px 30px", "fontSize": "16px"}),

        # Output Space
        html.Div(id="output_space_tab_4", style={"marginTop": "30px"})

    ], style={"margin": "20px"})

# ============ TAB 5 LAYOUT ============
def tab5_layout():
    return html.Div([

        html.H3("Non-Economic Event Tagging"),

        # Event Name
        html.Div([
            html.P("Enter event name", style={"marginBottom": "5px"}),
            dcc.Input(
                id='event_name_tab_5',
                type='text',
                style={"width": "300px"}
            )
        ], style={"marginBottom": "20px"}),

        # Event Tag
        html.Div([
            html.P("Select tag for the event", style={"marginBottom": "5px"}),
            dcc.Dropdown(
                id='event_tag_tab_5',
                options=NON_ECO_EVENT_TAGS,
                value=[],
                style={"width": "300px"}
            )
        ], style={"marginBottom": "20px"}),

        # Comments
        html.Div([
            html.P("Enter comments", style={"marginBottom": "5px"}),
            dcc.Input(
                id='comment_tab_5',
                type='text',
                style={"width": "300px"}
            )
        ], style={"marginBottom": "20px"}),

        # Person Name
        html.Div([
            html.P("Enter the name of the person entering the event", style={"marginBottom": "5px"}),
            dcc.Input(
                id='person_name_tab_5',
                type='text',
                style={"width": "300px"}
            )
        ], style={"marginBottom": "20px"}),

        # Date Range
        html.Div([
            html.P("Enter date range", style={"marginBottom": "5px"}),
            dcc.DatePickerRange(
                id='date_range_tab_5',
                min_date_allowed=date(2015, 1, 1),
                max_date_allowed=date(2050, 1, 1),
            )
        ], style={"marginBottom": "20px"}),

        # Start Time
        html.Div([
            html.P("Enter start time", style={"marginBottom": "5px"}),
            dbc.Input(
                id='start_time_tab_5',
                type='time',
                value='00:00',
                style={"width": "150px"}
            )
        ], style={"marginBottom": "20px"}),

        # End Time
        html.Div([
            html.P("Enter end time", style={"marginBottom": "5px"}),
            dbc.Input(
                id='end_time_tab_5',
                type='time',
                value='00:15',
                style={"width": "150px"}
            )
        ], style={"marginBottom": "30px"}),

        # Add / Delete Buttons
        html.Div([
            html.Button(
                "Add Tag",
                id="add_bool_tab_5",
                n_clicks=0,
                style={"padding": "10px 30px", "fontSize": "16px", "marginRight": "20px"}
            ),
            html.Button(
                "Delete Tagged Event",
                id="del_bool_tab_5",
                n_clicks=0,
                style={"padding": "10px 30px", "fontSize": "16px"}
            )
        ], style={"marginBottom": "30px"}),

        html.Div(id='df_display_tab_5'),

        # Filter checkbox
        html.Div([
            dcc.Checklist(
                id='tag_filter_bool_tab_5',
                options=[{"label": "Filter for specific tag", "value": "show"}],
                value=[]
            ),

            dcc.Dropdown(
                id = 'filter_tags_tab_5',
                options = NON_ECO_EVENT_TAGS,
                style={'display':'none'}
            )
        ], style={"marginBottom": "10px"}),

        html.Button(
            "Go",
            id="filter_bool_tab_5",
            n_clicks=0,
            style={"padding": "10px 30px", "fontSize": "16px", "marginBottom": "20px"}
        ),

        html.Div(id='graphs_tab_5')

    ], style={"margin": "20px"})

# ============ TAB 6 LAYOUT ============
def tab6_layout():
    return html.Div([
        html.H3("Analysis Library"),

        # Search Section
        html.Div([
            html.P("Filter files by tags:", style={"marginBottom": "5px"}),
            dcc.Dropdown(
                id='selected_tags_tab_6',
                options=[{"label": t, "value": t} for t in LIBRARY_TAGS],
                value=[],
                multi=True,
                placeholder="Select tags to filter...",
                style={"marginBottom": "15px"}
            ),
            html.Button(
                "Search Database",
                id='exec_bool_tab_6',
                n_clicks=0,
                style={"padding": "10px 30px", "fontSize": "16px", "marginBottom": "20px"}
            ),
        ]),

        # Download Section - matching files will appear here
        html.Div(id="file_buttons_tab_6", style={"marginBottom": "30px"}),
        
        # Download component
        dcc.Download(id="download_file_tab_6"),

        html.Hr(),

        # Upload Section
        html.Div([
            html.H4("Upload a File"),
            
            dcc.Upload(
                id='upload_file_tab_6',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select a File', style={"color": "blue", "textDecoration": "underline"})
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '2px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'marginBottom': '15px',
                    'backgroundColor': '#fafafa'
                },
            ),
            
            # Show selected file name
            html.Div(id='upload_filename_tab_6', style={"marginBottom": "15px"}),
            
            # Tags for the uploaded file
            html.P("Select tags for the uploaded file:", style={"marginBottom": "5px"}),
            dcc.Dropdown(
                id='upload_tags_tab_6',
                options=[{"label": t, "value": t} for t in LIBRARY_TAGS],
                value=[],
                multi=True,
                placeholder="Select tags...",
                style={"marginBottom": "15px"}
            ),
            
            # Preview filename
            html.Div(id='preview_filename_tab_6', style={"marginBottom": "15px", "fontStyle": "italic"}),
            
            html.Button(
                "Save File",
                id='save_file_tab_6',
                n_clicks=0,
                style={"padding": "10px 30px", "fontSize": "16px"}
            ),
            
            # Save result message
            html.Div(id='save_result_tab_6', style={"marginTop": "15px"}),
        ]),

    ], style={"margin": "20px"})

# ============ TAB 7 LAYOUT ============
def tab7_layout():
    
    return html.Div([
        html.H3("Pullback Analysis"),

        # Event Selection
        html.Div([
            html.P("Select an event:", style={"marginBottom": "5px"}),
            dcc.Dropdown(
                id='event_selected_tab_7',
                options=[{"label": e, "value": e} for e in EVENTS],
                value="CPI",
                clearable=False,
                style={"width": "300px", "marginBottom": "20px"}
            ),
        ]),

        # Threshold Inputs
        dbc.Row([
            dbc.Col([
                html.P("Trend Establish Threshold (bps):", style={"marginBottom": "5px"}),
                dcc.Input(
                    id='trend_establish_tab_7',
                    type='number',
                    value=3,
                    min=1,
                    style={"width": "150px"}
                ),
            ], width=4),
            dbc.Col([
                html.P("Trend Reverse Threshold (bps):", style={"marginBottom": "5px"}),
                dcc.Input(
                    id='trend_reverse_tab_7',
                    type='number',
                    value=5,
                    min=1,
                    style={"width": "150px"}
                ),
            ], width=4),
        ], style={"marginBottom": "20px"}),

        #conditional pullback
        dcc.Checklist(id = 'cond_pullback_bool_tab_7',
                      options=[{"label": "Conditional Pullback Value analysis", "value": True}],
                      style={'marginBottom': "15px"}),

        html.Div(
            id='bounds_input_area_tab_7',
            children=[
                dbc.Row([
                        dbc.Col([html.P("Lower bound:", style={"marginBottom": "5px"}),
                                dcc.Input(
                                    id='lower_bound_tab_7',
                                    type='number',
                                    min= -100,
                                    style={"width": "150px"}),
                            ],width=4
                        ),
                        dbc.Col([html.P("Upper bound:", style={"marginBottom": "5px"}),
                                dcc.Input(
                                    id='upper_bound_tab_7',
                                    type='number',
                                    min= -100,
                                    style={"width": "150px"}
                                ),
                            ],width=4
                        ),
                    ],
                    style={"marginBottom": "20px"}
                )
            ],
            style={'display': 'none'}),

        # Run Button
        html.Button(
            "Run Pullback Analysis",
            id='exec_bool_tab_7',
            n_clicks=0,
            style={"padding": "10px 30px", "fontSize": "16px", "marginBottom": "20px"}
        ),

        # Loading indicator
        dcc.Loading(
            id="loading_tab_7",
            type="default",
            children=[
                html.Div(id='output_space_tab_7')
            ]
        )
        ], style={"margin": "20px"})

# ============ TOP-LEVEL LAYOUT ============

app.layout = html.Div([

    # ===== STATE OF THE DASHBOARD =====
    dcc.Store(id="global_store", storage_type="session"),

    # ===== SIDEBAR =====
    html.Div(
        [
            dbc.Button(
                "☰", id="sidebar_btn", color="secondary", outline=True,
                style={"width": "100%", "marginBottom": "10px"}
            ),

            dbc.Collapse(
                id="collapse_sidebar",
                is_open=True,
                children=[

                    html.P("Instrument:", style={"marginTop": "10px"}),
                    dcc.Dropdown(
                        id="instruments",
                        options=["ZN", "ZB" , "ZT" , "ZF"],
                        value='ZN',
                        clearable=False,
                        style={"marginBottom": "10px"}
                    ),

                    html.P("Frequency:", style={"marginTop": "10px"}),
                    dcc.Dropdown(
                        id="frequency",
                        options=["1m", "15m", "1h", "1d"],
                        value='1h',
                        clearable=False,
                        style={"marginBottom": "10px"}
                    ),

                    html.Hr(),
                    html.Div("These settings apply to all tabs."),
                ],
            ),
        ],
        style={
            "position": "fixed",
            "top": 0,
            "left": 0,
            "bottom": 0,
            "width": "250px",
            "padding": "10px",
            "backgroundColor": "#f8f9fa",
            "overflowY": "auto",
            "boxShadow": "2px 0 5px rgba(0,0,0,0.1)",
            "zIndex": 1000
        }
    ),

    # ===== MAIN CONTENT AREA =====
    html.Div(
        [
            dcc.Tabs(
                id="tabs",
                value="tab1",
                children=[
                    dcc.Tab(label="Session Analysis", value="tab1"),
                    dcc.Tab(label="Probability Matrix", value="tab2"),
                    dcc.Tab(label="Custom Normlised Returns", value="tab3"),
                    dcc.Tab(label="Event Specific Distro", value="tab4"),
                    dcc.Tab(label="Non-Economic Event Tagging", value="tab5"),
                    dcc.Tab(label="Analysis Library", value="tab6"),
                    dcc.Tab(label="Pullback Analysis", value="tab7"),
                ]
            ),
            html.Div(id="tabs-content", style={"marginTop": "20px"})
        ],
        style={"marginLeft": "260px", "padding": "20px"}
    )
])

# --------------- STATE UPDATE CALLBACK -----------
@callback(
    Output("global_store", "data"),
    Input("frequency", "value"),
    Input("instruments", "value")
)
def update_state(freq, inst):
    return{
        "instrument": inst,
        "frequency": freq
    }

# --------------- SIDE BAR COLLAPSE CALLBACK -----------
@callback(
    Output("collapse_sidebar", "is_open"),
    Input("sidebar_btn", "n_clicks"),
    State("collapse_sidebar", "is_open")
)
def toggle_sidebar(n, is_open):
    if n:
        return not is_open
    return is_open

# --------------- TAB SWITCH CALLBACK -----------
@callback(
    Output("tabs-content", "children"),
    Input("tabs", "value")
)
def render_tab(active_tab):
    if active_tab == "tab1":
        return tab1_layout()
    elif active_tab == "tab2":
        return tab2_layout()
    elif active_tab == 'tab3':
        return tab3_layout()
    elif active_tab == 'tab4':
        return tab4_layout()
    elif active_tab == 'tab5':
        return tab5_layout()
    elif active_tab == 'tab6':
        return tab6_layout()
    elif active_tab == 'tab7':
        return tab7_layout()


# ----------- TAB 1 CALLBACKS ----------
@callback(
    Output("last_x_instances_val", "style"),
    Input("last_x_instances_bool", "value")
)
def toggle_last_x_input(checked):
    return {"display": "block"} if checked else {"display": "none"}

@callback(
    Output("custom_pivot_price", "style"),
    Input("custom_pivot_price_bool", "value")
)
def toggle_custom_pivot_input(checked):
    return {"display": "block"} if checked else {"display": "none"}

@callback(
    Output("output_space_tab_1", "children"),
    Input("exec_bool_tab_1", "n_clicks"),
    Input("global_store" , "data"),
    State("custom_pivot_price", "value"),
    State("last_x_instances_val", "value"),
    State("selected-sessions", "value"),
    State("last_x_instances_bool", "value"),
    State("custom_pivot_price_bool", "value"),
    prevent_initial_call=False
)
def render_tab_1(n_clicks, store_data, pivot_val, last_x_obs_val, selected_sessions,
               last_x_obs_bool, pivot_bool):

    if n_clicks == 0:
        return ""
    else:

        freq = store_data['frequency']
        inst = store_data['instrument']

        intraday_data = get_data('Intraday_data_files_processed_folder_pq', [freq, inst, 'nonevents'], '.parquet')

        intraday_data = intraday_data[['timestamp', 'session', 'Adj Close', 'Close',
                                    'High', 'Low', 'Open', 'Volume',
                                    'US/Eastern Timezone']]

        price_data_1m = get_data('Intraday_data_files_pq', ['1m', 'ZN'], '.parquet')
        latest_close_price = price_data_1m['Close'].iloc[-1]

        # Pivot handling
        if pivot_bool:
            if not pivot_val:
                return html.Div("Please enter a pivot price like 112'23.",
                                style={"color": "red"})

            pivot_price = convert_ticks_to_decimal(pivot_val)

            if pivot_price is None:
                return html.Div(
                    f"Invalid format: {pivot_val}. Use 112'23 format.",
                    style={"color": "red"}
                )
        else:
            pivot_price = latest_close_price

        # Filter
        filtered_intraday_data = intraday_data[
            intraday_data['session'].isin(selected_sessions)
        ]
        filtered_intraday_data['date'] = filtered_intraday_data['US/Eastern Timezone'].dt.date

        final_df = (
            filtered_intraday_data
            .groupby('date')
            .agg(
                open_price=('Open', 'first'),
                close_price=('Close', 'last'),
                high_price=('High', 'max'),
                low_price=('Low', 'min')
            )
        )

        final_df['Return'] = (final_df['close_price'] - final_df['open_price']) * 16
        final_df['Volatility Return'] = (final_df['high_price'] - final_df['low_price']) * 16
        final_df['Absolute Return'] = ((final_df['close_price'] -
                                        final_df['open_price']).abs()) * 16
        final_df = final_df.reset_index()

        if last_x_obs_bool and last_x_obs_val:
            final_df = final_df.tail(last_x_obs_val)

        final_df['Start_Date'] = final_df['date']
        fig_dict = plot_data(final_df,
                            ['Absolute Return', 'Return', 'Volatility Return'])

        # Option A: Two graphs per row (width=6)
        graphs = [dbc.Col(dcc.Graph(figure=fig), width=6)
                for fig in fig_dict.values()]

        # Option B: One graph per row (width=12) - maximum size
        # graphs = [dbc.Col(dcc.Graph(figure=fig), width=12)
        #         for fig in fig_dict.values()]

        # Pivot tables
        custom_percentiles = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80,
                            0.90, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97,
                            0.98, 0.99, 0.995, 0.996, 0.997, 0.998, 0.999, 1]
        required_columns = ['Absolute Return', 'Return', 'Volatility Return']
        pivot_tables_list = get_pivot_tables(final_df, custom_percentiles,
                                            required_columns, pivot_price)

        def df_to_table(df):
            return dash_table.DataTable(
                data=df.to_dict("records"),
                columns=[{"name": c, "id": c} for c in df.columns],
                style_table={"overflowX": "auto"},
                style_cell={"padding": "6px", "textAlign": "left"},
            )

        pivot_tables = [
            dbc.Col(df_to_table(df), width=12//len(pivot_tables_list))
            for df in pivot_tables_list
        ]

        # INFO BOX
        latest_ts = price_data_1m["US/Eastern Timezone"].iloc[-1]
        info_box = html.Div([
            html.H5("Run Information"),
            html.P(f"Plots for: {inst} , {freq}"),
            html.P(f"Selected sessions: {selected_sessions}"),
            html.P(f"Latest Close Price: {convert_decimal_to_ticks(latest_close_price)} at {latest_ts}"),
            html.P(f"Pivot price used: {convert_decimal_to_ticks(pivot_price)}"),
            html.P(f"Number of instances: {len(final_df)}"),
        ], style={
            "padding": "5px",
            "border": "1px solid #aaa",
            "borderRadius": "6px",
            "backgroundColor": "#f1f3f5",
            "marginTop": "10px"
        })

        return html.Div([
            dbc.Row(graphs, justify="around"),
            html.Hr(),
            dbc.Row(pivot_tables, justify="around"),
            info_box
        ])

# ----------- TAB 2 CALLBACKS ----------
@callback(
    Output('output_space_tab_2' , 'children'),
    Input("exec_bool_tab_2" , "n_clicks"),
    State('selected_version_tab_2' , 'value'),
    State('data_type' , 'value'),
    State('enter_bps_tab_2' , 'value'),
    State('enter_hrs' , 'value'),
    State('mode' , 'value')
)
def render_tab_2(n_clicks, version_value, data_type, enter_bps, enter_hrs, mode):

    if n_clicks == 0:
        return ""

    try:
        # --------------------- INPUT VALIDATION ---------------------
        if enter_bps is None:
            return html.Div("Enter the number of bps.", style={"color": "red"})

        if enter_hrs is None:
            return html.Div("Enter the number of hours.", style={"color": "red"})

        v = version_value

        # ============================================================
        # 1) CALL CORE PROBABILITY MATRIX ENGINE
        # ============================================================
        results = process_probability_matrix(enter_bps, enter_hrs, 'ZN', '1h', data_type, version_value)
        prob_matrix_dic_plots = results['prob_matrix_dic']

        display_data = get_probability_display_data(prob_matrix_dic_plots, version_value, enter_bps, enter_hrs, mode)

        # ============================================================
        # 2) BUILD PROBABILITY SUMMARY
        # ============================================================
        prob_df = display_data['prob_df']

        prob_table = dash_table.DataTable(
            data=prob_df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in prob_df.columns],
            style_table={"width": "60%"},
            style_cell={"textAlign": "left", "padding": "6px"}
        )

        # ============================================================
        # 3) PROBABILITY PLOT
        # ============================================================
        fig = display_data['plot']
        plot_graph = dcc.Graph(figure=fig)

        # ============================================================
        # 4) PROBABILITY MATRIX TABLE
        # ============================================================
        raw = display_data['matrix_raw']
        main_col = f"{enter_hrs} hr"

        def _highlight(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            if main_col in df.columns:
                styles.loc[:, main_col] = (
                    "background-color: #808000; font-weight: 700; "
                    "border-left: 2px solid #888; border-right: 2px solid #888;"
                )
            return styles

        styled_df = raw.style.apply(lambda _: _highlight(raw), axis=None)

        # Convert styled df to plain df for DataTable
        matrix_df_clean = styled_df.data

        matrix_df_clean = styled_df.data.reset_index()
        matrix_df_clean = matrix_df_clean.rename(columns={'index': 'bps'})

        matrix_table = dash_table.DataTable(
            data=matrix_df_clean.to_dict("records"),
            columns=[{"name": c, "id": c} for c in matrix_df_clean.columns],
            style_table={"overflowX": "scroll"},
            style_cell={"minWidth": "80px", "padding": "4px"}
        )

        # ============================================================
        # 5) LARGEST MOVEMENTS TABLE
        # ============================================================
        movt_df = display_data['movt_df'].copy()
        if 'Datetime' in movt_df.columns:
            movt_df['Datetime'] = movt_df['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

        largest_moves_table = dash_table.DataTable(
            data=movt_df.head(10).to_dict("records"),
            columns=[{"name": c, "id": c} for c in movt_df.columns],
            style_table={"overflowX": "auto"},
            style_cell={"padding": "6px"}
        )

        # ============================================================
        # 6) DOWNLOAD EXCEL
        # ============================================================
        excel_data, my_matrix_ver = prepare_matrix_download(prob_matrix_dic_plots)
        excel_base64 = base64.b64encode(excel_data.getvalue()).decode()

        excel_button = html.Div([
            html.Br(),
            html.A(
                "Download Probability Matrices (Excel)",
                href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," +
                     excel_base64,
                download=f"prob_matrix_{my_matrix_ver}.xlsx"
            )
        ])

        # ============================================================
        # FINAL OUTPUT RETURN
        # ============================================================
        return html.Div([
            html.H4("Probability Summary"),
            prob_table,

            html.Hr(),

            html.H4(f"Probability Plot ({mode})"),
            plot_graph,

            html.Hr(),

            html.H4(f"Probability Matrix Window — {max(enter_hrs-10, 1)} to {enter_hrs+10} hrs"),
            matrix_table,

            html.Hr(),

            html.H4("Largest Movements"),
            largest_moves_table,

            html.Hr(),

            html.H4("Downloads"),
            excel_button
        ])

    except Exception as e:
        return html.Div(f"Error: {e}", style={"color": "red"})

# ----------- TAB 3 CALLBACKS ----------
@callback(
    Output("custom_session", "style"),
    Input("custom_session_bool_tab_3" , "value")
)
def toggle_custom_session_input(trigger):
    return {"display": "block"} if trigger else {"display": "none"}

@callback(
    Output("custom_day_tab_3", "style"),
    Input("custom_day_bool_tab_3" , "value")
)
def toggle_custom_days_input(trigger):
    return {"display": "block"} if trigger else {"display": "none"}

@callback(
    Output("output_space_tab_3", "children"),
    Input("exec_bool_tab_3", "n_clicks"),
    State("selected_version_tab_3", "value"),
    State("enter_bps_tab_3", "value"),
    State("custom_session_bool_tab_3", "value"),
    State("enter_hrs_tab_3", "value"),
    State("delta_hrs_tab_3", "value"),
    State("custom_day_bool_tab_3", "value"),
    State("starting_day_tab_3", "value"),
    State("global_store", "data"),
)
def render_tab_3(
    n_clicks,
    version_value,
    enter_bps,
    custom_session_flag,
    enter_start,
    delta_hours,
    custom_day_flag,
    starting_day,
    store_data
):
    if n_clicks == 0:
        return ""

    try:
        # --------------------------------------------
        # Extract stored values
        # --------------------------------------------
        freq = store_data["frequency"]
        inst = store_data["instrument"]

        default_text = (
            f"Distribution of bps ({version_value}) Returns {inst} "
            f"with returns calculated for every {freq}"
        )
        finalname = default_text

        # --------------------------------------------
        # Custom session logic
        # --------------------------------------------
        filter_sessions = False
        session_list = []

        if custom_session_flag:
            if enter_start is not None and delta_hours is not None:
                start_day = starting_day if custom_day_flag else ""
                session_list.append((enter_start, delta_hours, start_day))
                filter_sessions = True

        # --------------------------------------------
        # Load dataframe
        # --------------------------------------------
        selected_df = custom_filtering_dataframe.get_dataframe(
            freq, inst, "Intraday_data_files_pq"
        )

        # Clean and sort
        finalcsv = selected_df.copy()
        finalcsv.index = finalcsv[finalcsv.columns[-1]]
        finalcsv.drop_duplicates(inplace=True)
        finalcsv.dropna(inplace=True, how="all")
        finalcsv.sort_index(inplace=True)
        finalcsv = finalcsv.loc[~finalcsv.index.duplicated(keep="last")]

        finalstart = str(finalcsv.index[0])[:10]
        finalend = str(finalcsv.index[-1])[:10]

        # --------------------------------------------
        # Filtering
        # --------------------------------------------
        if filter_sessions:
            filtered_df = custom_filtering_dataframe.filter_dataframe(
                selected_df,
                session_list,
                "",
                "US/Eastern Timezone",
                "US/Eastern",
                freq,
                inst,
            )

            session = session_list[0]
            ses_text = (
                f"{session[2]} {session[0]} ET → {session[0]} ET+{session[1]}{freq[-1]}"
            )
            finalname = f"{default_text} | Session: {ses_text} | Dates: {finalstart}-{finalend}"

            stats_plots_dict = custom_filtering_dataframe.calculate_stats_and_plots(
                filtered_df,
                finalname,
                version=version_value,
                check_movement=enter_bps,
                interval=freq,
                ticker=inst,
                target_column="Group",
            )

        else:
            finalname = f"{default_text} | Dates: {finalstart}-{finalend}"

            filtered_df = custom_filtering_dataframe.filter_dataframe(
                selected_df,
                "",
                "",
                "US/Eastern Timezone",
                "US/Eastern",
                freq,
                inst,
            )

            stats_plots_dict = custom_filtering_dataframe.calculate_stats_and_plots(
                filtered_df,
                finalname,
                version=version_value,
                check_movement=enter_bps,
                interval=freq,
                ticker=inst,
                target_column="US/Eastern Timezone",
            )

        # --------------------------------------------
        # Probability table
        # --------------------------------------------
        prob_df = pd.DataFrame(columns=["Description", "Value"])
        prob_df.loc[len(prob_df)] = [
            f"Probability of bps ({version_value}) > {abs(enter_bps)}",
            f"{round(stats_plots_dict['%>'],2)}%",
        ]
        prob_df.loc[len(prob_df)] = [
            f"Probability of bps ({version_value}) <= {abs(enter_bps)}",
            f"{round(stats_plots_dict['%<='],2)}%",
        ]
        prob_df.loc[len(prob_df)] = [
            f"ZScore for ({version_value}) <= {enter_bps} bps",
            str(stats_plots_dict["zscore<="]),
        ]

        # --------------------------------------------
        # Build layout
        # --------------------------------------------
        return html.Div(
            [
                html.H3(f"{inst} | {freq} | {finalstart} → {finalend}"),
                html.Hr(),

                html.H4("Filtered DataFrame"),
                html.Pre(filtered_df.head(20).to_string()),

                html.H4("Descriptive Statistics"),
                html.Pre(stats_plots_dict["stats"].to_string()),

                html.H4("Probability Table"),
                html.Pre(prob_df.to_string()),

                html.Hr(),
                html.H4("Probability Plot"),
                dcc.Graph(figure=stats_plots_dict["plot"]),
            ]
        )

    except Exception as e:
        return html.Div(
            [
                html.H4("Error Occurred", style={"color": "red"}),
                html.Pre(str(e)),
            ]
        )
    
# ----------- TAB 4 CALLBACKS ----------
@callback(
    Output("month_end_container_tab_4", "style"),
    Input("selected_event_tab_4", "value")
)
def toggle_month_end_input(selected_event):
    if selected_event == "Month End":
        return {"display": "block", "marginBottom": "15px"}
    return {"display": "none"}

@callback(
    Output("filter_isolated_inputs_tab_4", "style"),
    Input("filter_isolated_bool_tab_4", "value")
)
def toggle_isolated_inputs(checked):
    if checked:
        return {"display": "block", "marginLeft": "20px", "marginBottom": "15px"}
    return {"display": "none"}

@callback(
    Output("group_events_inputs_tab_4", "style"),
    Input("group_events_bool_tab_4", "value")
)
def toggle_group_inputs(checked):
    if checked:
        return {"display": "block", "marginLeft": "20px", "marginBottom": "15px"}
    return {"display": "none"}

@callback(
    Output("sub_event_filter_inputs_tab_4", "style"),
    Input("sub_event_filter_bool_tab_4", "value")
)
def toggle_sub_event_inputs(checked):
    if checked:
        return {"display": "block", "marginLeft": "20px", "marginBottom": "15px"}
    return {"display": "none"}

@callback(
    Output("selected_sub_events_tab_4", "options"),
    Input("selected_event_tab_4", "value")
)
def update_sub_event_options(selected_event):
    if selected_event and selected_event in SUB_EVENT_DICT:
        return [{"label": se, "value": se} for se in SUB_EVENT_DICT[selected_event]]
    return []

@callback(
    Output("sub_event_bounds_container_tab_4", "children"),
    Input("selected_sub_events_tab_4", "value"),
    State("selected_event_tab_4", "value")
)
def generate_bounds_inputs(selected_sub_events, selected_event):
    if not selected_sub_events:
        return []
    
    # Events that don't need bounds
    no_bounds_events = ['Fed Speeches', 'FOMC Minutes', 'Fed Press Conference', 'Month End']
    
    if selected_event in no_bounds_events:
        return [html.P(f"Selected: {', '.join(selected_sub_events)}", style={"color": "green"})]
    
    children = []
    for sub_event in selected_sub_events:
        children.append(
            html.Div([
                html.P(f"Bounds for {sub_event}:", style={"fontWeight": "bold", "marginTop": "10px"}),
                dbc.Row([
                    dbc.Col([
                        html.P("Lower bound (Actual - Expected):"),
                        dcc.Input(
                            id={"type": "lower_bound", "index": sub_event},
                            type="number",
                            step=0.0001,
                            value=0,
                            style={"width": "100%"}
                        ),
                    ], width=6),
                    dbc.Col([
                        html.P("Upper bound (Actual - Expected):"),
                        dcc.Input(
                            id={"type": "upper_bound", "index": sub_event},
                            type="number",
                            step=0.0001,
                            value=0,
                            style={"width": "100%"}
                        ),
                    ], width=6),
                ]),
            ])
        )
    return children

@callback(
    Output("last_x_obs_input_tab_4", "style"),
    Input("last_x_obs_bool_tab_4", "value")
)
def toggle_last_x_input(checked):
    if checked:
        return {"display": "block", "marginLeft": "20px", "marginBottom": "15px"}
    return {"display": "none"}

@callback(
    Output("custom_pivot_input_tab_4", "style"),
    Input("custom_pivot_bool_tab_4", "value")
)
def toggle_custom_pivot_input(checked):
    if checked:
        return {"display": "block", "marginLeft": "20px", "marginBottom": "15px"}
    return {"display": "none"}

@callback(
    Output("custom_bin_size_input" , "style"),
    Input("bool_custom_bin_size_tab_4" , "value")
)
def toggle_custom_bin_size_input(checked):
    if checked:
        return {"display": "block", "marginLeft": "20px", "marginBottom": "15px"}
    return {"display": "none"}

@callback(
    Output("output_space_tab_4", "children"),
    Input("exec_bool_tab_4", "n_clicks"),
    State("global_store", "data"),
    State("selected_event_tab_4", "value"),
    State("month_end_days_tab_4", "value"),
    State("filter_isolated_bool_tab_4", "value"),
    State("window_hrs_isolated_tab_4", "value"),
    State("filter_tier_list_tab_4", "value"),
    State("group_events_bool_tab_4", "value"),
    State("window_hrs_group_tab_4", "value"),
    State("selected_group_event_tab_4", "value"),
    State("sub_event_filter_bool_tab_4", "value"),
    State("selected_sub_events_tab_4", "value"),
    State({"type": "lower_bound", "index": ALL}, "value"),
    State({"type": "upper_bound", "index": ALL}, "value"),
    State("last_x_obs_bool_tab_4", "value"),
    State("last_x_obs_val_tab_4", "value"),
    State("delta1_tab_4", "value"),
    State("delta2_tab_4", "value"),
    State("custom_pivot_bool_tab_4", "value"),
    State("custom_pivot_val_tab_4", "value"),
    State("bool_custom_bin_size_tab_4" , "value"),
    State("custom_bin_size_tab_4" , "value"),
    State("remove_outliers_bool_tab_4" , "value"),
    prevent_initial_call=True
)
def render_tab_4(
    n_clicks, store_data, selected_event, month_end_days,
    filter_isolated_bool, window_hrs_isolated, filter_tier_list,
    group_events_bool, window_hrs_group, selected_group_event,
    sub_event_filter_bool, selected_sub_events, lower_bound , upper_bound,
    last_x_obs_bool, last_x_obs_val,
    delta1, delta2,
    custom_pivot_bool, custom_pivot_val,
    custom_bin_size_bool ,custom_bin_size,
    remove_outliers_bool
):
    if n_clicks == 0:
        return ""

    try:
        freq = store_data.get("frequency", "1h")
        inst = store_data.get("instrument", "ZN")

        # Load event data
        event_data = load_event_data(freq, inst)
        latest_close_price = event_data['latest_close_price']

        # Handle custom pivot price
        if custom_pivot_bool:
            custom_price = convert_ticks_to_decimal(custom_pivot_val)
            if custom_price is not None:
                latest_close_price = custom_price
            else:
                return html.Div("Invalid pivot price format. Use format like 112'23", style={"color": "red"})

        # Build sub-event filtering dict (you'd need pattern matching callbacks for dynamic inputs)
        sub_event_filtering_dict = {}
        # For simplicity, using empty bounds - in full implementation, use pattern matching
        if sub_event_filter_bool and selected_sub_events:
            for i,sub_event in enumerate(selected_sub_events):
                sub_event_filtering_dict[sub_event] = [0, 0]  # Default bounds

        # Determine window hours
        window_hrs = 0
        if filter_isolated_bool:
            window_hrs = window_hrs_isolated or 0
        elif group_events_bool:
            window_hrs = window_hrs_group or 0

        bin_size = 1
        if(custom_bin_size_bool):
            bin_size = custom_bin_size

        # Call controller
        results = process_event_distro(
            selected_event=selected_event,
            all_event_ts=event_data['all_event_ts'],
            ohcl_data=event_data['ohcl_data'],
            sub_event_dict=SUB_EVENT_DICT,
            delta1=delta1 or 1,
            delta2=delta2 or 0,
            filter_isolated=bool(filter_isolated_bool),
            window_hrs=window_hrs,
            filter_tier_list=filter_tier_list or [],
            group_events=bool(group_events_bool),
            selected_group_event=selected_group_event or "",
            sub_event_filter=bool(sub_event_filter_bool),
            sub_event_filtering_dict=sub_event_filtering_dict,
            last_x_obs=last_x_obs_val if last_x_obs_bool else None,
            month_end_days=month_end_days if selected_event == "Month End" else None,
            latest_close_price=latest_close_price,
            bin_size = bin_size
        )

        # Check for errors
        if results.get('error'):
            return html.Div(results['error'], style={"color": "red"})

        final_df = results['final_df']

        # Generate Plotly plots using the existing plot_data function
        fig_dict = results['fig_dict']

        graphs = [dbc.Col(dcc.Graph(figure=fig), width=6) for fig in fig_dict.values()]

        deviation_section = []
        if selected_event != 'Month End' and results.get('deviation_distro_dict'):
            sub_event_deviation = results['deviation_distro_dict']
            deviation_graphs = [
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(name, style={"fontWeight": "bold", "fontSize": "16px"}),
                        dbc.CardBody(dcc.Graph(figure=fig))
                    ]),
                    width=6
                )
                for name, fig in sub_event_deviation.items()
            ]
            deviation_section = [
                html.H3('Sub-Event Deviation'),
                dbc.Row(deviation_graphs, justify="around"),
                html.Hr(),
            ]

        # Build pivot tables
        pivot_tables = results['pivot_tables']

        def df_to_table(df, title):
            return html.Div([
                html.H5(title),
                dash_table.DataTable(
                    data=df.to_dict("records"),
                    columns=[{"name": c, "id": c} for c in df.columns],
                    style_table={"overflowX": "auto"},
                    style_cell={"padding": "6px", "textAlign": "left", "fontSize": "12px"},
                )
            ])

        pivot_cols = dbc.Row([
            dbc.Col(df_to_table(pivot_tables[0], "Based on Absolute Return"), width=4),
            dbc.Col(df_to_table(pivot_tables[1], "Based on Return"), width=4),
            dbc.Col(df_to_table(pivot_tables[2], "Based on Volatility Return"), width=4),
        ])

        # Download button
        excel_data = prepare_event_distro_download(final_df)
        excel_base64 = base64.b64encode(excel_data.getvalue()).decode()

        download_link = html.A(
            "📥 Download Data (Excel)",
            href=f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{excel_base64}",
            download="EventSpecificData.xlsx",
            style={"fontSize": "16px"}
        )

        # Info section
        info_section = html.Div([
            html.P(f"Event: {selected_event}"),
            html.P(f"Instances analyzed: {len(final_df['Start_Date'].unique())}"),
            html.P(f"Time window: {delta1 - delta2} hrs (after omitting {delta2} hrs)"),
            html.P(f"Pivot price: {results['latest_close_price_formatted']}"),
        ], style={"backgroundColor": "#f5f5f5", "padding": "15px", "borderRadius": "5px", "marginTop": "20px"})

        return html.Div([
            html.H3("Distribution Analysis"),
            dbc.Row(graphs, justify="around"),
            html.Hr(),
            *deviation_section,
            html.Hr(),
            html.H3("Pivot Tables"),
            pivot_cols,
            html.Hr(),
            download_link,
            info_section,
        ])

    except Exception as e:
        return html.Div([
            html.H4("Error Occurred", style={"color": "red"}),
            html.Pre(str(e)),
        ])

# ----------- TAB 5 CALLBACKS ----------
@callback(
    Output("filter_tags_tab_5", "style"),
    Input("tag_filter_bool_tab_5", "value")
)
def toggle_filter_tag_input(checked):
    return {"display": "block"} if checked else {"display": "none"}

@callback(
    Output('df_display_tab_5' , 'children'),
    Input("add_bool_tab_5" , 'n_clicks'),
    Input("del_bool_tab_5" , 'n_clicks'),
    State('event_name_tab_5' , 'value'),
    State('event_tag_tab_5' , 'value'),
    State('comment_tab_5' , 'value'),
    State('person_name_tab_5' , 'value'),
    State('date_range_tab_5' , 'start_date'),
    State('date_range_tab_5' , 'end_date'),
    State('start_time_tab_5' , 'value'),
    State('end_time_tab_5' , 'value'),
)
def add_del_event(n_clicks_add, n_clicks_del, event_name, event_tag, comment, person, start_date, end_date, start_time, end_time):
    
    # Helper to build the table with proper styling
    def build_table(data, message=None):
        table = dash_table.DataTable(
            data=data.to_dict("records"),
            columns=[{"name": c, "id": c} for c in data.columns],
            style_table={
                "width": "100%",
                "minWidth": "100%",
            },
            style_cell={
                "padding": "8px",
                "textAlign": "left",
                "fontSize": "12px",
                "whiteSpace": "normal",
                "height": "auto",
                "minWidth": "80px",
                "maxWidth": "200px",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
            },
            style_header={
                "backgroundColor": "#f8f9fa",
                "fontWeight": "bold",
                "borderBottom": "2px solid #dee2e6",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"}
            ],
            page_size=15,
        )
        if message:
            return html.Div([message, table])
        return html.Div([
            html.P("Existing Tagged Events:", style={"fontWeight": "bold", "marginBottom": "10px"}),
            table
        ])
    
    # Load existing data
    data = load_tagged_events()
    
    # Initial load - just show existing data
    if n_clicks_add == 0 and n_clicks_del == 0:
        if data.empty:
            return html.Div("No tagged events yet.", style={"color": "gray", "fontStyle": "italic"})
        return build_table(data)
    
    # Handle add/delete actions
    triggered_id = ctx.triggered_id

    # Parse date strings to date objects
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # Parse time strings to time objects
    start_time_obj = datetime.strptime(start_time, "%H:%M").time()
    end_time_obj = datetime.strptime(end_time, "%H:%M").time()
    
    # Combine and localize
    start_timestamp = datetime.combine(start_date_obj, start_time_obj)
    start_timestamp = pd.Timestamp(start_timestamp).tz_localize('US/Eastern')
    end_timestamp = datetime.combine(end_date_obj, end_time_obj)
    end_timestamp = pd.Timestamp(end_timestamp).tz_localize('US/Eastern')

    # Convert to tz-aware string with offset (no T separator)
    # Format: "2025-11-04 00:00:00-05:00"
    def format_ts_with_offset(ts):
        base = ts.strftime("%Y-%m-%d %H:%M:%S%z")
        # Insert colon in offset: -0500 → -05:00
        return base[:-2] + ':' + base[-2:]
    
    start_timestamp_str = format_ts_with_offset(start_timestamp)
    end_timestamp_str = format_ts_with_offset(end_timestamp)

    price_info = get_price_data_for_event(start_timestamp, end_timestamp, '1h', 'ZN')

    if triggered_id == 'add_bool_tab_5':
        event_info = {
            'event': event_name,
            'tag': event_tag,
            'comment': comment,
            'start_timestamp': start_timestamp_str,
            'end_timestamp': end_timestamp_str,
            'open': price_info['open'],
            'high': price_info['high'],
            'close': price_info['close'],
            'low': price_info['low'],
            'name': person,
        }
        data = add_tagged_event(data, event_info)
        message = html.Div("✅ Event added successfully!", style={"color": "green", "marginBottom": "10px"})

    elif triggered_id == 'del_bool_tab_5':
        event_info = {
            'event': event_name,
            'tag': event_tag,
            'comment': comment,
            'start_timestamp': start_timestamp_str,
            'end_timestamp': end_timestamp_str,
            'name': person,
        }
        data = delete_tagged_event(data, event_info)
        message = html.Div("🗑️ Event deleted successfully!", style={"color": "orange", "marginBottom": "10px"})
    else:
        message = None
    
    return build_table(data, message)
    
@callback(
    Output('graphs_tab_5' , 'children'),
    Input('filter_bool_tab_5' , 'n_clicks'),
    State('filter_tags_tab_5' , 'value')
)
def tag_analysis(n_clicks, selected_tag):
    if n_clicks == 0:
        return ""
    
    data = load_tagged_events()
    filter_results = filter_by_tag(data, selected_tag)
    
    if filter_results['plots'] is None:
        return html.Div("No data found for the selected tag(s).", style={"color": "orange", "fontStyle": "italic"})
    
    fig_dict = filter_results['plots']
    df = filter_results['filtered_df']
    
    graphs = [dbc.Col(dcc.Graph(figure=fig), width=6) for fig in fig_dict.values()]
    
    table = dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_table={
            "width": "100%",
            "minWidth": "100%",
        },
        style_cell={
            "padding": "8px",
            "textAlign": "left",
            "fontSize": "12px",
            "whiteSpace": "normal",
            "height": "auto",
            "minWidth": "80px",
            "maxWidth": "200px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
        },
        style_header={
            "backgroundColor": "#f8f9fa",
            "fontWeight": "bold",
            "borderBottom": "2px solid #dee2e6",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"}
        ],
        page_size=15,
    )

    return html.Div([
        dbc.Row(graphs, justify="around"),
        html.Hr(),
        html.P("Filtered Records:", style={"fontWeight": "bold", "marginTop": "20px"}),
        table
    ])

# ----------- TAB 6 CALLBACKS ----------
@callback(
    Output('file_buttons_tab_6', 'children'),
    Input('exec_bool_tab_6', 'n_clicks'),
    State('selected_tags_tab_6', 'value'),
    prevent_initial_call=True
)
def search_files(n_clicks, selected_tags):
    if not selected_tags:
        return html.Div("Please select at least one tag to search.", style={"color": "orange"})
    
    matching_files = get_matching_files(selected_tags)
    
    if not matching_files:
        return html.Div("No matching files found.", style={"color": "gray", "fontStyle": "italic"})
    
    # Create download buttons for each file
    buttons = []
    for i, file_info in enumerate(matching_files):
        buttons.append(
            html.Div([
                html.Button(
                    f"📥 Download {file_info['name']}",
                    id={'type': 'download_btn_tab_6', 'index': i},
                    n_clicks=0,
                    style={"marginRight": "10px", "marginBottom": "10px", "padding": "8px 20px"}
                ),
                # Store file path in a hidden div
                dcc.Store(id={'type': 'file_path_store', 'index': i}, data=file_info['path']),
            ], style={"display": "inline-block"})
        )
    
    return html.Div([
        html.P(f"Found {len(matching_files)} matching file(s):", style={"fontWeight": "bold", "marginBottom": "10px"}),
        html.Div(buttons)
    ])

@callback(
    Output('download_file_tab_6', 'data'),
    Input({'type': 'download_btn_tab_6', 'index': ALL}, 'n_clicks'),
    State({'type': 'file_path_store', 'index': ALL}, 'data'),
    prevent_initial_call=True
)
def download_file(n_clicks_list, file_paths):
    if not any(n_clicks_list):
        return None
    
    # Find which button was clicked
    triggered = ctx.triggered_id
    if triggered is None:
        return None
    
    idx = triggered['index']
    file_path = file_paths[idx]
    
    if file_path and os.path.exists(file_path):
        return dcc.send_file(file_path)
    
    return None

@callback(
    Output('upload_filename_tab_6', 'children'),
    Output('preview_filename_tab_6', 'children'),
    Input('upload_file_tab_6', 'filename'),
    Input('upload_tags_tab_6', 'value'),
)
def preview_upload(filename, tags):
    if not filename:
        return "", ""
    
    # Generate preview filename with tags
    cleaned_tags = [t.lower().replace(" ", "") for t in (tags or [])]
    tag_str = "_".join(cleaned_tags) if cleaned_tags else ""
    name_part, ext = os.path.splitext(filename)
    new_filename = f"{name_part}_{tag_str}{ext}" if tag_str else filename
    
    return (
        html.Div(f"Selected file: {filename}", style={"color": "green"}),
        f"File will be saved as: {new_filename}"
    )

@callback(
    Output('save_result_tab_6', 'children'),
    Input('save_file_tab_6', 'n_clicks'),
    State('upload_file_tab_6', 'contents'),
    State('upload_file_tab_6', 'filename'),
    State('upload_tags_tab_6', 'value'),
    prevent_initial_call=True
)
def save_file(n_clicks, contents, filename, tags):
    if not contents or not filename:
        return html.Div("Please select a file to upload.", style={"color": "red"})
    
    # Decode the uploaded file content
    import base64
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    # Create a file-like object for save_uploaded_file
    class FileWrapper:
        def __init__(self, name, data):
            self.name = name
            self._data = data
        def getbuffer(self):
            return self._data
    
    file_obj = FileWrapper(filename, decoded)
    result = save_uploaded_file(file_obj, tags or [])
    
    if result['success']:
        return html.Div(f"✅ File saved as: {result['filename']}", style={"color": "green"})
    else:
        return html.Div(f"❌ Error: {result.get('error', 'Unknown error')}", style={"color": "red"})

# ----------- TAB 7 CALLBACKS ----------
@callback(
    Output('bounds_input_area_tab_7' , 'style'),
    Input('cond_pullback_bool_tab_7' , 'value')
)
def toggle_bounds_input(checked):
    return {"display": "block"} if checked else {"display": "none"}

@callback(
    Output('output_space_tab_7', 'children'),
    Input('exec_bool_tab_7', 'n_clicks'),
    State('event_selected_tab_7', 'value'),
    State('trend_establish_tab_7', 'value'),
    State('trend_reverse_tab_7', 'value'),
    State('cond_pullback_bool_tab_7' , 'value'),
    State('lower_bound_tab_7' ,'value'),
    State('upper_bound_tab_7' ,'value'),
    prevent_initial_call=True
)
def run_pullback_analysis(n_clicks, event_selected, trend_establish, trend_reverse , cond_pullback_bool , lower_bound , upper_bound):
    if n_clicks == 0:
        return ""
    
    try:
        # Load OHLC data
        ohcl = pd.read_csv("/Users/siddhartha/Desktop/CODES/FRGM Codes/ZN1minute_DataBento_1min.csv")
        ohcl['timestamp'] = pd.to_datetime(ohcl['timestamp'])
        ohcl['timestamp'] = ohcl['timestamp'].dt.tz_localize('US/Eastern')

        # Load event data
        event_data = get_data("Intraday_data_files_processed_folder_pq", ['EconomicEventsSheet', 'target'], ".csv")
        event_data["events"] = event_data["events"].astype(str)
        event_data = event_data.dropna(subset=["events"])
        event_data = event_data.drop_duplicates(subset=["datetime", "events"], keep="last")
        event_data["cleaned_events"] = event_data["events"].str.strip().str.lower().str.replace(" ", "")
        event_data['datetime'] = pd.to_datetime(event_data['datetime'], utc=True, errors='coerce')
        event_data['datetime'] = event_data['datetime'].dt.tz_convert('US/Eastern')

        # Run analysis
        df_list = detect_moves(event_data, trend_establish, trend_reverse, event_selected, ohcl)
        df_list = [df.drop_duplicates(subset=["timestamp"], keep="last") for df in df_list]

        initial_moves_df = df_list[0]
        pullback_moves_df = df_list[1]

        #conditional pullback filtering
        if cond_pullback_bool:
            initial_moves_df , pullback_moves_df = conditional_filtering(initial_moves_df , pullback_moves_df , lower_bound , upper_bound)

        # Helper to format timestamp as tz-aware string (no T separator)
        # Format: "2025-11-04 00:00:00-05:00"
        def format_ts_with_offset(ts):
            if pd.isna(ts):
                return ""
            base = ts.strftime("%Y-%m-%d %H:%M:%S%z")
            # Insert colon in offset: -0500 → -05:00
            return base[:-2] + ':' + base[-2:]

        # Save CSVs
        initial_moves_df.to_csv(f"/Users/siddhartha/Desktop/CODES/FRGM Codes/initial.csv")
        pullback_moves_df.to_csv(f"/Users/siddhartha/Desktop/CODES/FRGM Codes/pullback.csv")

        # Build Initial Moves content
        initial_content = []
        if len(initial_moves_df) > 0 and 'Initial_Move' in initial_moves_df.columns:
            moves_data = initial_moves_df['Initial_Move'].dropna()
            if len(moves_data) > 1:
                initial_moves_df['Start_Date'] = initial_moves_df['timestamp']
                fig_dict = plot_data(initial_moves_df, ['Initial_Move'])
                graphs = [dbc.Col(dcc.Graph(figure=fig), width=12) for fig in fig_dict.values()]
                initial_content.append(dbc.Row(graphs))
            
            # Format timestamps as tz-aware strings for display
            display_df = initial_moves_df.copy()
            if 'timestamp' in display_df.columns:
                display_df['timestamp'] = display_df['timestamp'].apply(format_ts_with_offset)
            if 'Start_Date' in display_df.columns:
                display_df['Start_Date'] = display_df['Start_Date'].apply(format_ts_with_offset)
            
            initial_content.append(
                dash_table.DataTable(
                    data=display_df.to_dict("records"),
                    columns=[{"name": c, "id": c} for c in display_df.columns],
                    style_table={"overflowX": "auto"},
                    style_cell={"padding": "6px", "textAlign": "left", "fontSize": "12px"},
                    page_size=15,
                )
            )
        else:
            initial_content.append(html.Div("No initial moves found.", style={"color": "orange"}))

        # Build Pullback content
        pullback_content = []
        if len(pullback_moves_df) > 0 and 'Pullback' in pullback_moves_df.columns:
            moves_data = pullback_moves_df['Pullback'].dropna()
            if len(moves_data) > 1:
                pullback_moves_df['Start_Date'] = pullback_moves_df['timestamp']
                fig_dict = plot_data(pullback_moves_df, ['Pullback'])
                graphs = [dbc.Col(dcc.Graph(figure=fig), width=12) for fig in fig_dict.values()]
                pullback_content.append(dbc.Row(graphs))
            
            # Format timestamps as tz-aware strings for display
            display_df = pullback_moves_df.copy()
            if 'timestamp' in display_df.columns:
                display_df['timestamp'] = display_df['timestamp'].apply(format_ts_with_offset)
            if 'Start_Date' in display_df.columns:
                display_df['Start_Date'] = display_df['Start_Date'].apply(format_ts_with_offset)
            
            pullback_content.append(
                dash_table.DataTable(
                    data=display_df.to_dict("records"),
                    columns=[{"name": c, "id": c} for c in display_df.columns],
                    style_table={"overflowX": "auto"},
                    style_cell={"padding": "6px", "textAlign": "left", "fontSize": "12px"},
                    page_size=15,
                )
            )
        else:
            pullback_content.append(html.Div("No pullbacks found.", style={"color": "orange"}))

        # Create tabbed results using Dash Tabs
        return html.Div([
            html.Div(
                f"✅ Analysis complete! Initial moves: {len(initial_moves_df)}, Pullbacks: {len(pullback_moves_df)}",
                style={"color": "green", "fontWeight": "bold", "marginBottom": "20px"}
            ),
            
            html.H4(f"Results for {event_selected}"),
            
            dcc.Tabs([
                dcc.Tab(
                    label="Initial Moves",
                    children=html.Div(initial_content, style={"padding": "20px"})
                ),
                dcc.Tab(
                    label="Pullbacks",
                    children=html.Div(pullback_content, style={"padding": "20px"})
                ),
            ]),
        ])

    except Exception as e:
        return html.Div([
            html.H4("Error Occurred", style={"color": "red"}),
            html.Pre(str(e)),
        ])

# --------------- RUN APP -----------------------
if __name__ == "__main__":
    app.run(debug=True)
