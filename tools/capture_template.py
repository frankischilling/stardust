"""
Template Image Capture Tool
Helps you capture template images for the bot to use.
Position your mouse over the item you want to capture, then run this script.
"""
import mss
import cv2
import numpy as np
import pyautogui
import os
import time

def capture_template():
    """
    Captures a template image at the current mouse position.
    """
    print("=" * 60)
    print("Template Image Capture Tool")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Position your mouse at the CENTER of the log icon")
    print("   (Make sure the log is NOT selected/highlighted)")
    print("2. Press ENTER to capture the area")
    print("3. Enter a filename to save the template")
    print("\nPress ENTER when your mouse is positioned...")
    input()
    
    # Get mouse position
    mouse_x, mouse_y = pyautogui.position()
    print(f"Mouse position: ({mouse_x}, {mouse_y})")
    
    # Ask for size - larger is often better for template matching
    print("\nRecommended sizes:")
    print("  - Small items (20-30 pixels): Use 30-40 pixel capture")
    print("  - Medium items (30-50 pixels): Use 40-64 pixel capture")
    print("  - Large items (50+ pixels): Use 64-80 pixel capture")
    print("  - Recommended for logs: 64 pixels")
    
    size_choice = input("\nCapture size (30/40/50/64/80, or press ENTER for 64): ").strip()
    if not size_choice:
        capture_size = 64
    else:
        try:
            capture_size = int(size_choice)
            if capture_size < 20 or capture_size > 100:
                print("Size should be between 20 and 100, using 64")
                capture_size = 64
        except ValueError:
            print("Invalid size, using 64")
            capture_size = 64
    
    monitor = {
        "top": max(0, mouse_y - capture_size // 2),
        "left": max(0, mouse_x - capture_size // 2),
        "width": capture_size,
        "height": capture_size
    }
    
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(monitor))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Show preview info
    print(f"\nCaptured area: {capture_size}x{capture_size} pixels")
    
    # Get filename - default to log_icon.png
    filename = input("\nEnter filename (press ENTER for 'log_icon.png'): ").strip()
    if not filename:
        filename = "log_icon.png"
    
    # Ensure .png extension
    if not filename.endswith('.png'):
        filename += '.png'
    
    # Ensure templates directory exists
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        print(f"Created {templates_dir} directory")
    
    # Save the template
    filepath = os.path.join(templates_dir, filename)
    cv2.imwrite(filepath, screen_bgr)
    
    print(f"\n✓ Template saved to: {filepath}")
    print(f"  File size: {os.path.getsize(filepath)} bytes")
    print(f"  Dimensions: {screen_bgr.shape[1]}x{screen_bgr.shape[0]} pixels")
    
    # Show a preview option
    preview = input("\nSave a preview image to see what was captured? (y/n): ").strip().lower()
    if preview == 'y':
        preview_path = filepath.replace('.png', '_preview.png')
        # Make preview larger for viewing
        preview_img = cv2.resize(screen_bgr, (capture_size * 4, capture_size * 4), interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(preview_path, preview_img)
        print(f"  Preview saved to: {preview_path}")
    
    # Ask if they want to test it
    test = input("\nTest the template now? (y/n): ").strip().lower()
    if test == 'y':
        print("\nTesting template... Make sure the log is visible in your inventory.")
        time.sleep(2)
        
        import sys
        # Add scripts directory to path
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
        import bot_utils
        from woodcutter import INVENTORY_AREA
        
        # Test with different thresholds
        thresholds = [0.8, 0.7, 0.6, 0.5]
        found = False
        for threshold in thresholds:
            result = bot_utils.find_image(filepath, threshold=threshold, game_area=INVENTORY_AREA)
            if result:
                print(f"✓ Template works! Found at: {result} (threshold: {threshold})")
                found = True
                break
            else:
                print(f"  Threshold {threshold}: Not found")
        
        if not found:
            print("\n✗ Template not found in inventory. Try:")
            print("  - Make sure you have logs in your inventory")
            print("  - Recapture with the log NOT selected/highlighted")
            print("  - Try a slightly larger capture size")
            print("  - Check that inventory area is correct")

def capture_custom_size():
    """
    Captures a template with custom size.
    """
    print("\n" + "=" * 60)
    print("Custom Size Template Capture")
    print("=" * 60)
    print("Recommended: 64 pixels for log icons")
    
    try:
        size = int(input("Enter capture size in pixels (press ENTER for 64): ") or "64")
        if size < 10 or size > 200:
            print("Size should be between 10 and 200 pixels, using 64")
            size = 64
    except ValueError:
        print("Invalid size, using default 64 pixels")
        size = 64
    
    print(f"\nPosition your mouse over the item, then press ENTER...")
    input()
    
    mouse_x, mouse_y = pyautogui.position()
    monitor = {
        "top": max(0, mouse_y - size // 2),
        "left": max(0, mouse_x - size // 2),
        "width": size,
        "height": size
    }
    
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(monitor))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    filename = input("Enter filename (e.g., 'log_icon.png'): ").strip()
    if not filename:
        filename = "template.png"
    if not filename.endswith('.png'):
        filename += '.png'
    
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    filepath = os.path.join(templates_dir, filename)
    cv2.imwrite(filepath, screen_bgr)
    print(f"\n✓ Template saved to: {filepath}")

def main():
    print("Choose an option:")
    print("1. Capture template (64x64 pixels) - Recommended")
    print("2. Capture template (custom size)")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        capture_template()
    elif choice == "2":
        capture_custom_size()
    elif choice == "3":
        print("Exiting...")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()

