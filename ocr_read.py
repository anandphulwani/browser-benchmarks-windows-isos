import os
import sys
import re
import subprocess
import time
import logging
import argparse
import json
from PIL import Image, ImageDraw

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def crop_hexagon(img, hexagon_points, save_path):
    mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(mask).polygon(hexagon_points, outline=1, fill=255)
    result = Image.new('RGB', img.size)
    result.paste(img, mask=mask)
    bbox = mask.getbbox()
    hex_cropped = result.crop(bbox)
    hex_cropped.save(save_path)
    return save_path

def colors_close(c, target, tol=8):
    """Return True if RGB color c is within tol of target."""
    return all(abs(c[i] - target[i]) <= tol for i in range(3))

def find_color_runs(img, target_color, tol=8):
    """
    For each row, find contiguous runs of pixels that are close to target_color.
    Returns {y: [(x_start, x_end_inclusive), ...], ...}
    """
    img = img.convert("RGB")
    w, h = img.size
    px = img.load()

    runs_by_row = {}

    for y in range(h):
        x = 0
        row_runs = []
        while x < w:
            # start of a possible run
            if colors_close(px[x, y], target_color, tol):
                start = x
                x += 1
                while x < w and colors_close(px[x, y], target_color, tol):
                    x += 1
                end = x - 1
                row_runs.append((start, end))
            else:
                x += 1

        if row_runs:
            runs_by_row[y] = row_runs

    return runs_by_row

def find_grey_white_pair(
    img,
    grey_color=(64, 64, 64),   # adjust if needed
    white_color=(255, 255, 255),  # adjust if needed
    length=597,
    tol_grey=8,
    tol_white=8
):
    """
    Find one grey horizontal line that has a white horizontal line directly
    under it, with at least `length` overlapping pixels.

    Returns (x_start, y_grey, x_end, y_white) or None if not found.
    """
    img = img.convert("RGB")
    w, h = img.size

    grey_runs = find_color_runs(img, grey_color, tol=tol_grey)
    white_runs = find_color_runs(img, white_color, tol=tol_white)

    for y_grey, runs in grey_runs.items():
        y_white = y_grey + 1
        if y_white >= h or y_white not in white_runs:
            continue

        white_row_runs = white_runs[y_white]

        for gx0, gx1 in runs:
            for wx0, wx1 in white_row_runs:
                # overlap of the two runs
                overlap_start = max(gx0, wx0)
                overlap_end   = min(gx1, wx1)
                if overlap_end >= overlap_start:
                    overlap_len = overlap_end - overlap_start + 1
                    if overlap_len >= length:
                        # found a pair with sufficient overlapping width
                        return overlap_start, y_grey, overlap_start + length - 1, y_white

    return None

# === Configuration ===
OCR_EXECUTABLE = 'Capture2Text_CLI.exe'
THRESHOLD = 128
ROOT_DIR = os.path.join('.', 'data_collected')
CROPPED_DIR = os.path.join(os.getcwd(), 'cropped_images')

image_extensions = ('.png', '.jpg', '.jpeg')

# ROI configurations per script/folder type (kept exactly as in originals)

# 01. ocr_read_jetstream.py
jetstream_roi_configurations = {
    # 'Folder_X': [
    #     {'type': 'rectangle', 'box': (100, 200, 300, 400)},
    #     {'type': 'hexagon', 'points': [(100,150), (150,100), (250,100), (300,150), (250,200), (150,200)]},
    # ],
    'A01. Win10GhostSpectre SuperLite SE': [
        {'type': 'rectangle', 'box': (869, 265, 1073, 320)},
    ],
    'B05. TinyOS': [
        {'type': 'rectangle', 'box': (869, 290, 1073, 345)},
    ],
    'B11. Windows 10 MNF': [
        {'type': 'rectangle', 'box': (869, 290, 1073, 345)},
    ],
    # Default ROI if folder not explicitly defined
    'default': [
        {'type': 'rectangle', 'box': (869, 275, 1073, 330)},
    ]
}

# 02. ocr_read_speedometer.py
speedometer_roi_configurations = {
    'A01. Win10GhostSpectre SuperLite SE': [
        {'type': 'rectangle', 'box': (761, 510, 1200, 667)},
    ],
    # Default ROI if folder not explicitly defined
    'default': [
        {'type': 'rectangle', 'box': (761, 520, 1200, 677)},
    ]
}

