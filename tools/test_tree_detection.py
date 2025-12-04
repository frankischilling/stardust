"""
Test script to debug tree detection.
Run this to see exactly what the bot is detecting.
"""
import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot_utils

# Configuration - match your woodcutter.py settings
GAME_AREA = {"top": 25, "left": 0, "width": 1880, "height": 989}

# NARROWED COLOR RANGES - Target ONLY tree trunks
TREE_COLOR_LOWER = (10, 100, 40)      # Lower HSV bound
TREE_COLOR_UPPER = (22, 180, 120)     # Upper HSV bound

# UI exclusion areas
UI_EXCLUSION_LEFT = GAME_AREA["left"] + GAME_AREA["width"] * 0.65
UI_EXCLUSION_BOTTOM = GAME_AREA["top"] + GAME_AREA["height"] * 0.6
UI_EXCLUSION_RIGHT_EDGE = GAME_AREA["left"] + GAME_AREA["width"] * 0.5

# Tree region (vertical band)
TREE_REGION_TOP = GAME_AREA["top"] + int(GAME_AREA["height"] * 0.08)
TREE_REGION_BOTTOM = GAME_AREA["top"] + int(GAME_AREA["height"] * 0.68)

# Detection parameters
TREE_MIN_AREA = 500
TREE_MAX_AREA = 15000
TREE_MIN_HEIGHT = 35
TREE_MIN_WIDTH = 12

def main():
    print("=" * 60)
    print("Tree Detection Test Script")
    print("=" * 60)
    print("\nThis script will analyze what the bot detects with current settings.")
    print("Check the 'debug_test' folder for visualization images.")
    print("\nPress Enter to start detection...")
    input()
    
    print("\nRunning detection with current color range...")
    print(f"Color range: {TREE_COLOR_LOWER} to {TREE_COLOR_UPPER}")
    print(f"Min area: {TREE_MIN_AREA}, Max area: {TREE_MAX_AREA}")
    print(f"Min height: {TREE_MIN_HEIGHT}, Min width: {TREE_MIN_WIDTH}")
    
    # Create debug output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug_test")
    os.makedirs(output_dir, exist_ok=True)
    
    # Run detection with visualization
    debug_img, mask_img, info = bot_utils.visualize_color_detection(
        color_lower=TREE_COLOR_LOWER,
        color_upper=TREE_COLOR_UPPER,
        game_area=GAME_AREA,
        min_area=TREE_MIN_AREA,
        max_area=TREE_MAX_AREA,
        min_aspect_ratio=0.35,
        max_aspect_ratio=3.0,
        min_height=TREE_MIN_HEIGHT,
        min_width=TREE_MIN_WIDTH,
        max_width=300,
        max_height=400,
        exclude_ui_left=UI_EXCLUSION_LEFT,
        exclude_ui_bottom=UI_EXCLUSION_BOTTOM,
        exclude_ui_right_edge=UI_EXCLUSION_RIGHT_EDGE,
        world_y_min=TREE_REGION_TOP,
        world_y_max=TREE_REGION_BOTTOM,
        save_images=True,
        output_dir=output_dir
    )
    
    print("\n" + "=" * 60)
    print("Detection Results:")
    print("=" * 60)
    print(f"Total contours found: {info['total_contours']}")
    print(f"Valid trees: {info['valid_contours']}")
    print(f"Rejected objects: {info['invalid_contours']}")
    
    if info['selected_contour']:
        sel = info['selected_contour']
        print(f"\nSelected tree:")
        print(f"  Area: {int(sel['area'])}")
        print(f"  Size: {sel['w']}x{sel['h']}")
        print(f"  Position: ({sel['x']}, {sel['y']})")
    else:
        print("\nNo valid trees detected!")
    
    print(f"\nDebug images saved to: {output_dir}")
    print("\nAnalysis:")
    print("- Green boxes = Valid trees (would be clicked)")
    print("- Red boxes = Invalid objects (filtered out)")
    print("- Red circles = Click target (center of selected tree)")
    print("- Purple lines = UI exclusion boundaries")
    print("- Yellow lines = Tree band boundaries")
    
    if info['invalid_contours'] > info['valid_contours'] * 2:
        print("\n⚠ WARNING: Many objects are being rejected!")
        print("   Consider:")
        print("   1. Narrowing your color range further")
        print("   2. Adjusting TREE_REGION_TOP/BOTTOM")
        print("   3. Increasing min_area to filter small objects")
    
    if info['valid_contours'] == 0:
        print("\n⚠ WARNING: No trees detected!")
        print("   Consider:")
        print("   1. Widening your color range slightly")
        print("   2. Lowering min_area or min_height")
        print("   3. Checking if trees are in the tree band region")

if __name__ == "__main__":
    main()

