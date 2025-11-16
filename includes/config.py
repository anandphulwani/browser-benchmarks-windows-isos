# config.py

import os

# Folder that contains the "ISO Name" folders
ROOT_DIR = os.path.join(".", "data_collected")

# Path to the JSON file you’re maintaining
JSON_PATH = os.path.join(".", "data_benchmarks.json")

# Mapping: subfolder name -> JSON parent key
BENCH_CONFIG = {
    "Screenshots_JetStream": "jetstream",
    "Screenshots_MotionMark": "motionmark",
    "Screenshots_SpeedoMeter": "speedometer",
}

def ensure_paths():
    """Optional helper to sanity-check paths."""
    if not os.path.isdir(ROOT_DIR):
        raise FileNotFoundError(f"ROOT_DIR does not exist or is not a directory: {ROOT_DIR}")
    # JSON file may or may not exist yet – that's okay.
