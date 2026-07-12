"""
Test script for image OCR functionality
"""
import sys
from pathlib import Path

# Test if we can import the module
try:
    from ingestion.image import extract_text_from_image
    print("✓ Image module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import image module: {e}")
    sys.exit(1)

# Test with a sample image (you'll need to provide one)
def test_image_ocr():
    # This is a placeholder - you would need an actual image file
    print("\n📸 Image OCR Test")
    print("=" * 50)
    print("To test:")
    print("1. Place a test image in backend/data/test_image.png")
    print("2. Run: python image_test.py")
    print("\nOr use the frontend UI at /query -> Image OCR tab")
    print("\nSupported formats: PNG, JPG, JPEG, GIF, WebP")
    print("Model: llama-3.2-90b-vision-preview (Groq)")

if __name__ == "__main__":
    test_image_ocr()
