"""
Baker Stall Detection Debug Tool
Visualizes what the bot sees when detecting the baker stall using red object marker.
Shows the captured area and highlights where the stall is detected.
"""
import sys
import os
# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
import cv2
import numpy as np
import mss
import pyautogui
import time
import bot_utils
from ardy_baker import (
    GAME_AREA, 
    MARKER_COLOR_LOWER, 
    MARKER_COLOR_UPPER,
    MARKER_COLOR_SECONDARY_LOWER,
    MARKER_COLOR_SECONDARY_UPPER,
    UI_EXCLUSION_LEFT,
    UI_EXCLUSION_BOTTOM,
    UI_EXCLUSION_RIGHT_EDGE,
    STALL_WORLD_Y_MIN,
    STALL_WORLD_Y_MAX
)

# Create debug output directory
DEBUG_OUTPUT_DIR = "debug"
if not os.path.exists(DEBUG_OUTPUT_DIR):
    os.makedirs(DEBUG_OUTPUT_DIR)

def capture_game_area():
    """Capture the game area"""
    print("=" * 60)
    print("Baker Stall Detection Debug Tool")
    print("=" * 60)
    print(f"\nGame Area: {GAME_AREA}")
    print(f"Marker Color Range (Primary): {MARKER_COLOR_LOWER} to {MARKER_COLOR_UPPER}")
    print(f"Marker Color Range (Secondary): {MARKER_COLOR_SECONDARY_LOWER} to {MARKER_COLOR_SECONDARY_UPPER}")
    print(f"UI Exclusion Left: {UI_EXCLUSION_LEFT}")
    print(f"UI Exclusion Bottom: {UI_EXCLUSION_BOTTOM}")
    print(f"UI Exclusion Right Edge: {UI_EXCLUSION_RIGHT_EDGE}")
    print("\nCapturing game area...")
    
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(GAME_AREA))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Save raw capture
    timestamp = int(time.time())
    debug_path = os.path.join(DEBUG_OUTPUT_DIR, f"baker_stall_game_area_{timestamp}.png")
    cv2.imwrite(debug_path, screen_bgr)
    print(f"✓ Saved game area to: {debug_path}")
    print(f"  Size: {screen_bgr.shape[1]}x{screen_bgr.shape[0]} pixels")
    
    return screen_bgr

