"""
Stardust - Educational Woodcutting Bot
This script demonstrates basic bot mechanics using screen-scraping and color detection.

IMPORTANT: This is for educational purposes only. Using bots on RuneScape violates
the game's terms of service and will result in a permanent ban.
"""
import sys
import os
# Add parent directory to path to import bot_utils and config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot_utils
import pyautogui
import time
import random
import numpy as np

# Import player configuration
try:
    from config import player_config, player_stats
    USE_PLAYER_CONFIG = True
except ImportError:
    print("⚠ Warning: config/player_config.py or config/player_stats.py not found. Using default settings.")
    USE_PLAYER_CONFIG = False
    player_stats = None

# --- Configuration ---
# IMPORTANT: Set these to your game window's coordinates
# Use the calibrate_game_area.py script to find these values
GAME_AREA = {"top": 25, "left": 0, "width": 1880, "height": 989}

# --- Debug Mode ---
# Set to True to save debug images showing what the bot detects
# Images will be saved to a 'debug' folder in the project root
DEBUG_MODE = True  # Set to True to enable debug visualization

# IMPORTANT: Find the HSV color range for the tree you want to cut.
# Use tools/color_picker.py or tools/identify_tree_type.py to find these values.
# 
# Different tree types have different colors. Use identify_tree_type.py to compare them.
# 
# Default values (for regular trees):
# Tree 1: H=0, S=0, V=12 (dark trunk)
# Tree 2: H=10, S=67, V=23 (brown trunk)
# Narrowed range to reduce UI element detection
TREE_COLOR_LOWER = (1, 65, 45)      # Lower HSV bound - dark brown/black trees
TREE_COLOR_UPPER = (21, 125, 105)    # Upper HSV bound - brown trees (narrowed to reduce UI matches)

# Optional: Define different color ranges for different tree types
# Uncomment and configure these if you want to cut specific tree types:
# OAK_COLOR_LOWER = (0, 0, 10)      # Oak tree colors (if different from regular)
# OAK_COLOR_UPPER = (25, 80, 40)
# WILLOW_COLOR_LOWER = (0, 0, 10)   # Willow tree colors (if different from regular)
# WILLOW_COLOR_UPPER = (25, 80, 40)
# MAPLE_COLOR_LOWER = (0, 0, 10)    # Maple tree colors (if different from regular)
# MAPLE_COLOR_UPPER = (25, 80, 40)

# UI exclusion area - trees shouldn't be in the UI panels (right side)
# Adjust these if your UI is in a different location
# Exclude right side where inventory/minimap typically are
UI_EXCLUSION_LEFT = GAME_AREA["left"] + GAME_AREA["width"] * 0.65  # Exclude right 35% of screen (more aggressive)
# Also exclude bottom-right corner where inventory typically is
UI_EXCLUSION_BOTTOM = GAME_AREA["top"] + GAME_AREA["height"] * 0.6  # Exclude bottom 40% of screen
UI_EXCLUSION_RIGHT_EDGE = GAME_AREA["left"] + GAME_AREA["width"] * 0.5  # Exclude right 50% if object is wide

# Path to the image of a log in your inventory
# Take a screenshot of a single log icon and save it as log_icon.png
LOG_ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "log_icon.png")

# Tree type configuration
# This will be auto-set from player_config.py if available
# Otherwise, set it manually here:
# - "regular": Level 1 trees - 1 log per tree, ~2-3 seconds to cut down
# - "oak": Level 15 - 27 seconds per log, multiple logs per tree
# - "willow": Level 30 - 30 seconds per log, multiple logs per tree
# - "maple": Level 45 - 60 seconds per log, multiple logs per tree
# - "yew": Level 60 - 114 seconds per log, multiple logs per tree
# - "magic": Level 75 - 234 seconds per log, multiple logs per tree

