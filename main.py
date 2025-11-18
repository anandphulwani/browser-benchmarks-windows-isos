import os

from typing import List, Dict, Any

from includes.config import ROOT_DIR, JSON_PATH, BENCH_CONFIG, ensure_paths
from includes.store import load_json, save_json, get_iso_entry_for_name
from includes.bench_update import update_entry_for_bench


def process_all_isos() -> List[Dict[str, Any]]:
    data = load_json(JSON_PATH)

    for iso_name in os.listdir(ROOT_DIR):
        iso_path = os.path.join(ROOT_DIR, iso_name)
        if not os.path.isdir(iso_path):
            continue

        entry = get_iso_entry_for_name(data, iso_name)

        # Process each benchmark folder defined in BENCH_CONFIG
        for subfolder, bench_key in BENCH_CONFIG.items():
            update_entry_for_bench(entry, iso_path, subfolder, bench_key)

    return data


def main():
    ensure_paths()
    data = process_all_isos()
    save_json(JSON_PATH, data)
    print("Benchmark JSON updated.")


if __name__ == "__main__":
    main()
