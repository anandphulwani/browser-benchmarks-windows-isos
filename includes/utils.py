# utils.py

import os
from datetime import datetime
from typing import Optional, Tuple

# ---------- Timestamp helpers ----------

def parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """
    Parse YYYY-MM-DD-HH-mm-SS from a filename like '2025-04-16-09-33-13.png'.
    Returns None if the format doesn't match or extension is not .png.
    """
    base, ext = os.path.splitext(filename)
    if ext.lower() != ".png":
        return None
    try:
        return datetime.strptime(base, "%Y-%m-%d-%H-%M-%S")
    except ValueError:
        return None


def timestamp_str_to_dt(ts_str: str) -> Optional[datetime]:
    """
    Parse a YYYY-MM-DD-HH-mm-SS string or return None if empty/invalid.
    """
    if not ts_str:
        return None
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d-%H-%M-%S")
    except ValueError:
        return None


def dt_to_timestamp_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d-%H-%M-%S")


# ---------- Filesystem helpers ----------

def get_latest_file_timestamp(folder: str) -> Optional[Tuple[str, datetime]]:
    """
    Get the latest PNG file in a folder (by timestamp encoded in filename).
    Returns (filename_without_ext, datetime) or None if no valid files.
    """
    if not os.path.isdir(folder):
        return None

    latest: Optional[Tuple[str, datetime]] = None

    for name in os.listdir(folder):
        ts = parse_timestamp_from_filename(name)
        if ts is None:
            continue

        base, _ = os.path.splitext(name)
        if latest is None or ts > latest[1]:
            latest = (base, ts)

    return latest