# Auto-set from player config if available
if USE_PLAYER_CONFIG and player_stats:
    # Check if player has preferred tree type set
    if player_config.PREFERRED_TREE_TYPE:
        TREE_TYPE = player_config.PREFERRED_TREE_TYPE
    else:
        # Auto-select best tree based on level
        TREE_TYPE = player_stats.get_best_available_tree()
    
    # Verify player can actually cut this tree type
    available_trees = player_stats.get_available_tree_types()
    if TREE_TYPE not in available_trees:
        print(f"⚠ Warning: Cannot cut {TREE_TYPE} trees at level {player_stats.WOODCUTTING_LEVEL}")
        print(f"  Available trees: {available_trees}")
        TREE_TYPE = available_trees[0] if available_trees else "regular"
        print(f"  Using {TREE_TYPE} instead")
else:
    # Default fallback if config not available
    TREE_TYPE = "regular"

# Inventory area (typically bottom right of game window)
# Calibrated using calibrate_inventory.py
INVENTORY_AREA = {
    "top": 442,
    "left": 1509,
    "width": 354,
    "height": 494
}

# --- State Management ---
class BotState:
    """Simple state machine for bot behavior"""
    IDLE = "idle"
    CUTTING = "cutting"
    WALKING_TO_BANK = "walking_to_bank"
    BANKING = "banking"
    WALKING_TO_TREES = "walking_to_trees"

# --- Main Bot Logic ---

def check_inventory_full():
    """
    Checks if inventory is full by counting log icons.
    Returns True if inventory appears full (>= 27 items).
    Uses a higher threshold (0.9) to reduce false positives.
    """
    # Use higher threshold (0.9) to reduce false positives
    # The counting function groups nearby matches to avoid duplicates
    count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=0.9)
    print(f"Inventory check: Found {count} logs")
    # For a more accurate check, we could also verify by finding at least one log
    # and checking if count is reasonable (not way more than inventory slots)
    if count > 28:  # More than max inventory slots suggests false positives
        print(f"  Warning: Count ({count}) seems too high, may have false positives")
    return count >= 27

