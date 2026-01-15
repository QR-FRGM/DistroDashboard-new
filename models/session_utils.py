"""
Session utility functions for DistroDashboard.
Functions moved here from core/utils.py.
"""

#2.2 used to add the sessions column in case all data is considered.
def get_session(timestamp):
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


