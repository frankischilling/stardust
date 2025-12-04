# Creating Template Images

Template images are small screenshots that the bot uses to find specific items or UI elements on the screen. Here's how to create them:

## How to Create Template Images

### Method 1: Using Windows Snipping Tool

1. **Open RuneScape** and position your inventory so you can see a log
2. **Open Snipping Tool** (Windows key + Shift + S, or search "Snipping Tool")
3. **Select "Rectangular Snip"**
4. **Capture just the log icon** - make it tight around the item (about 20-30 pixels square)
5. **Save as PNG** in this `templates/` directory with a descriptive name (e.g., `log_icon.png`)

### Method 2: Using Print Screen + Image Editor

1. **Press Print Screen** while in RuneScape
2. **Open Paint** (or any image editor)
3. **Paste** the screenshot
4. **Crop** to just the item icon (make it small, 20-30 pixels)
5. **Save as PNG** in this `templates/` directory

### Method 3: Using Python (Automated)

You can also use this Python script to capture a template:

```python
import mss
import cv2
import numpy as np

# Position your mouse over the item, then run this
import pyautogui
x, y = pyautogui.position()
print(f"Capturing at ({x}, {y})")

with mss.mss() as sct:
    # Capture 30x30 area around mouse
    monitor = {
        "top": y - 15,
        "left": x - 15,
        "width": 30,
        "height": 30
    }
    img = np.array(sct.grab(monitor))
    cv2.imwrite("templates/log_icon.png", cv2.cvtColor(img, cv2.COLOR_BGRA2BGR))
    print("Saved template image!")
```

## Required Template Images

For the woodcutter bot, you need:

1. **log_icon.png** - A screenshot of a single log in your inventory
   - Should be cropped tightly around just the log icon
   - About 20-30 pixels square
   - PNG format (preserves transparency if needed)

## Tips for Better Template Matching

1. **Keep it small**: Only capture the item itself, not surrounding UI
2. **Use PNG format**: Better quality than JPG
3. **Match the game state**: If you play in fixed mode, capture in fixed mode. If resizable, capture in resizable
4. **Test different items**: You might need separate templates for different log types (regular logs, oak logs, etc.)
5. **Update if UI changes**: If Jagex updates the UI, you'll need new templates

## Testing Your Templates

After creating a template, you can test if it works:

```python
import bot_utils

# Test finding the log icon
result = bot_utils.find_image("templates/log_icon.png", threshold=0.8)
if result:
    print(f"Found at: {result}")
else:
    print("Not found - try adjusting threshold or recapture template")
```

## Optional Templates (For Future Enhancement)

- `bank_booth.png` - Bank booth/chest icon
- `deposit_all.png` - "Deposit-All" button text
- `tree_icon.png` - Tree icon from minimap or interface
- `inventory_full.png` - Indicator that inventory is full

