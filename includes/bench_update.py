# bench_update.py

from statistics import mean
from typing import Dict, Any, List

import os

from utils import (
    get_latest_file_timestamp,
    dt_to_timestamp_str,
    timestamp_str_to_dt,
)
from store import get_bench_dict


# --------- PLUG YOUR 20-ITEM LOGIC HERE ------------------------------------

def get_20_values_for_folder(folder_path: str, bench_key: str) -> List[float]:
    """
    TODO: Replace this stub with your real logic.

    It should:
      - look at the given folder_path (Screenshots_* folder)
      - compute / read whatever you need
      - return a list of 20 numeric values (float or int)

    'bench_key' will be one of:
      - 'Motionmark'
      - 'Jetstream'
      - 'Speedometer'
    """
    # Dummy implementation so the system runs; replace with your real logic.
    return [0.0] * 20


# --------- CORE UPDATE LOGIC -----------------------------------------------

def recompute_benchmark_avg(entry: Dict[str, Any]) -> None:
    """
    Recompute entry['benchmark_avg'] from Motionmark / Jetstream / Speedometer values.
    """
    all_means = []
    for key in ["Motionmark", "Jetstream", "Speedometer"]:
        b = get_bench_dict(entry, key)
        vals = b.get("values") or []
        if vals:
            all_means.append(mean(vals))

    if all_means:
        entry["benchmark_avg"] = f"{mean(all_means):.2f}"


def update_entry_for_bench(
    entry: Dict[str, Any],
    iso_folder: str,
    screenshots_subfolder: str,
    bench_key: str,
) -> None:
    """
    Apply rules 04(a), 04(b), 04(c) for one bench type.
    """
    folder_path = os.path.join(iso_folder, screenshots_subfolder)

    # 04(a). If folder doesn't exist or has no valid files => do nothing
    latest_file = get_latest_file_timestamp(folder_path)
    if latest_file is None:
        return

    _, latest_dt = latest_file
    latest_str = dt_to_timestamp_str(latest_dt)

    bench = get_bench_dict(entry, bench_key)
    stored_ts_str = bench.get("latest", "")
    stored_dt = timestamp_str_to_dt(stored_ts_str)

    # 04(b). Latest file is same or older than stored -> do nothing
    if stored_dt is not None and latest_dt <= stored_dt:
        return

    # 04(c). Latest file is newer -> recompute the 20 values
    values = get_20_values_for_folder(folder_path, bench_key)
    if len(values) != 20:
        raise ValueError(
            f"get_20_values_for_folder must return 20 items, got {len(values)} "
            f"for {bench_key} in {iso_folder}"
        )

    bench["values"] = values
    bench["latest"] = latest_str

    recompute_benchmark_avg(entry)
    entry["status"] = "Success"
