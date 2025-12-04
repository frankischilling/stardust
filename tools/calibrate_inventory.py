"""
Inventory Area Calibration Tool
Helps you find the exact coordinates of your inventory.
Automatically updates woodcutter.py with the calibrated values.
"""
import pyautogui
import time
import os
import re

# Get the paths to woodcutter.py and firemaking.py (in scripts directory, one level up from tools)
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
woodcutter_path = os.path.join(script_dir, "scripts", "woodcutter.py")
firemaking_path = os.path.join(script_dir, "scripts", "firemaking.py")

print("=" * 60)
print("Inventory Area Calibration Tool")
print("=" * 60)
print("\nInstructions:")
print("1. Make sure RuneScape is open and your inventory is visible")
print("2. Move your mouse to the TOP-LEFT corner of your inventory")
print("   ⚠ CRITICAL: Click on the LEFT EDGE of the VERY FIRST inventory slot (slot 1)")
print("   - Position your mouse at the LEFT EDGE of slot 1, not the center")
print("   - This ensures the first column is fully captured!")
print("   - If you click too far right, the first column will be cut off")
print("   - The corner of the FIRST inventory slot, not the tab or border")
print("3. Press ENTER when ready...")
input()

top_left = pyautogui.position()
print(f"Top-left corner: {top_left}")

print("\n4. Move your mouse to the BOTTOM-RIGHT corner of your inventory")
print("   ⚠ IMPORTANT: Click on the RIGHT EDGE of the VERY LAST inventory slot (slot 28)")
print("   - Position your mouse at the RIGHT EDGE of slot 28, not the center")
print("   - This ensures all 4 columns are fully captured!")
print("   - The bottom-right corner of the LAST inventory slot")
print("5. Press ENTER when ready...")
input()

bottom_right = pyautogui.position()
print(f"Bottom-right corner: {bottom_right}")

# Calculate inventory area
inventory_area = {
    "top": top_left.y,
    "left": top_left.x,
    "width": bottom_right.x - top_left.x,
    "height": bottom_right.y - top_left.y
}

print("\n" + "=" * 60)
print("Your Inventory Area Configuration:")
print("=" * 60)
print(f'INVENTORY_AREA = {{')
print(f'    "top": {inventory_area["top"]},')
print(f'    "left": {inventory_area["left"]},')
print(f'    "width": {inventory_area["width"]},')
print(f'    "height": {inventory_area["height"]}')
print(f'}}')

# Automatically update woodcutter.py and firemaking.py
files_to_update = [
    ("woodcutter.py", woodcutter_path),
    ("firemaking.py", firemaking_path)
]

updated_files = []
for file_name, file_path in files_to_update:
    try:
        if not os.path.exists(file_path):
            print(f"\n⚠ {file_name} not found at {file_path}, skipping...")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match INVENTORY_AREA block (multiline, handles various formats)
        # Match INVENTORY_AREA = { ... } including newlines - use DOTALL flag
        pattern = r'INVENTORY_AREA\s*=\s*\{.*?\}'
        # Create replacement with proper indentation
        replacement = f'INVENTORY_AREA = {{\n    "top": {inventory_area["top"]},\n    "left": {inventory_area["left"]},\n    "width": {inventory_area["width"]},\n    "height": {inventory_area["height"]}\n}}'
        
        # Use re.DOTALL to make . match newlines
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"\n✓ Automatically updated {file_name}")
            updated_files.append(file_name)
        else:
            print(f"\n⚠ Could not find INVENTORY_AREA in {file_name}")
            print("  Please manually update the file with the values above.")
            
    except Exception as e:
        print(f"\n⚠ Error updating {file_name}: {e}")
        print("  Please manually update the file with the values above.")

if updated_files:
    print(f"\n✓ Successfully updated INVENTORY_AREA in: {', '.join(updated_files)}")

print("\nNote: Make sure you clicked on the actual inventory GRID,")
print("      not the inventory tab or other UI elements.")

