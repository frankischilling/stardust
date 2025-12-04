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
# Note: Actual firemaking can take longer due to lag, server ticks, etc.
FIREMAKING_TIME = 3.5  # Increased from 3.0 to 3.5 seconds (more lenient for regular logs)

# --- Main Bot Logic ---

def get_log_count():
    """
    Gets the current count of logs in inventory using consistent method.
    Returns the number of logs found, or 0 if none found.
    Uses the same method everywhere for consistency.
    """
    # Use consistent method - try count_inventory_items with multiple thresholds
    # Use the highest count found (most accurate)
    max_count = 0
    counts_by_threshold = {}
    for threshold in [0.7, 0.8, 0.9, 0.6, 0.5]:
        count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=threshold)
        counts_by_threshold[threshold] = count
        if count > max_count:
            max_count = count
    
    # If counts are inconsistent, use the most common count (more reliable)
    if len(set(counts_by_threshold.values())) > 1:
        # Multiple different counts - use the most common one
        from collections import Counter
        count_freq = Counter(counts_by_threshold.values())
        most_common_count = count_freq.most_common(1)[0][0]
        if most_common_count != max_count:
            # Use most common if it's reasonable
            return most_common_count
    
    return max_count

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
    # Try multiple thresholds to catch tinderbox even if slightly different
    # (e.g., selected vs unselected, different lighting)
    for threshold in [0.7, 0.6, 0.8, 0.5]:
        tinderbox_pos = bot_utils.find_image(TINDERBOX_ICON_PATH, threshold=threshold, game_area=INVENTORY_AREA)
        if tinderbox_pos:
            return tinderbox_pos
    return None

def check_has_tinderbox():
    """
    Checks if tinderbox exists in inventory.
    Returns True if tinderbox is found, False otherwise.
    """
    tinderbox_pos = find_tinderbox_in_inventory()
    return tinderbox_pos is not None

# Global flag to track if a fire is currently being lit
_fire_in_progress = False
# Store the log position we clicked on for verification
_clicked_log_position = None

def light_fire():
    """
    Lights a fire by using tinderbox on a log in the inventory.
    Returns True if both log and tinderbox were found and fire was lit, False otherwise.
    CRITICAL: This function should only be called when no fire is in progress.
    """
    global _fire_in_progress, _clicked_log_position
    
    # Safety check: don't try to light another fire if one is already in progress
    if _fire_in_progress:
        print("⚠ Fire already in progress! Waiting for current fire to complete...")
        return False
    
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
    
    # Store the log position for verification in wait_for_fire()
    _clicked_log_position = log_pos
    
    # Mark that a fire is now in progress
    _fire_in_progress = True
    
    # Use tinderbox on log: right-click log, then click "Use" option, then click tinderbox
    # Or: use tinderbox on log directly
    # For simplicity, we'll use tinderbox on log (click tinderbox, then click log)
    bot_utils.human_like_move(tinderbox_pos[0], tinderbox_pos[1], profile="inventory")
    bot_utils.jitter_sleep(random.uniform(0.1, 0.2))
    pyautogui.click()  # Click tinderbox
    bot_utils.jitter_sleep(random.uniform(0.1, 0.2))
    
    # Now click on the log
    bot_utils.human_like_move(log_pos[0], log_pos[1], profile="inventory")
    bot_utils.jitter_sleep(random.uniform(0.1, 0.2))
    pyautogui.click()  # Use tinderbox on log
    
    return True

