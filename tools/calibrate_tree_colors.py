"""
Tree Color Calibration Tool
Helps you calibrate HSV color ranges for different tree types.
Automatically updates woodcutter.py with the calibrated values.
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
import re
from woodcutter import GAME_AREA

# Get the path to woodcutter.py
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
woodcutter_path = os.path.join(script_dir, "scripts", "woodcutter.py")

# Tree type mappings
TREE_TYPES = {
    "1": ("regular", "Regular Trees"),
    "2": ("oak", "Oak Trees"),
    "3": ("willow", "Willow Trees"),
    "4": ("maple", "Maple Trees"),
    "5": ("yew", "Yew Trees"),
    "6": ("magic", "Magic Trees"),
    "7": ("teak", "Teak Trees"),
    "8": ("mahogany", "Mahogany Trees")
}

def capture_tree_color_sample(tree_type_name, sample_num=1):
    """
    Captures a single HSV color sample from a tree.
    Returns the HSV value at the mouse position.
    """
    print(f"\n--- Sample {sample_num} ---")
    print(f"Move your mouse over a {tree_type_name} tree trunk")
    print("Press ENTER to capture this sample, or 's' to skip...")
    
    user_input = input().strip().lower()
    if user_input == 's':
        return None
    
    mouse_x, mouse_y = pyautogui.position()
    
    # Check if mouse is in game area
    if (mouse_x < GAME_AREA['left'] or mouse_x > GAME_AREA['left'] + GAME_AREA['width'] or
        mouse_y < GAME_AREA['top'] or mouse_y > GAME_AREA['top'] + GAME_AREA['height']):
        print("⚠ Mouse is outside game area!")
        return None
    
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
    
    print(f"  Captured: H={h}, S={s}, V={v} at ({mouse_x}, {mouse_y})")
    return (h, s, v)

def calculate_color_range(samples):
    """
    Calculates HSV color range from multiple samples.
    Returns (hsv_lower, hsv_upper) tuple.
    """
    if not samples:
        return None, None
    
    # Extract H, S, V values
    h_values = [s[0] for s in samples]
    s_values = [s[1] for s in samples]
    v_values = [s[2] for s in samples]
    
    # Calculate min/max for each channel
    h_min, h_max = min(h_values), max(h_values)
    s_min, s_max = min(s_values), max(s_values)
    v_min, v_max = min(v_values), max(v_values)
    
    # Calculate ranges
    h_range = h_max - h_min
    s_range = s_max - s_min
    v_range = v_max - v_min
    
    # Add tolerance based on range
    # For H: add 10-20 tolerance (Hue wraps around, so be careful)
    # For S and V: add 30-50 tolerance
    h_tolerance = max(10, min(20, h_range + 5))
    s_tolerance = max(30, min(50, s_range + 10))
    v_tolerance = max(30, min(50, v_range + 10))
    
    hsv_lower = (
        max(0, h_min - h_tolerance),
        max(0, s_min - s_tolerance),
        max(0, v_min - v_tolerance)
    )
    
    hsv_upper = (
        min(179, h_max + h_tolerance),
        min(255, s_max + s_tolerance),
        min(255, v_max + v_tolerance)
    )
    
    return hsv_lower, hsv_upper

def calibrate_tree_type(tree_type_key, tree_type_name):
    """
    Calibrates colors for a specific tree type.
    """
    print("=" * 60)
    print(f"Calibrating {tree_type_name}")
    print("=" * 60)
    print(f"\nInstructions:")
    print(f"1. Position yourself near {tree_type_name}")
    print(f"2. You'll capture 3-5 color samples from different parts of the tree")
    print(f"3. Try to sample the trunk/main body of the tree (not leaves)")
    print(f"4. Sample different trees if possible for better accuracy")
    
    samples = []
    num_samples = 5
    
    print(f"\nWe'll capture {num_samples} samples. You can skip samples by pressing 's'.")
    
    for i in range(1, num_samples + 1):
        sample = capture_tree_color_sample(tree_type_name, i)
        if sample:
            samples.append(sample)
    
    if len(samples) < 2:
        print(f"\n⚠ Not enough samples captured (got {len(samples)}, need at least 2)")
        print("Calibration cancelled.")
        return None
    
    # Calculate color range
    hsv_lower, hsv_upper = calculate_color_range(samples)
    
    print("\n" + "=" * 60)
    print(f"Calibration Results for {tree_type_name}")
    print("=" * 60)
    print(f"\nSamples captured: {len(samples)}")
    print(f"Sample values: {samples}")
    print(f"\nCalculated HSV Range:")
    print(f"  Lower: {hsv_lower}")
    print(f"  Upper: {hsv_upper}")
    
    # Show preview
    print(f"\nThis range will detect colors where:")
    print(f"  H (Hue): {hsv_lower[0]} to {hsv_upper[0]}")
    print(f"  S (Saturation): {hsv_lower[1]} to {hsv_upper[1]}")
    print(f"  V (Value/Brightness): {hsv_lower[2]} to {hsv_upper[2]}")
    
    # Ask for confirmation
    print("\n" + "=" * 60)
    confirm = input("Save this calibration? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("Calibration cancelled.")
        return None
    
    return {
        "tree_type": tree_type_key,
        "tree_name": tree_type_name,
        "hsv_lower": hsv_lower,
        "hsv_upper": hsv_upper,
        "samples": samples
    }

def update_woodcutter_file(calibration_data):
    """
    Updates woodcutter.py with the calibrated color values.
    """
    if not calibration_data:
        return False
    
    tree_type = calibration_data["tree_type"]
    tree_name = calibration_data["tree_name"]
    hsv_lower = calibration_data["hsv_lower"]
    hsv_upper = calibration_data["hsv_upper"]
    
    # Generate constant names
    const_name_upper = tree_type.upper()
    if tree_type == "regular":
        # Regular trees use TREE_COLOR_LOWER/UPPER (not REGULAR_COLOR_LOWER/UPPER)
        lower_const = "TREE_COLOR_LOWER"
        upper_const = "TREE_COLOR_UPPER"
    else:
        lower_const = f"{const_name_upper}_COLOR_LOWER"
        upper_const = f"{const_name_upper}_COLOR_UPPER"
    
    try:
        with open(woodcutter_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Format the new values
        lower_value = f"{lower_const} = {hsv_lower}"
        upper_value = f"{upper_const} = {hsv_upper}"
        
        if tree_type == "regular":
            # Replace TREE_COLOR_LOWER and TREE_COLOR_UPPER
            # Match the entire line (including comment) and preserve newline
            # Use multiline mode and be careful with newlines
            content = re.sub(
                r'TREE_COLOR_LOWER\s*=\s*\([^)]+\)[^\n]*(?:\n|$)',
                f"{lower_value}      # Lower HSV bound - dark brown/black trees\n",
                content,
                flags=re.MULTILINE
            )
            content = re.sub(
                r'TREE_COLOR_UPPER\s*=\s*\([^)]+\)[^\n]*(?:\n|$)',
                f"{upper_value}    # Upper HSV bound - brown trees (narrowed to reduce UI matches)\n",
                content,
                flags=re.MULTILINE
            )
        else:
            # For other tree types, handle commented or uncommented versions
            # Pattern to match commented or uncommented constant
            lower_pattern = rf'#?\s*{re.escape(lower_const)}\s*=\s*\([^)]+\)'
            upper_pattern = rf'#?\s*{re.escape(upper_const)}\s*=\s*\([^)]+\)'
            
            # Check if constants exist (commented or not)
            lower_exists = re.search(lower_pattern, content)
            upper_exists = re.search(upper_pattern, content)
            
            if lower_exists or upper_exists:
                # Replace existing (uncomment if needed)
                if lower_exists:
                    content = re.sub(lower_pattern, lower_value, content)
                if upper_exists:
                    content = re.sub(upper_pattern, upper_value, content)
            else:
                # Add new constants in the optional section (uncommented since we're calibrating)
                # Find the last tree type constant or the end of the optional section
                # Look for the pattern: # TREE_TYPE_COLOR_UPPER = ... or TREE_TYPE_COLOR_UPPER = ...
                last_tree_pattern = r'(#?\s*[A-Z_]+\s*=\s*\([^)]+\)\s*#.*\n)'
                matches = list(re.finditer(last_tree_pattern, content))
                
                if matches:
                    # Insert after the last tree type constant
                    last_match = matches[-1]
                    insert_pos = last_match.end()
                    insert_text = f"{lower_const} = {hsv_lower}      # {tree_name} tree colors\n{upper_value}\n"
                    content = content[:insert_pos] + insert_text + content[insert_pos:]
                else:
                    # Insert after the optional section comment
                    optional_section = r'(# Optional: Define different color ranges for different tree types\n# Uncomment and configure these if you want to cut specific tree types:)'
                    if re.search(optional_section, content):
                        insert_text = f"\n{lower_const} = {hsv_lower}      # {tree_name} tree colors\n{upper_value}\n"
                        content = re.sub(optional_section, r'\1' + insert_text, content)
                    else:
                        # Fallback: insert after TREE_COLOR_UPPER
                        insert_text = f"\n# {tree_name} tree colors\n{lower_const} = {hsv_lower}      # {tree_name} tree colors\n{upper_value}\n"
                        content = re.sub(r'(TREE_COLOR_UPPER\s*=\s*\([^)]+\)[^\n]*)', r'\1' + insert_text, content)
        
        # Write updated content
        with open(woodcutter_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n✓ Successfully updated {woodcutter_path}")
        print(f"  {lower_const} = {hsv_lower}")
        print(f"  {upper_const} = {hsv_upper}")
        return True
        
    except Exception as e:
        print(f"\n⚠ Error updating {woodcutter_path}: {e}")
        import traceback
        traceback.print_exc()
        print("\nPlease manually update the file with these values:")
        print(f"  {lower_const} = {hsv_lower}")
        print(f"  {upper_const} = {hsv_upper}")
        return False

def main():
    """
    Main calibration interface.
    """
    print("=" * 60)
    print("Tree Color Calibration Tool")
    print("=" * 60)
    print("\nThis tool helps you calibrate HSV color ranges for different tree types.")
    print("The calibrated values will be automatically saved to woodcutter.py")
    print("\nMake sure:")
    print("  - RuneScape is open and visible")
    print("  - You're positioned near the tree type you want to calibrate")
    print("  - The game area is properly calibrated (use calibrate_game_area.py if needed)")
    
    print("\n" + "=" * 60)
    print("Select Tree Type to Calibrate:")
    print("=" * 60)
    
    for key, (tree_key, tree_name) in TREE_TYPES.items():
        print(f"{key}. {tree_name}")
    
    print("9. Exit")
    
    choice = input("\nEnter choice (1-9): ").strip()
    
    if choice == "9":
        print("Exiting...")
        return
    
    if choice not in TREE_TYPES:
        print("Invalid choice.")
        return
    
    tree_key, tree_name = TREE_TYPES[choice]
    
    # Perform calibration
    calibration_data = calibrate_tree_type(tree_key, tree_name)
    
    if calibration_data:
        # Update woodcutter.py
        update_woodcutter_file(calibration_data)
        
        print("\n" + "=" * 60)
        print("Calibration Complete!")
        print("=" * 60)
        print(f"\n{tree_name} colors have been saved to woodcutter.py")
        print("\nNext steps:")
        print("  1. Test the calibration by running the bot")
        print("  2. If trees aren't detected correctly, run this tool again")
        print("  3. Try sampling different parts of the tree or different trees")
        print("  4. You can calibrate multiple tree types by running this tool again")

if __name__ == "__main__":
    main()