def visualize_color_detection(screen_bgr):
    """Visualize where the color detection finds the baker stall"""
    print("\n" + "=" * 60)
    print("Visualizing Color Detection")
    print("=" * 60)
    
    # Use the same parameters as find_baker_stall()
    detection_kwargs = {
        "color_lower": MARKER_COLOR_LOWER,
        "color_upper": MARKER_COLOR_UPPER,
        "game_area": GAME_AREA,
        # Mirror ardy_baker.find_baker_stall defaults (stall marker ~26k area)
        "min_area": 500,
        "max_area": 50000,
        "min_aspect_ratio": 0.0,
        "max_aspect_ratio": 4.0,
        "min_height": 15,
        "min_width": 15,
        "max_width": 800,
        "max_height": 800,
        "exclude_ui_left": UI_EXCLUSION_LEFT,
        "exclude_ui_bottom": UI_EXCLUSION_BOTTOM,
        "exclude_ui_right_edge": UI_EXCLUSION_RIGHT_EDGE,
        "world_y_min": STALL_WORLD_Y_MIN,
        "world_y_max": STALL_WORLD_Y_MAX,
        "relaxed_filters": True,
        "allow_wide_aspect": True,
        "secondary_color_range": (MARKER_COLOR_SECONDARY_LOWER, MARKER_COLOR_SECONDARY_UPPER),
        "output_dir": DEBUG_OUTPUT_DIR,
        "save_images": True
    }
    
    print("\nDetection Parameters:")
    print(f"  - Min area: {detection_kwargs['min_area']}")
    print(f"  - Max area: {detection_kwargs['max_area']}")
    print(f"  - Aspect ratio: {detection_kwargs['min_aspect_ratio']} to {detection_kwargs['max_aspect_ratio']}")
    print(f"  - Size limits: {detection_kwargs['min_width']}x{detection_kwargs['min_height']} to {detection_kwargs['max_width']}x{detection_kwargs['max_height']}")
    print(f"  - Relaxed filters: {detection_kwargs['relaxed_filters']}")
    print(f"  - Allow wide aspect: {detection_kwargs['allow_wide_aspect']}")
    
    # Use bot_utils visualization function
    debug_img, mask_img, detection_info = bot_utils.visualize_color_detection(**detection_kwargs)
    
    timestamp = int(time.time())
    debug_path = os.path.join(DEBUG_OUTPUT_DIR, f"baker_stall_detection_{timestamp}.png")
    mask_path = os.path.join(DEBUG_OUTPUT_DIR, f"baker_stall_mask_{timestamp}.png")
    
    cv2.imwrite(debug_path, debug_img)
    cv2.imwrite(mask_path, mask_img)
    
    print(f"\n📊 Detection Statistics:")
    print(f"  - Total contours found: {detection_info['total_contours']}")
    print(f"  - Valid contours: {detection_info['valid_contours']}")
    print(f"  - Invalid (filtered): {detection_info['invalid_contours']}")
    
    if detection_info['valid_contours'] > 0:
        print(f"\n✓ Found {detection_info['valid_contours']} valid marker(s)!")
        print(f"✓ Saved debug visualization to: {debug_path}")
        print(f"✓ Saved color mask to: {mask_path}")
        print("  - Green boxes = detected stall marker areas")
        print("  - Red dots = center points (where bot would click)")
        
        # Try to find the stall using the actual function
        from ardy_baker import find_baker_stall
        stall_pos = find_baker_stall()
        if stall_pos:
            print(f"\n✓ Bot function found stall at: {stall_pos}")
        else:
            print(f"\n⚠ Bot function did NOT find stall (but visualization shows detections)")
            print("  This might indicate a filtering issue or coordinate conversion problem")
    else:
        print(f"\n✗ No valid markers detected!")
        print(f"✓ Saved debug visualization to: {debug_path}")
        print(f"✓ Saved color mask to: {mask_path}")
        print("\nTroubleshooting:")
        print("  1. Check the mask image - are there white areas where the red marker is?")
        print("  2. If no white areas, the color range might be wrong")
        print("  3. If white areas exist but no detections, check the filter parameters")
        print("  4. Make sure RuneLite Object Marker plugin is enabled")
        print("  5. Make sure the baker stall is marked with RED fill color")
    
    return debug_img, mask_img