def wait_for_fire():
    """
    Waits for the fire to be lit and verifies it was successful.
    Returns True if fire was successfully lit (log was consumed), False otherwise.
    Polls inventory multiple times to ensure accurate detection.
    CRITICAL: This function blocks until fire is complete or timeout.
    Returns (success: bool, exhausted_all_checks: bool) tuple.
    exhausted_all_checks is True if we went through all max_checks without success.
    """
    global _fire_in_progress
    
    # Get initial count BEFORE clicking (more reliable baseline)
    # Wait a tiny bit to ensure inventory is stable
    bot_utils.jitter_sleep(0.1)
    initial_count = get_log_count()
    
    # If we got 0, try find_image as fallback
    if initial_count == 0:
        log_pos = find_log_in_inventory()
        if log_pos:
            # If we found a log but count is 0, estimate at least 1
            initial_count = 1
            print(f"  Initial log count: {initial_count} (estimated from find_image)")
        else:
            print(f"  ⚠ Warning: Initial log count is 0! No logs found in inventory.")
            _fire_in_progress = False
            return False, False  # Failed, but didn't exhaust checks (no logs to begin with)
    else:
        print(f"  Initial log count: {initial_count}")
    
    # Use the stored log position from light_fire() for verification
    global _clicked_log_position
    clicked_log_pos = _clicked_log_position
    
    # Get firemaking time from player_stats if available
    if USE_PLAYER_CONFIG and player_stats:
        try:
            # Firemaking time varies by log type, but for now use a simple default
            wait_time = FIREMAKING_TIME
            print(f"Lighting fire... (waiting {wait_time:.1f} seconds)")
            bot_utils.jitter_sleep(wait_time)
        except Exception as e:
            print(f"⚠ Warning: Could not get firemaking info: {e}")
            wait_time = FIREMAKING_TIME
            bot_utils.jitter_sleep(wait_time)
    else:
        # Default wait time
        wait_time = FIREMAKING_TIME
        print(f"Lighting fire... (waiting {wait_time:.1f} seconds)")
        bot_utils.jitter_sleep(wait_time)
    
    # Poll inventory multiple times to check if log was consumed
    # Firemaking can take longer than expected, especially with lag or slower connections
    # Be more patient - check many times with longer intervals
    max_checks = 12  # Increased from 5 to 12 (more patience)
    check_interval = 0.6  # Increased from 0.5 to 0.6 seconds (slightly longer between checks)
    total_max_wait = wait_time + (max_checks * check_interval)  # Total possible wait time
    
    print(f"  Polling inventory up to {max_checks} times ({total_max_wait:.1f}s total) to verify fire was lit...")
    
    for check_num in range(max_checks):
        # Wait a bit for inventory to update
        bot_utils.jitter_sleep(check_interval)
        
        # Use consistent counting method
        final_count = get_log_count()
        
        # Check if we can still find any log in inventory (alternative verification)
        any_log_exists = find_log_in_inventory() is not None
        
        # CRITICAL: Check if the specific log we clicked on is gone
        # This is more reliable than count detection
        clicked_log_gone = False
        if clicked_log_pos:
            # Check if we can still find a log at or near the clicked position
            # Use a small area around the clicked position (within 30 pixels)
            check_area = {
                "top": clicked_log_pos[1] - 30,
                "left": clicked_log_pos[0] - 30,
                "width": 60,
                "height": 60
            }
            # Make sure the area is within inventory bounds
            check_area["top"] = max(INVENTORY_AREA["top"], check_area["top"])
            check_area["left"] = max(INVENTORY_AREA["left"], check_area["left"])
            check_area["width"] = min(60, INVENTORY_AREA["left"] + INVENTORY_AREA["width"] - check_area["left"])
            check_area["height"] = min(60, INVENTORY_AREA["top"] + INVENTORY_AREA["height"] - check_area["top"])
            
            # Try to find a log in that specific area
            log_at_position = bot_utils.find_image(LOG_ICON_PATH, threshold=0.6, game_area=check_area)
            clicked_log_gone = (log_at_position is None)
        
        # If log count decreased, fire was successfully lit
        if final_count < initial_count:
            elapsed = wait_time + (check_num + 1) * check_interval
            print(f"  ✓ Fire lit successfully! Log consumed. (Inventory: {initial_count} -> {final_count}, took {elapsed:.1f}s)")
            _fire_in_progress = False  # Fire complete, reset flag
            return True, False  # Success, didn't exhaust checks
        
        # If the clicked log is gone, fire was likely lit (even if count is same)
        # This is a strong signal - the specific log we clicked on is consumed
        if clicked_log_gone and check_num >= 2:  # After at least 2 checks (1.2+ seconds)
            elapsed = wait_time + (check_num + 1) * check_interval
            print(f"  ✓ Fire lit successfully! Clicked log is gone. (took {elapsed:.1f}s)")
            print(f"     Note: Count detection showed {initial_count} -> {final_count}, but clicked log is consumed.")
            _fire_in_progress = False
            return True, False  # Success, didn't exhaust checks
        
        # Alternative check: if count is same but we've waited a while, check multiple times
        # Sometimes count detection is inconsistent, so verify with multiple checks
        if check_num >= 3:  # After waiting a bit (3+ checks = 1.8+ seconds)
            # Do 3 quick checks to see if count is consistently lower
            quick_counts = []
            for _ in range(3):
                bot_utils.jitter_sleep(0.2)
                quick_count = get_log_count()
                quick_counts.append(quick_count)
            
            # If any of the quick checks shows a lower count, fire was lit
            min_quick_count = min(quick_counts)
            if min_quick_count < initial_count:
                elapsed = wait_time + (check_num + 1) * check_interval
                print(f"  ✓ Fire lit successfully! Log consumed. (Inventory: {initial_count} -> {min_quick_count}, took {elapsed:.1f}s)")
                print(f"     Detected via multiple verification checks: {quick_counts}")
                _fire_in_progress = False
                return True, False  # Success, didn't exhaust checks
        
        # Only log status every 3 checks to reduce spam (but still check every time)
        if (check_num + 1) % 3 == 0 or check_num >= 6:
            elapsed = wait_time + (check_num + 1) * check_interval
            status_msg = f"  ⚠ Still waiting for fire... (check {check_num+1}/{max_checks}, count: {final_count}, elapsed: {elapsed:.1f}s)"
            if clicked_log_pos:
                status_msg += f", clicked log gone: {clicked_log_gone}"
            print(status_msg)
    
    # Final check after all polling - do multiple verification checks
    # Sometimes count detection is inconsistent, so verify with multiple rapid checks
    verification_counts = []
    for _ in range(5):  # 5 quick checks
        bot_utils.jitter_sleep(0.15)
        count = get_log_count()
        verification_counts.append(count)
    
    # Use the minimum count from all verification checks (most reliable)
    final_count = min(verification_counts)
    total_elapsed = wait_time + (max_checks * check_interval)
    
    # Final check: Is the clicked log gone?
    clicked_log_gone_final = False
    if clicked_log_pos:
        check_area = {
            "top": clicked_log_pos[1] - 30,
            "left": clicked_log_pos[0] - 30,
            "width": 60,
            "height": 60
        }
        check_area["top"] = max(INVENTORY_AREA["top"], check_area["top"])
        check_area["left"] = max(INVENTORY_AREA["left"], check_area["left"])
        check_area["width"] = min(60, INVENTORY_AREA["left"] + INVENTORY_AREA["width"] - check_area["left"])
        check_area["height"] = min(60, INVENTORY_AREA["top"] + INVENTORY_AREA["height"] - check_area["top"])
        log_at_position = bot_utils.find_image(LOG_ICON_PATH, threshold=0.6, game_area=check_area)
        clicked_log_gone_final = (log_at_position is None)
    
    if final_count < initial_count:
        print(f"  ✓ Fire lit successfully! Log consumed. (Inventory: {initial_count} -> {final_count}, took {total_elapsed:.1f}s)")
        print(f"     Verified with multiple checks: {verification_counts}")
        _fire_in_progress = False  # Fire complete, reset flag
        return True, False  # Success, didn't exhaust checks
    elif clicked_log_gone_final:
        # The clicked log is gone - fire was definitely lit
        print(f"  ✓ Fire lit successfully! Clicked log is gone after {total_elapsed:.1f}s")
        print(f"     Note: Count detection showed {initial_count} -> {final_count}, but clicked log is consumed.")
        print(f"     Verification counts: {verification_counts}")
        _fire_in_progress = False
        return True, False  # Success, didn't exhaust checks
    else:
        # Even if count is same, check if we can still find logs
        # If we had logs before and can't find any now, fire might have been lit
        any_log_exists = find_log_in_inventory() is not None
        if initial_count > 0 and not any_log_exists:
            # We had logs, waited a long time, and now can't find any
            # This suggests fire was lit even if count detection failed
            print(f"  ✓ Fire lit successfully! (No logs found after {total_elapsed:.1f}s)")
            print(f"     Note: Count detection showed {initial_count} -> {final_count}, but logs are gone.")
            _fire_in_progress = False
            return True, False  # Success, didn't exhaust checks
        
        print(f"  ⚠ Fire may not have been lit after {total_elapsed:.1f}s. Log count unchanged: {initial_count} -> {final_count}")
        print(f"     Verification counts: {verification_counts}")
        if clicked_log_pos:
            print(f"     Clicked log still exists: {not clicked_log_gone_final}")
        print(f"     Character may be stuck or unable to place fire at this location.")
        _fire_in_progress = False  # Reset flag even on failure (so we can retry)
        return False, True  # Failed AND exhausted all checks - strong signal we're stuck

