# Educational RuneScape Bot - Proof of Concept

**🚨 CRITICAL WARNING - USE AT YOUR OWN RISK 🚨**

## ⚠️ BAN RISK WARNING ⚠️

**USING THIS BOT ON RUNESCAPE MAY RESULT IN A PERMANENT BAN OF YOUR ACCOUNT.**

Jagex has sophisticated anti-cheat systems (BotWatch) that are designed to detect bots. **This bot has not been extensively tested**, so we cannot guarantee whether it will be detected or how quickly. However, using any automation tool violates RuneScape's Terms of Service, and if detected, bans are typically **PERMANENT** with **NO APPEAL**.

**The risk of being banned is real and significant.**

**DO NOT USE THIS ON:**
- ❌ Your main account
- ❌ Any account you value
- ❌ Any account with progress you care about
- ❌ Any account you've spent money on
- ❌ Any account you want to keep

**USE ONLY ON:**
- ✅ A throwaway test account created specifically for this educational project
- ✅ An account you are 100% willing to lose permanently

This project is **FOR EDUCATIONAL PURPOSES ONLY**. It was created to understand bot mechanics for anti-cheat development. Using bots on RuneScape violates the game's Terms of Service and will result in a **permanent ban** of your account.

## Purpose

This project demonstrates fundamental bot mechanics using screen-scraping and color detection. It serves as a learning tool to understand:

- How bots "see" the game (screen capture and image processing)
- Color detection and template matching
- Input automation (mouse and keyboard control)
- Basic state machine logic
- Anti-cheat detection vectors

## Project Structure

```
stardust/
├── scripts/              # Main bot scripts
│   ├── bot_utils.py     # Core utility functions
│   └── woodcutter.py    # Main bot script
├── tools/               # Calibration and testing tools
│   ├── calibrate_game_area.py
│   ├── calibrate_inventory.py
│   ├── color_picker.py
│   ├── capture_template.py
│   ├── test_setup.py
│   ├── test_detection.py
│   ├── test_threshold.py
│   ├── debug_tree_detection.py
│   ├── debug_inventory.py
│   └── fix_template.py
├── docs/                # Documentation
│   ├── README.md        # This file
│   ├── TUTORIAL.md      # Complete tutorial
│   ├── SETUP_GUIDE.md   # Quick setup guide
│   └── README_TEMPLATES.md
├── templates/           # Template images for detection
│   └── log_icon.png
├── requirements.txt     # Python dependencies
└── README.md           # Main README with warnings
```

## Setup Instructions

**Note:** Most scripts don't require manual editing. Just use the built-in calibration tools to set up your inventory and screen coordinates. The tools **automatically update** the configuration files for you! Manual editing is only needed for tree colors (from color_picker.py) and optionally tree type.

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Calibrate Game Area

Run the calibration tool to automatically configure your game window coordinates:

```bash
python tools/calibrate_game_area.py
```

Follow the instructions to capture the top-left and bottom-right corners of your game window. The tool will output the `GAME_AREA` values - copy these into `scripts/woodcutter.py`.

**Future improvement:** This will automatically update the configuration file in a future version.

### 3. Calibrate Inventory Area

Run the inventory calibration tool:

```bash
python tools/calibrate_inventory.py
```

Follow the instructions to capture your inventory area. The tool will output the `INVENTORY_AREA` values - copy these into `scripts/woodcutter.py`.

**Future improvement:** This will automatically update the configuration file in a future version.

### 4. Find Tree Colors

Use the color picker to find HSV values for trees:

```bash
python tools/color_picker.py
```

Position your mouse over a tree and press ENTER. Copy the output HSV values into `scripts/woodcutter.py`.

### 5. Create Template Images

Use the automated template capture tool:

```bash
python tools/capture_template.py
```

Follow the instructions to capture a log icon. The tool will automatically save it to `templates/log_icon.png`.

**Note:** You don't need to manually create screenshots or edit images - the tool handles everything.

### 6. Configure the Bot (Minimal)

Edit `scripts/woodcutter.py` and update only:
- `TREE_COLOR_LOWER` and `TREE_COLOR_UPPER`: HSV color range from step 4 (copy manually)
- `TREE_TYPE`: Optional - change if cutting different tree types (default: "regular")

**Note:** `GAME_AREA` and `INVENTORY_AREA` are already automatically configured by the calibration tools (steps 2-3). Most other settings are pre-configured and don't need changes.

