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
# Path to an empty inventory slot template (full empty slot image)
EMPTY_SLOT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "empty_slot.png")

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
    "height": 560  # Match woodcutter to capture bottom row fully
}

# Chat area (for detecting error messages)
# Calibrated using calibrate_chat.py
CHAT_AREA = {
    "top": 717,
    "left": 13,
    "width": 1209,
    "height": 228
}

# Path to the "can't fire" chat message template
# This is the chat message that appears when you can't light a fire
CANT_FIRE_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "cant_fire.png")

# Firemaking timing (in seconds)
# Time to wait for fire to be lit (varies by log type and level)
# Note: Actual firemaking can take longer due to lag, server ticks, etc.
FIREMAKING_TIME = 3.5  # Increased from 3.0 to 3.5 seconds (more lenient for regular logs)

# --- Main Bot Logic ---

def get_log_count():
    """
    Gets the current count of logs in inventory using the same logic as woodcutter.py.
    Uses empty slot templates and per-slot analysis for more accurate counting.
    Returns the number of logs found, or 0 if none found.
    Optimized to capture inventory only ONCE to reduce delays.
    """
    import cv2
    import mss
    import numpy as np
    
    # Single capture delay at the start (only once)
    bot_utils._maybe_capture_delay()
    
    # Calculate slot dimensions (4 columns, 7 rows = 28 slots)
    slot_width = INVENTORY_AREA["width"] // 4
    slot_height = INVENTORY_AREA["height"] // 7
    
    # Capture the inventory area ONCE for all detection
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(INVENTORY_AREA))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Load log template once
    log_template = cv2.imread(LOG_ICON_PATH, cv2.IMREAD_COLOR)
    if log_template is None:
        return 0
    
    # Convert template if needed
    if len(log_template.shape) == 3:
        channels = log_template.shape[2]
        if channels == 4:
            log_template = cv2.cvtColor(log_template, cv2.COLOR_BGRA2BGR)
        elif channels == 1:
            log_template = cv2.cvtColor(log_template, cv2.COLOR_GRAY2BGR)
    elif len(log_template.shape) == 2:
        log_template = cv2.cvtColor(log_template, cv2.COLOR_GRAY2BGR)
    
    # Count logs using multiple thresholds on the SAME capture (no additional delays)
    log_counts = []
    max_log_slots_found = 0
    occupied_slots = 0  # Initialize occupied_slots
    
    # Helper function to count matches on already-captured image
    def count_matches_on_image(template, threshold):
        result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        matches = list(zip(*locations[::-1]))
        if not matches:
            return 0
        
        # Group nearby matches (same logic as bot_utils.count_inventory_items)
        template_h, template_w = template.shape[:2]
        grouping_distance = min(40, max(30, template_w * 0.6))
        matches.sort(key=lambda m: (m[1], m[0]))
        
        grouped_matches = []
        for match in matches:
            x, y = match
            added = False
            for i, group in enumerate(grouped_matches):
                group_x, group_y = group
                distance = np.sqrt((x - group_x)**2 + (y - group_y)**2)
                if distance < grouping_distance:
                    added = True
                    break
            if not added:
                grouped_matches.append(match)
        
        return len(grouped_matches)
    
    # Count logs using multiple thresholds on the same capture
    for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]:
        count = count_matches_on_image(log_template, threshold)
        log_counts.append(count)
        if count > max_log_slots_found:
            max_log_slots_found = count
    if log_counts:
        # Median is less sensitive to occasional duplicate matches than max
        log_counts_sorted = sorted(log_counts)
        median_idx = len(log_counts_sorted) // 2
        median_log_count = log_counts_sorted[median_idx]
        max_log_slots_found = median_log_count
    
    # Count occupied slots using per-slot color analysis (for non-log items)
    for row in range(7):
        for col in range(4):
            # Calculate the slot area (relative to captured image)
            slot_left = col * slot_width
            slot_top = row * slot_height
            slot_right = min(slot_left + slot_width, INVENTORY_AREA["width"])
            slot_bottom = min(slot_top + slot_height, INVENTORY_AREA["height"])
            
            # Extract slot region from captured image
            slot_region = screen_bgr[slot_top:slot_bottom, slot_left:slot_right]
            
            if slot_region.size == 0:
                continue
            
            # Check if slot is occupied (has an item) using color analysis
            slot_hsv = cv2.cvtColor(slot_region, cv2.COLOR_BGR2HSV)
            mean_saturation = np.mean(slot_hsv[:, :, 1])
            mean_value = np.mean(slot_hsv[:, :, 2])
            std_value = np.std(slot_hsv[:, :, 2])
            std_saturation = np.std(slot_hsv[:, :, 1])
            bright_frac = np.mean(slot_hsv[:, :, 2] > 110)
            colorful_frac = np.mean(slot_hsv[:, :, 1] > 60)
            
            # Moderately strict to reduce overcounts while still catching filled slots
            is_occupied = (
                ((bright_frac > 0.10 and colorful_frac > 0.08) and (std_value > 12 or std_saturation > 7)) or
                ((mean_saturation > 50 and mean_value > 115) and (std_saturation > 9 and std_value > 16)) or
                (mean_value > 165 and std_value > 22)
            )
            
            if is_occupied:
                occupied_slots += 1
    
    # Ensure occupied is at least as high as log count (logs are occupied slots)
    occupied_slots = max(occupied_slots, max_log_slots_found)

    # Empty slot detection using template - PRIMARY method when available
    empty_slots = None
    empty_slot_count = 0
    # Check if empty slot template exists - try multiple path resolutions
    empty_slot_available = os.path.exists(EMPTY_SLOT_PATH)
    temp_empty_path = EMPTY_SLOT_PATH
    
    if not empty_slot_available:
        # Try relative path from current working directory
        rel_path = os.path.join("templates", "empty_slot.png")
        if os.path.exists(rel_path):
            empty_slot_available = True
            temp_empty_path = rel_path
        else:
            # Try absolute path resolution
            abs_path = os.path.abspath(EMPTY_SLOT_PATH)
            if os.path.exists(abs_path):
                empty_slot_available = True
                temp_empty_path = abs_path
    
    if empty_slot_available:
        try:
            # Load empty slot template once
            empty_template = cv2.imread(temp_empty_path, cv2.IMREAD_COLOR)
            if empty_template is not None:
                # Convert template if needed
                if len(empty_template.shape) == 3:
                    channels = empty_template.shape[2]
                    if channels == 4:
                        empty_template = cv2.cvtColor(empty_template, cv2.COLOR_BGRA2BGR)
                    elif channels == 1:
                        empty_template = cv2.cvtColor(empty_template, cv2.COLOR_GRAY2BGR)
                elif len(empty_template.shape) == 2:
                    empty_template = cv2.cvtColor(empty_template, cv2.COLOR_GRAY2BGR)
                
                # Try a wider range of thresholds to catch empty slots (on same capture)
                for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]:
                    count = count_matches_on_image(empty_template, threshold)
                    if count > empty_slot_count:
                        empty_slot_count = count
                # Treat 0 empty slots as a valid detection (means full)
                empty_slots = empty_slot_count
                # Calculate occupied from empty slots (most reliable)
                occupied_from_empty = max(0, 28 - empty_slots)
                occupied_slots = occupied_from_empty
                # Recalculate log count more carefully when we have empty slot data (on same capture)
                refined_log_count = 0
                for threshold in [0.65, 0.7, 0.75, 0.8]:
                    count = count_matches_on_image(log_template, threshold)
                    if count > refined_log_count:
                        refined_log_count = count
                # Use the refined count, capped to occupied slots (can't have more logs than occupied slots)
                max_log_slots_found = min(refined_log_count, occupied_slots)
            else:
                empty_slots = None
        except Exception as e:
            # Silent fallback - don't spam errors if empty slot template fails
            empty_slots = None
    
    # Global log count fallback ONLY if empty slot template not available
    if empty_slots is None:
        try:
            # Use already-captured image for additional threshold checks
            global_log_count = 0
            for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.45, 0.4, 0.35, 0.75, 0.8, 0.9]:
                count = count_matches_on_image(log_template, threshold)
                if count > global_log_count:
                    global_log_count = count
            # Use global count as fallback but don't inflate beyond per-slot count
            max_log_slots_found = max(max_log_slots_found, min(global_log_count, 28))
            # Only update occupied if we don't have empty slot data
            occupied_slots = max(occupied_slots, max_log_slots_found)
        except Exception:
            pass
    else:
        # When we have empty slot data, ensure log count doesn't exceed occupied
        max_log_slots_found = min(max_log_slots_found, occupied_slots)
    
    # Return the log count (not checking for full inventory, just counting logs)
    return max_log_slots_found

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

