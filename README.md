# Stardust - Educational RuneScape Bot

**Stardust** is a proof-of-concept RuneScape automation bot for educational purposes. While its initial focus is woodcutting, it is designed as a general framework and supports more than just woodcutting tasks.

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

**Note:** The default configuration for colors, screen dimensions, and other settings assumes a 1920x1080 display using the Fixed Classic Layout with Stretched Mode enabled. If you use a different setup, you can adjust these settings using the provided tools.

**Current Features:**

**Woodcutting Module (`scripts/woodcutter.py`):**
- **Advanced color-based tree detection** with multiple geometric filters:
  - Aspect ratio filtering (trees are taller than wide)
  - Size-based filtering (area, height, width constraints)
  - Shape analysis (solidity, extent, circularity, vertex count)
  - Vertical tree band filter (excludes indoor furniture and top-screen clutter)
  - Edge complexity filter (distinguishes trees from smooth objects)
  - Square object rejection (trees are never perfectly square)
  - Window/furniture filter (rejects wide, rectangular objects)
  - Small object filter (rejects tiny items like boxes/crates)
  - Physics-based filters (ground position exclusion, horizontal object rejection)
  - Proximity clustering (prefers trees near other trees)
- **Top-left action text confirmation** using OCR and template matching to verify "Chop down Tree" before clicking
- **Failed tree tracking** - automatically skips trees that don't yield logs after attempts
- **Camera rotation** - automatically rotates camera (arrow keys) when no trees are found
- **Inventory-based cutting logic** - waits for new log to appear in inventory before moving to next tree
- **Advanced inventory full detection** - scans each of 28 slots individually, accounts for non-log items (axe, etc.)
- **Context-aware mouse behavior** - different movement profiles for skilling vs inventory interactions
- **Session-level behavioral variance** - varies focus level and wander chance per session
- **Harmless repositioning** - occasionally moves character slightly to break repetitive patterns
- **Random breaks** to simulate human behavior (configurable frequency)
- **Debug visualization mode** for testing detection

**⚠️ IMPORTANT NOTE ON TREE DETECTION:**
While significant improvements have been made to tree detection with multiple filters and confirmation systems, **tree detection is still not perfect**. The bot may occasionally:
- Miss some trees
- Click on non-tree objects (though this is much rarer now)
- Get stuck trying to cut the same tree repeatedly
- Require manual intervention at times

**However, the detection is good enough to set up and run with minimal management** - you can step away to get food or watch a video, and the bot will generally work decently. Just be aware that occasional monitoring and intervention may be needed.

**Firemaking Module (`scripts/firemaking.py`):**
- Template matching to find logs and tinderbox in inventory
- Uses tinderbox-on-log clicks to light fires
- **"Can't fire" error detection** - detects chat messages when unable to place a fire
- **Intelligent stuck detection and movement** - automatically moves character if unable to place a fire, then tests new locations
- **Log count-based verification** - uses inventory log count changes to verify fire success (more reliable than chat messages)
- **Optimized counting** - single inventory capture for all checks (reduces delays significantly)
- **Advanced log counting** - uses same logic as woodcutter with empty slot templates and per-slot analysis
- **Double-lighting prevention** - prevents attempting to light multiple fires simultaneously
- **Improved fire detection** - multiple verification checks to confirm fire was lit
- **Chat area avoidance** - prevents clicking on chat when moving to new locations
- **Camera adjustments** - randomly rotates camera to "check surroundings" (simulates human behavior)
- Stops when inventory is empty (pathfinding/banking not implemented yet)
- Debug helpers:
  - `tools/debug_firemaking.py` - visualize inventory detection
  - `tools/debug_chat.py` - visualize chat area and error message detection
- **Anti-detection features**:
  - Context-aware mouse behavior (profiled movement)
  - Jittered clicks/movement
  - Idle pauses and "thinking" pauses
  - Capture timing randomness
  - Misclick simulation (rare deliberate misclicks followed by correction)
  - Harmless repositioning after fires
  - Random camera adjustments (looking around)
  - All configurable in `config/player_config.py`

**Ardougne Baker Thieving (`scripts/ardy_baker.py`):**
- **Spam steals from the Ardougne baker stall** while **staying on one tile** for efficient thieving
- **RuneLite Object Marker detection** - Uses red fill marker (same system as woodcutter marker mode) to detect the baker stall
- **Sticky stall targeting** - Locks onto the initial stall position and ignores distant red objects (text, hitsplats, etc.)
  - Requires 20 consecutive detections before switching to a new location
  - Rejects any detection more than 100 pixels from the original stall
  - Prevents random clicks on wrong objects
