# store.py

import json
from typing import List, Dict, Any

def load_json(path: str) -> List[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_json(path: str, data: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_iso_entry_for_name(data: List[Dict[str, Any]], iso_name: str) -> Dict[str, Any]:
    """
    Find JSON entry for given ISO name, or create a new one with default structure.
    """
    for entry in data:
        if entry.get("name") == iso_name:
            return entry

    new_entry = {
        "parent": None,  # adjust if you have a rule for parent IDs
        "name": iso_name,
        "main": ["", "", "", "", "", "", ""],
        "benchmark_avg": "",
        "passmark": "",
        "Motionmark": {
            "latest": "",
            "values": []
        },
        "Jetstream": {
            "latest": "",
            "values": []
        },
        "Speedometer": {
            "latest": "",
            "values": []
        },
        "status": "Pending",
    }
    data.append(new_entry)
    return new_entry


def get_bench_dict(entry: Dict[str, Any], bench_key: str) -> Dict[str, Any]:
    """
    Ensure entry[bench_key] exists and has the shape {"latest": str, "values": []}.
    """
    bench = entry.get(bench_key)
    if not isinstance(bench, dict):
        bench = {"latest": "", "values": []}
        entry[bench_key] = bench
    bench.setdefault("latest", "")
    bench.setdefault("values", [])
    return bench
