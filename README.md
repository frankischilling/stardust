# Stardust - Educational RuneScape Bot

**Stardust** is a proof-of-concept woodcutting bot for educational purposes.

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

## Purpose

This project is **FOR EDUCATIONAL PURPOSES ONLY**. It was created to understand bot mechanics for anti-cheat development. Using bots on RuneScape violates the game's Terms of Service and will result in a **permanent ban** of your account.

**THIS IS A VERY WORK-IN-PROGRESS (WIP) PROJECT**

**Stardust** is a general-purpose RuneScape bot framework designed for all skills and activities. Currently, woodcutting and firemaking are the first implemented features, demonstrating fundamental bot mechanics using screen-scraping, color detection, and template matching.

**Current Features:**

**Woodcutting Module (`scripts/woodcutter.py`):**
- Basic color-based tree detection (**Still a work in progress** - may not work, miss trees, or highlight wrong objects)
- Detection may need color recalibration for your specific setup, lighting, or graphics settings
- Supports detecting trees at different distances (zoomed in/out)
- Tracks recently clicked trees to avoid clicking the same tree repeatedly
- Random breaks to simulate human behavior
- Simple state machine for woodcutting cycles
- Inventory detection (checking if inventory is full)
- Debug visualization mode

**Firemaking Module (`scripts/firemaking.py`):**
- Template matching to find logs and tinderbox in inventory
- Uses tinderbox-on-log clicks to light fires
- Stops when inventory is empty (pathfinding/banking not implemented yet)
- Debug helper `tools/debug_firemaking.py` to visualize what the bot sees
- Anti-detection: jittered clicks/movement, idle pauses, and capture timing randomness (configurable)

