import json
import re
from typing import List, Dict, Any

def _wrap_values_arrays(json_text: str, per_line: int = 7) -> str:
    """
    Find "values": [ ... ] arrays and reformat them so that each line
    contains up to `per_line` numbers.

    Assumes the arrays contain only numeric literals (ints / floats).
    """

    # Match: "values": [ ... ]  (non-greedy inside the brackets)
    # Keep three groups: prefix, inner body, closing bracket (with indent)
    pattern = re.compile(r'("values"\s*:\s*\[)(.*?)(\n\s*])', re.DOTALL)

    def repl(match: re.Match) -> str:
        prefix, body, closing = match.groups()

        # Extract all numeric tokens inside the array
        nums = re.findall(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', body)
        if not nums:
            # Nothing numeric inside; just return original match
            return match.group(0)

        # Guess the indentation used for items (from the first number line)
        indent_match = re.search(r'\n(\s*)\S', body)
        indent = indent_match.group(1) if indent_match else "      "

        lines = []
        chunk_count = (len(nums) + per_line - 1) // per_line  # number of chunks
        for idx, i in enumerate(range(0, len(nums), per_line)):
            chunk = nums[i:i + per_line]
            # Join chunk into comma-separated string
            chunk_text = ", ".join(chunk)
            # Add trailing comma except for last chunk
            if idx < chunk_count - 1:
                lines.append(f"\n{indent}{chunk_text},")
            else:
                lines.append(f"\n{indent}{chunk_text}")

        return prefix + "".join(lines) + closing

    return pattern.sub(repl, json_text)


def save_json(path: str, data: List[Dict[str, Any]]) -> None:
    if not isinstance(data, list):
        raise TypeError(f"Data should be a list, got: {type(data).__name__}")

    # First create normal pretty JSON
    text = json.dumps(data, indent=2)

    # Then reflow the "values" arrays
    text = _wrap_values_arrays(text, per_line=7)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_json(path: str) -> List[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                # Empty file -> treat as no data
                return []
            return json.loads(content)
    except FileNotFoundError:
        # File doesn't exist yet -> start with empty list
        return []
    except json.JSONDecodeError:
        # Corrupt or invalid JSON -> you can either raise or reset
        # Here we choose to reset to an empty list
        return []

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