- **Smart stall waiting** - Waits for the red marker to reappear after each steal (marker disappears during steal animation)
  - Polls every 0.15-0.25 seconds until stall is visible again
  - 8-second timeout before counting as failure
  - 1.5-2.5 second delay after steal before checking for marker
- **Inventory management** - Drops excess loot when inventory is full:
  - Drops ALL bread first (cheapest item)
  - Drops ALL chocolate slice second
  - Drops ALL cakes last
  - Uses shift-click for fast dropping
  - Drops all items of each type until none remain
- **Guard stun avoidance** - Detects stun messages in chat and steps away briefly, then returns to home tile
- **Home tile tracking** - Maintains position on a single square, only moving for guard avoidance
- **Debug tools**:
  - `tools/debug_baker_stall.py` - Visualizes stall detection, shows what the bot sees
  - `DEBUG_MODE` and `DEBUG_SAVE_DETECTIONS` flags for detailed logging
- **Required templates** (in `templates/`):
  - `cake_icon.png` or `cake.png` - Cake inventory icon (for dropping)
  - `bread_icon.png` or `bread.png` - Bread inventory icon (for dropping)
  - `chocolateslice_icon.png` or `chocolate_slice.png` - Chocolate slice inventory icon (for dropping)
  - `stun_message.png` - Chat stun message template (optional but recommended for guard avoidance)
  - `empty_slot.png` - Empty inventory slot (for accurate counting)
- **Configuration**:
  - Uses same `GAME_AREA`, `INVENTORY_AREA`, and `CHAT_AREA` as other scripts
  - UI exclusion zones to filter out chat text and right-side UI panels
  - World Y-axis filtering to keep detections in main play area
  - Configurable delays and thresholds in script constants

