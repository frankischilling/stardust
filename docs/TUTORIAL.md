# Complete Tutorial: Building Your First RuneScape Bot

This tutorial will walk you through setting up and using **Stardust**, the educational woodcutting bot, from start to finish.

**Important Note:** Most scripts don't require manual editing. Just use the built-in calibration tools to set up your inventory and screen coordinates. The tools **automatically update** the configuration files for you! Manual editing is only needed for tree colors (from color_picker.py) and optionally tree type.

## Prerequisites

- Python 3.7 or higher installed
- RuneScape account (use a test account, NOT your main!)
- Basic understanding of Python (helpful but not required)

## Step 1: Installation

### 1.1 Install Python Dependencies

Open a terminal/command prompt in the project directory and run:

```bash
pip install -r requirements.txt
```

This installs:
- **OpenCV** - For image processing and template matching
- **NumPy** - For numerical operations
- **PyAutoGUI** - For mouse and keyboard automation
- **MSS** - For fast screen capture

### 1.2 Verify Installation

Run the setup test:

```bash
python test_setup.py
```

You should see all checks passing (✓). If any fail, reinstall the missing packages.

## Step 2: Calibration

### 2.1 Calibrate Game Window Area

**Why this is important:** The bot needs to know where the game window is on your screen to capture the correct area.

