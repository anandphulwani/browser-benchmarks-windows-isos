import os
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

# === Configuration ===
OCR_EXECUTABLE = 'Capture2Text_CLI.exe'
THRESHOLD = 128
ROOT_DIR = os.path.join('.', 'data_collected')
CROPPED_DIR = os.path.join(os.getcwd(), 'cropped_images')
os.makedirs(CROPPED_DIR, exist_ok=True)

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
}

# Map screenshot folder base name -> logical type name
SCREENSHOT_TYPE_MAP = {
    'Screenshots_JetStream': 'jetstream',
    'Screenshots_SpeedoMeter': 'speedometer',
    'Screenshots_MotionMark': 'motionmark',
}


def process_image(img, roi_list, filename_base, use_threshold_rectangles=False):
    concatenated_text = ''
    for idx, roi in enumerate(roi_list, start=1):
        cropped_path = os.path.join(CROPPED_DIR, f"cropped_{filename_base}_{idx}.png")
        try:
            if roi['type'] == 'rectangle':
                if use_threshold_rectangles:
                    # MotionMark behavior
                    roi_img = img.crop(roi['box']).convert('L')
                    roi_bw = roi_img.point(lambda x: 255 if x > THRESHOLD else 0)
                    roi_bw.save(cropped_path)
                else:
                    # JetStream & Speedometer behavior
                    roi_img = img.crop(roi['box'])
                    roi_img.save(cropped_path)
            elif roi['type'] == 'hexagon':
                crop_hexagon(img, roi['points'], cropped_path)
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
    return concatenated_text.strip()

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
    aggregated_results = {
        "jetstream": [],
        "motionmark": [],
        "speedometer": []
    }

    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        base = os.path.basename(dirpath)
        if base in screenshot_settings:
            this_type = SCREENSHOT_TYPE_MAP.get(base)

            # If a specific benchmark type is requested, skip others
            if benchmark_type and this_type != benchmark_type:
                continue

            settings = screenshot_settings[base]
            roi_configurations = settings['roi_configurations']
            use_threshold_rectangles = settings['use_threshold_rectangles']

            folder_name = os.path.basename(os.path.dirname(dirpath))

            # If a specific folder name is requested, skip others
            if target_folder_name and folder_name != target_folder_name:
                continue

            roi_list = roi_configurations.get(folder_name, roi_configurations['default'])

            extracted_values = []
            for filename in filenames:
                if filename.lower().endswith(image_extensions):
                    image_path = os.path.join(dirpath, filename)
                    try:
                        with Image.open(image_path) as img:
                            filename_base = os.path.splitext(filename)[0]
                            text = process_image(img, roi_list, filename_base, use_threshold_rectangles)
                            extracted_values.append(text)
                    except Exception as e:
                        logging.error(f"Failed to process image {image_path}: {e}")

            logging.info(f"Extracted Texts for {folder_name}: {', '.join(extracted_values)}")

            # Store results in JSON-serializable structure
            aggregated_results[this_type].append({
                "folder_name": folder_name,
                "values": extracted_values
            })

            import time
            time.sleep(2)
            if not debug:
                # Clean up cropped images
                for f in os.listdir(CROPPED_DIR):
                    try:
                        os.unlink(os.path.join(CROPPED_DIR, f))
                    except Exception as e:
                        logging.warning(f"Failed to delete {f}: {e}")

    if not debug:
        # Remove the cropped_images folder itself when not debugging
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
        choices=['motionmark', 'speedometer', 'jetstream'],
        help='Limit processing to this benchmark type.'
    )
    args = parser.parse_args()
    result = ocr_reader(
        debug=args.debug,
        target_folder_name=args.folder_name,
        benchmark_type=args.type
    )
