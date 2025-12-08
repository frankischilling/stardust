"""
Stardust - Educational Ardougne Baker Thieving Bot

Steals from the baker stall in Ardougne, stays in a single square for
fast spam stealing, and drops excess loot when inventory is full.

IMPORTANT: This is for educational purposes only. Using bots on
RuneScape violates the game's terms of service and will result in a
permanent ban.
"""
import sys
import os
import time
import random
import math
import cv2
import numpy as np
import mss
import pyautogui

# Add parent directory to path to import bot_utils and config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot_utils  # noqa: E402

# Import player configuration
try:
    from config import player_config, player_stats  # noqa: E402
    USE_PLAYER_CONFIG = True
except ImportError:
    print("⚠ Warning: config/player_config.py or config/player_stats.py not found. Using default settings.")
    USE_PLAYER_CONFIG = False
    player_stats = None

# --- Calibration Areas (reuse defaults from other scripts; user should calibrate) ---
GAME_AREA = {"top": 25, "left": 0, "width": 1880, "height": 989}
CHAT_AREA = {"top": 717, "left": 13, "width": 1209, "height": 228}
INVENTORY_AREA = {"top": 430, "left": 1354, "width": 445, "height": 560}

# --- Templates ---
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
# Support both naming conventions: cake_icon.png and cake.png
CAKE_TEMPLATE = os.path.join(TEMPLATES_DIR, "cake_icon.png")
if not os.path.exists(CAKE_TEMPLATE):
    CAKE_TEMPLATE = os.path.join(TEMPLATES_DIR, "cake.png")
BREAD_TEMPLATE = os.path.join(TEMPLATES_DIR, "bread_icon.png")
if not os.path.exists(BREAD_TEMPLATE):
    BREAD_TEMPLATE = os.path.join(TEMPLATES_DIR, "bread.png")
CHOCOLATE_SLICE_TEMPLATE = os.path.join(TEMPLATES_DIR, "chocolateslice_icon.png")
if not os.path.exists(CHOCOLATE_SLICE_TEMPLATE):
    CHOCOLATE_SLICE_TEMPLATE = os.path.join(TEMPLATES_DIR, "chocolate_slice.png")
STUN_TEMPLATE = os.path.join(TEMPLATES_DIR, "stun_message.png")
EMPTY_SLOT_TEMPLATE = os.path.join(TEMPLATES_DIR, "empty_slot.png")

# --- Marker-based detection (RuneLite Object Marker) ---
# Use red object marker to detect baker stall (same as woodcutter marker mode)
# Calibrated for red marker fill (same as woodcutter marker mode), with hue wraparound support.
MARKER_COLOR_LOWER = (0, 120, 120)
MARKER_COLOR_UPPER = (25, 255, 255)
MARKER_COLOR_SECONDARY_LOWER = (170, 120, 120)
MARKER_COLOR_SECONDARY_UPPER = (180, 255, 255)

# UI exclusion for marker detection (exclude right-side UI panels and chat)
UI_EXCLUSION_LEFT = GAME_AREA["left"] + GAME_AREA["width"] * 0.65  # Exclude right 35% of screen
UI_EXCLUSION_BOTTOM = GAME_AREA["top"] + GAME_AREA["height"] * 0.5  # Exclude bottom 50% (includes chat area)
UI_EXCLUSION_RIGHT_EDGE = GAME_AREA["left"] + GAME_AREA["width"] * 0.5  # Exclude right 50% if object is wide
# Keep detections in the main play area (avoid top UI/minimap and ground UI bleed)
STALL_WORLD_Y_MIN = GAME_AREA["top"] + int(GAME_AREA["height"] * 0.12)
STALL_WORLD_Y_MAX = GAME_AREA["top"] + int(GAME_AREA["height"] * 0.78)
# --- Toggles & thresholds ---
DEBUG_MODE = False           # Saves debug prints
DEBUG_SAVE_DETECTIONS = False  # Set True to dump detection images to /debug
THIEVING_CLICK_DELAY = 0.6  # Base delay between steals (increased for more human-like timing)
STUN_RECOVERY_DELAY = 2.0    # Wait after stun before resuming
STUN_MATCH_THRESHOLD = 0.75
STUN_CHECK_DELAYS = [0.2, 0.5, 0.8, 1.2]
STALL_RESPAWN_TIMEOUT = 8.0  # Seconds to wait for stall to reappear before counting a failure (increased)
STALL_POLL_INTERVAL_RANGE = (0.15, 0.25)  # Poll cadence while waiting for respawn
STALL_POST_STEAL_DELAY = (1.5, 2.5)  # Wait this long after steal before checking for stall again
STALL_MAX_DISTANCE_FROM_HOME = 300  # Ignore detections too far from home tile

