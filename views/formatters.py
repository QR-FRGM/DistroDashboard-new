"""
Formatting functions for DistroDashboard.
Functions moved here from core/utils.py.
"""

# 5.3 converts price from YF format(decimal) to TV format(ticks)
def convert_decimal_to_ticks(x):
    integer = int(x // 1)
    decimal = x - integer
    ticks = round(decimal * 32)

    # rollover case (e.g. 101'32 → 102'00)
    if ticks == 32:
        integer += 1
        ticks = 0

    # format with leading zero (e.g. 01, 02, 10)
    return f"{integer}'{ticks:02d}"

def convert_ticks_to_decimal(value: str):
    """Convert strings like '112'32' into decimal float (e.g., 112.390625)."""
    try:
        integer, frac = value.strip().split("'")
        return int(integer) + float(frac) / 32
    except Exception:
        return None


