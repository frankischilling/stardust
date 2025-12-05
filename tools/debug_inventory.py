"""
Inventory Debug Tool
Helps you visualize what the bot sees in the inventory area and test template matching.
"""
import sys
import os
# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
import cv2
import numpy as np
import mss
import pyautogui
from woodcutter import INVENTORY_AREA, LOG_ICON_PATH, EMPTY_SLOT_PATH

# Create debug output directory
DEBUG_OUTPUT_DIR = "debug"
if not os.path.exists(DEBUG_OUTPUT_DIR):
    os.makedirs(DEBUG_OUTPUT_DIR)

def capture_inventory_area():
    """Capture and save the inventory area so you can see what the bot sees"""
    print("=" * 60)
    print("Inventory Area Debug Tool")
    print("=" * 60)
    print(f"\nCurrent Inventory Area: {INVENTORY_AREA}")
    print("\nCapturing inventory area...")
    
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(INVENTORY_AREA))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Draw grid lines to visualize inventory slots
    # RuneScape inventory is typically 4 columns x 7 rows = 28 slots
    debug_img = screen_bgr.copy()
    h, w = screen_bgr.shape[:2]
    
    # Draw vertical lines (columns) - 4 columns means 3 dividers
    for i in range(1, 4):
        x = int(w * i / 4)
        cv2.line(debug_img, (x, 0), (x, h), (255, 0, 0), 1)  # Blue lines for columns
    
    # Draw horizontal lines (rows) - 7 rows means 6 dividers
    for i in range(1, 7):
        y = int(h * i / 7)
        cv2.line(debug_img, (0, y), (w, y), (0, 0, 255), 1)  # Red lines for rows
    
    # Label the slots
    slot_width = w / 4
    slot_height = h / 7
    for col in range(4):
        for row in range(7):
            slot_num = row * 4 + col + 1
            x = int(col * slot_width + slot_width / 2)
            y = int(row * slot_height + slot_height / 2)
            cv2.putText(debug_img, str(slot_num), (x - 10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    
    # Save the captured area
    debug_path = os.path.join(DEBUG_OUTPUT_DIR, "inventory_debug.png")
    cv2.imwrite(debug_path, debug_img)
    print(f"✓ Saved inventory area to: {debug_path}")
    print(f"  Size: {screen_bgr.shape[1]}x{screen_bgr.shape[0]} pixels")
    print(f"  Channels: {screen_bgr.shape[2]}")
    print(f"\n⚠ Check the image - it should show all 4 columns (slots 1-28)")
    print(f"   If you only see 3 columns, the inventory area 'left' coordinate is too far right!")
    print(f"   Use option 2 to recalibrate, making sure to click the VERY FIRST slot (top-left).")
    
    return screen_bgr

def test_template_matching(screen_bgr):
    """Test template matching with different thresholds"""
    print("\n" + "=" * 60)
    print("Testing Template Matching")
    print("=" * 60)
    
    if not os.path.exists(LOG_ICON_PATH):
        print(f"✗ Template not found: {LOG_ICON_PATH}")
        return
    
    # Load template
    template = cv2.imread(LOG_ICON_PATH, cv2.IMREAD_UNCHANGED)
    if template is None:
        print(f"✗ Could not load template: {LOG_ICON_PATH}")
        return
    
    print(f"Template shape: {template.shape}")
    
    # Convert template to BGR
    if len(template.shape) == 3:
        channels = template.shape[2]
        if channels == 4:
            template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
            print("Converted template from RGBA to BGR")
        elif channels == 3:
            print("Template already has 3 channels")
    elif len(template.shape) == 2:
        template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
        print("Converted template from grayscale to BGR")
    
    print(f"Template shape after conversion: {template.shape}")
    print(f"Screen shape: {screen_bgr.shape}")
    
    # Test with different thresholds
    print("\nTesting with different thresholds:")
    thresholds = [0.9, 0.8, 0.7, 0.6, 0.5]
    
    for threshold in thresholds:
        result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        print(f"  Threshold {threshold:.1f}: Max match = {max_val:.3f} ", end="")
        if max_val >= threshold:
            print(f"✓ FOUND at {max_loc}")
        else:
            print("✗ Not found")
        
        # Find all matches above threshold
        locations = np.where(result >= threshold)
        matches = list(zip(*locations[::-1]))
        if matches:
            print(f"    Found {len(matches)} match(es)")

def visualize_matches(screen_bgr):
    """Draw matches on the image"""
    print("\n" + "=" * 60)
    print("Creating Visual Debug Image")
    print("=" * 60)
    
    debug_img = screen_bgr.copy()
    
    # Draw log matches
    if os.path.exists(LOG_ICON_PATH):
        template = cv2.imread(LOG_ICON_PATH, cv2.IMREAD_UNCHANGED)
        if template is not None:
            # Convert template
            if len(template.shape) == 3 and template.shape[2] == 4:
                template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
            elif len(template.shape) == 2:
                template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
            
            # Find matches with lower threshold
            result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.6
            locations = np.where(result >= threshold)
            
            h, w = template.shape[:2]
            matches_found = 0
            for pt in zip(*locations[::-1]):
                matches_found += 1
                cv2.rectangle(debug_img, pt, (pt[0] + w, pt[1] + h), (0, 255, 0), 2)
                # Get match confidence
                match_val = result[pt[1], pt[0]]
                cv2.putText(debug_img, f"L:{match_val:.2f}", (pt[0], pt[1] - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
            print(f"  Found {matches_found} log match(es) with threshold {threshold}")
    
    # Draw empty slot matches
    empty_matches = 0
    if os.path.exists(EMPTY_SLOT_PATH):
        empty_template = cv2.imread(EMPTY_SLOT_PATH, cv2.IMREAD_UNCHANGED)
        if empty_template is not None:
            # Convert template
            if len(empty_template.shape) == 3 and empty_template.shape[2] == 4:
                empty_template = cv2.cvtColor(empty_template, cv2.COLOR_BGRA2BGR)
            elif len(empty_template.shape) == 2:
                empty_template = cv2.cvtColor(empty_template, cv2.COLOR_GRAY2BGR)
            
            # Find empty slot matches
            result = cv2.matchTemplate(screen_bgr, empty_template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.7
            locations = np.where(result >= threshold)
            
            h, w = empty_template.shape[:2]
            for pt in zip(*locations[::-1]):
                empty_matches += 1
                cv2.rectangle(debug_img, pt, (pt[0] + w, pt[1] + h), (255, 0, 0), 1)
                # Get match confidence
                match_val = result[pt[1], pt[0]]
                cv2.putText(debug_img, f"E:{match_val:.2f}", (pt[0], pt[1] + h + 12),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            
            print(f"  Found {empty_matches} empty slot match(es) with threshold {threshold}")
            print(f"  Calculated occupied: {28 - empty_matches} slots")
    
    # Save debug image
    debug_path = os.path.join(DEBUG_OUTPUT_DIR, "inventory_matches_debug.png")
    cv2.imwrite(debug_path, debug_img)
    print(f"✓ Saved debug image with matches: {debug_path}")
    print(f"  Green boxes = logs, Red boxes = empty slots")
    
    if matches_found == 0 and empty_matches == 0:
        print("\n⚠ No matches found even with low threshold.")
        print("  Possible issues:")
        print("  1. Inventory area coordinates are wrong")
        print("  2. Template images don't match current appearance")
        print("  3. Items might be in different slots than expected")

def show_inventory_coords():
    """Help user find correct inventory coordinates"""
    print("\n" + "=" * 60)
    print("Finding Inventory Coordinates")
    print("=" * 60)
    print("\nTo find the correct inventory area:")
    print("1. Move your mouse to the TOP-LEFT corner of your inventory")
    print("2. Press ENTER...")
    input()
    top_left = pyautogui.position()
    print(f"   Top-left: {top_left}")
    
    print("\n3. Move your mouse to the BOTTOM-RIGHT corner of your inventory")
    print("4. Press ENTER...")
    input()
    bottom_right = pyautogui.position()
    print(f"   Bottom-right: {bottom_right}")
    
    inventory_area = {
        "top": top_left.y,
        "left": top_left.x,
        "width": bottom_right.x - top_left.x,
        "height": bottom_right.y - top_left.y
    }
    
    print("\n" + "=" * 60)
    print("Suggested Inventory Area:")
    print("=" * 60)
    print(f'INVENTORY_AREA = {{"top": {inventory_area["top"]}, "left": {inventory_area["left"]}, "width": {inventory_area["width"]}, "height": {inventory_area["height"]}}}')
    print("\nCopy this into woodcutter.py!")

def main():
    print("Choose an option:")
    print("1. Capture and test inventory area (recommended)")
    print("2. Find correct inventory coordinates")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        screen_bgr = capture_inventory_area()
        test_template_matching(screen_bgr)
        visualize_matches(screen_bgr)
        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print(f"1. Check '{os.path.join(DEBUG_OUTPUT_DIR, 'inventory_debug.png')}' - does it show your inventory?")
        print(f"2. Check '{os.path.join(DEBUG_OUTPUT_DIR, 'inventory_matches_debug.png')}' - are there green boxes around logs?")
        print(f"3. If inventory_debug.png is wrong, use option 2 to recalibrate")
        print("4. If no green boxes, try recapturing the template with capture_template.py")
    elif choice == "2":
        show_inventory_coords()
    else:
        print("Exiting...")

if __name__ == "__main__":
    main()