def check_cant_fire_message():
    """
    Checks if the "can't light fire here" message appears in chat.
    Returns True if the message is detected, False otherwise.
    Checks multiple times over a period to catch the message even if it appears with delay.
    """
    import cv2
    import numpy as np
    import mss
    
    if not os.path.exists(CANT_FIRE_TEMPLATE_PATH):
        # Template doesn't exist yet, can't check
        return False
    
    # Preload template (handle RGBA/grayscale) for multi-scale matching
    tpl = cv2.imread(CANT_FIRE_TEMPLATE_PATH, cv2.IMREAD_UNCHANGED)
    if tpl is None:
        return False
    if len(tpl.shape) == 2:  # grayscale
        tpl = cv2.cvtColor(tpl, cv2.COLOR_GRAY2BGR)
    elif tpl.shape[2] == 4:  # RGBA
        tpl = cv2.cvtColor(tpl, cv2.COLOR_BGRA2BGR)
    tpl_h, tpl_w = tpl.shape[:2]
    
    # Check multiple times - chat messages can appear with slight delays
    # Check at these intervals (cumulative delays from start)
    check_delays = [0.2, 0.5, 0.8, 1.2]  # Check at these intervals (seconds)
    last_delay = 0
    
    best_match = (0.0, 1.0)  # (score, scale)
    for check_delay in check_delays:
        # Wait for the difference between this check and the last one
        wait_time = check_delay - last_delay
        bot_utils.jitter_sleep(wait_time)
        last_delay = check_delay
        
        # Capture chat area once per delay (only the bottom portion where recent messages appear)
        with mss.mss() as sct:
            chat_img = np.array(sct.grab(CHAT_AREA))
            chat_bgr_full = cv2.cvtColor(chat_img, cv2.COLOR_BGRA2BGR)
            h_full = chat_bgr_full.shape[0]
            # Focus on bottom 40% to emphasize most recent messages
            start_y = int(h_full * 0.6)
            chat_bgr = chat_bgr_full[start_y:, :]
        
        # Multi-scale, multi-threshold matching to catch font/size differences
        for scale in [1.0, 0.95, 1.05, 0.9]:
            if scale != 1.0:
                scaled_tpl = cv2.resize(tpl, (max(1, int(tpl_w * scale)), max(1, int(tpl_h * scale))), interpolation=cv2.INTER_AREA)
            else:
                scaled_tpl = tpl
            res = cv2.matchTemplate(chat_bgr, scaled_tpl, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if max_val > best_match[0]:
                best_match = (max_val, scale)
    
    # Accept only strong matches to avoid false positives
    if best_match[0] >= 0.75:
        print(f"⚠ Detected 'can't light fire here' message in chat! (best score {best_match[0]:.2f}, scale {best_match[1]:.2f})")
        return True
    return False

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
    
    # Don't check for chat messages here - that's handled in the main loop
    # This function just attempts to light the fire
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
        
        # Don't check chat messages here - chat checking only happens in main loop before moving
        
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
        if check_cant_fire_message():
            print("⚠ Chat says we can't light a fire here (detected during final verification). Moving to a new spot...")
            _fire_in_progress = False
            move_character_away()
            return False, True
    
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
    After each move, attempts to light a fire. Returns True if fire was successfully lit.
    """
    global _fire_in_progress
    
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
    
    # Get initial log count before moving
    initial_log_count = get_log_count()
    
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
        
        # CRITICAL: Make sure we don't click in the chat area
        chat_right = CHAT_AREA["left"] + CHAT_AREA["width"]
        chat_bottom = CHAT_AREA["top"] + CHAT_AREA["height"]
        
        # If the click would be in the chat area, move it above the chat
        if (CHAT_AREA["left"] <= walk_x <= chat_right and 
            CHAT_AREA["top"] <= walk_y <= chat_bottom):
            # Move the y coordinate above the chat area
            walk_y = CHAT_AREA["top"] - random.randint(50, 150)
            # Make sure it's still in valid game area
            walk_y = max(GAME_AREA["top"] + 120, walk_y)
            print(f"  Adjusted walk position to avoid chat area: ({walk_x}, {walk_y})")
        
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
        
        print("✓ Character moved to new location.")
        
        # After moving, wait a moment for any old chat messages to clear
        # Also give the game time to update after movement
        bot_utils.jitter_sleep(random.uniform(1.0, 1.5))
        
        # After moving, try to light a fire to see if this location works
        # After moving, we ONLY use log count to determine success (not chat messages)
        # This avoids detecting old error messages from the previous location
        print("  Testing if we can light a fire at this location...")
        
        # Get log count before attempting to light fire
        log_count_before = get_log_count()
        
        if light_fire():
            # Wait for fire to start and inventory to update
            # Don't check chat messages after moving - only use log count
            bot_utils.jitter_sleep(random.uniform(1.5, 2.0))
            
            # Check if log count decreased - this is the ONLY indicator we use after moving
            # Wait a moment for inventory to update
            bot_utils.jitter_sleep(random.uniform(0.5, 0.8))
            log_count_after = get_log_count()
            
            # If log count decreased, fire was successfully lit!
            if log_count_after < log_count_before:
                print(f"  ✓ Success! Fire lit successfully at new location. (Logs: {log_count_before} -> {log_count_after})")
                # Wait for fire to complete fully
                fire_success, exhausted_all_checks = wait_for_fire()
                if fire_success:
                    return True  # Found a good spot, return success
                else:
                    # Log count decreased but wait_for_fire didn't confirm - still consider it success
                    print(f"  ✓ Fire confirmed by log count decrease. (Logs: {log_count_before} -> {log_count_after})")
                    return True
            
            # Log count didn't decrease - fire didn't light, try next spot
            print(f"  ⚠ Fire didn't light at this location. (Logs: {log_count_before} -> {log_count_after}, unchanged)")
            # Reset fire in progress flag since we're moving again
            _fire_in_progress = False
            continue
        else:
            # Couldn't find logs/tinderbox
            # Reset flag if it was set
            _fire_in_progress = False
            print("  ⚠ Could not find logs/tinderbox. Trying next spot...")
            continue
    
    print("✓ Finished moving. Could not find a clear spot after all attempts.")
    return False  # Couldn't find a good spot


def adjust_camera():
    """
    Randomly adjusts the camera to simulate human-like behavior.
    Players often rotate the camera to check surroundings or adjust their view.
    Uses arrow keys to rotate camera left or right.
    """
    # Randomly choose left or right rotation
    direction = random.choice(['left', 'right'])
    
    # Determine which arrow key to press
    if direction == 'left':
        key = 'left'
    else:
        key = 'right'
    
    print(f"🔄 Adjusting camera {direction}...")
    
    # Small delay before pressing key (ensure window is focused)
    bot_utils.jitter_sleep(random.uniform(0.1, 0.2))
    
    # Press and hold the arrow key for a random duration (human-like)
    # RuneScape camera rotates while key is held
    hold_duration = random.uniform(0.3, 0.8)  # Hold for 0.3-0.8 seconds
    
    try:
        pyautogui.keyDown(key)
        time.sleep(hold_duration)  # Use time.sleep for more reliable key holding
        pyautogui.keyUp(key)
        if bot_utils.ANTI_DETECTION_ENABLED:
            bot_utils._log_anti(f"camera {direction} {hold_duration:.2f}s")
        print(f"  ✓ Camera adjusted {direction} (held for {hold_duration:.2f}s)")
    except Exception as e:
        # Try alternative method - press key multiple times
        try:
            for _ in range(2):
                pyautogui.press(key)
                time.sleep(0.1)
            print(f"  ✓ Camera adjusted {direction} (alternative method)")
        except Exception as e2:
            print(f"  ⚠ Failed to adjust camera: {e2}")
    
    # Small delay after camera movement to let view settle
    bot_utils.jitter_sleep(random.uniform(0.2, 0.4))

def maybe_small_reposition_after_fire(fires_lit):
    """
    Occasionally click a small walk target near the player between fires
    to simulate repositioning or adjusting the line of fires.
    Frequency increases slightly as more fires are lit.
    Also occasionally adjusts camera to check surroundings.
    """
    # Base small chance, scaled up very slightly after many fires.
    base_chance = 0.04
    bonus = min(0.06, fires_lit * 0.001)  # +0.1 at 100 fires max
    chance = base_chance + bonus
    if random.random() < chance:
        walk_x = GAME_AREA["left"] + int(GAME_AREA["width"] * random.uniform(0.35, 0.55))
        walk_y = GAME_AREA["top"] + int(GAME_AREA["height"] * random.uniform(0.55, 0.75))
        print(f"(Firemaking wander) Walking briefly to ({walk_x}, {walk_y}) between fires...")
        bot_utils.human_like_move(walk_x, walk_y, profile="skilling")
        bot_utils.jitter_sleep(random.uniform(0.08, 0.2))
        pyautogui.click()
        bot_utils.jitter_sleep(random.uniform(0.9, 1.8))
    
    # Occasionally adjust camera to "check surroundings"
    # Higher chance after many fires (players get restless)
    camera_chance = 0.25 + min(0.15, fires_lit * 0.001)  # 25% base, up to 40% after many fires
    if random.random() < camera_chance:
        adjust_camera()

def main():
    """
    Main bot loop for firemaking.
    Lights fires until inventory is empty, then stops.
    """
    global _fire_in_progress
    
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
    
    # Check for cant_fire template
    if not os.path.exists(CANT_FIRE_TEMPLATE_PATH):
        print("\n" + "=" * 60)
        print("⚠ CANT_FIRE TEMPLATE NOT FOUND")
        print("=" * 60)
        print(f"Template path: {CANT_FIRE_TEMPLATE_PATH}")
        print("\nThe bot can detect when it can't light a fire, but you need to:")
        print("1. Try to light a fire in an invalid location (e.g., too close to another fire)")
        print("2. Capture the chat message that appears using:")
        print("   python tools/capture_template.py")
        print("3. Save it as: cant_fire.png in the templates folder")
        print("4. Calibrate the chat area using:")
        print("   python tools/calibrate_chat.py")
        print("\nThe bot will still work without this, but won't detect 'can't fire' errors.")
        print("=" * 60)
    else:
        print(f"✓ Using cant_fire template: {os.path.basename(CANT_FIRE_TEMPLATE_PATH)}")
    
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
        fires_since_last_camera = 0  # Track fires since last camera adjustment
        
        while True:
            # Occasionally adjust camera at the start of loop (simulate checking surroundings)
            # Increase chance based on fires since last adjustment
            base_chance = 0.20  # 20% base chance
            bonus_chance = min(0.25, fires_since_last_camera * 0.03)  # +3% per fire, max 25%
            if random.random() < (base_chance + bonus_chance):
                adjust_camera()
                fires_since_last_camera = 0  # Reset counter
            else:
                fires_since_last_camera += 1
            
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
            if not _fire_in_progress:
                fire_attempt = light_fire()
                
                # If light_fire() returned False (couldn't find items), skip
                if not fire_attempt:
                    consecutive_failures += 1
                    print(f"Could not find tinderbox/log in inventory. (Failure count: {consecutive_failures})")
                    if consecutive_failures >= max_failures_before_move and has_logs:
                        print(f"\n⚠ Stuck detected! Failed {consecutive_failures} times but logs still exist.")
                        print("   Moving to a new location...")
                        move_character_away()
                        consecutive_failures = 0
                    else:
                        bot_utils.jitter_sleep(random.uniform(2, 4))
                    continue
                
                # After attempting to light fire, check for "can't fire" message
                # This check only happens in the main loop (before moving), not after moving
                bot_utils.jitter_sleep(random.uniform(0.5, 0.8))  # Wait for message to appear
                if check_cant_fire_message():
                    print("⚠ Detected 'can't light fire here' message. Moving to a new spot...")
                    _fire_in_progress = False  # Reset flag before moving
                    # move_character_away() will try to light a fire after each move
                    # Returns True if fire was successfully lit, False if all attempts failed
                    fire_success_after_move = move_character_away()
                    if fire_success_after_move:
                        # Fire was successfully lit at the new location
                        fires_lit += 1
                        consecutive_failures = 0  # Reset counter after success
                        print(f"Fire #{fires_lit} lit successfully after moving!")
                        
                        # Minimal delay after successful fire
                        bot_utils.jitter_sleep(random.uniform(0.2, 0.4))
                        maybe_small_reposition_after_fire(fires_lit)
                        
                        # Adjust camera after moving (check new surroundings)
                        if random.random() < 0.25:  # 25% chance after moving
                            adjust_camera()
                            fires_since_last_camera = 0
                        else:
                            fires_since_last_camera += 1
                        
                        if fires_lit > 20 and random.random() < 0.05:
                            long_pause = random.uniform(2.0, 4.0)
                            print(f"Taking a longer pause after many fires... ({long_pause:.1f} seconds)")
                            bot_utils.jitter_sleep(long_pause)
                        else:
                            bot_utils.maybe_idle("between_fires")
                            bot_utils.jitter_sleep(random.uniform(0.1, 0.3))
                    else:
                        # All movement attempts failed, continue loop to try again
                        consecutive_failures = 0  # Reset counter after moving
                        bot_utils.jitter_sleep(random.uniform(0.5, 1.0))
                    continue
                
                if fire_attempt:
                    # Wait for fire and check if it was actually successful
                    fire_success, exhausted_all_checks = wait_for_fire()
                    
                    if fire_success:
                        # Fire was successfully lit (log was consumed)
                        fires_lit += 1
                        consecutive_failures = 0  # Reset failure counter on success
                        print(f"Fire #{fires_lit} lit successfully!")
                        
                        # Minimal delay after successful fire to ensure inventory is fully updated
                        # Reduced delay for faster fire-after-fire cycle
                        bot_utils.jitter_sleep(random.uniform(0.2, 0.4))
                        
                        # Small random delay between fires, plus occasional longer
                        # "thinking" pauses after many fires.
                        maybe_small_reposition_after_fire(fires_lit)
                        
                        # Adjust camera more frequently after fires (players often check surroundings)
                        # Base chance increases with fires lit (players get restless over time)
                        camera_chance = 0.30 + min(0.20, fires_lit * 0.002)  # 30% base, up to 50% after many fires
                        if random.random() < camera_chance:
                            adjust_camera()
                            fires_since_last_camera = 0  # Reset counter
                        else:
                            fires_since_last_camera += 1

                        if fires_lit > 20 and random.random() < 0.05:  # Reduced chance from 0.15 to 0.05
                            long_pause = random.uniform(2.0, 4.0)  # Reduced duration from 4.0-9.0 to 2.0-4.0
                            print(f"Taking a longer pause after many fires... ({long_pause:.1f} seconds)")
                            bot_utils.jitter_sleep(long_pause)
                        else:
                            bot_utils.maybe_idle("between_fires")
                            bot_utils.jitter_sleep(random.uniform(0.1, 0.3))  # Reduced from 0.5-1.5 to 0.1-0.3
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
