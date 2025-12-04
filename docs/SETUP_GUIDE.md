# Quick Setup Guide

## ✅ Step 1: Game Area Calibration (COMPLETED)

You've already calibrated your game area:
```
GAME_AREA = {"top": 0, "left": 9, "width": 1910, "height": 1004}
```

This has been automatically updated in `woodcutter.py`.

## 📸 Step 2: Create Template Images

You need to create template images for the bot to recognize items. The easiest way is using the capture tool:

```bash
python capture_template.py
```

**What to capture:**
1. **log_icon.png** - Position your mouse over a log in your inventory, then capture it
   - This is the most important template for the woodcutter bot
   - Make sure the log is clearly visible

**Alternative method:**
- Use Windows Snipping Tool (Win + Shift + S)
- Capture just the log icon (about 20-30 pixels)
- Save as `templates/log_icon.png`

## 🎨 Step 3: Find Tree Colors

Run the color picker to find HSV values for trees:

```bash
python color_picker.py
```

**Instructions:**
1. Position your mouse over a tree in the game
2. Press ENTER
3. Copy the HSV values into `woodcutter.py`

You'll need to update these lines in `woodcutter.py`:
```python
TREE_COLOR_LOWER = (30, 100, 50)   # Replace with your values
TREE_COLOR_UPPER = (90, 255, 255)  # Replace with your values
```

## ⚙️ Step 4: Adjust Inventory Area (Optional)

The inventory area has been set for full-screen, but you may need to fine-tune it:

1. Open RuneScape
2. Note where your inventory is located
3. Adjust these values in `woodcutter.py` if needed:
```python
INVENTORY_AREA = {
    "top": GAME_AREA["top"] + 600,   # Adjust if needed
    "left": GAME_AREA["left"] + 1600,  # Adjust if needed
    "width": 300,
    "height": 400
}
```

## 🧪 Step 5: Test Your Setup

Before running the bot, test that everything works:

```bash
python test_setup.py
```

This will verify:
- All dependencies are installed
- Screen capture works
- Bot utilities load correctly

## 🚀 Step 6: Run the Bot

Once everything is configured:

```bash
python woodcutter.py
```

**Important reminders:**
- ⚠️ This is for educational purposes only
- ⚠️ Do NOT use on any account you value
- ⚠️ Using bots will result in a permanent ban
- Press `Ctrl+C` to stop the bot

## 🔧 Troubleshooting

### Template not found
- Lower the threshold in `woodcutter.py` (try 0.7 instead of 0.8)
- Recapture the template with better lighting
- Make sure the item is visible when the bot runs

### Tree not detected
- Run `color_picker.py` again and get new HSV values
- Adjust the color range (make it wider)
- Try different tree types (some are easier to detect)

### Inventory area wrong
- Use `calibrate_game_area.py` to find exact coordinates
- Adjust `INVENTORY_AREA` values in `woodcutter.py`

### Bot clicks wrong place
- Recalibrate your `GAME_AREA`
- Make sure RuneScape window hasn't moved
- Check that you're using the correct game mode (fixed/resizable)

## 📚 Next Steps for Learning

After getting the basic bot working, consider:

1. **Improve detection**: Combine color + template matching
2. **Add pathfinding**: Implement A* algorithm for navigation
3. **State machine**: Make the bot more robust with better state management
4. **Animation detection**: Detect when actions complete instead of using timers
5. **Anti-detection**: Add more human-like behavior patterns

## 💡 For Your Internship

When discussing this project with your team:

- Focus on the **detection vectors** you've identified
- Explain the **limitations** of screen-scraping vs reflection
- Discuss how **anti-cheat systems** can detect these patterns
- Show understanding of **human vs bot behavior** differences

Good luck with your internship! 🎓