def find_and_click_tree():
    """
    Finds a tree using color detection and clicks on it.
    Returns True if tree was found and clicked, False otherwise.
    Uses area and aspect ratio filters to avoid detecting players, sticks, etc.
    Prioritizes larger trees over small ground objects.
    Excludes UI areas to avoid detecting inventory/minimap elements.
    
    Automatically uses the correct color range based on TREE_TYPE if configured.
    
    WARNING: Color detection cannot distinguish between tree types!
    Make sure your color range is calibrated for the specific tree type you want to cut.
    If you're level 1 but the bot clicks oak trees, your color range is too broad.
    """
    # CRITICAL: Verify player can actually cut this tree type
    if USE_PLAYER_CONFIG and player_stats:
        if not player_stats.can_cut_tree_type(TREE_TYPE):
            print(f"  ❌ ERROR: Cannot cut {TREE_TYPE} trees at level {player_stats.WOODCUTTING_LEVEL}")
            available = player_stats.get_available_tree_types()
            print(f"  Available trees: {', '.join(available)}")
            print(f"  Please update PREFERRED_TREE_TYPE in config/player_config.py or update WOODCUTTING_LEVEL in config/player_stats.py")
            return False
        
        # Get tree info for size-based filtering
        tree_info = player_stats.get_tree_info(TREE_TYPE)
        if tree_info:
            required_level = tree_info["level"]
            if player_stats.WOODCUTTING_LEVEL < required_level:
                print(f"  ❌ ERROR: Cannot cut {TREE_TYPE} trees! Required level: {required_level}, Your level: {player_stats.WOODCUTTING_LEVEL}")
                return False
    
    print(f"Looking for a {TREE_TYPE} tree...")
    
    # Use tree-type-specific colors if available, otherwise use default
    # This allows you to configure different colors for different tree types
    color_lower = TREE_COLOR_LOWER
    color_upper = TREE_COLOR_UPPER
    
    # Check if tree-type-specific colors are defined
    if TREE_TYPE == "oak" and 'OAK_COLOR_LOWER' in globals():
        color_lower = OAK_COLOR_LOWER
        color_upper = OAK_COLOR_UPPER
        print("  Using oak-specific color range")
    elif TREE_TYPE == "willow" and 'WILLOW_COLOR_LOWER' in globals():
        color_lower = WILLOW_COLOR_LOWER
        color_upper = WILLOW_COLOR_UPPER
        print("  Using willow-specific color range")
    elif TREE_TYPE == "maple" and 'MAPLE_COLOR_LOWER' in globals():
        color_lower = MAPLE_COLOR_LOWER
        color_upper = MAPLE_COLOR_UPPER
        print("  Using maple-specific color range")
    elif TREE_TYPE == "yew" and 'YEW_COLOR_LOWER' in globals():
        color_lower = YEW_COLOR_LOWER
        color_upper = YEW_COLOR_UPPER
        print("  Using yew-specific color range")
    elif TREE_TYPE == "magic" and 'MAGIC_COLOR_LOWER' in globals():
        color_lower = MAGIC_COLOR_LOWER
        color_upper = MAGIC_COLOR_UPPER
        print("  Using magic-specific color range")
    else:
        print("  Using default color range (works for regular trees)")
    
    # Filter parameters based on tree type:
    # ⚠ IMPORTANT: Regular and oak trees have similar colors but DIFFERENT SIZES!
    # - Regular trees (level 1): Smaller - use min_area=400-800, max_area=8000, min_height=30
    # - Oak trees (level 15): Larger - use min_area=3000, max_area=50000, min_height=55
    # Size filtering is the KEY to distinguishing tree types when colors are similar!
    if TREE_TYPE == "regular":
        # Regular trees are smaller - filter out larger oak trees
        min_area = 600      # Minimum size for regular trees (increased to filter small furniture)
        max_area = 8000     # Maximum size - filters out larger oak trees!
        min_height = 35     # Trees should have some height (increased to filter short furniture)
        print("  Using size filters for REGULAR trees (filters out larger oak trees and furniture)")
    elif TREE_TYPE == "oak":
        # Oak trees are larger - filter out smaller regular trees
        min_area = 3000     # Minimum size - filters out smaller regular trees!
        max_area = 50000    # Allow large oak trees
        min_height = 55     # Oak trees are taller
        print("  Using size filters for OAK trees (filters out smaller regular trees)")
    else:
        # Default for other tree types
        min_area = 400      # Minimum size for trees
        max_area = 50000
        min_height = 30     # Trees should have some height
    
    # Filter parameters:
    # min_area: Varies by tree type (regular=400, oak=3000) - KEY for distinguishing tree types!
    # max_area: Varies by tree type (regular=8000, oak=50000) - filters wrong tree types!
    # aspect_ratio: 0.4 to 2.5 - trees can vary in shape
    # min_height: Varies by tree type (regular=30, oak=55) - helps filter wrong tree types
    # max_width: 300 - filters very wide UI panels (trees aren't that wide)
    # max_height: 400 - filters very tall UI panels (trees aren't that tall)
    # exclude_ui_left: Exclude right side where UI is (inventory, minimap, etc.)
    
    # Debug visualization if enabled
    if DEBUG_MODE:
        print("  🔍 DEBUG MODE: Creating visualization...")
        debug_img, mask_img, detection_info = bot_utils.visualize_color_detection(
            color_lower,
            color_upper,
            GAME_AREA,
            min_area=min_area,
            max_area=max_area,
            min_aspect_ratio=0.4,
            max_aspect_ratio=2.5,
            min_height=min_height,
            max_width=300,
            max_height=400,
            exclude_ui_left=UI_EXCLUSION_LEFT,
            exclude_ui_bottom=UI_EXCLUSION_BOTTOM,
            exclude_ui_right_edge=UI_EXCLUSION_RIGHT_EDGE
        )
        print(f"  📊 Detection stats:")
        print(f"     - Total contours found: {detection_info['total_contours']}")
        print(f"     - Valid contours: {detection_info['valid_contours']}")
        print(f"     - Invalid (filtered): {detection_info['invalid_contours']}")
        if detection_info['selected_contour']:
            sel = detection_info['selected_contour']
            print(f"     - Selected tree: Area={int(sel['area'])}, Size={sel['w']}x{sel['h']}")
        else:
            print(f"     - No valid trees detected!")
    
    tree_pos = bot_utils.find_color(
        color_lower, 
        color_upper, 
        GAME_AREA,
        min_area=min_area,      # Varies by tree type - KEY for filtering wrong tree types!
        max_area=max_area,      # Varies by tree type - filters wrong tree types!
        min_aspect_ratio=0.4,  # Trees can be somewhat tall
        max_aspect_ratio=2.5,  # Trees can be somewhat wide
        min_height=min_height,  # Varies by tree type - helps filter wrong tree types
        max_width=300,     # Maximum width (filters large UI panels)
        max_height=400,    # Maximum height (filters large UI panels)
        exclude_ui_left=UI_EXCLUSION_LEFT,  # Exclude UI area (right side)
        exclude_ui_bottom=UI_EXCLUSION_BOTTOM,  # Exclude bottom area (inventory)
        exclude_ui_right_edge=UI_EXCLUSION_RIGHT_EDGE  # Exclude if extends into right side
    )
    
    if tree_pos:
        print(f"Tree found at {tree_pos}. Clicking...")
        bot_utils.human_like_click(tree_pos[0], tree_pos[1])
        return True
    else:
        print("No tree found.")
        return False

