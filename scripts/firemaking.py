"""
Stardust - Educational Firemaking Bot
This script demonstrates basic bot mechanics using template matching for inventory items.

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
DEBUG_MODE = False  # Set to True to enable debug visualization

# Path to the image of a log in your inventory
# Take a screenshot of a single log icon and save it as log_icon.png
LOG_ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "log_icon.png")

# Path to the image of a tinderbox in your inventory
# Take a screenshot of a tinderbox icon and save it as tinderbox_icon.png or log_tinderbox.png
# Use tools/capture_template.py to create this template
TINDERBOX_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
TINDERBOX_ICON_PATH = None  # Will be set to first available template

# Check for tinderbox template with common filenames
for filename in ["tinderbox_icon.png", "log_tinderbox.png", "tinderbox.png"]:
    path = os.path.join(TINDERBOX_TEMPLATE_DIR, filename)
    if os.path.exists(path):
        TINDERBOX_ICON_PATH = path
        break

# Inventory area (typically bottom right of game window)
# Calibrated using calibrate_inventory.py
INVENTORY_AREA = {
    # Keep this in sync with tools/debug_inventory.py (calibrated with option 1)
    "top": 430,
    "left": 1354,
    "width": 445,
    "height": 505
}

# Firemaking timing (in seconds)
# Time to wait for fire to be lit (varies by log type and level)
FIREMAKING_TIME = 3.0  # Default time for regular logs

# --- Main Bot Logic ---

def find_log_in_inventory():
    """
    Finds a log in the inventory using template matching.
    Scans the full inventory area to find any log.
    Returns (x, y) coordinates of the log, or None if not found.
    """
    # Use a lower threshold to catch logs that might be slightly different
    # (e.g., selected vs unselected, different lighting)
    # Try multiple thresholds, starting with the most permissive
    for threshold in [0.6, 0.7, 0.8]:
        log_pos = bot_utils.find_image(LOG_ICON_PATH, threshold=threshold, game_area=INVENTORY_AREA)
        if log_pos:
            return log_pos
    return None

def find_tinderbox_in_inventory():
    """
    Finds a tinderbox in the inventory using template matching.
    Scans the full inventory area to find the tinderbox.
    Returns (x, y) coordinates of the tinderbox, or None if not found.
    """
    if TINDERBOX_ICON_PATH is None or not os.path.exists(TINDERBOX_ICON_PATH):
        return None
    # Use a slightly lower threshold to catch tinderbox even if slightly different
    tinderbox_pos = bot_utils.find_image(TINDERBOX_ICON_PATH, threshold=0.7, game_area=INVENTORY_AREA)
    return tinderbox_pos

def check_has_tinderbox():
    """
    Checks if tinderbox exists in inventory.
    Returns True if tinderbox is found, False otherwise.
    """
    tinderbox_pos = find_tinderbox_in_inventory()
    return tinderbox_pos is not None

def light_fire():
    """
    Lights a fire by using tinderbox on a log in the inventory.
    Returns True if both log and tinderbox were found and fire was lit, False otherwise.
    """
    print("Looking for logs and tinderbox in inventory...")
    bot_utils.maybe_idle("pre_light_fire")
    
    # Check for tinderbox first (it never gets consumed)
    tinderbox_pos = find_tinderbox_in_inventory()
    if not tinderbox_pos:
        print("⚠ No tinderbox found in inventory!")
        print("   Make sure you have a tinderbox and that tinderbox_icon.png template exists.")
        return False
    
    # Find a log
    log_pos = find_log_in_inventory()
    if not log_pos:
        print("No logs found in inventory.")
        return False
    
    print(f"Tinderbox found at {tinderbox_pos}")
    print(f"Log found at {log_pos}. Lighting fire...")
    
    # Use tinderbox on log: right-click log, then click "Use" option, then click tinderbox
    # Or: use tinderbox on log directly
    # For simplicity, we'll use tinderbox on log (click tinderbox, then click log)
    bot_utils.human_like_move(tinderbox_pos[0], tinderbox_pos[1])
    bot_utils.jitter_sleep(random.uniform(0.1, 0.2))
    pyautogui.click()  # Click tinderbox
    bot_utils.jitter_sleep(random.uniform(0.1, 0.2))
    
    # Now click on the log
    bot_utils.human_like_move(log_pos[0], log_pos[1])
    bot_utils.jitter_sleep(random.uniform(0.1, 0.2))
    pyautogui.click()  # Use tinderbox on log
    
    return True

def wait_for_fire():
    """
    Waits for the fire to be lit.
    Uses a simple timer-based approach.
    """
    # Get firemaking time from player_stats if available
    if USE_PLAYER_CONFIG and player_stats:
        try:
            # Firemaking time varies by log type, but for now use a simple default
            wait_time = FIREMAKING_TIME
            print(f"Lighting fire... (waiting {wait_time:.1f} seconds)")
            bot_utils.jitter_sleep(wait_time)
            return
        except Exception as e:
            print(f"⚠ Warning: Could not get firemaking info: {e}")
            pass
    
    # Default wait time
    wait_time = FIREMAKING_TIME
    print(f"Lighting fire... (waiting {wait_time:.1f} seconds)")
    bot_utils.jitter_sleep(wait_time)

def check_inventory_has_logs():
    """
    Checks if there are any logs left in the inventory.
    Scans the full inventory area to count all logs.
    Returns True if logs are found, False otherwise.
    """
    # First, try the simpler find_image method (more reliable)
    # This finds any log in the inventory, which is all we need to know
    log_pos = find_log_in_inventory()
    if log_pos:
        # If find_image works, also try to count for better feedback
        count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=0.6)
        if count > 0:
            print(f"  Found {count} log(s) in inventory")
        else:
            print(f"  Found log at {log_pos}")
        return True
    
    # Fallback: try count_inventory_items with multiple thresholds
    # Use a slightly lower threshold to catch all logs in inventory
    # This ensures we see logs even if they're slightly different (selected, lighting, etc.)
    for threshold in [0.6, 0.7, 0.8, 0.5]:
        count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=threshold)
        if count > 0:
            print(f"  Found {count} log(s) in inventory (threshold: {threshold})")
            return True
    
    print(f"  No logs found in inventory (tried find_image and thresholds: 0.6, 0.7, 0.8, 0.5)")
    return False

def confirm_logs_and_relocate_if_blocked():
    """
    Double-checks for logs when we *think* we are empty.
    If logs are actually present, move the character to a new tile and continue.
    Returns True if logs were found and we moved, False if truly empty.
    """
    print("🔄 Re-checking inventory for logs before stopping...")
    # Aggressive re-check at low threshold
    if bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=0.5) > 0:
        print("  Logs detected on re-check. Moving to a new spot to light them.")
        move_character_away()
        return True
    print("  No logs found on re-check. Stopping.")
    return False

def move_character_away():
    """
    Moves the character away from current position to avoid walls/obstacles.
    Clicks on the ground in the game area to walk.
    """
    print("⚠ Character may be stuck near a wall. Moving away...")
    
    # Calculate a safe area to click (center-left of game area, away from inventory)
    # This should be a clear area where the character can walk
    walk_area = {
        "x": GAME_AREA["left"] + GAME_AREA["width"] * 0.3,  # Left side of screen
        "y": GAME_AREA["top"] + GAME_AREA["height"] * 0.5,  # Middle vertically
    }
    
    # Add some randomness to the walk position
    walk_x = int(walk_area["x"] + random.uniform(-50, 50))
    walk_y = int(walk_area["y"] + random.uniform(-50, 50))
    
    # Make sure we're still in the game area
    walk_x = max(GAME_AREA["left"] + 50, min(walk_x, GAME_AREA["left"] + GAME_AREA["width"] - 50))
    walk_y = max(GAME_AREA["top"] + 50, min(walk_y, GAME_AREA["top"] + GAME_AREA["height"] - 50))
    
    print(f"Walking to ({walk_x}, {walk_y}) to get away from wall...")
    
    # Click on the ground to walk
    bot_utils.human_like_move(walk_x, walk_y)
    bot_utils.jitter_sleep(random.uniform(0.1, 0.2))
    pyautogui.click()
    
    # Wait for character to move
    bot_utils.jitter_sleep(random.uniform(1.5, 2.5))
    
    print("✓ Character moved. Retrying firemaking...")

def main():
    """
    Main bot loop for firemaking.
    Lights fires until inventory is empty, then stops.
    """
    print("=" * 60)
    print("Stardust - Educational Firemaking Bot")
    print("=" * 60)
    print("\nWARNING: This bot is for educational purposes only.")
    print("Using bots on RuneScape may result in a permanent ban.")
    
    if DEBUG_MODE:
        print("\n" + "=" * 60)
        print("🔍 DEBUG MODE ENABLED")
        print("=" * 60)
        print("Debug images will be saved to the 'debug' folder.")
        print("=" * 60)
    
    # Display player configuration if available
    if USE_PLAYER_CONFIG:
        print(f"\nPlayer Configuration:")
        if player_stats:
            print(f"  Firemaking Level: {player_stats.FIREMAKING_LEVEL}")
        print(f"  Log Template: {LOG_ICON_PATH}")
    else:
        print("⚠ Warning: Player config not loaded. Using default settings.")
    
    print("\n⚠ IMPORTANT: This bot will stop when inventory is empty.")
    print("   Pathfinding to bank is not implemented yet.")
    print("   Make sure you have logs AND a tinderbox in your inventory before starting.")
    
    # Check for tinderbox template
    if TINDERBOX_ICON_PATH is None or not os.path.exists(TINDERBOX_ICON_PATH):
        print("\n" + "=" * 60)
        print("⚠ TINDERBOX TEMPLATE NOT FOUND")
        print("=" * 60)
        print(f"Template directory: {TINDERBOX_TEMPLATE_DIR}")
        print("\nPlease create a tinderbox template using:")
        print("  python tools/capture_template.py")
        print("\nSave it as one of these filenames:")
        print("  - tinderbox_icon.png (recommended)")
        print("  - log_tinderbox.png")
        print("  - tinderbox.png")
        print("\nThe template should be saved in the templates folder.")
        print("=" * 60)
        return
    
    print(f"✓ Using tinderbox template: {os.path.basename(TINDERBOX_ICON_PATH)}")
    
    print("\nStarting in 5 seconds... Switch to RuneScape window now.")
    print("Press Ctrl+C in this terminal to stop the bot.\n")
    print(bot_utils.describe_anti_detection())
    
    bot_utils.jitter_sleep(5)
    
    # Check for tinderbox at start
    if not check_has_tinderbox():
        print("\n" + "=" * 60)
        print("⚠ NO TINDERBOX FOUND IN INVENTORY")
        print("=" * 60)
        print("Please make sure you have a tinderbox in your inventory.")
        print("The bot requires both logs and a tinderbox to light fires.")
        print("=" * 60)
        return
    
    print("✓ Tinderbox found in inventory")
    
    fires_lit = 0
    consecutive_failures = 0  # Track consecutive failures when logs still exist
    max_failures_before_move = 3  # Move character after 3 consecutive failures
    
    try:
        while True:
            # Check if we still have tinderbox (should always be there, but check anyway)
            if not check_has_tinderbox():
                print("\n⚠ Tinderbox not found! Make sure it's still in your inventory.")
                bot_utils.jitter_sleep(2)
                continue
            
            # Check if we still have logs
            has_logs = check_inventory_has_logs()
            if not has_logs:
                # Before stopping, do a re-check and reposition if logs still exist
                if confirm_logs_and_relocate_if_blocked():
                    has_logs = True
                else:
                    print("\n" + "=" * 60)
                    print("No more logs in inventory!")
                    print("=" * 60)
                    print(f"Total fires lit: {fires_lit}")
                    print("\n⚠ Pathfinding to bank is not implemented yet.")
                    print("   The bot will now stop.")
                    print("   Please manually bank and restart the bot if needed.")
                    break
            
            # Light a fire
            if light_fire():
                wait_for_fire()
                fires_lit += 1
                consecutive_failures = 0  # Reset failure counter on success
                print(f"Fire #{fires_lit} lit successfully!")
                
                # Small random delay between fires
                bot_utils.maybe_idle("between_fires")
                bot_utils.jitter_sleep(random.uniform(0.5, 1.5))
            else:
                # Failed to light fire, but logs still exist - might be stuck
                consecutive_failures += 1
                print(f"Could not light fire. (Failure count: {consecutive_failures})")
                
                # If we've failed multiple times but logs still exist, we're probably stuck
                if consecutive_failures >= max_failures_before_move and has_logs:
                    print(f"\n⚠ Stuck detected! Failed {consecutive_failures} times but logs still exist.")
                    print("   Character may be too close to a wall or obstacle.")
                    move_character_away()
                    consecutive_failures = 0  # Reset counter after moving
                else:
                    print("Waiting before retry...")
                    bot_utils.jitter_sleep(random.uniform(2, 4))
            
    except KeyboardInterrupt:
        print("\n\nBot stopped by user.")
        print(f"Total fires lit: {fires_lit}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        print(f"\nTotal fires lit before error: {fires_lit}")

if __name__ == "__main__":
    main()