### 6. Run the Bot

**⚠️ WARNING: This will get you banned. Use only on a throwaway account. ⚠️**

```bash
python scripts/woodcutter.py
```

Press `Ctrl+C` to stop the bot.

## How It Works

### Screen-Scraping Approach

This bot uses **external screen-scraping**, which means it:
1. Captures screenshots of the game window
2. Analyzes pixels to find objects (using color detection or template matching)
3. Simulates mouse/keyboard input to interact with the game

This is different from **reflection-based bots** (like DreamBot/RuneMate) that hook into the game's memory directly.

### Key Components

1. **scripts/bot_utils.py**: Core functions for:
   - `find_image()`: Template matching to find specific images on screen
   - `find_color()`: Color detection to find objects by color
   - `human_like_move()`: More natural mouse movements
   - `count_inventory_items()`: Count items in inventory

2. **scripts/woodcutter.py**: Main bot logic with a simple state machine:
   - `IDLE`: Looking for trees
   - `CUTTING`: Chopping wood
   - `WALKING_TO_BANK`: Moving to bank
   - `BANKING`: Depositing logs
   - `WALKING_TO_TREES`: Returning to trees

## Limitations & Improvements

This is a **proof of concept** with many limitations:

### Current Limitations:
- ❌ No pathfinding (assumes you're already at trees/bank)
- ❌ Simple timing-based waits (not animation detection)
- ❌ Fragile color detection (breaks with lighting changes)
- ❌ No error recovery for edge cases
- ❌ Basic state machine (not production-ready)

### Potential Improvements:
- ✅ **State Machine**: More robust state management
- ✅ **Pathfinding**: A* algorithm for navigation
- ✅ **Animation Detection**: Detect when actions complete
- ✅ **Multiple Detection Methods**: Combine color + template matching
- ✅ **Anti-Detection**: More human-like behavior patterns
- ✅ **Reflection Hooking**: Direct memory access (advanced)

## Anti-Cheat Detection Vectors

Understanding how bots work helps identify detection methods:

1. **Input Patterns**: Perfect timing, pixel-perfect clicks, straight mouse movements
2. **Behavioral Analysis**: Predictable loops, no human errors, consistent patterns
3. **Screen Reading**: External processes accessing game window
4. **Memory Hooks**: Unauthorized access to game memory (reflection bots)
5. **Statistical Analysis**: Unnatural play patterns (BotWatch)

## For Your Internship

When discussing this project:

> "For my preliminary research, I developed a proof-of-concept automation script using Python and OpenCV to understand the fundamental mechanics of game automation. My script uses screen-scraping and color detection to perform a simple task. Through this process, I've identified several key vulnerabilities and detection vectors, such as predictable input patterns, reliance on static UI elements, and the differences between external screen-scraping and internal client reflection. I'm eager to learn how Jagex's anti-cheat systems, like BotWatch, are designed to detect and counter these various methods."

## Resources

- **OpenCV Documentation**: https://docs.opencv.org/
- **PyAutoGUI Guide**: https://pyautogui.readthedocs.io/
- **MSS (Screen Capture)**: https://python-mss.readthedocs.io/

## Why You Might Be Banned

Jagex's BotWatch system is designed to detect bots through various methods:

1. **Input Pattern Analysis** - Perfect timing, pixel-perfect clicks, robotic mouse movements
2. **Behavioral Analysis** - Predictable loops, no human errors, consistent patterns
3. **Statistical Analysis** - Unnatural play patterns, perfect efficiency
4. **Screen Reading Detection** - External processes accessing game window
5. **Memory Hook Detection** - Unauthorized access to game memory

**This bot may exhibit some of these detectable patterns.** While we've attempted to add randomization and human-like behavior, this is a proof-of-concept project that has **not been extensively tested** for detectability. The risk of detection and ban is unknown but real. You **WILL** be banned.

## License

This project is licensed under the **GNU General Public License v3.0**.

**Important:** While this software is open source under GPL v3, using it to automate RuneScape gameplay violates the game's Terms of Service and may result in a permanent ban. The license grants you the right to use, modify, and distribute the code, but does not grant permission to violate game rules or terms of service.

---

**FINAL WARNING: Using this bot may result in a permanent ban. The detection risk is unknown but real. Use only on accounts you are willing to lose forever.**