**Known Limitations:**
- No pathfinding (assumes you're already near trees/bank)
- **Tree detection is still not perfect** - while significantly improved with multiple filters and confirmation systems, the bot may occasionally miss trees, click wrong objects, or require manual intervention. However, it's **good enough to set up and run with minimal management** - you can step away briefly, but occasional monitoring is recommended.
- No banking implementation - woodcutter stops when inventory is full, firemaking stops when inventory is empty
- Fire burn time in OSRS is constant; leveling Firemaking only unlocks higher-tier logs and increases light success rate, not burn speed
- Color detection may require recalibration for different graphics settings, lighting conditions, or custom client modifications

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
│   ├── firemaking.py    # Firemaking bot module
│   └── ardy_baker.py    # Ardougne baker thieving module
├── tools/               # Calibration and testing tools
│   ├── calibrate_game_area.py
│   ├── calibrate_inventory.py
│   ├── calibrate_chat.py        # Chat area calibration for error detection
│   ├── color_picker.py
│   ├── capture_template.py
│   ├── identify_tree_type.py
│   ├── test_setup.py
│   ├── test_detection.py
│   ├── test_threshold.py
│   ├── debug_tree_detection.py
   │   ├── debug_inventory.py       # Inventory template matching (generic)
   │   ├── debug_firemaking.py      # Firemaking-specific inventory debugging
   │   ├── debug_chat.py            # Chat area and error message debugging
   │   ├── debug_baker_stall.py     # Baker stall detection visualization
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
│   ├── log_icon.png
│   ├── empty_slot.png   # Empty inventory slot (for accurate counting)
│   ├── cant_fire.png    # Chat error message template (optional, for stuck detection)
│   ├── tinderbox_icon.png or log_tinderbox.png
│   ├── cake_icon.png    # Cake inventory icon for eating/dropping
│   ├── bread_icon.png   # Bread inventory icon (for dropping)
│   ├── chocolateslice_icon.png # Chocolate slice inventory icon (for dropping)
│   └── stun_message.png # Chat stun message template (optional, for guards)
│   Note: Baker stall detection uses RuneLite Object Marker (red fill) - no template needed
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Quick Start

**READ THE WARNINGS ABOVE FIRST**

**Note:** Most scripts don't require manual editing. Just use the built-in calibration tools to set up your inventory and screen coordinates. The tools **automatically update** the configuration files for you!

**Woodcutter note:** The woodcutter now supports **marker mode only**. Use the RuneLite Object Marker plugin with filled red highlights on trees (see Marker Mode section below).

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Read the tutorial:**
   See `docs/TUTORIAL.md` for complete step-by-step instructions.

3. **Configure your character:**
   - (Not implemented yet)


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

   **Step 4f: Create Empty Slot Template (Recommended for Accurate Counting)**
   - Make sure you have at least one empty inventory slot
   - Run `python tools/capture_template.py` and save as `empty_slot.png`
   - This template helps the bot accurately count items by detecting empty slots
   - Keep the template in the `templates` folder

   **Step 4g: Calibrate Chat Area (Firemaking - Optional but Recommended)**
   - Open RuneScape and make sure the chat is visible
   - Try to light a fire in an invalid location (e.g., too close to another fire) to see the error message
   - Run `python tools/calibrate_chat.py`
   - Follow the prompts:
     * Move mouse to **top-left corner** of the chat area (where messages appear) → Press ENTER
     * Move mouse to **bottom-right corner** of the chat area → Press ENTER
   - The tool **automatically updates** `scripts/firemaking.py` with the `CHAT_AREA` coordinates

   **Step 4h: Create "Can't Fire" Chat Template (Firemaking - Optional)**
   - Try to light a fire in an invalid location (e.g., too close to another fire)
   - Capture the chat message that appears (e.g., "You can't light a fire here")
   - Run `python tools/capture_template.py` and save as `cant_fire.png`
   - This helps the bot detect when it's stuck and automatically move to a new location
   - Keep the template in the `templates` folder

   **Note:** The calibration tools automatically update the configuration files - no manual editing needed for game area, inventory area, chat area, or tree colors!

5. **Test detection:**
   ```bash
   python tools/test_detection.py
   ```
   This verifies that tree detection and inventory detection are working correctly.

### Ardougne Baker Thieving Setup

**Step 1: Enable RuneLite Object Marker**
- Install and enable the RuneLite **Object Marker** plugin
- Mark the baker stall with a **filled red highlight** (255,0,0)
- The bot uses the same marker detection system as woodcutter marker mode

**Step 2: Calibrate Areas (if not already done)**
- Reuse the same calibrated `GAME_AREA`, `INVENTORY_AREA`, and `CHAT_AREA` from woodcutter/firemaking setup
- If you haven't calibrated yet, follow steps 4a, 4b, and 4g from the Quick Start section above

**Step 3: Create Inventory Templates**
- Capture inventory templates with `python tools/capture_template.py`:
  - `templates/cake_icon.png` or `cake.png` - Cake inventory icon (for dropping)
  - `templates/bread_icon.png` or `bread.png` - Bread inventory icon (for dropping)
  - `templates/chocolateslice_icon.png` or `chocolate_slice.png` - Chocolate slice inventory icon (for dropping)
  - `templates/stun_message.png` - Chat stun message template (optional but recommended for guard avoidance)
  - `templates/empty_slot.png` - Empty inventory slot (for accurate counting, same as woodcutter)

**Step 4: Test Detection (Recommended)**
- Run `python tools/debug_baker_stall.py` to visualize what the bot sees
- Choose option 1 to capture and visualize stall detection
- Verify that:
  - The red stall marker shows a green box (valid detection)
  - Red text in chat and small objects are filtered out
  - The stall is detected correctly

**Step 5: Run the Bot**
- Stand beside the baker stall on the tile you want to camp
- Hover your mouse over your character tile (this sets the "home tile")
- Run: `python scripts/ardy_baker.py`
- The bot will:
  - Detect the red-marked stall
  - Lock onto that stall position (sticky targeting)
  - Stay on your character tile (home tile tracking)
  - Spam steal from the stall
  - Wait for the marker to reappear after each steal
  - Drop all bread, chocolate slice, and excess cakes when inventory is full (shift-click)
  - Step away and return if guard stun is detected

**Troubleshooting:**
- If the bot clicks on wrong objects: The sticky targeting should prevent this, but if it happens, the stall might be too close to other red objects. Try moving to a different position.
- If the bot doesn't find the stall: Check that the Object Marker plugin is enabled and the stall is marked with RED fill color. Run the debug tool to see what's being detected.
- If dropping doesn't work: Make sure you have the inventory templates (`cake_icon.png`, `bread_icon.png`, `chocolateslice_icon.png`) in the `templates/` folder.

## Marker Mode (RuneLite Object Marker)
If you prefer marker-based detection instead of trunk colors:
- Install and enable the RuneLite **Object Marker** plugin.
- Mark trees with a **filled red highlight** (255,0,0); the bot’s marker HSV ranges cover both the 0–25 and 170–180 hue bands.
- In `config/player_config.py`, set `PREFERRED_TREE_TYPE = "marker"`.
- Ensure `templates/log_icon.png` is present and create `templates/empty_slot.png` (screenshot of a clean, empty inventory slot). The bot uses the empty-slot template to count how many slots are free, which makes full-inventory detection much more reliable for marker mode.
- Make sure you **have an axe equipped** before starting.
- Set the camera high and angled down so the highlighted trees are clearly visible in the game area.
- Run the woodcutter in debug first to confirm detections:
  ```bash
  python scripts/woodcutter.py
  ```
  Check the `debug/` images; green boxes on red highlights mean marker detection is working.

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
   
   **For Ardougne Baker Thieving:**
   ```bash
   python scripts/ardy_baker.py
   ```
   
   **Note:** Make sure you have the RuneLite Object Marker plugin enabled with the baker stall marked in RED.
   Stand beside the stall and hover your mouse over your character tile before starting.
   The bot will automatically drop loot when inventory is full and handle guard stuns.
   
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



## Recent Improvements

**Anti-Detection Enhancements:**
- ✅ **Context-aware mouse behavior** - Different movement profiles for skilling, inventory, and banking actions
- ✅ **Misclick simulation** - Rare deliberate misclicks followed by correction (configurable probability)
- ✅ **Session-level behavioral variance** - Varies focus level and wander chance per session to simulate human inconsistency
- ✅ **Harmless repositioning** - Occasionally moves character slightly to break repetitive patterns
- ✅ **Top-left action text confirmation** - Uses OCR and template matching to verify "Chop down Tree" before clicking

**Tree Detection Improvements:**
- ✅ **Multiple geometric filters** - Aspect ratio, size, shape analysis, edge complexity
- ✅ **Physics-based filters** - Vertical orientation, ground position exclusion, horizontal object rejection
- ✅ **Proximity clustering** - Prefers trees near other trees
- ✅ **Failed tree tracking** - Automatically skips trees that don't yield logs
- ✅ **Camera rotation** - Automatically rotates camera when no trees are found
- ✅ **Vertical tree band filter** - Excludes indoor furniture and top-screen clutter

**Inventory Management:**
- ✅ **Slot-by-slot scanning** - Scans each of 28 inventory slots individually
- ✅ **Occupied slot detection** - Accounts for non-log items (axe, tools, etc.)
- ✅ **Inventory-based cutting logic** - Waits for new log to appear before moving to next tree
- ✅ **Improved full detection** - More accurate inventory full detection

**Firemaking Improvements:**
- ✅ **"Can't fire" error detection** - Detects chat messages when unable to place a fire
- ✅ **Intelligent stuck detection and movement** - Automatically moves character and tests new locations
- ✅ **Log count-based verification** - Uses inventory changes to verify fire success (more reliable)
- ✅ **Optimized counting** - Single inventory capture reduces delays from 20+ to just 1 per check
- ✅ **Advanced log counting** - Uses same sophisticated logic as woodcutter (empty slot templates, per-slot analysis)
- ✅ **Chat area avoidance** - Prevents clicking on chat when moving to new locations
- ✅ **Double-lighting prevention** - Prevents concurrent fire lighting attempts
- ✅ **Improved fire detection** - Multiple verification checks
- ✅ **Chat calibration and debugging tools** - New tools for setting up error detection

**Ardougne Baker Thieving Improvements:**
- ✅ **RuneLite Object Marker detection** - Uses red fill marker system (same as woodcutter)
- ✅ **Sticky stall targeting** - Locks onto initial stall position, prevents clicking wrong objects
- ✅ **Smart stall waiting** - Waits for marker to reappear after each steal
- ✅ **Fast shift-click dropping** - Drops all loot items quickly using shift-click
- ✅ **Complete item dropping** - Drops ALL items of each type (bread, chocolate slice, cake) until none remain
- ✅ **Guard stun avoidance** - Detects stun messages and steps away, then returns
- ✅ **Home tile tracking** - Maintains position on single square for efficient spam stealing
- ✅ **UI exclusion zones** - Filters out chat text and right-side UI panels
- ✅ **World Y-axis filtering** - Keeps detections in main play area
- ✅ **Debug visualization tool** - `debug_baker_stall.py` to visualize what the bot sees

## TODO / Planned Features

This project is very much a work-in-progress. Planned improvements include:

- **Pathfinding** - Automatic navigation to trees and banks
- **Banking** - Full banking implementation to deposit logs and withdraw items
- **Better Tree Detection** - Further refinement of detection algorithms (tree detection is still not perfect)
- **Smart Tree Filtering** - Tree logic will use player stats to automatically ignore certain trees depending on the player's woodcutting level
- **State Detection** - Detect actual game states (cutting animation, inventory updates) instead of timers
- **Error Recovery** - Handle edge cases and recover from errors gracefully

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
