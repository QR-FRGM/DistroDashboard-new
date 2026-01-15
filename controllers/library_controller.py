"""
Controller for Tab 6: Analysis Library.
Handles business logic for file management and library operations.
"""

import os


# Default directory for library files
DEFAULT_DIRECTORY = "/mnt/non_eco_events"

# Available tags for library
LIBRARY_TAGS = [
    'CPI', 'PPI', 'PCE Price Index', 'Non Farm Payrolls', 'ISM Manufacturing PMI', 'ISM Services PMI',
    'S&P Global Manufacturing PMI Final', 'S&P Global Services PMI Final', 'Michigan',
    'Jobless Claims', 'ADP', 'JOLTs', 'Challenger Job Cuts', 'Fed Interest Rate Decision',
    'GDP Price Index QoQ Adv', 'Retail Sales', 'Fed Press Conference', 'FOMC Minutes', 'Fed Speeches', 'Month End',
    '2-Year Note Auction', '3-Year Note Auction', '5-Year Note Auction', '7-Year Note Auction', '10-Year Note Auction',
    '20-Year Bond Auction', '30-Year Bond Auction'
]


def get_matching_files(selected_event_tags, file_directory=DEFAULT_DIRECTORY):
    """
    Find files that match all selected event tags.
    
    Args:
        selected_event_tags: List of tags to match
        file_directory: Directory to search
    
    Returns:
        list of dicts with 'name', 'path' for matching files
    """
    matching_files = []
    
    if not os.path.exists(file_directory):
        return matching_files
    
    for file in os.scandir(file_directory):
        display_name, _ = os.path.splitext(file.name)
        # Check if all selected tags are in the filename
        if all(x.lower().replace(" ", "") in display_name.split('_') for x in selected_event_tags):
            matching_files.append({
                'name': file.name,
                'path': file.path,
            })
    
    return matching_files


def save_uploaded_file(uploaded_file, file_tags, file_directory=DEFAULT_DIRECTORY):
    """
    Save an uploaded file with appropriate tags in filename.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        file_tags: List of tags to add to filename
        file_directory: Directory to save to
    
    Returns:
        dict with 'success', 'filename', 'path'
    """
    # Clean and combine tags
    cleaned_tags = [t.lower().replace(" ", "") for t in file_tags]
    tag_str = "_".join(cleaned_tags) if file_tags else ""
    
    # Create new filename with tags
    name, ext = os.path.splitext(uploaded_file.name)
    new_filename = f"{name}_{tag_str}{ext}" if tag_str else uploaded_file.name
    
    # Save file
    save_path = os.path.join(file_directory, new_filename)
    
    try:
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return {
            'success': True,
            'filename': new_filename,
            'path': save_path,
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def read_file_for_download(file_path):
    """
    Read a file and return its contents for download.
    
    Args:
        file_path: Path to the file
    
    Returns:
        bytes: File contents
    """
    with open(file_path, "rb") as f:
        return f.read()