def check_inventory_has_logs():
    """
    Checks if there are any logs left in the inventory.
    Uses consistent counting method.
    Returns True if logs are found, False otherwise.
    """
    # Use consistent counting method
    count = get_log_count()
    
    if count > 0:
        print(f"  Found {count} log(s) in inventory")
        return True
    else:
        # Fallback: try find_image to see if we can find at least one log
        log_pos = find_log_in_inventory()
        if log_pos:
            print(f"  Found log at {log_pos} (count method returned 0, but log exists)")
            return True
        
        print(f"  No logs found in inventory")
        return False

def confirm_logs_and_relocate_if_blocked():
    """
    Double-checks for logs when we *think* we are empty.
    If logs are actually present, move the character to a new tile and continue.
    Returns True if logs were found and we moved, False if truly empty.
    """
    print("🔄 Re-checking inventory for logs before stopping...")
    # Use consistent counting method
    count = get_log_count()
    if count > 0:
        print(f"  Logs detected on re-check ({count} logs). Moving to a new spot to light them.")
        move_character_away()
        return True
    print("  No logs found on re-check. Stopping.")
    return False

def move_character_away():
    """
    Moves the character away from current position to avoid walls/obstacles/fires.
    Clicks on the ground in the game area to walk to a location where fire can be placed.
    Tries multiple positions to find a clear spot, moving further away each time.
    """
    print("⚠ Character may be stuck. Moving to a new location where fire can be placed...")
    
    # Define multiple distinct areas to try, spread across the game area
    # These are far apart to avoid moving to another fire location
    walk_areas = [
        # Area 1: Far left-center (away from inventory)
        {
            "x": GAME_AREA["left"] + GAME_AREA["width"] * 0.25,
            "y": GAME_AREA["top"] + GAME_AREA["height"] * 0.5,
        },
        # Area 2: Upper-left (different quadrant)
        {
            "x": GAME_AREA["left"] + GAME_AREA["width"] * 0.3,
            "y": GAME_AREA["top"] + GAME_AREA["height"] * 0.4,
        },
        # Area 3: Lower-left (different quadrant)
        {
            "x": GAME_AREA["left"] + GAME_AREA["width"] * 0.3,
            "y": GAME_AREA["top"] + GAME_AREA["height"] * 0.7,
        },
        # Area 4: Center-left (middle area)
        {
            "x": GAME_AREA["left"] + GAME_AREA["width"] * 0.35,
            "y": GAME_AREA["top"] + GAME_AREA["height"] * 0.55,
        },
        # Area 5: Upper-center (different area)
        {
            "x": GAME_AREA["left"] + GAME_AREA["width"] * 0.4,
            "y": GAME_AREA["top"] + GAME_AREA["height"] * 0.45,
        },
        # Area 6: Lower-center (different area)
        {
            "x": GAME_AREA["left"] + GAME_AREA["width"] * 0.4,
            "y": GAME_AREA["top"] + GAME_AREA["height"] * 0.65,
        },
    ]
    
    # Shuffle the list to try different areas each time
    random.shuffle(walk_areas)
    
    # Try up to 3 different positions
    max_attempts = 3
    for attempt in range(max_attempts):
        # Pick a position from the shuffled list
        walk_area = walk_areas[attempt % len(walk_areas)]
        
        # Add significant randomness to avoid moving to the same spot
        # Use larger random offsets to move further away
        walk_x = int(walk_area["x"] + random.uniform(-150, 150))
        walk_y = int(walk_area["y"] + random.uniform(-120, 120))
        
        # Make sure we're still in the game area and away from edges/inventory
        walk_x = max(GAME_AREA["left"] + 120, min(walk_x, GAME_AREA["left"] + GAME_AREA["width"] * 0.55))
        walk_y = max(GAME_AREA["top"] + 120, min(walk_y, GAME_AREA["top"] + GAME_AREA["height"] - 120))
        
        print(f"Attempt {attempt + 1}/{max_attempts}: Walking to ({walk_x}, {walk_y}) to find a clear spot...")
        
        # CRITICAL: Click on the ground to walk (not in inventory area)
        # Make sure we're clicking in the game world, not on UI
        bot_utils.human_like_move(walk_x, walk_y, profile="skilling")
        bot_utils.jitter_sleep(random.uniform(0.15, 0.25))
        
        # Left-click to walk (not right-click)
        pyautogui.click(button='left')
        
        # Wait longer for character to actually move
        print("  Waiting for character to move...")
        bot_utils.jitter_sleep(random.uniform(2.5, 4.0))
        
        # Additional small delay to ensure character has stopped moving
        bot_utils.jitter_sleep(random.uniform(0.5, 1.0))
        
        # After moving, wait a bit longer to ensure we're in a new area
        # This gives time for any fires to be visible if we moved near them
        if attempt < max_attempts - 1:
            print("  Checking if location is clear...")
            bot_utils.jitter_sleep(random.uniform(0.5, 1.0))
        
        print("✓ Character moved to new location.")
    
    print("✓ Finished moving. Retrying firemaking...")