# 03. ocr_read_motionmark.py
motionmark_roi_configurations = {
    'A01. Win10GhostSpectre SuperLite SE': [
        {'type': 'rectangle', 'box': (177, 325, 558, 431)},
        {'type': 'rectangle', 'box': (150, 445, 650, 560)},
        {'type': 'hexagon', 'points': [(440, 546), (440, 599), (252, 599), (252, 546), (294, 546), (316, 546)]},
    ],
    'B11. Windows 10 MNF': [
        {'type': 'rectangle', 'box': (177, 345, 558, 451)},
        {'type': 'rectangle', 'box': (150, 465, 650, 580)},
        {'type': 'hexagon', 'points': [(450, 566), (450, 619), (255, 619), (255, 566), (294, 566), (316, 566)]},
    ],
    'B12. Windows 10 Mordern N Fast': [
        {'type': 'rectangle', 'box': (177, 328, 558, 434)},
        {'type': 'rectangle', 'box': (150, 448, 650, 563)},
        {'type': 'hexagon', 'points': [(445, 551), (445, 604), (260, 604), (260, 551), (294, 551), (316, 551)]},
    ],
    # Default ROI if folder not explicitly defined
    'default': [
        {'type': 'rectangle', 'box': (177, 330, 558, 436)},
        {'type': 'rectangle', 'box': (150, 450, 650, 565)},
        {'type': 'hexagon', 'points': [(440, 551), (440, 604), (260, 604), (260, 551), (294, 551), (316, 551)]},
    ]
}

# 04. ocr_read_passmark.py
passmark_roi_configurations = {
    # Default ROI if folder not explicitly defined
    'default': [
        {'type': 'rectangle', 'box': (262, 246, 228, 51)},
        {'type': 'rectangle', 'box': (562, 216, 77, 15)},
        {'type': 'rectangle', 'box': (562, 276, 77, 15)},
        {'type': 'rectangle', 'box': (562, 336, 77, 15)},
        {'type': 'rectangle', 'box': (562, 396, 77, 15)},
        {'type': 'rectangle', 'box': (562, 456, 77, 15)},
    ]
}

# Settings per screenshots folder, to keep original behavior of each script
screenshot_settings = {
    # 01. ocr_read_jetstream.py
    'Screenshots_JetStream': {
        'roi_configurations': jetstream_roi_configurations,
        'use_threshold_rectangles': False,  # plain crop
    },
    # 02. ocr_read_speedometer.py
    'Screenshots_SpeedoMeter': {
        'roi_configurations': speedometer_roi_configurations,
        'use_threshold_rectangles': False,  # plain crop
    },
    # 03. ocr_read_motionmark.py
    'Screenshots_MotionMark': {
        'roi_configurations': motionmark_roi_configurations,
        'use_threshold_rectangles': True,   # grayscale + threshold
    },
    'Screenshots_Passmark': {
        'roi_configurations': passmark_roi_configurations,
        'use_threshold_rectangles': False,
    },
}

# Map screenshot folder base name -> logical type name
SCREENSHOT_TYPE_MAP = {
    'Screenshots_JetStream': 'jetstream',
    'Screenshots_SpeedoMeter': 'speedometer',
    'Screenshots_MotionMark': 'motionmark',
    'Screenshots_Passmark': 'passmark',
}

def process_image(img, roi_list, filename_base, benchmark_type, use_threshold_rectangles=False, offsets=[0, 0]):
    x_offset, y_offset = offsets
    concatenated_text = ''
    
    for idx, roi in enumerate(roi_list, start=1):
        cropped_path = os.path.join(CROPPED_DIR, f"cropped_{filename_base}_{idx}.png")
        try:
            if roi['type'] == 'rectangle':
                # Apply offsets to rectangle box
                x, y, w, h = roi['box']
                adjusted_box = (x + x_offset, y + y_offset, x + w + x_offset, y + h + y_offset)
                
                if use_threshold_rectangles:
                    # MotionMark behavior
                    roi_img = img.crop(adjusted_box).convert('L')
                    roi_bw = roi_img.point(lambda x: 255 if x > THRESHOLD else 0)
                    roi_bw.save(cropped_path)
                else:
                    # JetStream & Speedometer behavior
                    roi_img = img.crop(adjusted_box)
                    roi_img.save(cropped_path)
            elif roi['type'] == 'hexagon':
                # Apply offsets to hexagon points
                adjusted_points = [
                    (x + x_offset, y + y_offset) for (x, y) in roi['points']
                ]
                crop_hexagon(img, adjusted_points, cropped_path)
            else:
                logging.warning(f"Unknown ROI type: {roi['type']}")
                continue
            
            # Run OCR
            result = subprocess.run(
                [OCR_EXECUTABLE, '-i', cropped_path],
                capture_output=True,
                text=True,
                check=True
            )
            text = result.stdout.strip()
            if idx == 1:
                text = text.replace(' ', '')
            
            concatenated_text += text + ' '

        except subprocess.CalledProcessError as e:
            logging.error(f"OCR failed for {cropped_path}: {e}")
        except Exception as e:
            logging.error(f"Error processing ROI {idx} in {filename_base}: {e}")

    concatenated_text = concatenated_text.strip()

    if benchmark_type == "jetstream":
        concatenated_text = concatenated_text.replace("181_.442","181.442")
        concatenated_text = concatenated_text.replace("178-035","178.035")
        regex_to_match = r"^([\d.]+)$"
    elif benchmark_type == "motionmark":
        concatenated_text = concatenated_text.replace("@ ","@")
        concatenated_text = concatenated_text.replace(" %","%")
        regex_to_match = r"^([\d.]+)\s+@(\d+)fps\s+([\d.]+)%$"
    elif benchmark_type == "speedometer":
        regex_to_match = r"^([\d]+(?:\.\d+)?)$"
    elif benchmark_type == "passmark":
        regex_to_match = r"^([\d\w\s\.\/]+)$"

    match = re.search(regex_to_match, concatenated_text)
    if not match:
        print(f"Error: Failed to match pattern for `{benchmark_type}` in fie `{cropped_path}`, got this: `{concatenated_text}`")
        sys.exit(1)

    print(".", end="", flush=True)
    return concatenated_text

