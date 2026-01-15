"""
Controllers module for DistroDashboard.
Contains orchestration logic between models and views for each tab.
"""

from .session_controller import (
    process_session_analysis,
)

from .probability_controller import (
    process_probability_matrix,
    get_probability_display_data,
    prepare_matrix_download,
)

from .custom_filter_controller import (
    get_filtered_dataframe,
    calculate_time_difference,
    process_custom_filter,
    prepare_custom_filter_download,
)

from .event_distro_controller import (
    load_event_data,
    process_event_distro,
    prepare_event_distro_download,
)

from .tagging_controller import (
    TAGS,
    load_tagged_events,
    add_tagged_event,
    delete_tagged_event,
    get_price_data_for_event,
    filter_by_tag,
)

from .library_controller import (
    LIBRARY_TAGS,
    get_matching_files,
    save_uploaded_file,
    read_file_for_download,
)
