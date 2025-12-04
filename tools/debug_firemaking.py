"""
Firemaking Debug Tool
Helps you visualize what the firemaking bot sees in the inventory area.
Tests template matching for both logs and tinderbox.
"""
import sys
import os
# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
import cv2
import numpy as np
import mss
import pyautogui
from firemaking import INVENTORY_AREA, LOG_ICON_PATH, TINDERBOX_ICON_PATH

# Create debug output directory
DEBUG_OUTPUT_DIR = "debug"
if not os.path.exists(DEBUG_OUTPUT_DIR):
    os.makedirs(DEBUG_OUTPUT_DIR)

def capture_inventory_area():
    """Capture and save the inventory area so you can see what the bot sees"""
    print("=" * 60)
    print("Firemaking Inventory Debug Tool")
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
    debug_path = os.path.join(DEBUG_OUTPUT_DIR, "firemaking_inventory_debug.png")
    cv2.imwrite(debug_path, debug_img)
    print(f"✓ Saved inventory area to: {debug_path}")
    print(f"  Size: {screen_bgr.shape[1]}x{screen_bgr.shape[0]} pixels")
    print(f"  Channels: {screen_bgr.shape[2]}")
    print(f"\n⚠ Check the image - it should show all 4 columns (slots 1-28)")
    print(f"   If you only see 3 columns, the inventory area 'left' coordinate is too far right!")
    print(f"   If the first column is cut off, you need to move 'left' further left.")
    print(f"   Use tools/calibrate_inventory.py to recalibrate.")
    print(f"\n💡 Tip: The inventory area should start at the LEFT edge of slot 1,")
    print(f"   not the center. Make sure to click the very left edge when calibrating.")
    
    return screen_bgr

def test_log_template_matching(screen_bgr):
    """Test template matching for logs with different thresholds"""
    print("\n" + "=" * 60)
    print("Testing Log Template Matching")
    print("=" * 60)
    
    if not os.path.exists(LOG_ICON_PATH):
        print(f"✗ Log template not found: {LOG_ICON_PATH}")
        return None
    
    # Load template
    template = cv2.imread(LOG_ICON_PATH, cv2.IMREAD_UNCHANGED)
    if template is None:
        print(f"✗ Could not load log template: {LOG_ICON_PATH}")
        return None
    
    # Convert template to BGR
    if len(template.shape) == 3:
        channels = template.shape[2]
        if channels == 4:
            template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
        elif channels == 1:
            template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
    elif len(template.shape) == 2:
        template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
    
    print(f"Log template shape: {template.shape}")
    print(f"Screen shape: {screen_bgr.shape}")
    
    # Test with different thresholds
    print("\nTesting with different thresholds:")
    thresholds = [0.9, 0.8, 0.7, 0.6, 0.5]
    
    best_threshold = None
    best_matches = []
    
    for threshold in thresholds:
        result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # Find all matches above threshold
        locations = np.where(result >= threshold)
        matches = list(zip(*locations[::-1]))  # Switch x and y coordinates
        
        print(f"  Threshold {threshold:.1f}: Max match = {max_val:.3f} ", end="")
        if matches:
            print(f"✓ Found {len(matches)} match(es)")
            if best_threshold is None:
                best_threshold = threshold
                best_matches = matches
        else:
            print("✗ Not found")
    
    return template, best_threshold, best_matches

