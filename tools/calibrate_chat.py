"""
Chat Area Calibration Tool
Helps you find the exact coordinates of the chat area in RuneScape.
Automatically updates firemaking.py with the calibrated values.
"""
import pyautogui
import time
import os
import re

# Get the path to firemaking.py (in scripts directory, one level up from tools)
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
firemaking_path = os.path.join(script_dir, "scripts", "firemaking.py")

print("=" * 60)
print("Chat Area Calibration Tool")
print("=" * 60)
print("\nInstructions:")
print("1. Make sure RuneScape is open and the chat is visible")
print("2. Try to light a fire in a place where you can't (e.g., too close to another fire)")
print("   This will show the 'You can't light a fire here' message in chat")
print("3. Move your mouse to the TOP-LEFT corner of the chat area")
print("   - This should be where chat messages appear (not the input box)")
print("   - Usually the left edge of the chat window, near the top")
print("4. Press ENTER when ready...")
input()

top_left = pyautogui.position()
print(f"Top-left corner: {top_left}")

print("\n5. Move your mouse to the BOTTOM-RIGHT corner of the chat area")
print("   - This should be the bottom-right of where chat messages appear")
print("   - Usually the right edge of the chat window, near the bottom")
print("   - Make sure to include the area where error messages appear")
print("6. Press ENTER when ready...")
input()

bottom_right = pyautogui.position()
print(f"Bottom-right corner: {bottom_right}")

# Calculate chat area
chat_area = {
    "top": top_left.y,
    "left": top_left.x,
    "width": bottom_right.x - top_left.x,
    "height": bottom_right.y - top_left.y
}

print("\n" + "=" * 60)
print("Your Chat Area Configuration:")
print("=" * 60)
print(f'CHAT_AREA = {{')
print(f'    "top": {chat_area["top"]},')
print(f'    "left": {chat_area["left"]},')
print(f'    "width": {chat_area["width"]},')
print(f'    "height": {chat_area["height"]}')
print(f'}}')

# Automatically update firemaking.py
try:
    if not os.path.exists(firemaking_path):
        print(f"\n⚠ firemaking.py not found at {firemaking_path}")
        print("  Please manually update the file with the values above.")
    else:
        with open(firemaking_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match CHAT_AREA block (multiline, handles various formats)
        pattern = r'CHAT_AREA\s*=\s*\{.*?\}'
        # Create replacement with proper indentation
        replacement = f'CHAT_AREA = {{\n    "top": {chat_area["top"]},\n    "left": {chat_area["left"]},\n    "width": {chat_area["width"]},\n    "height": {chat_area["height"]}\n}}'
        
        # Use re.DOTALL to make . match newlines
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            
            with open(firemaking_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"\n✓ Automatically updated firemaking.py")
        else:
            # CHAT_AREA doesn't exist yet, add it after INVENTORY_AREA
            # Find INVENTORY_AREA block and add CHAT_AREA after it
            inventory_pattern = r'(INVENTORY_AREA\s*=\s*\{[^}]+\})'
            if re.search(inventory_pattern, content, re.DOTALL):
                # Add CHAT_AREA after INVENTORY_AREA
                chat_config = f'\n\n# Chat area (for detecting error messages)\n# Calibrated using calibrate_chat.py\n{replacement}'
                content = re.sub(inventory_pattern, r'\1' + chat_config, content, flags=re.DOTALL)
                
                with open(firemaking_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"\n✓ Automatically added CHAT_AREA to firemaking.py")
            else:
                print(f"\n⚠ Could not find INVENTORY_AREA in firemaking.py")
                print("  Please manually add the CHAT_AREA configuration.")
                
except Exception as e:
    print(f"\n⚠ Error updating firemaking.py: {e}")
    print("  Please manually update the file with the values above.")

print("\nNote: Make sure the chat area includes where error messages appear.")
print("      You can test by trying to light a fire in an invalid location.")