def show_color_at_point():
    """Let user click on screen to see HSV values at that point"""
    print("\n" + "=" * 60)
    print("Color Picker - Click on Red Marker")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Move your mouse over the RED MARKER on the baker stall")
    print("2. Press ENTER to get the HSV color at that point")
    print("3. This will help verify the color range is correct")
    input()
    
    mouse_x, mouse_y = pyautogui.position()
    
    # Check if mouse is in game area
    if (mouse_x < GAME_AREA['left'] or mouse_x > GAME_AREA['left'] + GAME_AREA['width'] or
        mouse_y < GAME_AREA['top'] or mouse_y > GAME_AREA['top'] + GAME_AREA['height']):
        print("⚠ Mouse is outside game area!")
        print(f"Game area: left={GAME_AREA['left']}, top={GAME_AREA['top']}, "
              f"right={GAME_AREA['left'] + GAME_AREA['width']}, "
              f"bottom={GAME_AREA['top'] + GAME_AREA['height']}")
        return
    
    # Calculate relative position in game area
    rel_x = mouse_x - GAME_AREA['left']
    rel_y = mouse_y - GAME_AREA['top']
    
    # Capture small area around mouse
    capture_area = {
        "top": max(GAME_AREA['top'], mouse_y - 10),
        "left": max(GAME_AREA['left'], mouse_x - 10),
        "width": 20,
        "height": 20
    }
    
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(capture_area))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
        screen_hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)
    
    # Get HSV at center (where mouse is)
    center_x, center_y = 10, 10
    hsv_value = screen_hsv[center_y, center_x]
    
    print(f"\nMouse position: ({mouse_x}, {mouse_y})")
    print(f"HSV value at marker: H={hsv_value[0]}, S={hsv_value[1]}, V={hsv_value[2]}")
    print(f"\nCurrent color ranges:")
    print(f"  Primary Lower: {MARKER_COLOR_LOWER}")
    print(f"  Primary Upper: {MARKER_COLOR_UPPER}")
    print(f"  Secondary Lower: {MARKER_COLOR_SECONDARY_LOWER}")
    print(f"  Secondary Upper: {MARKER_COLOR_SECONDARY_UPPER}")
    
    # Check if it's in primary range
    in_primary = (MARKER_COLOR_LOWER[0] <= hsv_value[0] <= MARKER_COLOR_UPPER[0] and
                  MARKER_COLOR_LOWER[1] <= hsv_value[1] <= MARKER_COLOR_UPPER[1] and
                  MARKER_COLOR_LOWER[2] <= hsv_value[2] <= MARKER_COLOR_UPPER[2])
    
    # Check if it's in secondary range (for hue wraparound)
    in_secondary = (MARKER_COLOR_SECONDARY_LOWER[0] <= hsv_value[0] <= MARKER_COLOR_SECONDARY_UPPER[0] and
                    MARKER_COLOR_SECONDARY_LOWER[1] <= hsv_value[1] <= MARKER_COLOR_SECONDARY_UPPER[1] and
                    MARKER_COLOR_SECONDARY_LOWER[2] <= hsv_value[2] <= MARKER_COLOR_SECONDARY_UPPER[2])
    
    if in_primary:
        print("✓ This color IS in the PRIMARY range")
    elif in_secondary:
        print("✓ This color IS in the SECONDARY range (hue wraparound)")
    else:
        print("✗ This color is NOT in either range")
        print("\nYou may need to adjust MARKER_COLOR_LOWER/UPPER in ardy_baker.py")
        print("to include this color")

def test_actual_detection():
    """Test the actual find_baker_stall function"""
    print("\n" + "=" * 60)
    print("Testing Actual Bot Detection Function")
    print("=" * 60)
    print("\nCalling find_baker_stall()...")
    
    from ardy_baker import find_baker_stall
    stall_pos = find_baker_stall()
    
    if stall_pos:
        print(f"✓ SUCCESS! Found stall at: {stall_pos}")
        print(f"  Screen coordinates: ({stall_pos[0]}, {stall_pos[1]})")
    else:
        print("✗ FAILED! Could not find stall")
        print("\nPossible issues:")
        print("  1. Red marker not visible on screen")
        print("  2. Marker is in UI exclusion zone")
        print("  3. Color range doesn't match marker color")
        print("  4. Filters are too strict (unlikely with current settings)")

def main():
    print("Choose an option:")
    print("1. Capture and visualize stall detection (recommended)")
    print("2. Show color at mouse position (for calibrating colors)")
    print("3. Test actual bot detection function")
    print("4. All of the above")
    print("5. Exit")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1" or choice == "4":
        screen_bgr = capture_game_area()
        visualize_color_detection(screen_bgr)
        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print(f"1. Check '{DEBUG_OUTPUT_DIR}/baker_stall_game_area_*.png' - does it show your game?")
        print(f"2. Check '{DEBUG_OUTPUT_DIR}/baker_stall_mask_*.png' - white areas are detected red color")
        print(f"3. Check '{DEBUG_OUTPUT_DIR}/baker_stall_detection_*.png' - green boxes show detected markers")
        print("4. If wrong things are detected, use option 2 to recalibrate colors")
        print("5. If nothing is detected, check that the marker is visible and red")
    
    if choice == "2" or choice == "4":
        show_color_at_point()
    
    if choice == "3" or choice == "4":
        test_actual_detection()
    
    if choice == "5":
        print("Exiting...")

if __name__ == "__main__":
    main()
