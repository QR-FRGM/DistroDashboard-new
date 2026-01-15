"""
Helper utility functions for DistroDashboard.
Functions moved here from core/utils.py.
"""

import time
import re
import unicodedata
from functools import wraps
import pandas as pd

def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"⏱️ {func.__name__} executed in {end - start:.3f} seconds")
        return result
    return wrapper

# 5.1.1used to remove non-breaking spaces, zero width spaces, leading & lagging spaces from the event data file.
def clean_text(s):
    if pd.isna(s):
        return s
    # Normalize unicode (e.g., smart quotes, composed accents -> standard form)
    s = unicodedata.normalize("NFKC", s)
    # Replace known invisible space-like chars with normal space
    s = re.sub(r"[\u200B-\u200D\uFEFF\u00A0]", " ", s)
    # Collapse multiple spaces/tabs/newlines into one
    s = re.sub(r"\s+", " ", s)
    return s.strip()

#for converting the strings like $1.2B to numeric values. 
# Used for conditional filtering (hotter/colder than exprected) in tab 5
def convert_shorthand(x):
    if pd.isna(x):
        return x

    x = str(x).strip().upper()
    x = x.replace(',', '').replace('$', '')

    # Remove any repeated leading dashes or symbols like "--", "-$", etc.
    while x.startswith('--') or x.startswith('-$') or x.startswith('$$'):
        x = x[1:]

    # Now handle suffix multipliers
    multiplier = 1
    if x.endswith('T'):
        multiplier = 1_000_000_000_000
        x = x[:-1]
    elif x.endswith('M'):
        multiplier = 1_000_000
        x = x[:-1]
    elif x.endswith('B'):
        multiplier = 1_000_000_000
        x = x[:-1]
    elif x.endswith('K'):
        multiplier = 1_000
        x = x[:-1]
    elif x.endswith('%'):
        multiplier = 0.01
        x = x[:-1]

    try:
        return float(x) * multiplier
    except ValueError:
        return pd.to_numeric(x, errors='coerce')

def sanitize_sheet_name(name: str) -> str:
    """Sanitize Excel sheet names by replacing invalid characters and truncating to 31 chars."""
    invalid_chars = ['\\', '/', '*', '?', ':', '[', ']']
    for ch in invalid_chars:
        name = name.replace(ch, "_")  # replace invalid chars with underscore
    return name[:31]  # Excel allows max 31 characters in a sheet name


