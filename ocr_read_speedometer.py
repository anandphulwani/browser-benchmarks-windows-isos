import os
import subprocess
import time
import logging
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
ROOT_DIR = '.'
CROPPED_DIR = os.path.join(os.getcwd(), 'cropped_images')
os.makedirs(CROPPED_DIR, exist_ok=True)

# ROI configurations per folder
roi_configurations = {
    'A01. Win10GhostSpectre SuperLite SE': [
        {'type': 'rectangle', 'box': (761, 510, 1200, 667)},
    ],
    # Default ROI if folder not explicitly defined
    'default': [
        {'type': 'rectangle', 'box': (761, 520, 1200, 677)},
    ]
}

image_extensions = ('.png', '.jpg', '.jpeg')

def process_image(img, roi_list, filename_base):
    concatenated_text = ''
    for idx, roi in enumerate(roi_list, start=1):
        cropped_path = os.path.join(CROPPED_DIR, f"cropped_{filename_base}_{idx}.png")
        try:
            if roi['type'] == 'rectangle':
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

def main():
    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        if os.path.basename(dirpath) == 'Screenshots_SpeedoMeter':
            folder_name = os.path.basename(os.path.dirname(dirpath))
            roi_list = roi_configurations.get(folder_name, roi_configurations['default'])

            extracted_values = []
            for filename in filenames:
                if filename.lower().endswith(image_extensions):
                    image_path = os.path.join(dirpath, filename)
                    try:
                        with Image.open(image_path) as img:
                            filename_base = os.path.splitext(filename)[0]
                            text = process_image(img, roi_list, filename_base)
                            extracted_values.append(text)
                    except Exception as e:
                        logging.error(f"Failed to process image {image_path}: {e}")

            logging.info(f"Extracted Texts for {folder_name}: {', '.join(extracted_values)}")
            import time
            time.sleep(10)
            # Clean up cropped images
            for f in os.listdir(CROPPED_DIR):
                try:
                    os.unlink(os.path.join(CROPPED_DIR, f))
                except Exception as e:
                    logging.warning(f"Failed to delete {f}: {e}")

if __name__ == "__main__":
    main()
