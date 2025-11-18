from statistics import mean
from typing import Dict, Any, List
import os
import re

from includes.utils import (
    get_latest_file_timestamp,
    dt_to_timestamp_str,
    timestamp_str_to_dt,
)
from includes.store import get_bench_dict
from ocr_read import ocr_reader


# --------- PLUG YOUR 20-ITEM LOGIC HERE ------------------------------------

def get_values_for_folder(folder_path: str, bench_key: str) -> List[float]:
    """
    It should:
      - look at the given folder_path (Screenshots_* folder)
      - compute / read whatever you need
      - return a list of 20 numeric values (float or int)

    'bench_key' will be one of:
      - 'motionmark'
      - 'jetstream'
      - 'speedometer'
    """
    values = ocr_reader(
        debug=False,
        target_folder_name=folder_path,
        benchmark_type=bench_key
    )
    return values


# --------- CORE UPDATE LOGIC -----------------------------------------------

def recompute_benchmark_type_avg(entry: Dict[str, Any]) -> None:
    """
    Recompute entry['benchmark_avg'] from Motionmark / Jetstream / Speedometer values.
    """
    all_means = []
    for key in ["motionmark", "jetstream", "speedometer"]:
        b = get_bench_dict(entry, key)
        raw_vals = b.get("values") or []
        if not raw_vals:
            continue

        if key == "motionmark":
            # Motionmark: extract score, fps, percent from each string
            scores: List[float] = []
            fps_list: List[int] = []
            percents: List[float] = []
            grouped_text: List[str] = []
            for v in raw_vals:
                match = re.match(r"([\d.]+)\s+@(\d+)fps\s+([\d.]+)%", v)
                if match:
                    score, fps, percent = match.groups()
                    scores.append(float(score))
                    fps_list.append(int(fps))
                    percents.append(float(percent))
                    grouped_text.append(f"{float(score):.3f} @{int(fps):.0f}fps {float(percent):.2f}%")
            
            # You can combine them as needed — here we're taking the average of all three metrics
            score_avg = f"{mean(scores):.3f}" if scores else "0.000"
            fps_avg = f"{mean(fps_list):.0f}" if fps_list else "0"
            percent_avg = f"{mean(percents):.2f}" if percents else "0.00"

            average = f"{score_avg} @{fps_avg}fps {percent_avg}%"
            highest = f"{max(grouped_text)}"
            lowest = f"{min(grouped_text)}"
        else:
            # Others: just convert string values to int
            vals: List[float] = []
            for v in raw_vals:
                vals.append(float(v))
            average = f"{mean(vals):.2f}" if key == "speedometer" else f"{mean(vals):.3f}"
            highest = f"{max(vals):.2f}" if key == "speedometer" else f"{max(vals):.3f}"
            lowest = f"{min(vals):.2f}" if key == "speedometer" else f"{min(vals):.3f}"
        entry[key]["average"] = average
        entry[key]["highest"] = highest
        entry[key]["lowest"] = lowest

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
    values = get_values_for_folder(os.path.basename(iso_folder), bench_key)
    if bench_key == "passmark":
        values = values[0].split(" ")
        if len(values) != 6:
            raise ValueError(
                f"get_values_for_folder must return 6 items, got {len(values)} "
                f"for {bench_key} in {iso_folder}"
            )
        bench["main"] = values[0]
        bench["cpu"] = values[1]
        bench["2d"] = values[2]
        bench["3d"] = values[3]
        bench["memory"] = values[4]
        bench["disk"] = values[5]
    else:
        if len(values) != 20:
            raise ValueError(
                f"get_values_for_folder must return 20 items, got {len(values)} "
                f"for {bench_key} in {iso_folder}"
            )

        bench["values"] = values
        recompute_benchmark_type_avg(entry)
    bench["latest"] = latest_str
    entry["status"] = ""