def wait_for_cutting_completion():
    """
    Waits for the character to finish cutting.
    In a more advanced bot, this would check for animation states.
    For now, we use a simple randomized wait time based on tree type.
    Note: This is a simple timer-based approach. A real bot would detect
    when the inventory updates or when the animation stops.
    """
    # Get wait time from player_stats if available, otherwise use defaults
    if USE_PLAYER_CONFIG and player_stats:
        try:
            tree_info = player_stats.get_tree_info(TREE_TYPE)
            if tree_info:
                wait_range = tree_info["wait_time"]
                xp = tree_info["xp"]
                logs_per = tree_info.get("logs_per_tree", "multiple")
                wait_time = random.uniform(wait_range[0], wait_range[1])
                print(f"Cutting {TREE_TYPE} tree... (waiting {wait_time:.1f} seconds, {xp} XP per log, {logs_per} logs per tree)")
                time.sleep(wait_time)
                return
        except Exception as e:
            print(f"⚠ Warning: Could not get tree info from player_stats: {e}")
            pass  # Fallback to default if error
    
    # Default wait times (fallback if config not available)
    tree_wait_times = {
        "regular": (2, 3),      # Level 1 - 1 log per tree, ~2.4 seconds to cut down
        "oak": (25, 29),        # Level 15 - 45 ticks (27 seconds) per log
        "willow": (28, 32),     # Level 30 - 50 ticks (30 seconds) per log
        "teak": (28, 32),       # Level 35 - 50 ticks (30 seconds) per log
        "maple": (58, 62),      # Level 45 - 100 ticks (60 seconds) per log
        "mahogany": (58, 62),   # Level 50 - 100 ticks (60 seconds) per log
        "yew": (110, 118),      # Level 60 - 190 ticks (114 seconds) per log
        "magic": (230, 238),    # Level 75 - 390 ticks (234 seconds) per log
    }
    
    # Get wait time for current tree type, default to regular if not found
    wait_range = tree_wait_times.get(TREE_TYPE, tree_wait_times["regular"])
    wait_time = random.uniform(wait_range[0], wait_range[1])
    
    print(f"Cutting {TREE_TYPE} tree... (waiting {wait_time:.1f} seconds per log)")
    time.sleep(wait_time)

def drop_logs():
    """
    Drops all logs from inventory.
    Used when LOG_DISPOSAL_METHOD is set to "drop" in player_config.
    """
    print("Dropping logs...")
    
    # Find all log icons in inventory
    count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=0.9)
    
    if count == 0:
        print("No logs found in inventory.")
        return False
    
    print(f"Dropping {count} logs...")
    
    # Find and drop each log
    # In a real implementation, you'd iterate through inventory slots
    # For now, we'll just find one and drop it multiple times
    log_pos = bot_utils.find_image(LOG_ICON_PATH, threshold=0.9, game_area=INVENTORY_AREA)
    
    if log_pos:
        # Shift-click to drop (or right-click and select drop)
        # For now, just right-click and we'd need a drop template
        bot_utils.human_like_move(log_pos[0], log_pos[1])
        time.sleep(random.uniform(0.1, 0.2))
        pyautogui.rightClick()
        time.sleep(random.uniform(0.2, 0.4))
        # In a real implementation, find and click "Drop" option
        print("(Placeholder: Would click Drop here)")
        return True
    
    return False