**Known Limitations:**
- No pathfinding (assumes you're already near trees/bank)
- **Tree detection is still a work in progress** - may not work at all, miss trees, highlight wrong objects (furniture, UI elements, etc.), or require color recalibration for your specific setup, lighting, or graphics settings
- Filters are continuously being improved but false positives and false negatives are still common
- Simple timing-based wait system (doesn't detect actual game state)
- No error recovery or advanced state detection
- Firemaking module stops when inventory is empty (no banking yet)
- Fire burn time in OSRS is constant; leveling Firemaking only unlocks higher-tier logs and increases light success rate, not burn speed

This serves as a learning tool to understand:

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
│   ├── woodcutter.py    # Woodcutting bot module
│   └── firemaking.py    # Firemaking bot module
├── tools/               # Calibration and testing tools
│   ├── calibrate_game_area.py
│   ├── calibrate_inventory.py
│   ├── color_picker.py
│   ├── capture_template.py
│   ├── identify_tree_type.py
│   ├── test_setup.py
│   ├── test_detection.py
│   ├── test_threshold.py
│   ├── debug_tree_detection.py
│   ├── debug_inventory.py       # Inventory template matching (generic)
│   ├── debug_firemaking.py      # Firemaking-specific inventory debugging
│   └── fix_template.py
├── config/              # Player configuration
│   ├── player_stats.py  # Your character's skill levels
│   ├── player_config.py # Bot behavior preferences
│   └── README.md        # Config documentation
├── docs/                # Documentation
│   ├── README.md        # Detailed documentation
│   ├── TUTORIAL.md      # Complete step-by-step tutorial
│   ├── SETUP_GUIDE.md   # Quick setup guide
│   └── README_TEMPLATES.md
├── templates/           # Template images for detection
│   └── log_icon.png
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Quick Start

**READ THE WARNINGS ABOVE FIRST**

**Note:** Most scripts don't require manual editing. Just use the built-in calibration tools to set up your inventory and screen coordinates. The tools **automatically update** the configuration files for you!

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Read the tutorial:**
   See `docs/TUTORIAL.md` for complete step-by-step instructions.

3. **Configure your character:**
   - Edit `config/player_stats.py` - Update your **Woodcutting Level** (most important!)
   - If using firemaking, also update your **Firemaking Level** (burn time is fixed; level mainly unlocks higher-tier logs and improves light chance)
   - Edit `config/player_config.py` - Set preferences (optional, has sensible defaults)
   - The bot automatically selects the best tree type based on your level

4. **Calibrate your setup (automated):**
   
   **Step 4a: Calibrate Game Window Area**
   - Open RuneScape and position the window where you want it
   - Run `python tools/calibrate_game_area.py`
   - Follow the prompts:
     * Move mouse to **top-left corner** of the game window → Press ENTER
     * Move mouse to **bottom-right corner** of the game window → Press ENTER
   - The tool **automatically updates** `scripts/woodcutter.py` with the `GAME_AREA` coordinates
   
   **Step 4b: Calibrate Inventory Area**
   - Make sure your inventory is visible in RuneScape
   - Run `python tools/calibrate_inventory.py`
   - Follow the prompts:
     * Move mouse to **top-left corner** of the inventory grid (not the tab, the actual grid) → Press ENTER
     * Move mouse to **bottom-right corner** of the inventory grid → Press ENTER
   - The tool **automatically updates** `scripts/woodcutter.py` with the `INVENTORY_AREA` coordinates
   
   **Step 4c: Calibrate Tree Colors**
   - **Important:** The default color calibration is set up for **basic OSRS** (standard textures, default lighting, no shading mods)
   - If you're using **custom textures, lighting mods, or shading**, you **MUST** recalibrate the tree colors
   - Run `python tools/calibrate_tree_colors.py` (recommended) or `python tools/color_picker.py`
   - Follow the prompts to capture tree colors
   - The calibration tool **automatically updates** `scripts/woodcutter.py` with the color values
   
   **Step 4d: Create Log Template**
   - Make sure you have at least one log in your inventory
   - Run `python tools/capture_template.py`
   - Follow the prompts to capture a log icon template

   **Step 4e: Create Tinderbox Template (Firemaking)**
   - Ensure a tinderbox is in your inventory
   - Run `python tools/capture_template.py` and save as `tinderbox_icon.png` (or `log_tinderbox.png`)
   - Keep the template in the `templates` folder so `firemaking.py` can load it

   **Note:** The calibration tools automatically update the configuration files - no manual editing needed for game area, inventory area, or tree colors!

5. **Test detection:**
   ```bash
   python tools/test_detection.py
   ```
   This verifies that tree detection and inventory detection are working correctly.

6. **Run the bot (AT YOUR OWN RISK):**
   
   **For Woodcutting:**
   ```bash
   python scripts/woodcutter.py
   ```
   
   **For Firemaking:**
   ```bash
   python scripts/firemaking.py
   ```
   
   **Note:** The firemaking bot will stop when your inventory is empty since pathfinding to bank is not implemented yet.
   Make sure logs and a tinderbox are in your inventory before you start.
   Anti-detection settings (jittered input, idle pauses, capture delays) are enabled by default; tune them in `config/player_config.py`.

## Troubleshooting

### Woodcutting Module Not Working?

**If the woodcutting module isn't detecting trees correctly, the most common fix is to recalibrate the tree colors:**

1. **Run the tree color calibration tool:**
   ```bash
   python tools/calibrate_tree_colors.py
   ```

2. **Select the tree type you're trying to cut** (e.g., "1" for Regular Trees)

3. **Follow the prompts** to capture 3-5 color samples from different parts of the tree trunk

4. **Save the calibration** - The tool automatically updates `scripts/woodcutter.py` with the new color values

5. **Test again** with `python tools/debug_tree_detection.py` to verify trees are now detected

**Why this helps:** Tree colors can vary based on:
- Your graphics settings (lighting, shadows, textures)
- Time of day in-game
- Different tree types
- Custom client modifications

If the bot isn't finding trees, it's usually because the color range doesn't match your specific setup. Recalibrating ensures the color detection matches your game's appearance.

## TODO / Planned Features

This project is very much a work-in-progress. Planned improvements include:

- **Pathfinding** - Automatic navigation to trees and banks
- **Banking** - Full banking implementation to deposit logs and withdraw items
- **Better Tree Detection** - Improved detection and distinction between different tree types (oak, willow, maple, yew, magic, etc.)
- **Smart Tree Filtering** - Tree logic will use player stats to automatically ignore certain trees depending on the player's woodcutting level (e.g., ignore oak trees if level is too low)
- **State Detection** - Detect actual game states (cutting animation, inventory updates) instead of timers
- **Error Recovery** - Handle edge cases and recover from errors gracefully
- **Advanced Filtering** - More sophisticated filters to distinguish trees from other objects (furniture, UI elements, etc.)

## Documentation

- **[Complete Tutorial](docs/TUTORIAL.md)** - Step-by-step guide from installation to running
- **[Setup Guide](docs/SETUP_GUIDE.md)** - Quick reference for setup
- **[Detailed README](docs/README.md)** - Full documentation and technical details

## Why You Might Be Banned

Jagex's BotWatch system is designed to detect bots through various methods:

1. **Input Pattern Analysis** - Perfect timing, pixel-perfect clicks, robotic mouse movements
2. **Behavioral Analysis** - Predictable loops, no human errors, consistent patterns
3. **Statistical Analysis** - Unnatural play patterns, perfect efficiency
4. **Screen Reading Detection** - External processes accessing game window
5. **Memory Hook Detection** - Unauthorized access to game memory

**This bot may exhibit some of these detectable patterns.** While we've attempted to add randomization and human-like behavior, this is a proof-of-concept project that has **not been extensively tested** for detectability. The risk of detection and ban is unknown but real.

## Legal and Ethical Notice

- Using bots violates RuneScape's Terms of Service
- Bans are permanent and cannot be appealed
- This project is for educational/research purposes only
- Do not use this to gain unfair advantages
- Respect other players and the game economy

## For Anti-Cheat Developers

This project demonstrates:

- Screen-scraping bot mechanics
- Color detection and template matching
- Input automation patterns
- State machine design
- Detection vectors and vulnerabilities

Use this knowledge to improve anti-cheat systems, not to create better bots.

## License

This project is licensed under the **GNU General Public License v3.0**.

**Important:** While this software is open source under GPL v3, using it to automate RuneScape gameplay violates the game's Terms of Service and may result in a permanent ban. The license grants you the right to use, modify, and distribute the code, but does not grant permission to violate game rules or terms of service.

---

**FINAL WARNING: Using this bot may result in a permanent ban. The detection risk is unknown but real. Use only on accounts you are willing to lose forever.**