# Position tracking to stay in one square
_home_tile = None  # (x, y) screen coords
HOME_TOLERANCE_PX = 6

# Sticky stall targeting to avoid drifting to other red UI/hitsplats
STALL_DRIFT_TOLERANCE = 30  # Max pixels considered the same stall
STALL_JUMP_CONFIRMATIONS = 20  # Confirm a new location this many times before switching (very high to prevent false switches)
STALL_REACQUIRE_MISSES = 5  # Misses before clearing cached stall
STALL_MAX_DISTANCE_FROM_ORIGINAL = 100  # Never switch to a location more than this many pixels from original stall

_stall_target = None
_stall_jump_candidate = None
_stall_jump_confirms = 0
_stall_miss_streak = 0


# --- Helpers --------------------------------------------------------------------
def _load_template(path):
    tpl = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if tpl is None:
        return None
    if len(tpl.shape) == 2:
        tpl = cv2.cvtColor(tpl, cv2.COLOR_GRAY2BGR)
    elif tpl.shape[2] == 4:
        tpl = cv2.cvtColor(tpl, cv2.COLOR_BGRA2BGR)
    return tpl


def _capture(area):
    with mss.mss() as sct:
        return np.array(sct.grab(area))


def find_baker_stall():
    """Find baker stall using red object marker (mirrors woodcutter marker logic)."""
    detection_kwargs = {
        "color_lower": MARKER_COLOR_LOWER,
        "color_upper": MARKER_COLOR_UPPER,
        "game_area": GAME_AREA,
        # Stall marker is large (≈26k area). Use higher floors to ignore pants/windows.
        "min_area": 500,
        "max_area": 50000,
        "min_aspect_ratio": 0.0,
        "max_aspect_ratio": 4.0,
        "min_height": 15,
        "min_width": 15,
        "max_width": 800,
        "max_height": 800,
        "exclude_ui_left": UI_EXCLUSION_LEFT,
        "exclude_ui_bottom": UI_EXCLUSION_BOTTOM,
        "exclude_ui_right_edge": UI_EXCLUSION_RIGHT_EDGE,
        "world_y_min": STALL_WORLD_Y_MIN,
        "world_y_max": STALL_WORLD_Y_MAX,
        "relaxed_filters": True,
        "allow_wide_aspect": True,
        "secondary_color_range": (MARKER_COLOR_SECONDARY_LOWER, MARKER_COLOR_SECONDARY_UPPER),
    }

    all_markers = bot_utils.find_all_colors(**detection_kwargs)

    if not all_markers:
        fallback_kwargs = detection_kwargs.copy()
        fallback_kwargs.update({
            "min_area": max(200, int(detection_kwargs["min_area"] * 0.5)),
            "min_height": max(10, int(detection_kwargs["min_height"] * 0.6)),
            "min_aspect_ratio": 0.0,
            "max_aspect_ratio": 4.0,
            "max_width": 900,
            "max_height": 900,
            "relaxed_filters": True,
            "exclude_ui_left": UI_EXCLUSION_LEFT,
            "exclude_ui_bottom": UI_EXCLUSION_BOTTOM,
            "exclude_ui_right_edge": UI_EXCLUSION_RIGHT_EDGE,
            "world_y_min": STALL_WORLD_Y_MIN,
            "world_y_max": STALL_WORLD_Y_MAX,
        })
        all_markers = bot_utils.find_all_colors(**fallback_kwargs)

    return all_markers[0] if all_markers else None