def bank_logs():
    """
    Attempts to deposit logs at the bank.
    This is a simplified version - a real bot would need:
    - Pathfinding to reach the bank
    - Detection of bank booth/chest
    - Opening the bank interface
    - Clicking deposit-all or individual items
    """
    # Check player config for disposal method
    if USE_PLAYER_CONFIG and player_config.LOG_DISPOSAL_METHOD == "drop":
        return drop_logs()
    
    print("Attempting to bank logs...")
    
    # Find log icon in inventory (use higher threshold 0.9 to reduce false positives)
    log_pos = bot_utils.find_image(LOG_ICON_PATH, threshold=0.9, game_area=INVENTORY_AREA)
    
    if log_pos:
        print("Found logs in inventory. Right-clicking...")
        # Right-click on logs
        bot_utils.human_like_move(log_pos[0], log_pos[1])
        time.sleep(random.uniform(0.1, 0.3))
        pyautogui.rightClick()
        time.sleep(random.uniform(0.3, 0.5))
        
        # In a real implementation, you'd need to find and click "Deposit-All"
        # For now, this is a placeholder
        print("(Placeholder: Would click Deposit-All here)")
        
        # Close bank with Escape
        time.sleep(random.uniform(0.5, 1.0))
        pyautogui.press('escape')
        time.sleep(random.uniform(0.5, 1.0))
        return True
    else:
        print("Could not find logs in inventory.")
        return False

def take_break():
    """
    Simulates an AFK break to appear more human-like.
    Real players don't play continuously for hours.
    Uses settings from player_config.py if available.
    """
    if USE_PLAYER_CONFIG:
        if not player_config.ENABLE_BREAKS:
            return
        break_chance = player_config.BREAK_CHANCE
        break_min = player_config.BREAK_DURATION_MIN
        break_max = player_config.BREAK_DURATION_MAX
    else:
        break_chance = 0.1  # 10% default
        break_min = 30
        break_max = 120
    
    if random.random() < break_chance:
        break_duration = random.uniform(break_min, break_max)
        print(f"Taking a break for {break_duration:.1f} seconds...")
        time.sleep(break_duration)