def maybe_small_reposition_after_fire(fires_lit):
    """
    Occasionally click a small walk target near the player between fires
    to simulate repositioning or adjusting the line of fires.
    Frequency increases slightly as more fires are lit.
    """
    # Base small chance, scaled up very slightly after many fires.
    base_chance = 0.04
    bonus = min(0.06, fires_lit * 0.001)  # +0.1 at 100 fires max
    chance = base_chance + bonus
    if random.random() > chance:
        return

    walk_x = GAME_AREA["left"] + int(GAME_AREA["width"] * random.uniform(0.35, 0.55))
    walk_y = GAME_AREA["top"] + int(GAME_AREA["height"] * random.uniform(0.55, 0.75))
    print(f"(Firemaking wander) Walking briefly to ({walk_x}, {walk_y}) between fires...")
    bot_utils.human_like_move(walk_x, walk_y, profile="skilling")
    bot_utils.jitter_sleep(random.uniform(0.08, 0.2))
    pyautogui.click()
    bot_utils.jitter_sleep(random.uniform(0.9, 1.8))

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
            
            # Light a fire (only if no fire is currently in progress)
            # The _fire_in_progress flag prevents double-lighting
            if not _fire_in_progress and light_fire():
                # Wait for fire and check if it was actually successful
                fire_success, exhausted_all_checks = wait_for_fire()
                
                if fire_success:
                    # Fire was successfully lit (log was consumed)
                    fires_lit += 1
                    consecutive_failures = 0  # Reset failure counter on success
                    print(f"Fire #{fires_lit} lit successfully!")
                    
                    # CRITICAL: Wait longer after successful fire to ensure inventory is fully updated
                    # This prevents the bot from trying to light another fire too quickly
                    # and accidentally clicking/dropping logs
                    bot_utils.jitter_sleep(random.uniform(1.0, 2.0))
                    
                    # Small random delay between fires, plus occasional longer
                    # "thinking" pauses after many fires.
                    maybe_small_reposition_after_fire(fires_lit)

                    if fires_lit > 20 and random.random() < 0.15:
                        long_pause = random.uniform(4.0, 9.0)
                        print(f"Taking a longer pause after many fires... ({long_pause:.1f} seconds)")
                        bot_utils.jitter_sleep(long_pause)
                    else:
                        bot_utils.maybe_idle("between_fires")
                        bot_utils.jitter_sleep(random.uniform(0.5, 1.5))
                else:
                    # light_fire() succeeded (clicked items) but fire wasn't actually lit
                    # This means we're stuck - can't place fire at current location
                    consecutive_failures += 1
                    print(f"⚠ Fire attempt failed - log not consumed. (Failure count: {consecutive_failures})")
                    print("   Character may be stuck or unable to place fire at this location.")
                    
                    # If we exhausted all checks (went through all 12), that's a strong signal we're stuck
                    # Move immediately rather than waiting for 3 failures
                    if exhausted_all_checks and has_logs:
                        print(f"\n⚠ Stuck detected! Went through all verification checks but fire wasn't lit.")
                        print("   Moving to a new location immediately...")
                        move_character_away()
                        consecutive_failures = 0  # Reset counter after moving
                        # Wait a bit longer after moving before retrying
                        bot_utils.jitter_sleep(random.uniform(1.0, 2.0))
                    # Otherwise, if we've failed multiple times but logs still exist, we might be stuck
                    elif consecutive_failures >= max_failures_before_move and has_logs:
                        print(f"\n⚠ Possible stuck detected! Failed {consecutive_failures} times but logs still exist.")
                        print("   This might be due to lag or slow firemaking. Moving to a new location...")
                        move_character_away()
                        consecutive_failures = 0  # Reset counter after moving
                        # Wait a bit longer after moving before retrying
                        bot_utils.jitter_sleep(random.uniform(1.0, 2.0))
                    else:
                        print("Waiting before retry...")
                        bot_utils.jitter_sleep(random.uniform(1, 2))
            else:
                # Failed to find/click tinderbox or log in inventory
                consecutive_failures += 1
                print(f"Could not find tinderbox/log in inventory. (Failure count: {consecutive_failures})")
                
                # If we've failed multiple times but logs still exist, we might be stuck
                if consecutive_failures >= max_failures_before_move and has_logs:
                    print(f"\n⚠ Stuck detected! Failed {consecutive_failures} times but logs still exist.")
                    print("   Moving to a new location...")
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

