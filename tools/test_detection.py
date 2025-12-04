"""
Quick Detection Test
Tests if the bot can find trees and logs with your current configuration.
"""
import sys
import os
# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
import bot_utils
import pyautogui
import time

# Import configuration from woodcutter
from woodcutter import GAME_AREA, TREE_COLOR_LOWER, TREE_COLOR_UPPER, LOG_ICON_PATH, INVENTORY_AREA

def test_tree_detection():
    """Test if trees can be detected"""
    print("=" * 60)
    print("Testing Tree Detection")
    print("=" * 60)
    print(f"Game Area: {GAME_AREA}")
    print(f"Tree Color Range: {TREE_COLOR_LOWER} to {TREE_COLOR_UPPER}")
    print("\nLooking for trees... (make sure RuneScape is visible)")
    time.sleep(2)
    
    tree_pos = bot_utils.find_color(TREE_COLOR_LOWER, TREE_COLOR_UPPER, GAME_AREA)
    
    if tree_pos:
        print(f"✓ Tree found at: {tree_pos}")
        return True
    else:
        print("✗ No tree found")
        print("\nTroubleshooting:")
        print("1. Make sure a tree is visible in the game window")
        print("2. Try running color_picker.py again to get new HSV values")
        print("3. Adjust TREE_COLOR_LOWER and TREE_COLOR_UPPER in woodcutter.py")
        return False

def test_log_detection():
    """Test if logs can be detected in inventory"""
    print("\n" + "=" * 60)
    print("Testing Log Detection")
    print("=" * 60)
    print(f"Inventory Area: {INVENTORY_AREA}")
    print(f"Log Template: {LOG_ICON_PATH}")
    print("\nLooking for logs in inventory... (make sure inventory is visible)")
    time.sleep(2)
    
    # Try with different thresholds
    print("Testing with different thresholds...")
    thresholds = [0.8, 0.7, 0.6, 0.5]
    log_pos = None
    best_threshold = None
    
    for threshold in thresholds:
        log_pos = bot_utils.find_image(LOG_ICON_PATH, threshold=threshold, game_area=INVENTORY_AREA)
        if log_pos:
            print(f"  Threshold {threshold}: ✓ Found at {log_pos}")
            best_threshold = threshold
            break
        else:
            print(f"  Threshold {threshold}: ✗ Not found")
    
    if log_pos:
        print(f"\n✓ Log found at: {log_pos} (threshold: {best_threshold})")
        
        # Count how many logs with the working threshold
        count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=best_threshold)
        print(f"✓ Found {count} logs in inventory")
        print(f"\n⚠ Note: Update threshold in woodcutter.py to {best_threshold} for better detection")
        return True
    else:
        print("\n✗ No log found even with low thresholds")
        print("\nTroubleshooting:")
        print("1. The template image might not match your current log appearance")
        print("2. Try recapturing the template:")
        print("   python capture_template.py")
        print("   (Make sure the log is NOT selected/highlighted)")
        print("3. Run debug tool to see what's being captured:")
        print("   python debug_inventory.py")
        return False

def main():
    print("Bot Detection Test")
    print("Make sure RuneScape is open and visible before running tests.\n")
    input("Press ENTER when ready...")
    
    tree_ok = test_tree_detection()
    log_ok = test_log_detection()
    
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    print(f"Tree Detection: {'✓ PASS' if tree_ok else '✗ FAIL'}")
    print(f"Log Detection: {'✓ PASS' if log_ok else '✗ FAIL'}")
    
    if tree_ok and log_ok:
        print("\n✓ All tests passed! Your bot should be ready to run.")
        print("Run: python woodcutter.py")
    else:
        print("\n✗ Some tests failed. Fix the issues above before running the bot.")

if __name__ == "__main__":
    main()

