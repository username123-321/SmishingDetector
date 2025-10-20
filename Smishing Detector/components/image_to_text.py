# image_to_text.py
from PIL import Image, ImageOps
import pytesseract
import platform
import cv2
import numpy as np

# Set Tesseract path for Windows
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_image(image_path):
    """
    Extracts text from an SMS image.
    Preprocesses image to keep mainly SMS bubbles.
    """
    try:
        # Load image with OpenCV
        img = cv2.imread(image_path)

        if img is None:
            return ""

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply adaptive threshold to highlight text
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

        # Optional: remove small noise
        kernel = np.ones((2,2), np.uint8)
        clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        # Invert back to normal
        processed = cv2.bitwise_not(clean)

        # Convert back to PIL Image
        pil_img = Image.fromarray(processed)

        # OCR
        text = pytesseract.image_to_string(pil_img, lang='eng')
        return text.strip()

    except Exception as e:
        print(f"Error reading image: {e}")
        return ""