def main():
    """
    Main bot loop. Implements a simple state machine for woodcutting.
    """
    print("=" * 60)
    print("Stardust - Educational Woodcutting Bot")
    print("=" * 60)
    print("\nWARNING: This bot is for educational purposes only.")
    print("Using bots on RuneScape may result in a permanent ban.")
    
    if DEBUG_MODE:
        print("\n" + "=" * 60)
        print("🔍 DEBUG MODE ENABLED")
        print("=" * 60)
        print("Debug images will be saved to the 'debug' folder.")
        print("Green boxes = Valid trees (would be clicked)")
        print("Red boxes = Invalid objects (filtered out)")
        print("Red circles = Click target (center of selected tree)")
        print("Purple line = UI exclusion boundary")
        print("=" * 60)
    
    # Display player configuration if available
    if USE_PLAYER_CONFIG:
        print(f"\nPlayer Configuration:")
        print(f"  Woodcutting Level: {player_config.WOODCUTTING_LEVEL}")
        print(f"  Available Trees: {', '.join(player_config.get_available_tree_types())}")
        print(f"  Selected Tree Type: {TREE_TYPE}")
        
        # CRITICAL: Verify player can cut this tree type
        if player_stats:
            tree_info = player_stats.get_tree_info(TREE_TYPE)
            if tree_info:
                required_level = tree_info["level"]
                if player_stats.WOODCUTTING_LEVEL < required_level:
                    print(f"\n❌ ERROR: Cannot cut {TREE_TYPE} trees!")
                    print(f"   Required Level: {required_level}")
                    print(f"   Your Level: {player_stats.WOODCUTTING_LEVEL}")
                    print(f"   Please update WOODCUTTING_LEVEL in config/player_stats.py")
                    print(f"   Or set PREFERRED_TREE_TYPE to a tree you can cut in config/player_config.py")
                    print("\nBot will not start. Please fix your configuration.")
                    return
                else:
                    print(f"  ✓ Tree Type Valid (Level {required_level} required, you are level {player_stats.WOODCUTTING_LEVEL})")
            else:
                print(f"\n⚠ Warning: Unknown tree type '{TREE_TYPE}'")
                if player_stats:
                    print(f"   Available trees: {', '.join(player_stats.get_available_tree_types())}")
        
        # Warn about color calibration
        print(f"\n⚠ IMPORTANT: Color Detection Warning")
        print(f"   The bot uses color detection to find trees.")
        print(f"   Make sure TREE_COLOR_LOWER and TREE_COLOR_UPPER are calibrated for {TREE_TYPE} trees.")
        print(f"   Different tree types may have different colors!")
        print(f"   Use tools/color_picker.py or tools/identify_tree_type.py to calibrate.")
        print(f"   Size filtering helps distinguish tree types, but color calibration is critical!")
        if TREE_TYPE == "regular":
            print(f"   ⚠ If you see oak trees but are level 1, your color range may be detecting oak trees.")
            print(f"   ⚠ The bot uses size filtering (max_area=8000) to filter out larger oak trees.")
        
        if player_config.LOG_DISPOSAL_METHOD == "drop":
            print(f"  Log Disposal: Dropping logs")
        else:
            print(f"  Log Disposal: Banking logs")
        if player_config.ENABLE_BREAKS:
            print(f"  Breaks: Enabled ({player_config.BREAK_CHANCE*100:.0f}% chance)")
        else:
            print(f"  Breaks: Disabled")
    else:
        print("⚠ Warning: Player config not loaded. Using default settings.")
        print(f"  Selected Tree Type: {TREE_TYPE} (default)")
    
    print("\nStarting in 5 seconds... Switch to RuneScape window now.")
    print("Press Ctrl+C in this terminal to stop the bot.\n")
    
    time.sleep(5)
    
    state = BotState.IDLE
    cycles_completed = 0
    
    try:
        while True:
            # Take occasional breaks to appear more human-like
            take_break()
            
            # State machine logic
            if state == BotState.IDLE:
                print("\n--- Starting new cycle ---")
                if find_and_click_tree():
                    state = BotState.CUTTING
                    wait_for_cutting_completion()
                else:
                    print("Could not find tree. Waiting...")
                    time.sleep(random.uniform(2, 4))
            
            elif state == BotState.CUTTING:
                # Wait a bit before checking inventory (don't check too frequently)
                time.sleep(random.uniform(2, 4))
                
                # Check if we should continue cutting or go bank
                if check_inventory_full():
                    print("Inventory is full! Moving to bank...")
                    state = BotState.WALKING_TO_BANK
                else:
                    # Continue cutting - wait longer between tree clicks
                    # This simulates the time it takes to cut multiple logs from one tree
                    wait_between_trees = random.uniform(3, 6)  # Wait 3-6 seconds between trees
                    print(f"Continuing to cut... (waiting {wait_between_trees:.1f} seconds)")
                    time.sleep(wait_between_trees)
                    
                    # Find and click next tree
                    if find_and_click_tree():
                        # Wait for cutting to start and get first log
                        wait_for_cutting_completion()
                    else:
                        print("Lost tree. Searching again...")
                        state = BotState.IDLE
                        time.sleep(random.uniform(1, 2))
            
            elif state == BotState.WALKING_TO_BANK:
                # In a real bot, this would use pathfinding
                # For now, we assume you're already near a bank
                print("(Placeholder: Would use pathfinding to reach bank)")
                state = BotState.BANKING
                time.sleep(random.uniform(1, 2))
            
            elif state == BotState.BANKING:
                if bank_logs():
                    print("Successfully banked logs!")
                    cycles_completed += 1
                    print(f"Cycles completed: {cycles_completed}")
                    state = BotState.WALKING_TO_TREES
                else:
                    print("Banking failed. Retrying...")
                    time.sleep(random.uniform(1, 2))
            
            elif state == BotState.WALKING_TO_TREES:
                # In a real bot, this would use pathfinding
                print("(Placeholder: Would use pathfinding to reach trees)")
                state = BotState.IDLE
                time.sleep(random.uniform(1, 2))
            
            # Small random delay between state transitions
            time.sleep(random.uniform(0.5, 1.5))
            
    except KeyboardInterrupt:
        print("\n\nBot stopped by user.")
        print(f"Total cycles completed: {cycles_completed}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