def _dist(a, b):
    """Euclidean distance between two (x, y) points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def wait_for_stall_visible(timeout=STALL_RESPAWN_TIMEOUT):
    """
    Poll for the stall to be visible again before clicking.
    Returns the stall position or None if not found within timeout.
    """
    start = time.time()
    while time.time() - start < timeout:
        stall = get_sticky_stall_target()
        if stall:
            return stall
        bot_utils.jitter_sleep(random.uniform(*STALL_POLL_INTERVAL_RANGE))
    return None


def get_sticky_stall_target():
    """
    Keep clicking the initially found stall and ignore sudden jumps to other red pixels
    unless they are confirmed in consecutive detections. Very strict to avoid clicking wrong objects.
    """
    global _stall_target, _stall_jump_candidate, _stall_jump_confirms, _stall_miss_streak
    stall = find_baker_stall()

    if stall:
        _stall_miss_streak = 0

        # If we have a locked target, be very strict about switching
        if _stall_target is not None:
            distance = _dist(stall, _stall_target)

            # Same location or very close: update and use it
            if distance <= STALL_DRIFT_TOLERANCE:
                _stall_target = stall
                _stall_jump_candidate = None
                _stall_jump_confirms = 0
                return _stall_target

            # If new detection is too far from original, completely reject it
            if distance > STALL_MAX_DISTANCE_FROM_ORIGINAL:
                # Too far - ignore this detection completely, stick with original
                if DEBUG_MODE:
                    print(f"[debug] Rejecting distant detection at {stall} (distance: {distance:.1f}px from original {_stall_target})")
                _stall_jump_candidate = None
                _stall_jump_confirms = 0
                return _stall_target
            
            # Medium distance: require many confirmations before switching
            if _stall_jump_candidate and _dist(stall, _stall_jump_candidate) <= STALL_DRIFT_TOLERANCE:
                _stall_jump_confirms += 1
            else:
                # New candidate location - reset confirmation counter
                _stall_jump_candidate = stall
                _stall_jump_confirms = 1
            
            # Only switch if we've confirmed the new location MANY times (very strict)
            if _stall_jump_confirms >= STALL_JUMP_CONFIRMATIONS:
                if DEBUG_MODE:
                    print(f"[debug] Switching stall target from {_stall_target} to {stall} after {_stall_jump_confirms} confirmations")
                _stall_target = stall
                _stall_jump_candidate = None
                _stall_jump_confirms = 0
                return _stall_target
            else:
                # Not enough confirmations - stick with original target
                return _stall_target
        else:
            # No locked target yet - accept first detection
            _stall_target = stall
            _stall_jump_candidate = None
            _stall_jump_confirms = 0
            return _stall_target
    else:
        _stall_miss_streak += 1
        if _stall_miss_streak >= STALL_REACQUIRE_MISSES:
            # Clear target after many misses (stall might have moved or disappeared)
            _stall_target = None
            _stall_jump_candidate = None
            _stall_jump_confirms = 0
        # On miss, do NOT return cached target; force caller to wait for a fresh detection
        return None

    return _stall_target


def find_cake():
    """Template match cakes in inventory. Tries multiple thresholds to find any cake."""
    if not os.path.exists(CAKE_TEMPLATE):
        return None
    # Try lower thresholds first to catch all items, even if slightly different
    for threshold in [0.6, 0.65, 0.7, 0.75, 0.8]:
        pos = bot_utils.find_image(CAKE_TEMPLATE, threshold=threshold, game_area=INVENTORY_AREA)
        if pos:
            return pos
    return None


def find_bread():
    """Template match bread in inventory. Tries multiple thresholds to find any bread."""
    if not os.path.exists(BREAD_TEMPLATE):
        return None
    # Try lower thresholds first to catch all items, even if slightly different
    for threshold in [0.6, 0.65, 0.7, 0.75, 0.8]:
        pos = bot_utils.find_image(BREAD_TEMPLATE, threshold=threshold, game_area=INVENTORY_AREA)
        if pos:
            return pos
    return None


def find_chocolate_slice():
    """Template match chocolate slice in inventory. Tries multiple thresholds to find any chocolate slice."""
    if not os.path.exists(CHOCOLATE_SLICE_TEMPLATE):
        return None
    # Try lower thresholds first to catch all items, even if slightly different
    for threshold in [0.6, 0.65, 0.7, 0.75, 0.8]:
        pos = bot_utils.find_image(CHOCOLATE_SLICE_TEMPLATE, threshold=threshold, game_area=INVENTORY_AREA)
        if pos:
            return pos
    return None


def count_occupied_slots():
    """Count occupied inventory slots via empty-slot template; fallback to full."""
    if not os.path.exists(EMPTY_SLOT_TEMPLATE):
        return 28
    tpl = _load_template(EMPTY_SLOT_TEMPLATE)
    if tpl is None:
        return 28

    bot_utils._maybe_capture_delay()
    screen_bgra = _capture(INVENTORY_AREA)
    screen = cv2.cvtColor(screen_bgra, cv2.COLOR_BGRA2BGR)

    max_empty = 0
    for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]:
        res = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        matches = list(zip(*loc[::-1]))
        if not matches:
            continue
        tpl_h, tpl_w = tpl.shape[:2]
        grouping = min(40, max(30, tpl_w * 0.6))
        matches.sort(key=lambda m: (m[1], m[0]))
        grouped = []
        for (x, y) in matches:
            added = False
            for i, (gx, gy) in enumerate(grouped):
                if np.hypot(x - gx, y - gy) < grouping:
                    grouped[i] = ((gx + x) // 2, (gy + y) // 2)
                    added = True
                    break
            if not added:
                grouped.append((x, y))
        max_empty = max(max_empty, len(grouped))

    occupied = max(0, 28 - max_empty)
    return occupied


def is_inventory_full():
    return count_occupied_slots() >= 28


def check_stun_message():
    """Scan chat for stun template (guard caught)."""
    if not os.path.exists(STUN_TEMPLATE):
        return False
    tpl = _load_template(STUN_TEMPLATE)
    if tpl is None:
        return False
    tpl_h, tpl_w = tpl.shape[:2]

    best = 0.0
    last = 0
    for delay in STUN_CHECK_DELAYS:
        bot_utils.jitter_sleep(delay - last)
        last = delay
        chat_bgra = _capture(CHAT_AREA)
        chat_bgr_full = cv2.cvtColor(chat_bgra, cv2.COLOR_BGRA2BGR)
        h_full = chat_bgr_full.shape[0]
        chat_bgr = chat_bgr_full[int(h_full * 0.6):, :]

        for scale in [1.0, 0.95, 1.05, 0.9]:
            if scale != 1.0:
                scaled = cv2.resize(
                    tpl,
                    (max(1, int(tpl_w * scale)), max(1, int(tpl_h * scale))),
                    interpolation=cv2.INTER_AREA,
                )
            else:
                scaled = tpl
            res = cv2.matchTemplate(chat_bgr, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            best = max(best, max_val)

    if best >= STUN_MATCH_THRESHOLD:
        if DEBUG_MODE:
            print(f"⚠ Stun detected (score={best:.2f})")
        return True
    return False




def drop_item(item_pos, item_name="item"):
    """Helper to drop a single item at given position using shift-click (fast)."""
    if not item_pos:
        return False
    # Add small random offset to click position for more human-like behavior
    click_x = item_pos[0] + random.randint(-3, 3)
    click_y = item_pos[1] + random.randint(-3, 3)
    bot_utils.human_like_move(click_x, click_y, profile="inventory")
    bot_utils.jitter_sleep(random.uniform(0.03, 0.08))  # Faster movement delay
    # Hold shift and click to drop
    pyautogui.keyDown('shift')
    bot_utils.jitter_sleep(random.uniform(0.01, 0.03))  # Faster key press
    pyautogui.click()
    bot_utils.jitter_sleep(random.uniform(0.01, 0.03))  # Faster release
    pyautogui.keyUp('shift')
    bot_utils.jitter_sleep(random.uniform(0.08, 0.15))  # Faster between drops
    return True


def drop_excess_loot():
    """Drop ALL loot items (bread, cake, chocolate slice) quickly when inventory is full."""
    if not is_inventory_full():
        return
    print("  Inventory full. Dropping all loot items...")
    drops = 0
    max_iterations = 100  # Increased safety limit
    consecutive_failures = 0
    max_consecutive_failures = 3  # Break if we fail to find items 3 times in a row
    
    # Drop ALL bread first (cheapest)
    bread_dropped = 0
    consecutive_failures = 0
    for _ in range(max_iterations):
        bread_pos = find_bread()
        if bread_pos:
            if drop_item(bread_pos, "bread"):
                drops += 1
                bread_dropped += 1
                consecutive_failures = 0
                # Small delay to let inventory update after drop
                bot_utils.jitter_sleep(random.uniform(0.05, 0.1))
                continue
        consecutive_failures += 1
        if consecutive_failures >= max_consecutive_failures:
            break
    
    # Drop ALL chocolate slice
    choc_dropped = 0
    consecutive_failures = 0
    for _ in range(max_iterations):
        choc_pos = find_chocolate_slice()
        if choc_pos:
            if drop_item(choc_pos, "chocolate slice"):
                drops += 1
                choc_dropped += 1
                consecutive_failures = 0
                # Small delay to let inventory update after drop
                bot_utils.jitter_sleep(random.uniform(0.05, 0.1))
                continue
        consecutive_failures += 1
        if consecutive_failures >= max_consecutive_failures:
            break
    
    # Drop ALL cakes
    cake_dropped = 0
    consecutive_failures = 0
    for _ in range(max_iterations):
        cake_pos = find_cake()
        if cake_pos:
            if drop_item(cake_pos, "cake"):
                drops += 1
                cake_dropped += 1
                consecutive_failures = 0
                # Small delay to let inventory update after drop
                bot_utils.jitter_sleep(random.uniform(0.05, 0.1))
                continue
        consecutive_failures += 1
        if consecutive_failures >= max_consecutive_failures:
            break
    
    if drops:
        print(f"  Dropped {drops} loot items (bread: {bread_dropped}, chocolate: {choc_dropped}, cake: {cake_dropped}).")


def record_home_tile():
    """
    Record current mouse position as the home tile (user should hover over
    their tile before start). Fallback to center of GAME_AREA.
    """
    global _home_tile
    try:
        mx, my = pyautogui.position()
        _home_tile = (mx, my)
    except Exception:
        _home_tile = (
            GAME_AREA["left"] + GAME_AREA["width"] // 2,
            GAME_AREA["top"] + GAME_AREA["height"] // 2,
        )
    if DEBUG_MODE:
        print(f"[debug] Home tile set to: {_home_tile}")


def return_home():
    """Ensure we stay on the same square; click home tile if drift detected."""
    if not _home_tile:
        return
    # Do not re-click too often; slight randomness
    if random.random() < 0.05:
        bot_utils.human_like_move(_home_tile[0], _home_tile[1], profile="skilling")
        bot_utils.jitter_sleep(random.uniform(0.08, 0.15))
        pyautogui.click()
        bot_utils.jitter_sleep(random.uniform(0.4, 0.6))


def step_away_and_back():
    """Basic guard avoidance: small step away then back to home tile."""
    if not _home_tile:
        return
    offset_x = random.randint(-55, 55)
    offset_y = random.randint(-55, 55)
    away_x = _home_tile[0] + offset_x
    away_y = _home_tile[1] + offset_y

    # Bounds to stay inside game view and out of chat
    away_x = min(max(away_x, GAME_AREA["left"] + 40), GAME_AREA["left"] + GAME_AREA["width"] - 40)
    away_y = min(max(away_y, GAME_AREA["top"] + 40), GAME_AREA["top"] + GAME_AREA["height"] - 40)
    chat_right = CHAT_AREA["left"] + CHAT_AREA["width"]
    chat_bottom = CHAT_AREA["top"] + CHAT_AREA["height"]
    if CHAT_AREA["left"] <= away_x <= chat_right and CHAT_AREA["top"] <= away_y <= chat_bottom:
        away_y = CHAT_AREA["top"] - random.randint(40, 120)

    print(f"  Stepping away to ({away_x}, {away_y})...")
    bot_utils.human_like_move(away_x, away_y, profile="skilling")
    bot_utils.jitter_sleep(random.uniform(0.08, 0.18))
    pyautogui.click()
    bot_utils.jitter_sleep(random.uniform(0.9, 1.2))

    print(f"  Returning to home tile {_home_tile}...")
    bot_utils.human_like_move(_home_tile[0], _home_tile[1], profile="skilling")
    bot_utils.jitter_sleep(random.uniform(0.08, 0.18))
    pyautogui.click()
    bot_utils.jitter_sleep(random.uniform(0.9, 1.2))


def steal_once(stall_pos):
    """Attempt one steal at the given stall position; return True if click issued."""
    if not stall_pos:
        return False
    bot_utils.human_like_click(stall_pos[0], stall_pos[1], profile="skilling")
    return True


def save_debug_detection():
    """Optional: save game capture for manual template tuning."""
    if not DEBUG_SAVE_DETECTIONS:
        return
    os.makedirs("debug", exist_ok=True)
    img = _capture(GAME_AREA)
    ts = int(time.time())
    path = os.path.join("debug", f"ardy_baker_capture_{ts}.png")
    cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_BGRA2BGR))
    print(f"[debug] Saved detection capture -> {path}")


# --- Main loop -----------------------------------------------------------------
def main():
    global _home_tile, _stall_target, _stall_jump_candidate, _stall_jump_confirms, _stall_miss_streak
    print("=" * 60)
    print("Stardust - Educational Ardougne Baker Thieving Bot")
    print("=" * 60)
    print("\nWARNING: Educational use only. Botting violates RuneScape ToS.")

    if DEBUG_MODE:
        print("\n" + "=" * 60)
        print("🔍 DEBUG MODE ENABLED")
        print("=" * 60)

    if USE_PLAYER_CONFIG and player_stats:
        print(f"  Player Thieving Level: {getattr(player_stats, 'THIEVING_LEVEL', 'unknown')}")

    # Template checks
    print("\n⚠ IMPORTANT: This bot uses RuneLite Object Marker for stall detection.")
    print("   Make sure you have:")
    print("   1. RuneLite Object Marker plugin enabled")
    print("   2. Baker stall marked with RED fill color")
    print("   3. Marker is visible on screen")
    
    if not os.path.exists(CAKE_TEMPLATE):
        print("⚠ cake_icon.png or cake.png not found in templates/ (cake dropping limited).")
    if not os.path.exists(BREAD_TEMPLATE):
        print("⚠ bread_icon.png or bread.png not found in templates/ (loot dropping limited).")
    if not os.path.exists(CHOCOLATE_SLICE_TEMPLATE):
        print("⚠ chocolateslice_icon.png or chocolate_slice.png not found in templates/ (loot dropping limited).")
    if not os.path.exists(STUN_TEMPLATE):
        print("⚠ stun_message.png not found in templates/ (stun detect limited).")

    print("\nPlace your character on the desired tile beside the baker stall.")
    print("Hover your mouse over your character tile, then keep the window focused.")
    print("Starting in 5 seconds...")
    bot_utils.jitter_sleep(5)

    record_home_tile()

    # Locate stall before loop
    stall_pos = find_baker_stall()
    if not stall_pos:
        print("\n⚠ Baker stall not found. Ensure:")
        print("   1. RuneLite Object Marker plugin is enabled")
        print("   2. Baker stall is marked with RED fill color")
        print("   3. Marker is visible on screen (not blocked)")
        print("   4. Camera angle shows the marked stall")
        save_debug_detection()
        return
    print(f"✓ Baker stall detected at {stall_pos} (using red object marker)")
    _stall_target = stall_pos
    _stall_jump_candidate = None
    _stall_jump_confirms = 0
    _stall_miss_streak = 0
    save_debug_detection()

    steals = 0
    failures = 0
    try:
        while True:

            stall = wait_for_stall_visible()
            if not stall:
                failures += 1
                print(f"⚠ Could not find baker stall (fail #{failures})")
                if failures % 3 == 0:
                    save_debug_detection()
                bot_utils.jitter_sleep(random.uniform(0.8, 1.4))
                if failures >= 8:
                    print("⚠ Too many failures. Check:")
                    print("   - RuneLite Object Marker plugin is enabled")
                    print("   - Baker stall is marked with RED fill")
                    print("   - Marker is visible (not blocked by character/objects)")
                    print("   - Camera angle shows the marked stall")
                    bot_utils.jitter_sleep(3)
                    failures = 0
                continue

            ok = steal_once(stall)
            if not ok:
                failures += 1
                print(f"⚠ Could not click baker stall (fail #{failures})")
                bot_utils.jitter_sleep(random.uniform(0.8, 1.4))
                continue

            steals += 1
            failures = 0
            if DEBUG_MODE:
                print(f"Steal #{steals}")
            
            # Wait after clicking - the red marker disappears when you steal and needs time to reappear
            # This is critical: the marker goes away during the steal animation
            bot_utils.jitter_sleep(random.uniform(*STALL_POST_STEAL_DELAY))
            
            if check_stun_message():
                print("⚠ Stunned by guard. Stepping away briefly...")
                step_away_and_back()
                bot_utils.jitter_sleep(STUN_RECOVERY_DELAY)
            if is_inventory_full():
                drop_excess_loot()
            
            # The stall marker will now be checked in the next loop iteration via wait_for_stall_visible()
            # which will poll until the marker reappears

            bot_utils.maybe_idle("between_steals")

    except KeyboardInterrupt:
        print("\nBot stopped by user.")
        print(f"Total steals: {steals}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        print(f"Total steals before error: {steals}")


if __name__ == "__main__":
    main()
