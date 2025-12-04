"""
Tree Detection Debug Tool
Visualizes what the bot sees when detecting trees.
Shows the captured area and highlights where trees are detected.
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
from woodcutter import GAME_AREA, TREE_COLOR_LOWER, TREE_COLOR_UPPER, UI_EXCLUSION_LEFT

def capture_game_area():
    """Capture the game area"""
    print("=" * 60)
    print("Tree Detection Debug Tool")
    print("=" * 60)
    print(f"\nGame Area: {GAME_AREA}")
    print(f"Tree Color Range: {TREE_COLOR_LOWER} to {TREE_COLOR_UPPER}")
    print("\nCapturing game area...")
    
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(GAME_AREA))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Save raw capture
    cv2.imwrite("game_area_debug.png", screen_bgr)
    print(f"✓ Saved game area to: game_area_debug.png")
    print(f"  Size: {screen_bgr.shape[1]}x{screen_bgr.shape[0]} pixels")
    
    return screen_bgr

def visualize_color_detection(screen_bgr):
    """Visualize where the color detection finds trees"""
    print("\n" + "=" * 60)
    print("Visualizing Color Detection")
    print("=" * 60)
    
    # Convert to HSV
    screen_hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)
    
    # Create mask for tree color range
    mask = cv2.inRange(screen_hsv, np.array(TREE_COLOR_LOWER), np.array(TREE_COLOR_UPPER))
    
    # Save the mask
    cv2.imwrite("tree_color_mask.png", mask)
    print("✓ Saved color mask to: tree_color_mask.png")
    print("  White areas = detected as tree color")
    print("  Black areas = not matching tree color")
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("\n✗ No contours found - no trees detected!")
        return screen_bgr
    
    # Filter by area, aspect ratio, and height (like the bot does)
    min_area = 400
    max_area = 50000
    min_aspect_ratio = 0.4
    max_aspect_ratio = 2.5
    min_height = 30
    max_width = 300
    max_height = 400
    
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue
        
        x, y, w, h = cv2.boundingRect(contour)
        if w == 0 or h == 0:
            continue
        
        # Check minimum height
        if h < min_height:
            continue
        
        # Check maximum width/height (filters large UI panels)
        if w > max_width or h > max_height:
            continue
        
        aspect_ratio = w / h
        if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
            continue
        
        # Check if contour is in UI exclusion area
        abs_x = x + GAME_AREA['left']
        if UI_EXCLUSION_LEFT and abs_x > UI_EXCLUSION_LEFT:
            continue  # Skip UI area
        
        valid_contours.append((contour, area))
    
    # Sort by area (largest first) to show priority
    valid_contours.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\nFound {len(contours)} total contours")
    print(f"Found {len(valid_contours)} valid contours after filtering:")
    print(f"  - Area: {min_area} to {max_area}")
    print(f"  - Aspect ratio: {min_aspect_ratio} to {max_aspect_ratio}")
    print(f"  - Height: {min_height} to {max_height} pixels")
    print(f"  - Width: max {max_width} pixels (filters large UI panels)")
    if UI_EXCLUSION_LEFT:
        print(f"  - UI exclusion: X > {UI_EXCLUSION_LEFT} (right side excluded)")
    print(f"  (Sorted by area - largest first)")
    
    # Draw on the original image
    debug_img = screen_bgr.copy()
    
    for i, (contour, area) in enumerate(valid_contours):
        # Get center
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            area = cv2.contourArea(contour)
            
            # Draw bounding box
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw center point
            cv2.circle(debug_img, (cX, cY), 5, (0, 0, 255), -1)
            
            # Draw label
            label = f"Tree {i+1} (area: {int(area)})"
            cv2.putText(debug_img, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Calculate absolute screen coordinates
            abs_x = cX + GAME_AREA['left']
            abs_y = cY + GAME_AREA['top']
            print(f"  Tree {i+1}: Center at ({abs_x}, {abs_y}), Area: {int(area)}")
    
    # Save debug image
    cv2.imwrite("tree_detection_debug.png", debug_img)
    print(f"\n✓ Saved debug visualization to: tree_detection_debug.png")
    print("  Green boxes = detected tree areas")
    print("  Red dots = center points (where bot would click)")
    
    return debug_img

def show_color_at_point():
    """Let user click on screen to see HSV values at that point"""
    print("\n" + "=" * 60)
    print("Color Picker - Click on Actual Tree")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Move your mouse over an ACTUAL TREE in the game")
    print("2. Press ENTER to get the HSV color at that point")
    print("3. This will help you see what color trees actually are")
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
    print(f"HSV value at tree: H={hsv_value[0]}, S={hsv_value[1]}, V={hsv_value[2]}")
    print(f"\nCurrent color range:")
    print(f"  Lower: {TREE_COLOR_LOWER}")
    print(f"  Upper: {TREE_COLOR_UPPER}")
    
    # Check if it's in range
    in_range = (TREE_COLOR_LOWER[0] <= hsv_value[0] <= TREE_COLOR_UPPER[0] and
                TREE_COLOR_LOWER[1] <= hsv_value[1] <= TREE_COLOR_UPPER[1] and
                TREE_COLOR_LOWER[2] <= hsv_value[2] <= TREE_COLOR_UPPER[2])
    
    if in_range:
        print("✓ This color IS in the current range")
    else:
        print("✗ This color is NOT in the current range")
        print("\nYou may need to adjust TREE_COLOR_LOWER and TREE_COLOR_UPPER")
        print("in woodcutter.py to include this color")

def main():
    print("Choose an option:")
    print("1. Capture and visualize tree detection (recommended)")
    print("2. Show color at mouse position (for calibrating colors)")
    print("3. Both")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1" or choice == "3":
        screen_bgr = capture_game_area()
        visualize_color_detection(screen_bgr)
        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("1. Check 'game_area_debug.png' - does it show your game?")
        print("2. Check 'tree_color_mask.png' - white areas are detected")
        print("3. Check 'tree_detection_debug.png' - green boxes show detected trees")
        print("4. If wrong things are detected, use option 2 to recalibrate colors")
    
    if choice == "2" or choice == "3":
        show_color_at_point()
    
    if choice == "4":
        print("Exiting...")

if __name__ == "__main__":
    main()