def test_tinderbox_template_matching(screen_bgr):
    """Test template matching for tinderbox with different thresholds"""
    print("\n" + "=" * 60)
    print("Testing Tinderbox Template Matching")
    print("=" * 60)
    
    if TINDERBOX_ICON_PATH is None or not os.path.exists(TINDERBOX_ICON_PATH):
        print(f"✗ Tinderbox template not found")
        print(f"  Expected one of: tinderbox_icon.png, log_tinderbox.png, tinderbox.png")
        print(f"  In templates folder")
        return None, None, []
    
    # Load template
    template = cv2.imread(TINDERBOX_ICON_PATH, cv2.IMREAD_UNCHANGED)
    if template is None:
        print(f"✗ Could not load tinderbox template: {TINDERBOX_ICON_PATH}")
        return None, None, []
    
    # Convert template to BGR
    if len(template.shape) == 3:
        channels = template.shape[2]
        if channels == 4:
            template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
        elif channels == 1:
            template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
    elif len(template.shape) == 2:
        template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
    
    print(f"Tinderbox template: {os.path.basename(TINDERBOX_ICON_PATH)}")
    print(f"Tinderbox template shape: {template.shape}")
    
    # Test with different thresholds
    print("\nTesting with different thresholds:")
    thresholds = [0.9, 0.8, 0.7, 0.6, 0.5]
    
    best_threshold = None
    best_matches = []
    
    for threshold in thresholds:
        result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # Find all matches above threshold
        locations = np.where(result >= threshold)
        matches = list(zip(*locations[::-1]))  # Switch x and y coordinates
        
        print(f"  Threshold {threshold:.1f}: Max match = {max_val:.3f} ", end="")
        if matches:
            print(f"✓ Found {len(matches)} match(es)")
            if best_threshold is None:
                best_threshold = threshold
                best_matches = matches
        else:
            print("✗ Not found")
    
    return template, best_threshold, best_matches

