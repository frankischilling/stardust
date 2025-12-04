"""
Tree Type Identification Tool
Helps you identify and configure different tree types (regular, oak, willow, etc.)
by capturing their unique colors.
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
from woodcutter import GAME_AREA

def capture_tree_colors(tree_type_name):
    """
    Captures HSV colors for a specific tree type.
    """
    print("=" * 60)
    print(f"Capturing Colors for {tree_type_name} Trees")
    print("=" * 60)
    print(f"\nInstructions:")
    print(f"1. Position yourself near {tree_type_name} trees")
    print(f"2. Move your mouse over a {tree_type_name} tree trunk")
    print(f"3. Press ENTER to capture the color...")
    input()
    
    mouse_x, mouse_y = pyautogui.position()
    
    # Check if mouse is in game area
    if (mouse_x < GAME_AREA['left'] or mouse_x > GAME_AREA['left'] + GAME_AREA['width'] or
        mouse_y < GAME_AREA['top'] or mouse_y > GAME_AREA['top'] + GAME_AREA['height']):
        print("⚠ Mouse is outside game area!")
        return None
    
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
    
    h = int(hsv_value[0])
    s = int(hsv_value[1])
    v = int(hsv_value[2])
    
    print(f"\nMouse position: ({mouse_x}, {mouse_y})")
    print(f"HSV value: H={h}, S={s}, V={v}")
    
    # Calculate a range
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
    
    return {
        "name": tree_type_name,
        "hsv_lower": hsv_lower,
        "hsv_upper": hsv_upper,
        "sample_hsv": (h, s, v)
    }

def compare_tree_colors():
    """
    Captures colors for multiple tree types and compares them.
    """
    print("=" * 60)
    print("Tree Type Color Comparison Tool")
    print("=" * 60)
    print("\nThis tool helps you identify different tree types by their colors.")
    print("You'll capture colors for each tree type, and we'll compare them.")
    
    tree_types = []
    
    # Capture regular trees
    print("\n" + "=" * 60)
    regular = capture_tree_colors("Regular")
    if regular:
        tree_types.append(regular)
    
    # Ask if user wants to capture other types
    while True:
        print("\n" + "=" * 60)
        print("Capture another tree type?")
        print("1. Oak")
        print("2. Willow")
        print("3. Maple")
        print("4. Yew")
        print("5. Magic")
        print("6. Done - Show comparison")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == "1":
            oak = capture_tree_colors("Oak")
            if oak:
                tree_types.append(oak)
        elif choice == "2":
            willow = capture_tree_colors("Willow")
            if willow:
                tree_types.append(willow)
        elif choice == "3":
            maple = capture_tree_colors("Maple")
            if maple:
                tree_types.append(maple)
        elif choice == "4":
            yew = capture_tree_colors("Yew")
            if yew:
                tree_types.append(yew)
        elif choice == "5":
            magic = capture_tree_colors("Magic")
            if magic:
                tree_types.append(magic)
        elif choice == "6":
            break
        else:
            print("Invalid choice")
    
    # Display comparison
    if len(tree_types) > 0:
        print("\n" + "=" * 60)
        print("Tree Type Color Comparison")
        print("=" * 60)
        
        for tree in tree_types:
            print(f"\n{tree['name']} Trees:")
            print(f"  Sample HSV: {tree['sample_hsv']}")
            print(f"  Lower: {tree['hsv_lower']}")
            print(f"  Upper: {tree['hsv_upper']}")
        
        # Check for overlaps
        print("\n" + "=" * 60)
        print("Overlap Analysis")
        print("=" * 60)
        
        if len(tree_types) > 1:
            for i, tree1 in enumerate(tree_types):
                for tree2 in tree_types[i+1:]:
                    # Check if color ranges overlap
                    h1_low, s1_low, v1_low = tree1['hsv_lower']
                    h1_high, s1_high, v1_high = tree1['hsv_upper']
                    h2_low, s2_low, v2_low = tree2['hsv_lower']
                    h2_high, s2_high, v2_high = tree2['hsv_upper']
                    
                    h_overlap = not (h1_high < h2_low or h2_high < h1_low)
                    s_overlap = not (s1_high < s2_low or s2_high < s1_low)
                    v_overlap = not (v1_high < v2_low or v2_high < v1_low)
                    
                    if h_overlap and s_overlap and v_overlap:
                        print(f"\n⚠ WARNING: {tree1['name']} and {tree2['name']} color ranges OVERLAP!")
                        print(f"   The bot may detect both types. Consider narrowing the ranges.")
                    else:
                        print(f"\n✓ {tree1['name']} and {tree2['name']} ranges are distinct")
        
        # Generate code snippets
        print("\n" + "=" * 60)
        print("Code to Add to woodcutter.py")
        print("=" * 60)
        print("\n# Tree type color configurations")
        for tree in tree_types:
            name_upper = tree['name'].upper().replace(' ', '_')
            print(f"{name_upper}_COLOR_LOWER = {tree['hsv_lower']}")
            print(f"{name_upper}_COLOR_UPPER = {tree['hsv_upper']}")
        
        print("\n# Then in find_and_click_tree(), use the appropriate color range:")
        print("# if TREE_TYPE == 'regular':")
        print("#     tree_pos = bot_utils.find_color(REGULAR_COLOR_LOWER, REGULAR_COLOR_UPPER, ...)")
        print("# elif TREE_TYPE == 'oak':")
        print("#     tree_pos = bot_utils.find_color(OAK_COLOR_LOWER, OAK_COLOR_UPPER, ...)")

def main():
    print("Choose an option:")
    print("1. Compare multiple tree types (recommended)")
    print("2. Capture single tree type")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        compare_tree_colors()
    elif choice == "2":
        tree_name = input("Enter tree type name (e.g., 'Oak', 'Willow'): ").strip()
        if tree_name:
            result = capture_tree_colors(tree_name)
            if result:
                print(f"\n{tree_name} Tree Colors:")
                print(f"  Lower: {result['hsv_lower']}")
                print(f"  Upper: {result['hsv_upper']}")
    else:
        print("Exiting...")

if __name__ == "__main__":
    main()

