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
TREE_COLOR_LOWER = (12, 106, 120)   # Tight range based on actual tree trunk: H=17, S=121, V=135
TREE_COLOR_UPPER = (22, 136, 150)   # H±5, S±15, V±15 - much tighter to reduce false positives

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
# Path to an empty inventory slot template (full empty slot image)
EMPTY_SLOT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "empty_slot.png")

# Tree type configuration
# This will be auto-set from player_config.py if available
# Otherwise, set it manually here:
# - "regular": Level 1 trees - 1 log per tree, ~2-3 seconds to cut down
# - "oak": Level 15 - 27 seconds per log, multiple logs per tree
# - "willow": Level 30 - 30 seconds per log, multiple logs per tree
# - "maple": Level 45 - 60 seconds per log, multiple logs per tree
# - "yew": Level 60 - 114 seconds per log, multiple logs per tree
# - "magic": Level 75 - 234 seconds per log, multiple logs per tree
# - "marker": Use RuneLite object marker color instead of trunk HSV

# Marker-mode HSV (object marker highlight). Calibrated for red marker fill (255,0,0).
# We include a second range to catch the hue wraparound near 180 for bright reds.
# Lower S/V tightened enough to avoid UI bleed but loose enough for semi-transparent fills.
MARKER_COLOR_LOWER = (0, 120, 120)
MARKER_COLOR_UPPER = (25, 255, 255)
MARKER_COLOR_SECONDARY_LOWER = (170, 120, 120)
MARKER_COLOR_SECONDARY_UPPER = (180, 255, 255)

# Auto-set from player config if available
if USE_PLAYER_CONFIG and player_stats:
    # Check if player has preferred tree type set
    if player_config.PREFERRED_TREE_TYPE:
        TREE_TYPE = player_config.PREFERRED_TREE_TYPE
    else:
        # Auto-select best tree based on level
        TREE_TYPE = player_stats.get_best_available_tree()
    
    # Verify player can actually cut this tree type (skip validation for marker mode)
    if TREE_TYPE != "marker":
        available_trees = player_stats.get_available_tree_types()
        if TREE_TYPE not in available_trees:
            print(f"⚠ Warning: Cannot cut {TREE_TYPE} trees at level {player_stats.WOODCUTTING_LEVEL}")
            print(f"  Available trees: {available_trees}")
            TREE_TYPE = available_trees[0] if available_trees else "regular"
            print(f"  Using {TREE_TYPE} instead")
else:
    # Default fallback if config not available
    TREE_TYPE = "regular"
# Force marker mode only (marker-based detection)
TREE_TYPE = "marker"

