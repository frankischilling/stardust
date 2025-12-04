"""
Game Area Calibration Tool
Helps you find the coordinates of your RuneScape game window.
Automatically updates woodcutter.py with the calibrated values.
"""
import pyautogui
import time
import os
import re

# Get the path to woodcutter.py (in scripts directory, one level up from tools)
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
woodcutter_path = os.path.join(script_dir, "scripts", "woodcutter.py")

print("=" * 60)
print("Game Area Calibration Tool")
print("=" * 60)
print("\nInstructions:")
print("1. Position your RuneScape game window where you want it")
print("2. Move your mouse to the TOP-LEFT corner of the game window")
print("3. Press ENTER when ready...")
input()

top_left = pyautogui.position()
print(f"Top-left corner: {top_left}")

print("\n4. Move your mouse to the BOTTOM-RIGHT corner of the game window")
print("5. Press ENTER when ready...")
input()

bottom_right = pyautogui.position()
print(f"Bottom-right corner: {bottom_right}")

# Calculate game area
game_area = {
    "top": top_left.y,
    "left": top_left.x,
    "width": bottom_right.x - top_left.x,
    "height": bottom_right.y - top_left.y
}

print("\n" + "=" * 60)
print("Your Game Area Configuration:")
print("=" * 60)
print(f'GAME_AREA = {{"top": {game_area["top"]}, "left": {game_area["left"]}, "width": {game_area["width"]}, "height": {game_area["height"]}}}')

# Automatically update woodcutter.py
try:
    with open(woodcutter_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match GAME_AREA line
    pattern = r'GAME_AREA\s*=\s*\{[^}]+\}'
    replacement = f'GAME_AREA = {{"top": {game_area["top"]}, "left": {game_area["left"]}, "width": {game_area["width"]}, "height": {game_area["height"]}}}'
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        
        with open(woodcutter_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n✓ Automatically updated {woodcutter_path}")
        print("  GAME_AREA has been configured!")
    else:
        print(f"\n⚠ Could not find GAME_AREA in {woodcutter_path}")
        print("  Please manually update the file with the values above.")
        
except Exception as e:
    print(f"\n⚠ Error updating {woodcutter_path}: {e}")
    print("  Please manually update the file with the values above.")

