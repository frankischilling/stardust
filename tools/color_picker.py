"""
Color Picker Tool
Helps you find HSV color values from a screenshot.
Use this to calibrate the tree color detection.
"""
import cv2
import numpy as np
import mss
import pyautogui

def pick_color_from_screen():
    """
    Captures the screen and allows you to click on a pixel to get its HSV value.
    """
    print("=" * 60)
    print("Color Picker Tool")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Position your mouse over the object you want to detect (e.g., a tree)")
    print("2. Press ENTER to capture the screen and get color values...")
    input()
    
    # Get mouse position
    mouse_x, mouse_y = pyautogui.position()
    
    # Capture a small area around the mouse
    capture_area = {
        "top": max(0, mouse_y - 50),
        "left": max(0, mouse_x - 50),
        "width": 100,
        "height": 100
    }
    
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(capture_area))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
        screen_hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)
    
    # Get the pixel at the center (where mouse is)
    center_x, center_y = 50, 50  # Center of captured area
    hsv_value = screen_hsv[center_y, center_x]
    
    # Convert to Python int to avoid numpy overflow issues
    h = int(hsv_value[0])
    s = int(hsv_value[1])
    v = int(hsv_value[2])
    
    print(f"\nMouse position: ({mouse_x}, {mouse_y})")
    print(f"HSV value at that pixel: H={h}, S={s}, V={v}")
    
    # Calculate a range (you may need to adjust these tolerances)
    h_tolerance = 20
    s_tolerance = 50
    v_tolerance = 50
    
    hsv_lower = (
        max(0, h - h_tolerance),
        max(0, s - s_tolerance),
        max(0, v - v_tolerance)
    )
    
    hsv_upper = (
        min(179, h + h_tolerance),
        min(255, s + s_tolerance),
        min(255, v + v_tolerance)
    )
    
    print("\n" + "=" * 60)
    print("Suggested HSV Color Range:")
    print("=" * 60)
    print(f'TREE_COLOR_LOWER = {hsv_lower}')
    print(f'TREE_COLOR_UPPER = {hsv_upper}')
    print("\nCopy these into your woodcutter.py file!")
    print("\nNote: You may need to adjust the tolerance values if detection is too strict or too loose.")

if __name__ == "__main__":
    pick_color_from_screen()