# Inventory area (typically bottom right of game window)
# Calibrated using calibrate_inventory.py
INVENTORY_AREA = {
    "top": 430,
    "left": 1354,
    "width": 445,
    "height": 560  # Increased to capture bottom row fully
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
    Checks if inventory is full by scanning each inventory slot for:
    1. Logs (using template matching on pre-captured image)
    2. Any occupied slots (detecting non-empty slots)
    
    Inventory has 28 slots arranged in a 4x7 grid.
    Returns True if inventory appears full (27+ slots occupied, or 26+ logs found).
    """
    import cv2
    import mss
    import numpy as np
    
    # Delay to ensure inventory has fully updated after receiving a log
    # This is critical - the inventory UI needs time to update
    bot_utils.jitter_sleep(random.uniform(0.3, 0.5))
    
    # Calculate slot dimensions (4 columns, 7 rows = 28 slots)
    slot_width = INVENTORY_AREA["width"] // 4
    slot_height = INVENTORY_AREA["height"] // 7
    
    # Capture the inventory area ONCE for both log detection and occupied slot detection
    # This avoids multiple capture delays
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(INVENTORY_AREA))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Load log template once
    try:
        log_template = cv2.imread(LOG_ICON_PATH, cv2.IMREAD_COLOR)
        if log_template is None:
            print("  ⚠ Log template not found, using fallback method")
            # Fallback to simple log count
            max_log_count = 0
            for threshold in [0.7, 0.8, 0.6, 0.9, 0.5]:
                count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=threshold)
                if count > max_log_count:
                    max_log_count = count
            if max_log_count >= 26:
                print(f"Inventory check: FULL! Found {max_log_count} logs (26+ = effectively full)")
                return True
            print(f"Inventory check: Found {max_log_count} logs (not full)")
            return False
    except Exception as e:
        print(f"  ⚠ Error loading log template: {e}, using fallback")
        # Fallback
        max_log_count = 0
        for threshold in [0.7, 0.8, 0.6, 0.9, 0.5]:
            count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=threshold)
            if count > max_log_count:
                max_log_count = count
        if max_log_count >= 26:
            print(f"Inventory check: FULL! Found {max_log_count} logs (26+ = effectively full)")
            return True
        print(f"Inventory check: Found {max_log_count} logs (not full)")
        return False
    
    # Use count_inventory_items as PRIMARY method (same as debug script) - more accurate with grouping
    log_counts = []
    max_log_slots_found = 0
    occupied_slots = 0
    
    # Count logs using multiple thresholds and take a robust median to avoid overcounting
    for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]:
        count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=threshold)
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
            # Try a wider range of thresholds to catch empty slots
            for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]:
                count = bot_utils.count_inventory_items(temp_empty_path, INVENTORY_AREA, threshold=threshold)
                if count > empty_slot_count:
                    empty_slot_count = count
            # Treat 0 empty slots as a valid detection (means full)
            empty_slots = empty_slot_count
            # Calculate occupied from empty slots (most reliable)
            occupied_from_empty = max(0, 28 - empty_slots)
            occupied_slots = occupied_from_empty
            # Recalculate log count more carefully when we have empty slot data
            refined_log_count = 0
            for threshold in [0.65, 0.7, 0.75, 0.8]:
                count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=threshold)
                if count > refined_log_count:
                    refined_log_count = count
            # Use the refined count, capped to occupied slots (can't have more logs than occupied slots)
            max_log_slots_found = min(refined_log_count, occupied_slots)
        except Exception as e:
            print(f"  ⚠ Warning: Could not count empty slots ({e})")
            import traceback
            traceback.print_exc()
            empty_slots = None
    else:
        # Debug: show what paths were checked
        print(f"  ⚠ Empty slot template not found. Checked paths:")
        print(f"     - {EMPTY_SLOT_PATH} (exists: {os.path.exists(EMPTY_SLOT_PATH)})")
        rel_path = os.path.join("templates", "empty_slot.png")
        print(f"     - {rel_path} (exists: {os.path.exists(rel_path)})")
        abs_path = os.path.abspath(EMPTY_SLOT_PATH)
        print(f"     - {abs_path} (exists: {os.path.exists(abs_path)})")
    
    # Global log count fallback ONLY if empty slot template not available
    if empty_slots is None:
        try:
            global_log_count = 0
            for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.45, 0.4, 0.35, 0.75, 0.8, 0.9]:
                count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=threshold)
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
    
    # Decision logic:
    # - If 27+ occupied slots: definitely full
    # - If 26+ logs: likely full (26 logs + 1 axe = 27 items = effectively full)
    # - If 26+ occupied slots AND 25+ logs: likely full (accounting for axe)
    
    if empty_slots is not None:
        print(f"Inventory check: Found {max_log_slots_found} log slots, {occupied_slots} occupied slots, {empty_slots} empty (out of 28) [using empty slot template]")
    else:
        print(f"Inventory check: Found {max_log_slots_found} log slots, {occupied_slots} occupied slots (out of 28) [empty slot template not available]")
    
    # Only stop when completely full (28 occupied slots)
    # Continue cutting until the very last slot is filled
    if occupied_slots >= 28:
        print(f"Inventory check: FULL! {occupied_slots} occupied slots (28 = completely full)")
        return True
    
    # Also stop if we have 27+ logs (accounting for tool and other items, this means full)
    if max_log_slots_found >= 27:
        print(f"Inventory check: FULL! Found {max_log_slots_found} logs (27+ logs = full)")
        return True
    
    return False

# Track recently clicked tree positions to avoid clicking the same tree repeatedly
_last_clicked_trees = []  # List of (x, y) positions, max 5 entries
_MIN_TREE_DISTANCE = 50   # Minimum distance in pixels to consider a different tree

# Track failed tree attempts (trees that didn't yield logs after clicking)
_failed_trees = {}  # Dict of (x, y) -> attempt_count, max 3 attempts before skipping
_MAX_FAILED_ATTEMPTS = 1  # Skip tree after 1 failed attempt (more aggressive)
_FAILED_TREE_DISTANCE = 120  # Distance in pixels to consider a tree "the same" as a failed one (increased to catch nearby trees)

def find_and_click_tree():
    """
    Finds a tree using color detection and clicks on it.
    Returns True if tree was found and clicked, False otherwise.
    Uses area and aspect ratio filters to avoid detecting players, sticks, etc.
    Prioritizes larger trees over small ground objects.
    Excludes UI areas to avoid detecting inventory/minimap elements.
    
    Automatically uses the correct color range based on TREE_TYPE if configured.
    Tracks recently clicked trees to avoid clicking the same tree repeatedly.
    
    WARNING: Color detection cannot distinguish between tree types!
    Make sure your color range is calibrated for the specific tree type you want to cut.
    If you're level 1 but the bot clicks oak trees, your color range is too broad.
    """
    global _last_clicked_trees, _failed_trees
    # CRITICAL: Verify player can actually cut this tree type (skip for marker mode)
    marker_mode = TREE_TYPE == "marker"
    if USE_PLAYER_CONFIG and player_stats and not marker_mode:
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
    
    # Use marker mode or tree-type-specific colors
    if marker_mode:
        color_lower = MARKER_COLOR_LOWER
        color_upper = MARKER_COLOR_UPPER
        print("  Using object marker color range")
    else:
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
    
    # Filter parameters based on tree type (marker uses lenient size)
    # ⚠ IMPORTANT: Regular and oak trees have similar colors but DIFFERENT SIZES!
    # - Regular trees (level 1): Smaller - use min_area=400-800, max_area=8000, min_height=30
    # - Oak trees (level 15): Larger - use min_area=3000, max_area=50000, min_height=55
    # Size filtering is the KEY to distinguishing tree types when colors are similar!
    if marker_mode:
        # Marker blobs can vary widely; broaden the scope
        min_area = 2
        max_area = 50000
        min_height = 1
        print("  Using size filters for MARKER mode (object marker highlights)")
    elif TREE_TYPE == "regular":
        min_area = 280      # Minimum size - avoid ground clutter while keeping distant trunks
        max_area = 15000    # Allow trunk + canopy to be one contour
        min_height = 15     # Trees should have some height - lowered for zoomed-out trees (was 35)
        print("  Using size filters for REGULAR trees (supports zoomed-out/distant trees)")
    elif TREE_TYPE == "oak":
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
    detection_kwargs = {
        "color_lower": color_lower,
        "color_upper": color_upper,
        "game_area": GAME_AREA,
        "min_area": min_area,
        "max_area": max_area,
        "min_aspect_ratio": 0.35 if not marker_mode else 0.0,
        "max_aspect_ratio": 0.70 if not marker_mode else 4.0,  # marker splats can be very wide/tall
        # Standing trees: 0.3-0.65 aspect ratio (much taller than wide)
        # Fallen logs: 0.8-0.95 aspect ratio (more square/wide) - REJECTED
        "min_height": min_height,
        "max_width": 300 if not marker_mode else 800,
        "max_height": 400 if not marker_mode else 800,
        "exclude_ui_left": UI_EXCLUSION_LEFT,
        "exclude_ui_bottom": UI_EXCLUSION_BOTTOM,
        "exclude_ui_right_edge": UI_EXCLUSION_RIGHT_EDGE,
        # Keep detections in the mid-ground band (not sky/top bar, not ground plane clutter)
        "world_y_min": GAME_AREA["top"] + int(GAME_AREA["height"] * 0.10) if not marker_mode else None,
        "world_y_max": GAME_AREA["top"] + int(GAME_AREA["height"] * 0.82) if not marker_mode else None,
        "relaxed_filters": True if marker_mode else False,  # marker mode: skip strict filters in primary pass
        "allow_wide_aspect": True if marker_mode else False,  # marker splats can be round/wide
        "secondary_color_range": (
            (MARKER_COLOR_SECONDARY_LOWER, MARKER_COLOR_SECONDARY_UPPER) if marker_mode else None
        ),
    }
    
    # Debug visualization if enabled
    if DEBUG_MODE:
        print("  🔍 DEBUG MODE: Creating visualization...")
        debug_img, mask_img, detection_info = bot_utils.visualize_color_detection(**detection_kwargs)
        print(f"  📊 Detection stats:")
        print(f"     - Total contours found: {detection_info['total_contours']}")
        print(f"     - Valid contours: {detection_info['valid_contours']}")
        print(f"     - Invalid (filtered): {detection_info['invalid_contours']}")
        if detection_info['selected_contour']:
            sel = detection_info['selected_contour']
            print(f"     - Selected tree: Area={int(sel['area'])}, Size={sel['w']}x{sel['h']}")
        else:
            print(f"     - No valid trees detected!")
    
    # Find all valid trees
    all_trees = bot_utils.find_all_colors(**detection_kwargs)
    
    # Fallback: relax filters to catch small/distant trees (more lenient for marker mode)
    # BUT still enforce physics/UI bands unless marker_mode bypasses aspect checks
    if not all_trees:
        print("No tree found with primary filters. Trying relaxed distant-tree filters...")
        fallback_kwargs = detection_kwargs.copy()
        if marker_mode:
            fallback_kwargs.update({
                "min_area": max(2, int(min_area * 0.2)),
                "min_height": max(1, int(min_height * 0.3)),
                "min_aspect_ratio": 0.0,
                "max_aspect_ratio": 4.0,
                "max_width": 900,
                "max_height": 900,
                "relaxed_filters": True,
            })
        else:
            fallback_kwargs.update({
                "min_area": max(60, int(min_area * 0.3)),  # much smaller trunks/canopies
                "min_height": max(8, int(min_height * 0.5)),
                "min_aspect_ratio": 0.25,  # allow thinner silhouettes at distance
                "max_aspect_ratio": 0.75,  # Still enforce physics: trees are taller than wide (reject flat ground objects)
                # Slightly more lenient (0.75 vs 0.70) for distant trees, but still reject fallen logs (0.8-0.95)
                "max_width": 340,
                "max_height": 420,
                "relaxed_filters": True,  # allow smaller/distant trees only in fallback
            })
        all_trees = bot_utils.find_all_colors(**fallback_kwargs)
        
        if DEBUG_MODE:
            _, _, fb_info = bot_utils.visualize_color_detection(save_images=False, **fallback_kwargs)
            print(f"  📊 Fallback detection: total contours={fb_info['total_contours']}, valid={fb_info['valid_contours']}")
    
    if not all_trees:
        print("No tree found.")
        # Try moving camera to look for trees in different directions
        print("  Attempting to move camera to find trees...")
        move_camera()
        # Try detection again after camera movement
        all_trees = bot_utils.find_all_colors(**detection_kwargs)
        
        # If still no trees, try fallback detection
        if not all_trees:
            print("  Still no trees found. Trying relaxed filters after camera movement...")
            fallback_kwargs = detection_kwargs.copy()
            if marker_mode:
                fallback_kwargs.update({
                    "min_area": max(2, int(min_area * 0.2)),
                    "min_height": max(1, int(min_height * 0.3)),
                    "min_aspect_ratio": 0.0,
                    "max_aspect_ratio": 4.0,
                    "max_width": 900,
                    "max_height": 900,
                    "relaxed_filters": True,
                    "world_y_min": None,
                    "world_y_max": None,
                })
            else:
                fallback_kwargs.update({
                    "min_area": max(60, int(min_area * 0.3)),
                    "min_height": max(8, int(min_height * 0.5)),
                    "min_aspect_ratio": 0.25,
                    "max_aspect_ratio": 0.75,
                    "max_width": 340,
                    "max_height": 420,
                    "relaxed_filters": True,
                })
            all_trees = bot_utils.find_all_colors(**fallback_kwargs)
        
        if not all_trees:
            print("  No trees found even after camera movement.")
            return False
        else:
            print(f"  ✓ Found {len(all_trees)} tree(s) after camera movement!")
    
    # Filter out trees that are too close to recently clicked ones OR have failed multiple times
    available_trees = []
    for tree_pos in all_trees:
        # Check if too close to recently clicked trees
        too_close = False
        for last_pos in _last_clicked_trees:
            distance = np.sqrt((tree_pos[0] - last_pos[0])**2 + (tree_pos[1] - last_pos[1])**2)
            if distance < _MIN_TREE_DISTANCE:
                too_close = True
                break
        
        # Check if this tree (or one very close to it) has failed too many times
        # Use a larger distance threshold to catch trees that are "the same" but detected slightly differently
        tree_skipped = False
        for failed_key, failed_count in _failed_trees.items():
            if failed_count >= _MAX_FAILED_ATTEMPTS:
                # Check distance to this failed tree
                distance_to_failed = np.sqrt((tree_pos[0] - failed_key[0])**2 + (tree_pos[1] - failed_key[1])**2)
                if distance_to_failed < _FAILED_TREE_DISTANCE:
                    tree_skipped = True
                    break
        
        if tree_skipped:
            continue  # Skip this tree - it's too close to a failed tree
        
        if not too_close:
            available_trees.append(tree_pos)
    
    # If no trees are far enough from recent clicks, check if we should clear recent clicks or use fallback
    if not available_trees:
        # If we have failed trees but no available trees, don't use failed ones - wait for new trees
        if len(_failed_trees) > 0:
            print(f"  ⚠ No available trees (all {len(all_trees)} trees are near recently clicked or failed ones)")
            print(f"     Waiting for new trees or clearing recent clicks...")
            # Clear recent clicks to allow retrying, but keep failed trees
            _last_clicked_trees = []
            # Try again with cleared recent clicks (but failed trees still filtered)
            available_trees = []
            for tree_pos in all_trees:
                # Check if this tree is near a failed one
                tree_skipped = False
                for failed_key, failed_count in _failed_trees.items():
                    if failed_count >= _MAX_FAILED_ATTEMPTS:
                        distance_to_failed = np.sqrt((tree_pos[0] - failed_key[0])**2 + (tree_pos[1] - failed_key[1])**2)
                        if distance_to_failed < _FAILED_TREE_DISTANCE:
                            tree_skipped = True
                            break
                if not tree_skipped:
                    available_trees.append(tree_pos)
            
            if not available_trees:
                print(f"  ⚠ All trees are failed. Trying to move camera to find new trees...")
                move_camera()
                # Try detection again after camera movement
                all_trees = bot_utils.find_all_colors(**detection_kwargs)
                if not all_trees:
                    # Try fallback
                    fallback_kwargs = detection_kwargs.copy()
                    fallback_kwargs.update({
                        "min_area": max(60, int(min_area * 0.3)),
                        "min_height": max(8, int(min_height * 0.5)),
                        "min_aspect_ratio": 0.25,
                        "max_aspect_ratio": 0.75,
                        "max_width": 340,
                        "max_height": 420,
                        "relaxed_filters": True,
                    })
                    all_trees = bot_utils.find_all_colors(**fallback_kwargs)
                
                # Re-filter with new trees
                available_trees = []
                for tree_pos in all_trees:
                    tree_skipped = False
                    for failed_key, failed_count in _failed_trees.items():
                        if failed_count >= _MAX_FAILED_ATTEMPTS:
                            distance_to_failed = np.sqrt((tree_pos[0] - failed_key[0])**2 + (tree_pos[1] - failed_key[1])**2)
                            if distance_to_failed < _FAILED_TREE_DISTANCE:
                                tree_skipped = True
                                break
                    if not tree_skipped:
                        available_trees.append(tree_pos)
                
                if not available_trees:
                    print(f"  ⚠ All trees are failed even after camera movement. Cannot proceed.")
                    return False
                else:
                    print(f"  ✓ Found {len(available_trees)} available tree(s) after camera movement!")
        else:
            # No failed trees, just clear recent clicks and use any tree
            available_trees = all_trees
            print(f"  All {len(all_trees)} trees are near recently clicked ones, using closest available")
            _last_clicked_trees = []  # Clear to allow retrying
    
    # Pick the first available tree (largest, or furthest from recent clicks)
    tree_pos = available_trees[0]
    
    # Add to recently clicked list (keep only last 5)
    _last_clicked_trees.append(tree_pos)
    if len(_last_clicked_trees) > 5:
        _last_clicked_trees.pop(0)
    
    print(f"Tree found at {tree_pos} ({len(all_trees)} total, {len(available_trees)} available). Clicking...")
    bot_utils.maybe_idle("pre_tree_click")
    bot_utils.human_like_click(tree_pos[0], tree_pos[1])
    return True

def find_log_in_inventory():
    """
    Finds a log in the inventory using template matching.
    Similar to firemaking.py - scans the full inventory area to find any log.
    Returns (x, y) coordinates of the log, or None if not found.
    """
    # Use multiple thresholds, starting with the most permissive
    for threshold in [0.6, 0.7, 0.8, 0.9]:
        log_pos = bot_utils.find_image(LOG_ICON_PATH, threshold=threshold, game_area=INVENTORY_AREA)
        if log_pos:
            return log_pos
    return None

def get_log_count():
    """
    Gets the current count of logs in inventory.
    Returns the number of logs found, or 0 if none found.
    """
    # Try multiple thresholds and return the max count observed
    max_count = 0
    for threshold in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 0.25]:
        count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=threshold)
        if count > max_count:
            max_count = count
    # Fallback: single find_image passes if max_count is still 0
    if max_count == 0:
        for threshold in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.25]:
            if bot_utils.find_image(LOG_ICON_PATH, threshold=threshold, game_area=INVENTORY_AREA):
                max_count = 1
                break
    return max_count

def wait_for_cutting_completion():
    """
    Waits for a new log to appear in inventory after clicking a tree.
    This ensures the bot doesn't move too quickly - it waits for actual inventory changes.
    Similar logic to firemaking.py which waits for inventory changes.
    """
    print(f"Cutting {TREE_TYPE} tree... Waiting for log to appear in inventory...")
    
    # Get initial log count before cutting
    initial_count = get_log_count()
    print(f"  Initial log count: {initial_count}")
    
    # Maximum time to wait for a log (based on tree type)
    if USE_PLAYER_CONFIG and player_stats:
        try:
            tree_info = player_stats.get_tree_info(TREE_TYPE)
            if tree_info:
                wait_range = tree_info["wait_time"]
                max_wait = wait_range[1] * 1.5  # Allow 50% extra time as safety margin
                xp = tree_info["xp"]
                logs_per = tree_info.get("logs_per_tree", "multiple")
                print(f"  Expected: {xp} XP per log, {logs_per} logs per tree, max wait: {max_wait:.1f}s")
        except Exception as e:
            print(f"⚠ Warning: Could not get tree info: {e}")
            max_wait = 30.0  # Default max wait
    else:
        # Default max wait times based on tree type
        max_wait_times = {
            "regular": 5.0,      # Level 1 - quick
            "oak": 45.0,         # Level 15 - ~27 seconds per log
            "willow": 50.0,      # Level 30 - ~30 seconds per log
            "teak": 50.0,        # Level 35 - ~30 seconds per log
            "maple": 95.0,       # Level 45 - ~60 seconds per log
            "mahogany": 95.0,    # Level 50 - ~60 seconds per log
            "yew": 180.0,        # Level 60 - ~114 seconds per log
            "magic": 360.0,      # Level 75 - ~234 seconds per log
        }
        max_wait = max_wait_times.get(TREE_TYPE, 30.0)
    
    # Ensure max_wait is set even if tree metadata was missing
    try:
        max_wait
    except NameError:
        max_wait = 30.0
    
    # Poll inventory periodically until a new log appears or timeout
    start_time = time.time()
    check_interval = 0.5  # Check every 0.5 seconds
    last_count = initial_count
    
    check_num = 0
    while (time.time() - start_time) < max_wait:
        current_count = get_log_count()
        any_log_exists = find_log_in_inventory() is not None
        
        # CRITICAL: Check if inventory is full BEFORE waiting for new log
        if check_inventory_full():
            elapsed = time.time() - start_time
            print(f"  ⚠ Inventory is FULL! Stopping cutting. (checked after {elapsed:.1f}s)")
            return False  # Return False to indicate we should stop cutting
        
        # If log count increased, we got a new log!
        if current_count > initial_count:
            elapsed = time.time() - start_time
            print(f"  ✓ Log received! New count: {current_count} (was {initial_count}, took {elapsed:.1f}s)")
            # Wait a bit for inventory to fully update before checking if full
            bot_utils.jitter_sleep(random.uniform(0.3, 0.5))
            # Check again if inventory is now full
            if check_inventory_full():
                print(f"  ⚠ Inventory is now FULL after receiving log!")
                return False  # Return False to indicate we should stop cutting
            return True

        # Fallback: if we see logs in inventory but the count hasn't budged after several checks,
        # assume one new log was added (helps marker mode where template counts can be noisy).
        if any_log_exists and current_count >= initial_count and (check_num >= 4):
            elapsed = time.time() - start_time
            assumed_count = max(current_count, initial_count + 1)
            print(f"  ✓ Log likely received (detected via image). Assuming count: {assumed_count} (was {initial_count}, took {elapsed:.1f}s)")
            bot_utils.jitter_sleep(random.uniform(0.3, 0.5))
            if check_inventory_full():
                print(f"  ⚠ Inventory is now FULL after receiving log!")
                return False
            return True
        
        # Log count changed but didn't increase (shouldn't happen, but log it)
        if current_count != last_count:
            print(f"  ⚠ Log count changed: {last_count} -> {current_count} (unexpected)")
            last_count = current_count
        
        # Wait before next check
        bot_utils.jitter_sleep(check_interval)
        check_num += 1
    
    # Timeout - check if we actually got a log despite the timeout
    elapsed = time.time() - start_time
    final_count = get_log_count()
    
    # CRITICAL: Check if log count increased even though we hit timeout
    # This can happen if the log appeared but we didn't detect it in time
    if final_count > initial_count:
        print(f"  ✓ Log received! (detected after timeout: {elapsed:.1f}s)")
        print(f"     Count: {initial_count} -> {final_count}")
        # Check if inventory is now full
        if check_inventory_full():
            print(f"  ⚠ Inventory is now FULL after receiving log!")
            return False  # Return False to indicate we should stop cutting
        return True  # Log was received, continue cutting
    
    # Timeout and no log appeared - check if inventory is full first
    # CRITICAL: Check inventory full status even on timeout
    if check_inventory_full():
        print(f"  ⚠ Inventory is FULL! (checked after timeout: {elapsed:.1f}s)")
        return False  # Return False to indicate we should stop cutting
    
    # Timeout and no log appeared - mark this as a failed attempt
    print(f"  ⚠ Timeout after {elapsed:.1f}s. Final count: {final_count} (was {initial_count})")
    print(f"  → Tree may have been depleted or cutting failed. Continuing anyway...")
    # Return special value to indicate timeout without log (caller will track failures)
    return "timeout_no_log"

def move_camera():
    """
    Moves the camera left or right to look for trees in different directions.
    Uses arrow keys to rotate the camera view.
    """
    # Randomly choose left or right
    direction = random.choice(['left', 'right'])
    
    # Determine which arrow key to press
    # pyautogui uses 'left' and 'right' for arrow keys
    if direction == 'left':
        key = 'left'
        print("  🔄 Rotating camera left to look for trees...")
    else:
        key = 'right'
        print("  🔄 Rotating camera right to look for trees...")
    
    # Press and hold the arrow key for a random duration (human-like)
    # RuneScape camera rotates while key is held
    hold_duration = random.uniform(0.4, 1.0)  # Hold for 0.4-1.0 seconds (longer for more rotation)
    
    # Small delay before pressing key (ensure window is focused)
    bot_utils.jitter_sleep(random.uniform(0.1, 0.2))
    
    # Press and hold the key
    try:
        pyautogui.keyDown(key)
        time.sleep(hold_duration)  # Use time.sleep for more reliable key holding
        pyautogui.keyUp(key)
        print(f"  ✓ Camera rotated {direction} (held key for {hold_duration:.2f}s)")
    except Exception as e:
        print(f"  ⚠ Failed to rotate camera: {e}")
        # Try alternative method - press key multiple times
        try:
            for _ in range(3):
                pyautogui.press(key)
                time.sleep(0.1)
            print(f"  ✓ Camera rotated {direction} (alternative method)")
        except Exception as e2:
            print(f"  ⚠ Camera rotation failed: {e2}")
    
    # Small delay after camera movement to let view settle
    bot_utils.jitter_sleep(random.uniform(0.3, 0.5))

def refresh_view():
    """
    Reset tree memory so the next detection pass considers freshly respawned trees.
    No in-game camera movement is performed here.
    """
    global _last_clicked_trees, _failed_trees
    print("Refreshing detection state for potential respawns...")
    _last_clicked_trees = []  # allow clicking previously used spots once trees regrow
    # DON'T clear failed trees - keep them skipped to avoid going back to unreachable trees
    # Only clear if we explicitly want to reset (e.g., after moving to a new area)
    # _failed_trees.clear()  # Commented out - keep failed trees in skip list

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
        bot_utils.jitter_sleep(random.uniform(0.1, 0.2))
        pyautogui.rightClick()
        bot_utils.jitter_sleep(random.uniform(0.2, 0.4))
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
        bot_utils.jitter_sleep(random.uniform(0.1, 0.3))
        pyautogui.rightClick()
        bot_utils.jitter_sleep(random.uniform(0.3, 0.5))
        
        # In a real implementation, you'd need to find and click "Deposit-All"
        # For now, this is a placeholder
        print("(Placeholder: Would click Deposit-All here)")
        
        # Close bank with Escape
        bot_utils.jitter_sleep(random.uniform(0.5, 1.0))
        pyautogui.press('escape')
        bot_utils.jitter_sleep(random.uniform(0.5, 1.0))
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
        break_chance = 0.02  # 2% default (reduced from 10%)
        break_min = 30
        break_max = 120
    
    if random.random() < break_chance:
        break_duration = random.uniform(break_min, break_max)
        print(f"Taking a break for {break_duration:.1f} seconds...")
        bot_utils.jitter_sleep(break_duration)

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
        if player_stats:
            print(f"  Woodcutting Level: {player_stats.WOODCUTTING_LEVEL}")
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
    print(bot_utils.describe_anti_detection())
    
    bot_utils.jitter_sleep(5)
    
    # Declare globals at the start of main function
    global _failed_trees, _last_clicked_trees
    
    state = BotState.IDLE
    cycles_completed = 0
    
    try:
        while True:
            # Take occasional breaks to appear more human-like
            take_break()
            
            # State machine logic
            if state == BotState.IDLE:
                print("\n--- Starting new cycle ---")
                
                # Check if inventory is already full before starting
                if check_inventory_full():
                    print("Inventory is already full! Stopping bot.")
                    break  # Exit the loop - banking not implemented
                
                if find_and_click_tree():
                    state = BotState.CUTTING
                    # Store the tree position to track failures
                    current_tree_pos = _last_clicked_trees[-1] if _last_clicked_trees else None
                    
                    # Wait for cutting to start and get a new log
                    # This function also checks for full inventory during the wait
                    log_received = wait_for_cutting_completion()
                    # Only refresh view if we got a log (success) - don't refresh on failure
                    if log_received is True:
                        refresh_view()
                    
                    # If wait_for_cutting_completion returned False, inventory is full
                    if log_received is False:
                        print("Inventory became full during cutting! Stopping bot.")
                        break  # Exit the loop - banking not implemented
                    # If wait_for_cutting_completion returned "timeout_no_log", mark tree as failed
                    elif log_received == "timeout_no_log" and current_tree_pos:
                        tree_key = tuple(current_tree_pos)
                        _failed_trees[tree_key] = _failed_trees.get(tree_key, 0) + 1
                        failed_count = _failed_trees[tree_key]
                        print(f"  ⚠ Tree at {current_tree_pos} failed {failed_count} time(s). Will skip if it fails {_MAX_FAILED_ATTEMPTS} times.")
                        if failed_count >= _MAX_FAILED_ATTEMPTS:
                            print(f"  ⚠ PERMANENTLY SKIPPING tree at {current_tree_pos} - failed {failed_count} times (player may not be able to reach it)")
                            print(f"     This tree and trees within {_FAILED_TREE_DISTANCE} pixels will be skipped.")
                            # Also remove from recent clicks to prevent immediate retry
                            _last_clicked_trees = [pos for pos in _last_clicked_trees if tuple(pos) != tree_key]
                    # If log_received is True, clear any failure count for this tree (success!)
                    elif log_received is True and current_tree_pos:
                        tree_key = tuple(current_tree_pos)
                        if tree_key in _failed_trees:
                            del _failed_trees[tree_key]
                            print(f"  ✓ Tree at {current_tree_pos} succeeded - cleared failure count")
                else:
                    print("Could not find tree. Waiting...")
                    bot_utils.maybe_idle("idle_no_tree")
                    bot_utils.jitter_sleep(random.uniform(2, 4))
            
            elif state == BotState.CUTTING:
                # wait_for_cutting_completion() already waited for a new log to appear
                # It also checks for full inventory during the wait
                # Now check again if inventory is full, otherwise continue to next tree
                
                # CRITICAL: Check if inventory is full before continuing
                if check_inventory_full():
                    print("Inventory is full! Stopping bot.")
                    break  # Exit the loop - banking not implemented
                
                # Small delay before looking for next tree (human-like pause)
                bot_utils.jitter_sleep(random.uniform(0.5, 1.5))
                
                # Check again before clicking next tree (in case it filled up during delay)
                if check_inventory_full():
                    print("Inventory became full! Stopping bot.")
                    break  # Exit the loop - banking not implemented
                
                # Find and click next tree
                if find_and_click_tree():
                    # Store the tree position to track failures
                    current_tree_pos = _last_clicked_trees[-1] if _last_clicked_trees else None
                    
                    # Wait for cutting to start and get a new log
                    # This function also checks for full inventory during the wait
                    log_received = wait_for_cutting_completion()
                    # Only refresh view if we got a log (success) - don't refresh on failure
                    if log_received is True:
                        refresh_view()
                    
                    # If wait_for_cutting_completion returned False, inventory is full
                    if log_received is False:
                        print("Inventory became full during cutting! Stopping bot.")
                        break  # Exit the loop - banking not implemented
                    # If wait_for_cutting_completion returned "timeout_no_log", mark tree as failed
                    elif log_received == "timeout_no_log" and current_tree_pos:
                        tree_key = tuple(current_tree_pos)
                        _failed_trees[tree_key] = _failed_trees.get(tree_key, 0) + 1
                        failed_count = _failed_trees[tree_key]
                        print(f"  ⚠ Tree at {current_tree_pos} failed {failed_count} time(s). Will skip if it fails {_MAX_FAILED_ATTEMPTS} times.")
                        if failed_count >= _MAX_FAILED_ATTEMPTS:
                            print(f"  ⚠ PERMANENTLY SKIPPING tree at {current_tree_pos} - failed {failed_count} times (player may not be able to reach it)")
                            print(f"     This tree and trees within {_FAILED_TREE_DISTANCE} pixels will be skipped.")
                            # Also remove from recent clicks to prevent immediate retry
                            _last_clicked_trees = [pos for pos in _last_clicked_trees if tuple(pos) != tree_key]
                    # If log_received is True, clear any failure count for this tree (success!)
                    elif log_received is True and current_tree_pos:
                        tree_key = tuple(current_tree_pos)
                        if tree_key in _failed_trees:
                            del _failed_trees[tree_key]
                            print(f"  ✓ Tree at {current_tree_pos} succeeded - cleared failure count")
                    
                    # Stay in CUTTING state to continue cutting
                else:
                    print("Lost tree. Searching again...")
                    state = BotState.IDLE
                    bot_utils.jitter_sleep(random.uniform(1, 2))
            
            elif state == BotState.WALKING_TO_BANK:
                # Banking not implemented - should not reach here
                print("⚠ Banking not implemented. Stopping bot.")
                break
            
            elif state == BotState.BANKING:
                # Banking not implemented - should not reach here
                print("⚠ Banking not implemented. Stopping bot.")
                break
            
            elif state == BotState.WALKING_TO_TREES:
                # Banking not implemented - should not reach here
                print("⚠ Banking not implemented. Stopping bot.")
                break
            
            # Small random delay between state transitions
            bot_utils.maybe_idle("loop_idle")
            bot_utils.jitter_sleep(random.uniform(0.5, 1.5))
            
    except KeyboardInterrupt:
        print("\n\nBot stopped by user.")
        print(f"Total cycles completed: {cycles_completed}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
