"""
Template Image Fixer
Converts template images to the correct format (BGR, 3 channels) for OpenCV matching.
Run this if you're having template matching issues.
"""
import cv2
import numpy as np
import os

def fix_template(template_path):
    """
    Fixes a template image to ensure it's in BGR format (3 channels).
    """
    if not os.path.exists(template_path):
        print(f"Error: File not found: {template_path}")
        return False
    
    # Load the image
    img = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"Error: Could not load image: {template_path}")
        return False
    
    print(f"Original image shape: {img.shape}")
    print(f"Original image dtype: {img.dtype}")
    
    # Convert to BGR (3 channels)
    if len(img.shape) == 3:
        channels = img.shape[2]
        if channels == 4:  # RGBA or BGRA
            print("Converting RGBA to BGR...")
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif channels == 3:  # Already 3 channels
            print("Image already has 3 channels, ensuring BGR format...")
            img_bgr = img.copy()
        else:
            print(f"Unexpected number of channels: {channels}")
            return False
    elif len(img.shape) == 2:  # Grayscale
        print("Converting grayscale to BGR...")
        img_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        print(f"Unexpected image shape: {img.shape}")
        return False
    
    # Create backup
    backup_path = template_path + ".backup"
    if os.path.exists(backup_path):
        os.remove(backup_path)
    os.rename(template_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Save fixed image
    cv2.imwrite(template_path, img_bgr)
    print(f"✓ Fixed template saved: {template_path}")
    print(f"  New shape: {img_bgr.shape}")
    print(f"  New dtype: {img_bgr.dtype}")
    
    return True

def main():
    print("=" * 60)
    print("Template Image Fixer")
    print("=" * 60)
    
    template_path = "templates/log_icon.png"
    
    if not os.path.exists(template_path):
        print(f"\nTemplate not found: {template_path}")
        print("Please create the template first using:")
        print("  python capture_template.py")
        return
    
    print(f"\nFixing template: {template_path}")
    if fix_template(template_path):
        print("\n✓ Template fixed successfully!")
        print("Try running test_detection.py again.")
    else:
        print("\n✗ Failed to fix template.")

if __name__ == "__main__":
    main()