def visualize_matches(screen_bgr, log_template, log_threshold, log_matches, 
                      tinderbox_template, tinderbox_threshold, tinderbox_matches):
    """Draw matches on the image"""
    print("\n" + "=" * 60)
    print("Creating Visual Debug Image")
    print("=" * 60)
    
    debug_img = screen_bgr.copy()
    
    # Draw log matches in green
    if log_template is not None and log_matches:
        log_h, log_w = log_template.shape[:2]
        for pt in log_matches:
            cv2.rectangle(debug_img, pt, (pt[0] + log_w, pt[1] + log_h), (0, 255, 0), 2)
            # Get match confidence
            result = cv2.matchTemplate(screen_bgr, log_template, cv2.TM_CCOEFF_NORMED)
            match_val = result[pt[1], pt[0]]
            cv2.putText(debug_img, f"Log {match_val:.2f}", (pt[0], pt[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        print(f"✓ Found {len(log_matches)} log match(es) (green boxes)")
    else:
        print("✗ No log matches found")
    
    # Draw tinderbox matches in cyan
    if tinderbox_template is not None and tinderbox_matches:
        tinderbox_h, tinderbox_w = tinderbox_template.shape[:2]
        for pt in tinderbox_matches:
            cv2.rectangle(debug_img, pt, (pt[0] + tinderbox_w, pt[1] + tinderbox_h), (255, 255, 0), 2)
            # Get match confidence
            result = cv2.matchTemplate(screen_bgr, tinderbox_template, cv2.TM_CCOEFF_NORMED)
            match_val = result[pt[1], pt[0]]
            cv2.putText(debug_img, f"Tbox {match_val:.2f}", (pt[0], pt[1] + tinderbox_h + 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        print(f"✓ Found {len(tinderbox_matches)} tinderbox match(es) (yellow boxes)")
    else:
        print("✗ No tinderbox matches found")
    
    # Draw grid lines
    h, w = screen_bgr.shape[:2]
    for i in range(1, 4):
        x = int(w * i / 4)
        cv2.line(debug_img, (x, 0), (x, h), (128, 128, 128), 1)
    for i in range(1, 7):
        y = int(h * i / 7)
        cv2.line(debug_img, (0, y), (w, y), (128, 128, 128), 1)
    
    # Save debug image
    debug_path = os.path.join(DEBUG_OUTPUT_DIR, "firemaking_matches_debug.png")
    cv2.imwrite(debug_path, debug_img)
    print(f"\n✓ Saved debug image with matches: {debug_path}")
    print(f"  Green boxes = Log matches")
    print(f"  Yellow boxes = Tinderbox matches")
    print(f"  Numbers show match confidence")
    
    if not log_matches and not tinderbox_matches:
        print("\n⚠ No matches found!")
        print("  Possible issues:")
        print("  1. Inventory area coordinates are wrong - check if first column is visible")
        print("     (If only 3 columns show, 'left' coordinate needs to move further left)")
        print("     Use tools/calibrate_inventory.py to recalibrate")
        print("  2. Template images don't match current item appearance")
        print("  3. Items might be in different inventory slots")
        print("  4. Items might be selected/highlighted (affects appearance)")
        print("  5. Try recapturing templates with capture_template.py")
    
    # Check if inventory area might be missing the first column
    h, w = screen_bgr.shape[:2]
    expected_width_per_column = w / 4
    if expected_width_per_column < 50:
        print(f"\n⚠ Warning: Inventory width seems too narrow!")
        print(f"   Width: {w} pixels, Expected ~{50*4} pixels for 4 columns")
        print(f"   The 'left' coordinate might be too far right, cutting off the first column.")
        print(f"   Try recalibrating with calibrate_inventory.py")

def suggest_inventory_adjustment(screen_bgr):
    """Analyze the captured inventory and suggest adjustments if needed"""
    h, w = screen_bgr.shape[:2]
    
    # Typical inventory slot is about 40-50 pixels wide
    # For 4 columns, we'd expect width to be around 160-200 pixels minimum
    expected_min_width = 160  # 4 columns * 40 pixels
    expected_slot_width = w / 4
    
    print("\n" + "=" * 60)
    print("Inventory Area Analysis")
    print("=" * 60)
    print(f"Current inventory width: {w} pixels")
    print(f"Expected width for 4 columns: ~{expected_min_width} pixels minimum")
    print(f"Average slot width: {expected_slot_width:.1f} pixels")
    
    if w < expected_min_width:
        print(f"\n⚠ WARNING: Inventory width ({w}) seems too narrow!")
        print(f"   This suggests the inventory area might be missing columns.")
        adjustment = expected_min_width - w
        new_left = INVENTORY_AREA["left"] - adjustment
        print(f"\n💡 Suggested fix:")
        print(f"   Move 'left' coordinate further left by ~{adjustment} pixels")
        print(f"   Current 'left': {INVENTORY_AREA['left']}")
        print(f"   Suggested 'left': {new_left}")
        print(f"   Or recalibrate using: python tools/calibrate_inventory.py")
    
    if expected_slot_width < 35:
        print(f"\n⚠ WARNING: Slot width ({expected_slot_width:.1f}) seems too narrow!")
        print(f"   Typical inventory slots are 40-50 pixels wide.")
        print(f"   The inventory area might be missing the first column on the left.")
        print(f"   Try moving 'left' coordinate further left by 30-50 pixels.")

def main():
    print("=" * 60)
    print("Firemaking Debug Tool")
    print("=" * 60)
    print("\nThis tool helps you debug why the firemaking bot")
    print("might not be seeing logs or tinderbox in your inventory.")
    print("\nMake sure:")
    print("  - Your inventory is visible in RuneScape")
    print("  - You have logs in your inventory")
    print("  - You have a tinderbox in your inventory")
    
    input("\nPress ENTER to start debugging...")
    
    # Capture inventory
    screen_bgr = capture_inventory_area()
    
    # Analyze inventory area and suggest adjustments
    suggest_inventory_adjustment(screen_bgr)
    
    # Test log matching
    log_template, log_threshold, log_matches = test_log_template_matching(screen_bgr)
    
    # Test tinderbox matching
    tinderbox_template, tinderbox_threshold, tinderbox_matches = test_tinderbox_template_matching(screen_bgr)
    
    # Visualize matches
    visualize_matches(screen_bgr, log_template, log_threshold, log_matches,
                     tinderbox_template, tinderbox_threshold, tinderbox_matches)
    
    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)
    print(f"1. Check '{os.path.join(DEBUG_OUTPUT_DIR, 'firemaking_inventory_debug.png')}' - does it show your full inventory?")
    print(f"2. Check '{os.path.join(DEBUG_OUTPUT_DIR, 'firemaking_matches_debug.png')}' - are there green/yellow boxes?")
    print("3. If inventory is wrong (missing first column), run: python tools/calibrate_inventory.py")
    print("   Make sure to click the LEFT EDGE of slot 1, not the center!")
    print("4. If no matches, try recapturing templates with: python tools/capture_template.py")
    print("5. Make sure items are NOT selected/highlighted when capturing templates")

if __name__ == "__main__":
    main()