1. **Open RuneScape** and position the window where you want it (don't move it after calibration!)
2. **Run the calibration tool:**

```bash
python tools/calibrate_game_area.py
```

3. **Follow the on-screen instructions:**
   - Move your mouse to the **top-left corner** of the game window (where the game content starts, not including window borders)
   - Press **ENTER** when ready
   - Move your mouse to the **bottom-right corner** of the game window (where the game content ends)
   - Press **ENTER** when ready

**The tool automatically updates `scripts/woodcutter.py` with the `GAME_AREA` values - no manual copying needed!**

You'll see a confirmation message: `✓ Automatically updated scripts/woodcutter.py`

**Tips:**
- Make sure the game window is in the position you'll use when running the bot
- Don't include window borders or title bars - just the game content area
- If you move the game window later, you'll need to recalibrate

### 2.2 Calibrate Inventory Area

**Why this is important:** The bot needs to know where your inventory is to check if it's full and to find log icons.

1. **Open your inventory** in RuneScape (make sure it's visible)
2. **Run the inventory calibration:**

```bash
python tools/calibrate_inventory.py
```

3. **Follow the on-screen instructions:**
   - Move your mouse to the **top-left corner** of the inventory **grid** (the actual item slots, NOT the inventory tab button)
   - Press **ENTER** when ready
   - Move your mouse to the **bottom-right corner** of the inventory **grid** (the last item slot)
   - Press **ENTER** when ready

**The tool automatically updates `scripts/woodcutter.py` with the `INVENTORY_AREA` values - no manual copying needed!**

You'll see a confirmation message: `✓ Automatically updated scripts/woodcutter.py`

**Important:**
- Click on the actual inventory **grid**, not the inventory tab or other UI elements
- Make sure the inventory is in the same position it will be when running the bot
- The inventory area should include all 28 inventory slots

### 2.3 Calibrate Tree Colors

**⚠️ IMPORTANT: Color Calibration Notice ⚠️**

The default color calibration in this bot is set up for **basic OSRS** (standard textures, default lighting, no shading mods). 

**You MUST recalibrate tree colors if you are using:**
- Custom texture packs
- Lighting mods (like 117 HD)
- Shading mods
- Any visual modifications that change how trees appear

**Why this matters:** Different visual settings change the colors of trees, so the default calibration may not work for your setup.

**Method 1: Using the Tree Color Calibration Tool (Recommended)**

1. Position yourself near trees in RuneScape
2. Run the calibration tool:

```bash
python tools/calibrate_tree_colors.py
```

3. Select the tree type you want to calibrate (e.g., "1" for Regular Trees)
4. Follow the prompts:
   - You'll capture 3-5 color samples from different parts of the tree
   - Move your mouse over tree trunks (not leaves) and press ENTER for each sample
   - The tool will calculate the optimal color range automatically
5. Confirm to save the calibration

**The tool automatically updates `scripts/woodcutter.py` with the color values - no manual copying needed!**

**Method 2: Using the Color Picker (Manual)**

1. Position yourself near trees in RuneScape
2. Run the color picker:

```bash
python tools/color_picker.py
```

3. Move your mouse over an **actual tree trunk** (not leaves, not ground)
4. Press ENTER
5. Copy the HSV values into `scripts/woodcutter.py` manually

**Example output:**
```python
TREE_COLOR_LOWER = (0, 0, 10)
TREE_COLOR_UPPER = (25, 80, 40)
```

**Tips:**
- Sample from the tree trunk, not leaves or ground
- Try sampling from different trees for better accuracy
- If trees aren't detected well, recalibrate with more samples
- Test with `python tools/debug_tree_detection.py` to see what's being detected

### 2.4 Create Log Template

1. Make sure you have at least one log in your inventory
2. Run the template capture tool:

```bash
python capture_template.py
```

3. Choose option 1 (recommended)
4. Position your mouse at the **center** of a log icon in your inventory
5. Press ENTER
6. When asked for size, press ENTER (uses 64 pixels - recommended)
7. When asked for filename, press ENTER (uses `log_icon.png`)
8. Test the template (choose 'y' when prompted)

**Important:** 
- Make sure the log is **NOT selected/highlighted** (no yellow border)
- Capture it in the same game state you'll be using (same UI scale, same client)

## Step 3: Configuration

### 3.1 Update woodcutter.py (Minimal)

Open `scripts/woodcutter.py` and update only these values:

```python
# Tree colors (from color_picker.py - copy manually)
TREE_COLOR_LOWER = (0, 0, 10)
TREE_COLOR_UPPER = (25, 80, 40)

# Tree type (optional - change based on what you're cutting)
TREE_TYPE = "regular"  # Options: "regular", "oak", "willow", "maple", "yew", "magic"
```

**Note:** `GAME_AREA` and `INVENTORY_AREA` are already automatically configured by the calibration tools (steps 2.1-2.2). You don't need to edit those!

### 3.2 Adjust Tree Type (Optional)

If you're cutting different trees, change `TREE_TYPE`:

- `"regular"` - Level 1 trees (2-3 seconds per tree)
- `"oak"` - Level 15 (27 seconds per log)
- `"willow"` - Level 30 (30 seconds per log)
- `"maple"` - Level 45 (60 seconds per log)
- `"yew"` - Level 60 (114 seconds per log)
- `"magic"` - Level 75 (234 seconds per log)

## Step 4: Testing

### 4.1 Test Detection

Before running the full bot, test that detection works:

```bash
python test_detection.py
```

**What to check:**
- ✓ Tree Detection: Should find trees in the game world
- ✓ Log Detection: Should find logs in your inventory

**If tree detection fails:**
- Run `python debug_tree_detection.py` (option 1) to see what's being detected
- Check that trees are visible in the game window
- Try recalibrating tree colors with `color_picker.py`

**If log detection fails:**
- Make sure you have logs in your inventory
- Recapture the template with `capture_template.py`
- Check that inventory area coordinates are correct

### 4.2 Test Thresholds (Optional)

If log detection has false positives (detects non-logs):

```bash
python test_threshold.py
```

This shows which threshold works best. Update the threshold in `woodcutter.py` if needed.

## Step 5: Running the Bot

### 5.1 Prepare Your Game

1. **Position yourself near trees** - The bot will look for trees in the game window
2. **Have an axe equipped** - Required for woodcutting
3. **Clear inventory space** - Or be ready to bank
4. **Be near a bank** (optional) - If you want to test banking functionality

### 5.2 Start the Bot

```bash
python woodcutter.py
```

**What happens:**
1. Bot waits 5 seconds (switch to RuneScape window!)
2. Bot looks for trees and clicks them
3. Bot waits for cutting to complete
4. Bot checks if inventory is full
5. If full, bot attempts to bank (pathfinding not implemented - you need to be near bank)
6. Repeats

### 5.3 Stop the Bot

Press `Ctrl+C` in the terminal to stop the bot safely.

## Step 6: Troubleshooting

### Problem: Bot clicks wrong objects

**Solution:**
- Run `python debug_tree_detection.py` to see what's detected
- Adjust `TREE_COLOR_LOWER` and `TREE_COLOR_UPPER` to be more specific
- Increase `min_area` in `find_and_click_tree()` to filter small objects
- Adjust `UI_EXCLUSION_LEFT` to exclude more of the right side

### Problem: Bot detects UI elements

**Solution:**
- The bot already excludes the right 30% of screen (UI area)
- If still detecting UI, reduce `UI_EXCLUSION_LEFT` value (exclude more area)
- Narrow the color range further

### Problem: Bot doesn't find trees

**Solution:**
- Make sure trees are visible in the game window
- Check `GAME_AREA` coordinates are correct
- Recalibrate tree colors - trees might look different in different lighting
- Run `debug_tree_detection.py` to see what colors are being detected

### Problem: Bot doesn't find logs

**Solution:**
- Make sure you have logs in inventory
- Recapture template - make sure log is NOT selected
- Lower the threshold (change 0.9 to 0.8 in `woodcutter.py`)
- Check `INVENTORY_AREA` coordinates

### Problem: Bot clicks too fast/slow

**Solution:**
- Adjust `TREE_TYPE` in `woodcutter.py` to match your tree
- Modify wait times in `wait_for_cutting_completion()` function
- Adjust delays in the state machine (in `main()` function)

### Problem: Bot gets stuck

**Solution:**
- Check that trees are respawning
- Make sure you're not in combat
- Verify game window hasn't moved (recalibrate if needed)
- Check that inventory isn't full and stuck

## Step 7: Understanding the Code

### Key Files

- **`bot_utils.py`** - Core functions for detection and input
  - `find_image()` - Template matching
  - `find_color()` - Color detection with filtering
  - `human_like_move()` - Natural mouse movements

- **`woodcutter.py`** - Main bot logic
  - State machine (IDLE → CUTTING → BANKING)
  - Tree detection and clicking
  - Inventory management

- **`debug_tree_detection.py`** - Visualization tool
  - Shows what the bot "sees"
  - Helps calibrate colors and filters

### How It Works

1. **Screen Capture** - Uses MSS to capture game window
2. **Color Detection** - Finds pixels matching tree color range
3. **Filtering** - Removes false positives (UI, players, small objects)
4. **Template Matching** - Finds log icons in inventory
5. **Input Simulation** - Clicks trees and interacts with game

### State Machine

```
IDLE → CUTTING → (inventory full?) → BANKING → IDLE
  ↑                                    ↓
  └────────── (continue cutting) ─────┘
```

## Step 8: Advanced Customization

### Adjust Detection Filters

In `woodcutter.py`, `find_and_click_tree()` function:

```python
tree_pos = bot_utils.find_color(
    TREE_COLOR_LOWER, 
    TREE_COLOR_UPPER, 
    GAME_AREA,
    min_area=400,      # Increase to filter smaller objects
    max_area=50000,    # Decrease to filter larger objects
    min_aspect_ratio=0.4,  # Adjust tree shape requirements
    max_aspect_ratio=2.5,
    min_height=30,     # Minimum tree height
    max_width=300,     # Maximum width (filters UI panels)
    max_height=400,    # Maximum height (filters UI panels)
    exclude_ui_left=UI_EXCLUSION_LEFT
)
```

### Add More Human-like Behavior

- Increase random delays between actions
- Add more mouse movement randomization
- Implement AFK breaks (already included)
- Add error recovery logic

### Improve Detection

- Use multiple detection methods (combine color + template)
- Add animation detection (detect when cutting stops)
- Implement pathfinding for navigation
- Add inventory slot detection (check specific slots)

## Step 9: For Your Internship

When discussing this project with your team at Jagex:

### Key Points to Mention

1. **Detection Methods**: "I implemented both color detection and template matching to understand different bot approaches."

2. **Filtering Techniques**: "I added multiple filters (area, aspect ratio, position) to reduce false positives and understand how bots distinguish objects."

3. **Anti-Detection Vectors**: "Through this project, I identified several detection vectors like predictable timing, perfect mouse movements, and static UI reliance."

4. **Limitations**: "This screen-scraping approach has clear limitations compared to reflection-based bots, which helped me understand the detection challenges."

5. **State Management**: "I implemented a state machine to understand how bots manage complex behaviors and decision-making."

### Questions to Ask

- "How does BotWatch detect screen-scraping bots vs reflection bots?"
- "What behavioral patterns are most indicative of botting?"
- "How do you handle false positives in detection systems?"
- "What techniques are used to detect memory hooks?"

## Final Notes

⚠️ **Remember:**
- This is for **educational purposes only**
- **DO NOT** use on any account you value
- Using bots violates Terms of Service
- You **WILL** be banned if detected

This project demonstrates understanding of bot mechanics to help with anti-cheat development. Use this knowledge responsibly!

Good luck with your internship! 🎓