def ocr_reader(debug=False, target_folder_name=None, benchmark_type=None):
    """
    benchmark_type: one of None, 'motionmark', 'speedometer', 'jetstream'
    Returns a dict suitable for JSON, e.g.:
    {
        "motionmark": [
            {"folder_name": "...", "values": ["...", "..."]},
        ],
        "speedometer": [],
        "jetstream": []
    }
    """
    os.makedirs(CROPPED_DIR, exist_ok=True)
    aggregated_results = {
        "jetstream": [],
        "motionmark": [],
        "speedometer": [],
        "passmark": []
    }

    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        base = os.path.basename(dirpath)
        if base in screenshot_settings:
            this_type = SCREENSHOT_TYPE_MAP.get(base)
            folder_name = os.path.basename(os.path.dirname(dirpath))
            extracted_values = []

            # If a specific benchmark type is requested, skip others
            if benchmark_type and this_type != benchmark_type:
                continue

            settings = screenshot_settings[base]
            roi_configurations = settings['roi_configurations']
            use_threshold_rectangles = settings['use_threshold_rectangles']

            # If a specific folder name is requested, skip others
            if target_folder_name and folder_name != target_folder_name:
                continue

            roi_list = roi_configurations.get(folder_name, roi_configurations['default'])

            
            for filename in filenames:
                if filename.lower().endswith(image_extensions):
                    image_path = os.path.join(dirpath, filename)
                    try:
                        with Image.open(image_path) as img:
                            offsets = [0, 0]
                            if this_type == "passmark":
                                pair = find_grey_white_pair(img, length=597)
                                if pair:
                                    x0, y_grey, x1, y_white = pair
                                    offset_x = x0 - 113
                                    offset_y = y_white - 193
                                    offsets = [offset_x, offset_y]
                                else:
                                    print(f"No matching grey/white line pair found, for folder: {folder_name} and type: {this_type}")
                                    sys.exit(1)
                            filename_base = os.path.splitext(filename)[0]
                            text = process_image(img, roi_list, filename_base, benchmark_type, use_threshold_rectangles, offsets)
                            extracted_values.append(text)
                    except Exception as e:
                        logging.error(f"Failed to process image {image_path}: {e}")
                print("")
            logging.info(f"Extracted Texts for {folder_name}: {', '.join(extracted_values)}")

            # Store results in JSON-serializable structure
            aggregated_results[this_type].append({
                "folder_name": folder_name,
                "values": extracted_values
            })

    if not debug and os.path.isdir(CROPPED_DIR):
        for f in os.listdir(CROPPED_DIR):
            try:
                os.unlink(os.path.join(CROPPED_DIR, f))
            except Exception as e:
                logging.warning(f"Failed to delete {f}: {e}")
        try:
            os.rmdir(CROPPED_DIR)
        except Exception as e:
            logging.warning(f"Failed to remove cropped_images folder: {e}")

    if target_folder_name and benchmark_type:
        return aggregated_results[benchmark_type][0]['values']
    else:
        return aggregated_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process screenshots and perform OCR.")
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (keep cropped_images folder and its contents).'
    )
    parser.add_argument(
        '--folder-name',
        help='Process only this specific folder name (e.g. "A01. Win10GhostSpectre SuperLite SE").'
    )
    parser.add_argument(
        '--type',
        choices=['motionmark', 'speedometer', 'jetstream', 'passmark'],
        help='Limit processing to this benchmark type.'
    )
    args = parser.parse_args()
    result = ocr_reader(
        debug=args.debug,
        target_folder_name=args.folder_name,
        benchmark_type=args.type
    )
