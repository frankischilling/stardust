"""
Bot utility functions for screen capture, color detection, image matching, and human-like interactions.
"""
import cv2
import numpy as np
import mss
import pyautogui
import time
import random
import os
from datetime import datetime

try:
    import pytesseract
    from PIL import Image
    _HAS_OCR = True
except Exception:
    _HAS_OCR = False

# Optional player config for anti-detection tuning
try:
    from config import player_config
    _CFG = player_config
except Exception:
    _CFG = None

# Anti-detection defaults (overridden if player_config is present)
ANTI_DETECTION_ENABLED = getattr(_CFG, "ANTI_DETECTION_ENABLED", False)
CURSOR_JITTER_PX = getattr(_CFG, "CURSOR_JITTER_PX", 2)
CURSOR_OVERSHOOT_CHANCE = getattr(_CFG, "CURSOR_OVERSHOOT_CHANCE", 0.0)
CURSOR_MICRO_STUTTER_CHANCE = getattr(_CFG, "CURSOR_MICRO_STUTTER_CHANCE", 0.0)
MOVE_DURATION_RANGE = getattr(_CFG, "MOVE_DURATION_RANGE", (0.1, 0.3))
ACTION_JITTER_RANGE = getattr(_CFG, "ACTION_JITTER_RANGE", (0.0, 0.0))
IDLE_CHANCE = getattr(_CFG, "IDLE_CHANCE", 0.0)
IDLE_DURATION_RANGE = getattr(_CFG, "IDLE_DURATION_RANGE", (0.1, 0.2))
THINKING_PAUSE_CHANCE = getattr(_CFG, "THINKING_PAUSE_CHANCE", 0.0)
THINKING_PAUSE_RANGE = getattr(_CFG, "THINKING_PAUSE_RANGE", (0.5, 1.0))
CAPTURE_DELAY_RANGE = getattr(_CFG, "CAPTURE_DELAY_RANGE", (0.0, 0.0))
# Very small chance to deliberately misclick near a target before correcting.
CURSOR_MISCLICK_CHANCE = getattr(_CFG, "CURSOR_MISCLICK_CHANCE", 0.01)


def _log_anti(msg):
    """Lightweight anti-detection runtime log."""
    if ANTI_DETECTION_ENABLED:
        print(f"[anti-detection] {msg}")

def find_all_colors(color_lower, color_upper, game_area, min_area=400, max_area=50000,
                    min_aspect_ratio=0.4, max_aspect_ratio=2.5, min_height=30,
                    min_width=0, max_width=300, max_height=400, exclude_ui_left=None, 
                    exclude_ui_bottom=None, exclude_ui_right_edge=None,
                    world_y_min=None, world_y_max=None, relaxed_filters=False,
                    allow_wide_aspect=False, secondary_color_range=None):
    """
    Finds ALL valid objects in the game area by HSV color range.
    
    Args:
        Same as find_color
        relaxed_filters: If True, skip the strictest shape/size rejections to allow distant trees
    
    Returns:
        List of tuples [(x, y), ...] of center points of all valid objects, sorted by area (largest first)
    """
    # Small random delay before capture to avoid perfectly periodic sampling
    _maybe_capture_delay()
    # Capture game area
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(game_area))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Convert to HSV
    screen_hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)
    
    # Create mask for primary color range
    mask = cv2.inRange(screen_hsv, np.array(color_lower), np.array(color_upper))
    # Optional secondary range (helps catch hue wraparound like bright reds near 180)
    if secondary_color_range:
        low2, up2 = secondary_color_range
        mask2 = cv2.inRange(screen_hsv, np.array(low2), np.array(up2))
        mask = cv2.bitwise_or(mask, mask2)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return []
    
    valid_contours = []
    
    # Filter contours by area, aspect ratio, height, width, and UI exclusion
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue
        
        x, y, w, h = cv2.boundingRect(contour)
        if w == 0 or h == 0:
            continue
        
        # Check minimum height
        if h < min_height:
            continue
        
        # Check minimum / maximum width/height (filters skinny players & large UI panels)
        if w < min_width or w > max_width or h > max_height:
            continue
        
        # Calculate aspect ratio FIRST - we need it for all filters
        aspect_ratio = w / h
        
        # --- PHYSICS-BASED FILTER: Trees are ALWAYS taller than wide (even in relaxed mode) ---
        # This is a fundamental physical property - trees grow vertically, ground objects are horizontal
        # Standing trees typically have aspect ratios of 0.3-0.65 (much taller than wide)
        # Fallen logs, even when detected at an angle, will be closer to 0.8-0.95 (more square/wide)
        if not allow_wide_aspect:
            if aspect_ratio >= 1.0:
                continue  # Trees are NEVER wider than tall - reject all wide/flat objects (ground, windows, tables, etc.)
            
            # CRITICAL: Reject objects that are too square/horizontal (fallen logs, ground objects)
            # Even with aspect < 1.0, if width is close to height, it's likely a fallen log
            if aspect_ratio > 0.70:  # Too square/horizontal for a standing tree
                continue  # Ground objects, fallen logs, barrels, boxes - trees are MUCH taller than wide
            
            # --- ADDITIONAL FILTER: Reject horizontal/fallen objects (more aggressive) ---
            # Fallen logs and ground items are long and horizontal (width >> height)
            # Even if aspect_ratio < 0.70, check if object is suspiciously wide relative to its height
            if w > h * 1.3 and area > 1500:  # More aggressive - catches more fallen logs
                # But allow if it's clearly vertical (very tall relative to width)
                if h < w * 0.8:  # Height is less than 80% of width = too horizontal
                    continue  # Too horizontal - likely fallen log or ground object
            # --- end horizontal object filter ---
            # --- end physics-based aspect ratio filter ---
        
        # Check min/max aspect ratio bounds (after rejecting wide/square objects)
        if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
            continue
        
        if not relaxed_filters:
            # --- Filter for SMALL objects (boxes, crates, windows, small furniture) ---
            # Very small objects: tiny area, any height - definitely not trees
            # RELAXED: Only reject very tiny objects to allow actual trees
            if area < 300:
                continue  # Too tiny = box/crate/window/decor, not tree (relaxed from 800)
            # Small boxes/crates: small area, short height, any aspect ratio
            # RELAXED: Only reject if both small area AND very short
            if area < 600 and h < 35:
                continue  # Too small and short = box/crate/window, not tree (relaxed)
            # Small windows/boxes: small area, medium height but still too small
            # RELAXED: Only reject if both small area AND short height
            if area < 800 and h < 40:
                continue  # Small object = window/box/crate, not tree (relaxed)
            # Small rectangular objects (windows, boxes): small area, any reasonable aspect
            # RELAXED: Only reject if all dimensions are small
            if area < 700 and w < 40 and h < 40:
                continue  # Small rectangular object = window/box/crate, not tree (relaxed)
            # Small objects with both dimensions small (definitely not trees)
            # RELAXED: Only reject very small objects
            if w < 25 and h < 25:
                continue  # Both dimensions too small = small decor/box, not tree (relaxed from 50)
            # Very small objects regardless of shape (only reject if very small)
            if area < 400 and (w < 30 or h < 30):
                continue  # Too small in any dimension = not a tree (relaxed)
            # --- end small object filter ---
            
            # --- Aggressive filter for LADDERS (very tall, very thin) ---
            # Ladders: extremely tall and narrow (aspect ratio < 0.3, narrow width)
            if aspect_ratio < 0.3 and w < 25:
                continue  # Ladder (very tall and narrow)
            # Ladders: tall with very narrow width
            if h > 80 and w < 20:
                continue  # Ladder (tall and very narrow)
            # Ladders: tall with low area (thin vertical lines)
            if h > 60 and area < 800 and w < 30:
                continue  # Ladder (tall, thin, low area)
            # Extremely thin objects (ladders, poles, thin structures)
            if w < 15 and h > 40:
                continue  # Extremely thin (ladder/pole)
            # --- end ladder filter ---
            
            # --- Filter for round/square objects (player heads, barrels, posts) - RELAXED ---
            # Player heads: small, round/square (aspect ratio 0.7-0.9), small area
            # Only reject if very small AND round/square
            if 0.75 <= aspect_ratio < 0.98 and area < 1000:
                continue  # Round/square very small object = player head/barrel/post, not tree
            # Even slightly round/square objects are suspicious if very small
            if 0.80 <= aspect_ratio < 0.98 and area < 1500:
                continue  # Round/square small object = likely not a tree
            # --- end round/square filter ---
            
            # Filter out plants (small to medium circular/compact objects)
            # Plants are typically more circular than trees and shorter
            # Aggressive filter: any small object (area < 700) that is short (h < 50) is likely a plant
            if area < 700 and h < 50:
                continue  # Likely small plant or ground clutter (too small and short)
            # Small to medium plants: area < 1000, roughly circular (aspect ratio 0.7-0.9)
            if 0.7 <= aspect_ratio < 0.9 and area < 1000:
                continue  # Likely small plant or ground clutter
            # Medium plants: area 1000-7000, circular-ish, and short (height < 80)
            if 0.7 <= aspect_ratio < 0.9 and 1000 <= area < 7000 and h < 80:
                continue  # Likely medium-sized plant (too compact and short to be a tree)
            
            # Filter out window frames and UI borders (very thin objects at edges)
            # Window frames are often thin horizontal or vertical lines
            edge_threshold = 20  # Pixels from edge to consider "at edge"
            is_near_left_edge = x < edge_threshold
            is_near_right_edge = (x + w) > (game_area['width'] - edge_threshold)
            is_near_top_edge = y < edge_threshold
            is_near_bottom_edge = (y + h) > (game_area['height'] - edge_threshold)
            
            # Very thin horizontal lines (window frames, UI borders)
            if h < 10 and (is_near_top_edge or is_near_bottom_edge):
                continue  # Likely window frame or UI border
            
            # Very thin vertical lines (window frames, UI borders)
            if w < 10 and (is_near_left_edge or is_near_right_edge):
                continue  # Likely window frame or UI border
            
            # Very wide but thin objects (window frames, UI panels)
            if (w > 200 and h < 15) or (h > 200 and w < 15):
                continue  # Likely window frame or UI border
        else:
            # Minimal guards in relaxed mode to let distant trees through
            # BUT still enforce physics-based rules (trees are vertical, above ground)
            if area < max(min_area * 0.6, 60):
                continue  # Way too small even for relaxed detection
            if h < max(int(min_height * 0.6), 10):
                continue  # Too short in relaxed mode
            if w < max(int(min_width * 0.6), 10):
                continue  # Too narrow in relaxed mode
            
            # Even in relaxed mode, reject very flat objects (ground objects, fallen logs)
            # Trees are always taller than wide, even when distant
            # Standing trees: 0.3-0.65, Fallen logs: 0.8-0.95
            if not allow_wide_aspect and aspect_ratio > 0.75:  # Stricter than before - reject fallen logs even in relaxed mode
                continue  # Too flat/square - likely ground object or fallen log, not a tree
        
        # Check UI exclusion areas
        abs_x = x + game_area['left']
        abs_y = y + game_area['top']
        abs_x_right = abs_x + w  # Right edge of object
        
        # Exclude if object is in right-side UI area (inventory, minimap)
        if exclude_ui_left is not None:
            # Exclude if left edge OR right edge is in UI area
            if abs_x > exclude_ui_left or abs_x_right > exclude_ui_left:
                continue  # Skip UI area
        
        # Exclude if object is in bottom-right corner (inventory area)
        if exclude_ui_bottom is not None and exclude_ui_left is not None:
            if abs_y > exclude_ui_bottom and abs_x > exclude_ui_left:
                continue  # Skip bottom-right inventory area
        
        # Exclude wide objects that extend into right side (UI panels are often wide)
        if exclude_ui_right_edge is not None:
            if abs_x_right > exclude_ui_right_edge:
                continue  # Skip if object extends into right side
        
        # --- PHYSICS-BASED FILTER: Ground exclusion (trees are above the ground) ---
        # Ground objects are at the very bottom of the screen. Trees grow from the ground,
        # but the visible part of a tree is above the ground level.
        # Calculate bottom edge of object (relative to game area)
        bottom_edge_y = y + h
        screen_bottom = game_area['height']
        center_y = y + h // 2
        
        # Reject objects whose bottom edge is at the very bottom of the screen (ground level)
        # Allow a small margin (5% of screen height) for trees that are very close to ground
        ground_threshold = screen_bottom * 0.95  # Bottom 5% of screen is ground
        if bottom_edge_y >= ground_threshold:
            continue  # Object is at ground level - likely ground texture/shadow/item/fallen log, not a tree
        
        # Also reject objects that are too low in the screen (bottom 15% is likely ground/clutter)
        # Trees should be in the middle/upper portion of the visible world
        low_ground_threshold = screen_bottom * 0.85  # Bottom 15% of screen
        if center_y >= low_ground_threshold and aspect_ratio > 0.7:
            continue  # Too low and too flat - likely ground object
        
        # --- ADDITIONAL FILTER: Reject large horizontal objects at low positions (fallen logs) ---
        # Fallen logs are large, horizontal, and at ground level
        # They have significant area but are wider than tall (even if aspect_ratio < 1.0, they're suspiciously wide)
        # Check: if object is low AND wide relative to height AND large area = fallen log
        if center_y >= low_ground_threshold:
            # At low position - check if it's suspiciously horizontal
            if w > h * 1.2 and area > 3000:  # Wide relative to height AND large area
                continue  # Large, horizontal, low object = fallen log, not a tree
            # Also reject if it's very wide (even if not huge area, wide objects at ground = fallen logs)
            if w > h * 1.5:  # Width is 50%+ more than height
                continue  # Too horizontal at ground level = fallen log
        
        # --- NEW: restrict trees to a vertical band of the world view ---
        if world_y_min is not None or world_y_max is not None:
            center_abs_y = abs_y + h // 2
            if world_y_min is not None and center_abs_y < world_y_min:
                continue  # Too high (top bar / sky / misc clutter)
            if world_y_max is not None and center_abs_y > world_y_max:
                continue  # Too low (indoor furniture / feet / ground clutter)
        # --- end new block ---
        
        if not relaxed_filters:
            # --- NEW: edge complexity check (trees have jagged edges, furniture is smoother) ---
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                # Trees have higher perimeter-to-area ratio (more complex shapes)
                perimeter_area_ratio = perimeter / (area + 1e-5)
                # Very smooth shapes (low ratio) are likely furniture/barrels
                if perimeter_area_ratio < 0.15 and area > 500:
                    continue  # Too smooth for a tree (likely furniture/barrel)
            # --- end edge complexity check ---
            
            # --- NEW: shape-based rejection (players, windows, barrels, furniture) - RELAXED ---
            # Only apply strict shape rejection to small objects
            # For medium/large objects, be lenient to allow trees through
            rejection = None
            if area < 1500 or h < 40:  # Only check shape for small objects
                rejection = _shape_rejection_reason(contour, w, h, area)
            if rejection:
                # Uncomment if you want to see why each one was rejected:
                # print(f"[find_all_colors] reject @({abs_x},{abs_y}) area={int(area)}: {rejection}")
                continue
            # --- end shape filter ---
        
        # Calculate center
        M = cv2.moments(contour)
        if M["m00"] == 0:
            continue
        
        # Calculate center relative to game area
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        
        # Convert to absolute screen coordinates
        abs_x = cX + game_area['left']
        abs_y = cY + game_area['top']
        
        valid_contours.append((abs_x, abs_y, area))
    
    # Sort by area (largest first)
    valid_contours.sort(key=lambda x: x[2], reverse=True)
    
    # Return just the (x, y) positions
    return [(x, y) for x, y, _ in valid_contours]

def find_color(color_lower, color_upper, game_area, min_area=400, max_area=50000,
               min_aspect_ratio=0.4, max_aspect_ratio=2.5, min_height=30,
               min_width=0, max_width=300, max_height=400, exclude_ui_left=None, 
               exclude_ui_bottom=None, exclude_ui_right_edge=None,
               world_y_min=None, world_y_max=None, relaxed_filters=False,
               allow_wide_aspect=False, secondary_color_range=None):
    """
    Finds the largest valid object in the game area by HSV color range.
    
    Args mirror find_all_colors; relaxed_filters behaves the same way.
    
    Returns:
        Tuple (x, y) of center point of largest valid object, or None if not found
    """
    results = find_all_colors(
        color_lower=color_lower,
        color_upper=color_upper,
        game_area=game_area,
        min_area=min_area,
        max_area=max_area,
        min_aspect_ratio=min_aspect_ratio,
        max_aspect_ratio=max_aspect_ratio,
        min_height=min_height,
        min_width=min_width,
        max_width=max_width,
        max_height=max_height,
        exclude_ui_left=exclude_ui_left,
        exclude_ui_bottom=exclude_ui_bottom,
        exclude_ui_right_edge=exclude_ui_right_edge,
        world_y_min=world_y_min,
        world_y_max=world_y_max,
        relaxed_filters=relaxed_filters,
        allow_wide_aspect=allow_wide_aspect,
        secondary_color_range=secondary_color_range,
    )
    return results[0] if results else None

def visualize_color_detection(color_lower, color_upper, game_area, min_area=400, max_area=50000,
                              min_aspect_ratio=0.4, max_aspect_ratio=2.5, min_height=30,
                              min_width=0, max_width=300, max_height=400, exclude_ui_left=None,
                              exclude_ui_bottom=None, exclude_ui_right_edge=None,
                              world_y_min=None, world_y_max=None, relaxed_filters=False,
                              output_dir="debug", save_images=True,
                              allow_wide_aspect=False, secondary_color_range=None):
    """
    Visualizes what the bot detects when searching for objects by color.
    Creates debug images showing the detection process.
    
    Args:
        Same parameters as find_color()
        output_dir: Directory to save debug images
        save_images: Whether to save images to disk
        relaxed_filters: Skip the strictest shape/size rejections to highlight distant trees
    
    Returns:
        Tuple (debug_image, mask_image, detection_info)
        - debug_image: Image with detected objects highlighted
        - mask_image: Binary mask showing color matches
        - detection_info: Dict with detection statistics
    """
    # Create output directory if it doesn't exist
    if save_images and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Capture game area
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(game_area))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Convert to HSV
    screen_hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)
    
    # Create mask for color range (optionally combine secondary range for hue wraparound)
    mask = cv2.inRange(screen_hsv, np.array(color_lower), np.array(color_upper))
    if secondary_color_range:
        low2, up2 = secondary_color_range
        mask2 = cv2.inRange(screen_hsv, np.array(low2), np.array(up2))
        mask = cv2.bitwise_or(mask, mask2)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Create debug image
    debug_img = screen_bgr.copy()
    
    all_contours = []
    valid_contours = []
    invalid_contours = []
    
    # Process all contours
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        
        all_contours.append({
            'contour': contour,
            'area': area,
            'x': x, 'y': y, 'w': w, 'h': h,
            'reason': None
        })
        
        # Apply filters
        if area < min_area:
            all_contours[-1]['reason'] = f'Area too small ({int(area)} < {min_area})'
            invalid_contours.append(all_contours[-1])
            continue
        if area > max_area:
            all_contours[-1]['reason'] = f'Area too large ({int(area)} > {max_area})'
            invalid_contours.append(all_contours[-1])
            continue
        if w == 0 or h == 0:
            all_contours[-1]['reason'] = 'Zero width or height'
            invalid_contours.append(all_contours[-1])
            continue
        if h < min_height:
            all_contours[-1]['reason'] = f'Height too small ({h} < {min_height})'
            invalid_contours.append(all_contours[-1])
            continue
        if w < min_width:
            all_contours[-1]['reason'] = f'Width too small ({w} < {min_width})'
            invalid_contours.append(all_contours[-1])
            continue
        if w > max_width or h > max_height:
            all_contours[-1]['reason'] = f'Too large ({w}x{h} > {max_width}x{max_height})'
            invalid_contours.append(all_contours[-1])
            continue
        
        # Calculate aspect ratio FIRST - we need it for all filters
        aspect_ratio = w / h
        
        # HARD physics rule: trees stand upright. Even relaxed mode rejects wide/square objects.
        if not allow_wide_aspect and aspect_ratio >= 0.97:
            all_contours[-1]['reason'] = f'Too square/wide for tree (aspect={aspect_ratio:.2f})'
            invalid_contours.append(all_contours[-1])
            continue
        
        # Check min/max aspect ratio bounds (after rejecting wide/square objects)
        if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
            all_contours[-1]['reason'] = f'Aspect ratio out of range ({aspect_ratio:.2f})'
            invalid_contours.append(all_contours[-1])
            continue
        
        if not relaxed_filters:
            # --- Aggressive filter for SMALL objects (boxes, crates, windows, small furniture) ---
            if area < 800:
                all_contours[-1]['reason'] = f'Too tiny (box/crate/window/decor, area={int(area)})'
                invalid_contours.append(all_contours[-1])
                continue
            if area < 1500 and h < 60:
                all_contours[-1]['reason'] = f'Too small and short (box/crate/window, area={int(area)}, h={h})'
                invalid_contours.append(all_contours[-1])
                continue
            if area < 2500 and h < 70:
                all_contours[-1]['reason'] = f'Small object (window/box/crate, area={int(area)}, h={h})'
                invalid_contours.append(all_contours[-1])
                continue
            if area < 2000 and w < 80 and h < 80:
                all_contours[-1]['reason'] = f'Small rectangular object (window/box/crate, {w}x{h}, area={int(area)})'
                invalid_contours.append(all_contours[-1])
                continue
            if w < 50 and h < 50:
                all_contours[-1]['reason'] = f'Both dimensions too small (small decor/box, {w}x{h})'
                invalid_contours.append(all_contours[-1])
                continue
            # Very small objects regardless of shape
            if area < 1000 and (w < 60 or h < 60):
                all_contours[-1]['reason'] = f'Too small in any dimension (area={int(area)}, w={w}, h={h})'
                invalid_contours.append(all_contours[-1])
                continue
            # --- end small object filter ---
            
            # --- Aggressive filter for LADDERS (very tall, very thin) ---
            if aspect_ratio < 0.3 and w < 25:
                all_contours[-1]['reason'] = f'Ladder (very tall and narrow, aspect={aspect_ratio:.2f}, w={w})'
                invalid_contours.append(all_contours[-1])
                continue
            if h > 80 and w < 20:
                all_contours[-1]['reason'] = f'Ladder (tall and very narrow, h={h}, w={w})'
                invalid_contours.append(all_contours[-1])
                continue
            if h > 60 and area < 800 and w < 30:
                all_contours[-1]['reason'] = f'Ladder (tall, thin, low area, h={h}, w={w}, area={int(area)})'
                invalid_contours.append(all_contours[-1])
                continue
            if w < 15 and h > 40:
                all_contours[-1]['reason'] = f'Extremely thin (ladder/pole, w={w}, h={h})'
                invalid_contours.append(all_contours[-1])
                continue
            # --- end ladder filter ---
            
            # --- Aggressive filter for round/square objects (player heads, barrels, posts) ---
            if 0.7 <= aspect_ratio < 0.9 and area < 2000:
                all_contours[-1]['reason'] = f'Round/square small object (player head/barrel/post, aspect={aspect_ratio:.2f}, area={int(area)})'
                invalid_contours.append(all_contours[-1])
                continue
            if 0.75 <= aspect_ratio < 0.9 and area < 4000:
                all_contours[-1]['reason'] = f'Round/square medium object (likely not a tree, aspect={aspect_ratio:.2f}, area={int(area)})'
                invalid_contours.append(all_contours[-1])
                continue
            # --- end round/square filter ---
            
            # Filter out window frames and UI borders (very thin objects at edges)
            edge_threshold = 20  # Pixels from edge to consider "at edge"
            is_near_left_edge = x < edge_threshold
            is_near_right_edge = (x + w) > (game_area['width'] - edge_threshold)
            is_near_top_edge = y < edge_threshold
            is_near_bottom_edge = (y + h) > (game_area['height'] - edge_threshold)
            
            # Very thin horizontal lines (window frames, UI borders)
            if h < 10 and (is_near_top_edge or is_near_bottom_edge):
                all_contours[-1]['reason'] = f'Thin horizontal line at edge (likely window frame, {w}x{h})'
                invalid_contours.append(all_contours[-1])
                continue
            
            # Very thin vertical lines (window frames, UI borders)
            if w < 10 and (is_near_left_edge or is_near_right_edge):
                all_contours[-1]['reason'] = f'Thin vertical line at edge (likely window frame, {w}x{h})'
                invalid_contours.append(all_contours[-1])
                continue
            
            # Very wide but thin objects (window frames, UI panels)
            if (w > 200 and h < 15) or (h > 200 and w < 15):
                all_contours[-1]['reason'] = f'Thin wide object (likely window frame/UI border, {w}x{h})'
                invalid_contours.append(all_contours[-1])
                continue
        else:
            # Relaxed mode: only reject extremely tiny blobs
            if area < max(min_area * 0.6, 60):
                all_contours[-1]['reason'] = f'Too small for relaxed detection (area={int(area)})'
                invalid_contours.append(all_contours[-1])
                continue
            if h < max(int(min_height * 0.6), 10):
                all_contours[-1]['reason'] = f'Too short for relaxed detection (h={h})'
                invalid_contours.append(all_contours[-1])
                continue
            if w < max(int(min_width * 0.6), 10):
                all_contours[-1]['reason'] = f'Too narrow for relaxed detection (w={w})'
                invalid_contours.append(all_contours[-1])
                continue
        
        # Check UI exclusion areas
        abs_x = x + game_area['left']
        abs_y = y + game_area['top']
        abs_x_right = abs_x + w  # Right edge of object
        
        # Exclude if object is in right-side UI area (inventory, minimap)
        if exclude_ui_left is not None:
            # Exclude if left edge OR right edge is in UI area
            if abs_x > exclude_ui_left or abs_x_right > exclude_ui_left:
                all_contours[-1]['reason'] = f'In UI exclusion area (x={abs_x} or right={abs_x_right} > {exclude_ui_left})'
                invalid_contours.append(all_contours[-1])
                continue
        
        # Exclude if object is in bottom-right corner (inventory area)
        if exclude_ui_bottom is not None and exclude_ui_left is not None:
            if abs_y > exclude_ui_bottom and abs_x > exclude_ui_left:
                all_contours[-1]['reason'] = f'In bottom-right UI area (inventory)'
                invalid_contours.append(all_contours[-1])
                continue
        
        # Exclude wide objects that extend into right side (UI panels are often wide)
        if exclude_ui_right_edge is not None:
            if abs_x_right > exclude_ui_right_edge:
                all_contours[-1]['reason'] = f'Extends into UI area (right edge {abs_x_right} > {exclude_ui_right_edge})'
                invalid_contours.append(all_contours[-1])
                continue
        
        # --- NEW: vertical band filter with debug reasons ---
        if world_y_min is not None or world_y_max is not None:
            center_abs_y = abs_y + h // 2
            if world_y_min is not None and center_abs_y < world_y_min:
                all_contours[-1]['reason'] = f'Above tree band (center_y={center_abs_y} < {int(world_y_min)})'
                invalid_contours.append(all_contours[-1])
                continue
            if world_y_max is not None and center_abs_y > world_y_max:
                all_contours[-1]['reason'] = f'Below tree band (center_y={center_abs_y} > {int(world_y_max)})'
                invalid_contours.append(all_contours[-1])
                continue
        # --- end new block ---
        
        if not relaxed_filters:
            # --- NEW: edge complexity check with debug reasons ---
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                perimeter_area_ratio = perimeter / (area + 1e-5)
                if perimeter_area_ratio < 0.15 and area > 500:
                    all_contours[-1]['reason'] = f'Too smooth/round (perim/area={perimeter_area_ratio:.3f}, likely furniture)'
                    invalid_contours.append(all_contours[-1])
                    continue
            # --- end edge complexity check ---
            
            # --- NEW: shape-based rejection for debug view ---
            shape_reason = _shape_rejection_reason(contour, w, h, area)
            if shape_reason:
                all_contours[-1]['reason'] = shape_reason
                invalid_contours.append(all_contours[-1])
                continue
            # --- end new part ---
        
        # Valid contour
        valid_contours.append(all_contours[-1])
    
    # Sort valid contours by area (largest first)
    valid_contours.sort(key=lambda c: c['area'], reverse=True)
    
    # Draw invalid contours in red (filtered out)
    for contour_info in invalid_contours:
        x, y, w, h = contour_info['x'], contour_info['y'], contour_info['w'], contour_info['h']
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 1)  # Red for invalid
    
    # Draw valid contours in green (would be clicked)
    for i, contour_info in enumerate(valid_contours):
        contour = contour_info['contour']
        x, y, w, h = contour_info['x'], contour_info['y'], contour_info['w'], contour_info['h']
        
        # Draw bounding box
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green for valid
        
        # Calculate center
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            
            # Draw center point
            cv2.circle(debug_img, (cX, cY), 5, (0, 0, 255), -1)  # Red circle for center
            
            # Draw label
            label = f"#{i+1} (area: {int(contour_info['area'])})"
            cv2.putText(debug_img, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Draw UI exclusion lines/areas if applicable
    if exclude_ui_left is not None:
        rel_x = int(exclude_ui_left - game_area['left'])
        if 0 <= rel_x < game_area['width']:
            cv2.line(debug_img, (rel_x, 0), (rel_x, int(game_area['height'])), (255, 0, 255), 2)
            cv2.putText(debug_img, "UI Exclusion (Right)", (rel_x + 5, 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
    
    if exclude_ui_bottom is not None:
        rel_y = int(exclude_ui_bottom - game_area['top'])
        if 0 <= rel_y < game_area['height']:
            cv2.line(debug_img, (0, rel_y), (int(game_area['width']), rel_y), (255, 0, 255), 2)
            cv2.putText(debug_img, "UI Exclusion (Bottom)", (5, rel_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
    
    if exclude_ui_right_edge is not None:
        rel_x = int(exclude_ui_right_edge - game_area['left'])
        if 0 <= rel_x < game_area['width']:
            cv2.line(debug_img, (rel_x, 0), (rel_x, int(game_area['height'])), (255, 165, 0), 1)
            cv2.putText(debug_img, "UI Edge", (rel_x + 5, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 1)
    
    # Draw tree band boundaries if applicable
    if world_y_min is not None:
        rel_y = int(world_y_min - game_area['top'])
        if 0 <= rel_y < game_area['height']:
            cv2.line(debug_img, (0, rel_y), (int(game_area['width']), rel_y), (0, 255, 255), 1)
            cv2.putText(debug_img, "Tree band top", (5, rel_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    if world_y_max is not None:
        rel_y = int(world_y_max - game_area['top'])
        if 0 <= rel_y < game_area['height']:
            cv2.line(debug_img, (0, rel_y), (int(game_area['width']), rel_y), (0, 165, 255), 1)
            cv2.putText(debug_img, "Tree band bottom", (5, rel_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
    
    # Save images if requested
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if save_images:
        debug_path = os.path.join(output_dir, f"detection_{timestamp}.png")
        mask_path = os.path.join(output_dir, f"mask_{timestamp}.png")
        cv2.imwrite(debug_path, debug_img)
        cv2.imwrite(mask_path, mask)
        print(f"  💾 Saved debug images:")
        print(f"     - {debug_path}")
        print(f"     - {mask_path}")
    
    # Create detection info
    detection_info = {
        'total_contours': len(contours),
        'valid_contours': len(valid_contours),
        'invalid_contours': len(invalid_contours),
        'selected_contour': valid_contours[0] if valid_contours else None,
        'color_range': (color_lower, color_upper),
        'filters': {
            'min_area': min_area,
            'max_area': max_area,
            'min_aspect_ratio': min_aspect_ratio,
            'max_aspect_ratio': max_aspect_ratio,
            'min_height': min_height,
            'max_width': max_width,
            'max_height': max_height,
            'exclude_ui_left': exclude_ui_left,
            'exclude_ui_bottom': exclude_ui_bottom,
            'exclude_ui_right_edge': exclude_ui_right_edge,
            'relaxed_filters': relaxed_filters
        }
    }
    
    return debug_img, mask, detection_info

def find_image(template_path, threshold=0.8, game_area=None):
    """
    Finds an image template in the game area using template matching.
    
    Args:
        template_path: Path to template image file
        threshold: Minimum match confidence (0.0 to 1.0)
        game_area: Dict with 'top', 'left', 'width', 'height', or None for full screen
    
    Returns:
        Tuple (x, y) of center point of match, or None if not found
    """
    try:
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            return None
    except Exception:
        return None
    
    # Small random delay before capture to avoid perfectly periodic sampling
    _maybe_capture_delay()
    # Capture screen area
    if game_area:
        capture_area = game_area
    else:
        # Full screen
        capture_area = {
            "top": 0,
            "left": 0,
            "width": pyautogui.size().width,
            "height": pyautogui.size().height
        }
    
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(capture_area))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Validate template size: template must be smaller than or equal to capture area
    # OpenCV requires: template <= image (both width and height)
    template_h, template_w = template.shape[:2]
    capture_h, capture_w = screen_bgr.shape[:2]
    
    # If template is slightly larger, crop it to fit (common with capture differences)
    if template_h > capture_h or template_w > capture_w:
        # Template is too large - crop it to fit the capture area
        crop_h = min(template_h, capture_h)
        crop_w = min(template_w, capture_w)
        template = template[0:crop_h, 0:crop_w]
        template_h, template_w = template.shape[:2]
        # After cropping, verify it's now small enough
        if template_h > capture_h or template_w > capture_w:
            # Still too large even after cropping - skip
            return None
    
    # Template matching
    result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    if max_val < threshold:
        return None
    
    # Get center of match (template_h, template_w already defined above)
    center_x = max_loc[0] + template_w // 2
    center_y = max_loc[1] + template_h // 2
    
    # Convert to absolute screen coordinates
    abs_x = center_x + capture_area['left']
    abs_y = center_y + capture_area['top']
    
    return (abs_x, abs_y)

def count_inventory_items(template_path, inventory_area, threshold=0.8):
    """
    Counts items in inventory by finding template matches and grouping nearby matches.
    
    Args:
        template_path: Path to item template image
        inventory_area: Dict with 'top', 'left', 'width', 'height' of inventory
        threshold: Minimum match confidence (0.0 to 1.0)
    
    Returns:
        Integer count of items found
    """
    try:
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            return 0
    except Exception:
        return 0
    
    # Small random delay before capture to avoid perfectly periodic sampling
    _maybe_capture_delay()
    # Capture inventory area
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(inventory_area))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Template matching
    result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
    
    # Find all matches above threshold
    locations = np.where(result >= threshold)
    matches = list(zip(*locations[::-1]))  # Switch x and y coordinates
    
    if not matches:
        return 0
    
    # If we found matches, we have at least 1 item
    # Group nearby matches to avoid counting duplicates
    # Inventory items are typically spaced apart (usually 40-50 pixels between slots)
    template_h, template_w = template.shape[:2]
    
    # Use a more conservative grouping distance
    # Inventory slots are typically 40-50 pixels apart
    # We want to group matches within the same slot but not across different slots
    # For a 64x64 template, matches on the same item will be within ~30 pixels
    # Different inventory slots will be 40+ pixels apart
    grouping_distance = min(40, max(30, template_w * 0.6))  # Between 30-40 pixels
    
    # Sort matches by position to make grouping more predictable
    matches.sort(key=lambda m: (m[1], m[0]))  # Sort by y, then x
    
    grouped_matches = []
    for match in matches:
        x, y = match
        # Check if this match is near any existing group
        added = False
        for i, group in enumerate(grouped_matches):
            group_x, group_y = group
            distance = np.sqrt((x - group_x)**2 + (y - group_y)**2)
            if distance < grouping_distance:  # Within grouping distance, consider it the same item
                # Update group to be the average position (better center)
                grouped_matches[i] = ((group_x + x) // 2, (group_y + y) // 2)
                added = True
                break
        
        if not added:
            grouped_matches.append((x, y))
    
    # Ensure we return at least 1 if we found any matches
    # (safety check in case grouping somehow removed all matches)
    return max(1, len(grouped_matches)) if matches else 0

def _profiled_move_range(profile):
    """
    Returns a per-profile move duration range based on MOVE_DURATION_RANGE.
    
    Profiles are light-weight multipliers over the base range:
        - "default": no change
        - "skilling": slightly slower, more deliberate motions
        - "inventory": slightly faster/snappier
        - "banking": medium-fast
    """
    base_min, base_max = MOVE_DURATION_RANGE
    # Multipliers tuned to be subtle – we want different "feels", not extremes.
    if profile == "skilling":
        factor = 1.15
    elif profile == "inventory":
        factor = 0.8
    elif profile == "banking":
        factor = 0.9
    else:
        factor = 1.0
    return base_min * factor, base_max * factor


def _profiled_overshoot_chance(profile):
    """Small per-profile tweaks to overshoot chance."""
    if profile == "skilling":
        return CURSOR_OVERSHOOT_CHANCE * 1.1
    if profile == "inventory":
        return CURSOR_OVERSHOOT_CHANCE * 0.8
    if profile == "banking":
        return CURSOR_OVERSHOOT_CHANCE
    return CURSOR_OVERSHOOT_CHANCE


def _profiled_micro_stutter_chance(profile):
    """Small per-profile tweaks to micro-stutter chance."""
    if profile == "skilling":
        return CURSOR_MICRO_STUTTER_CHANCE * 1.2
    if profile == "inventory":
        return CURSOR_MICRO_STUTTER_CHANCE * 0.7
    if profile == "banking":
        return CURSOR_MICRO_STUTTER_CHANCE
    return CURSOR_MICRO_STUTTER_CHANCE


def human_like_move(x, y, profile="default"):
    """
    Moves mouse to coordinates with human-like behavior (slight randomness).
    
    Args:
        x: Target X coordinate
        y: Target Y coordinate
        profile: High-level action profile ("default", "skilling", "inventory", "banking")
    """
    # Add small random offset to make movement more human-like
    offset_x = random.uniform(-CURSOR_JITTER_PX, CURSOR_JITTER_PX)
    offset_y = random.uniform(-CURSOR_JITTER_PX, CURSOR_JITTER_PX)
    
    target_x = int(x + offset_x)
    target_y = int(y + offset_y)
    if ANTI_DETECTION_ENABLED:
        _log_anti(f"move[{profile}] target=({x},{y}) jitter=({target_x},{target_y})")
    
    move_range = _profiled_move_range(profile)
    overshoot_chance = _profiled_overshoot_chance(profile)
    micro_stutter_chance = _profiled_micro_stutter_chance(profile)

    # Optional overshoot then settle
    if ANTI_DETECTION_ENABLED and random.random() < overshoot_chance:
        overshoot_x = target_x + random.randint(-6, 6)
        overshoot_y = target_y + random.randint(-6, 6)
        _log_anti(f"overshoot[{profile}] to ({overshoot_x},{overshoot_y})")
        pyautogui.moveTo(overshoot_x, overshoot_y,
                         duration=random.uniform(*move_range))
        _tiny_pause()

    # Occasional micro-stutter before final move
    if ANTI_DETECTION_ENABLED and random.random() < micro_stutter_chance:
        wiggle_x = target_x + random.randint(-3, 3)
        wiggle_y = target_y + random.randint(-3, 3)
        _log_anti(f"micro-stutter[{profile}] to ({wiggle_x},{wiggle_y})")
        pyautogui.moveTo(wiggle_x, wiggle_y,
                         duration=random.uniform(0.03, 0.07))
        _tiny_pause()
    
    # Final move with jittered duration
    pyautogui.moveTo(
        target_x,
        target_y,
        duration=random.uniform(*move_range)
    )

def human_like_click(x, y, button='left', profile="default"):
    """
    Clicks at coordinates with human-like behavior (random delays, slight movement).
    
    Args:
        x: Target X coordinate
        y: Target Y coordinate
        button: Mouse button ('left' or 'right')
    """
    # Move to location first (profiled)
    human_like_move(x, y, profile=profile)
    
    # Optional deliberate misclick near the target before correcting.
    # This simulates a small human mistake with an immediate adjustment.
    if ANTI_DETECTION_ENABLED and random.random() < CURSOR_MISCLICK_CHANCE:
        miss_dx = random.randint(-30, 30)
        miss_dy = random.randint(-30, 30)
        miss_x = x + miss_dx
        miss_y = y + miss_dy
        _log_anti(f"misclick[{profile}] near target ({x},{y}) -> ({miss_x},{miss_y})")
        human_like_move(miss_x, miss_y, profile=profile)
        _sleep_jittered(0.06, 0.2)
        if button == 'left':
            pyautogui.click()
        else:
            pyautogui.rightClick()
        _sleep_jittered(0.08, 0.22)
        # Then fall through to the proper, corrected click.
    
    # Small random delay before clicking
    _sleep_jittered(0.08, 0.18)
    
    # Click
    if button == 'left':
        pyautogui.click()
    else:
        pyautogui.rightClick()
    
    # Small random delay after clicking
    _sleep_jittered(0.05, 0.12)

def maybe_idle(label=""):
    """
    Occasionally pause to break perfect loops.
    
    Args:
        label: optional label for debugging/logging
    """
    if not ANTI_DETECTION_ENABLED:
        return
    if random.random() < IDLE_CHANCE:
        duration = random.uniform(*IDLE_DURATION_RANGE)
        _log_anti(f"idle pause {duration:.2f}s ({label})")
        time.sleep(duration)
    elif random.random() < THINKING_PAUSE_CHANCE:
        duration = random.uniform(*THINKING_PAUSE_RANGE)
        _log_anti(f"thinking pause {duration:.2f}s ({label})")
        time.sleep(duration)

def describe_anti_detection():
    """
    Returns a human-readable summary of anti-detection settings.
    """
    if not ANTI_DETECTION_ENABLED:
        return "Anti-detection: disabled"
    return (
        "Anti-detection enabled: "
        f"cursor jitter ±{CURSOR_JITTER_PX}px, "
        f"overshoot {int(CURSOR_OVERSHOOT_CHANCE*100)}%, "
        f"micro-stutter {int(CURSOR_MICRO_STUTTER_CHANCE*100)}%, "
        f"move duration {MOVE_DURATION_RANGE[0]:.2f}-{MOVE_DURATION_RANGE[1]:.2f}s, "
        f"action jitter ±{ACTION_JITTER_RANGE[0]:.2f}/{ACTION_JITTER_RANGE[1]:.2f}s, "
        f"idle {int(IDLE_CHANCE*100)}% ({IDLE_DURATION_RANGE[0]:.1f}-{IDLE_DURATION_RANGE[1]:.1f}s), "
        f"thinking {int(THINKING_PAUSE_CHANCE*100)}% ({THINKING_PAUSE_RANGE[0]:.1f}-{THINKING_PAUSE_RANGE[1]:.1f}s), "
        f"capture delay {CAPTURE_DELAY_RANGE[0]:.2f}-{CAPTURE_DELAY_RANGE[1]:.2f}s"
    )

def jitter_sleep(base_seconds):
    """
    Sleep with a small random jitter added/subtracted.
    
    Args:
        base_seconds: desired base sleep duration
    """
    if not ANTI_DETECTION_ENABLED:
        time.sleep(base_seconds)
        return
    jitter = random.uniform(-ACTION_JITTER_RANGE[0], ACTION_JITTER_RANGE[1])
    _log_anti(f"sleep {base_seconds:.2f}s jitter {jitter:+.2f}s")
    time.sleep(max(0, base_seconds + jitter))

def _sleep_jittered(min_s, max_s):
    """
    Sleep for random duration within range and apply anti-detection jitter.
    """
    duration = random.uniform(min_s, max_s)
    jitter_sleep(duration)

def _tiny_pause():
    """
    Very small pause to avoid robotic instant moves.
    """
    time.sleep(random.uniform(0.01, 0.04))

def _maybe_capture_delay():
    """
    Random tiny delay before a screen grab to avoid perfect polling cadence.
    """
    if not ANTI_DETECTION_ENABLED:
        return
    delay = random.uniform(*CAPTURE_DELAY_RANGE)
    if delay > 0:
        _log_anti(f"capture delay {delay:.2f}s")
        time.sleep(delay)


# Override: stricter shape rejection to filter players/windows/barrels
def _shape_rejection_reason(contour, w, h, area):
    """
    EXTREME shape filtering to reject anything that's not clearly a tree.
    Trees in OSRS have specific characteristics:
    - Taller than wide (aspect ratio < 0.65 typically)
    - Irregular, jagged edges
    - Not perfectly rectangular or circular
    - Located in the "middle ground" of the screen (not at edges where UI is)
    
    Returns a string reason if it should be rejected, or None to keep it.
    """
    # Skip if too small to analyze
    if area < 100:
        return "Too small for shape analysis"
    
    # Calculate basic shape properties
    aspect_ratio = w / h if h > 0 else 0
    
    # --- CRITICAL: Trees are ALWAYS taller than wide ---
    # This is the most important filter - reject anything wide
    # Relaxed from 0.65 to 0.85 to allow slightly wider trees
    if aspect_ratio > 0.85:
        return f"Too wide for tree (aspect={aspect_ratio:.2f})"
    
    # Calculate shape complexity metrics
    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    if hull_area > 0:
        solidity = area / hull_area
    else:
        solidity = 1.0
    
    perimeter = cv2.arcLength(contour, True)
    if perimeter > 0:
        circularity = (4 * np.pi * area) / (perimeter * perimeter + 1e-5)
    else:
        circularity = 0
    
    # Approximate polygon to count vertices
    epsilon = 0.02 * perimeter
    approx = cv2.approxPolyDP(contour, epsilon, True)
    vertices = len(approx)
    
    # Calculate bounding box area
    box_area = w * h
    
    # Very "hole-y" or wispy shapes (grass, shadows etc.)
    if solidity < 0.35:
        return f"Low solidity ({solidity:.2f})"
    
    # Extremely sparse shapes inside their box (thin UI lines / planks).
    extent = area / box_area if box_area > 0 else 0
    if extent < 0.10:
        return f"Low extent ({extent:.2f})"
    
    # --- TREE-SPECIFIC FILTERS ---
    
    # 1. Reject perfectly rectangular objects (windows, doors, furniture) - RELAXED
    # Only reject if very rectangular AND small
    if vertices >= 4 and vertices <= 8 and solidity > 0.90 and area < 2000:
        return f"Perfectly rectangular (vertices={vertices}, solidity={solidity:.2f})"
    
    # 2. Reject very circular objects (barrels, heads, round furniture) - RELAXED
    # Only reject if very circular AND small
    if circularity > 0.80 and area < 2000:
        return f"Too circular (circularity={circularity:.2f})"
    
    # 3. Reject objects that fill their bounding box too much (UI elements) - RELAXED
    # Only reject if fills box AND small
    if box_area > 0 and (area / box_area) > 0.90 and area < 1500:
        return f"Too solid/fills bounding box (area/box={area/box_area:.2f})"
    
    # 4. Reject objects that are too "compact" (likely furniture) - RELAXED
    if solidity > 0.95 and area < 3000:  # Only reject if very compact AND small
        return f"Too compact (solidity={solidity:.2f})"
    
    # 5. Reject objects with very simple shapes (few vertices = man-made objects) - RELAXED
    if vertices < 4 and area > 1000:  # Only reject if very few vertices AND large
        return f"Too simple (vertices={vertices})"
    
    # 6. Reject objects that are too "smooth" (likely furniture) - RELAXED
    if perimeter > 0:
        # Trees have complex edges, so perimeter/area ratio should be higher
        complexity = perimeter / (area + 1e-5)
        if complexity < 0.05 and area > 2000:  # Only reject if very smooth AND large
            return f"Too smooth (complexity={complexity:.2f})"
    
    # 7. Height/width sanity check - trees should be reasonably sized - RELAXED
    if h < 20 or h > 450:  # More lenient height range
        return f"Height out of tree range (h={h})"
    
    # 11. LADDERS: Very tall and very narrow (aspect ratio < 0.3, narrow width)
    if aspect_ratio < 0.3 and w < 25:
        return f"Ladder (very tall and narrow, aspect={aspect_ratio:.2f}, w={w})"
    
    # 12. LADDERS: Tall with very narrow width
    if h > 80 and w < 20:
        return f"Ladder (tall and very narrow, h={h}, w={w})"
    
    # 13. LADDERS: Tall with low area (thin vertical lines)
    if h > 60 and area < 800 and w < 30:
        return f"Ladder (tall, thin, low area, h={h}, w={w}, area={int(area)})"
    
    # 14. Very small objects (more aggressive)
    if area < 1000 and (w < 60 or h < 60):
        return f"Too small (area={int(area)}, w={w}, h={h})"
    
    # 15. Extremely thin objects (ladders, poles, thin structures)
    if w < 15 and h > 40:
        return f"Extremely thin (ladder/pole, w={w}, h={h})"
    
    # 8. Round-ish compact blobs -> barrels, posts, circular props.
    if circularity > 0.60 and extent > 0.50 and area < 9000:
        return f"Round/compact blob (circ={circularity:.2f}, extent={extent:.2f})"
    
    # 9. Tall slender blobs -> players / NPCs / sign posts.
    if aspect_ratio < 0.75 and h > 45 and 0.25 < extent < 0.75 and 0.45 < solidity < 0.97 and area < 12000:
        return (
            f"Tall/slender blob (aspect={aspect_ratio:.2f}, h={h}, "
            f"extent={extent:.2f}, solidity={solidity:.2f})"
        )
    
    # 10. Very wide and not very tall -> benches, tables, long rails.
    if aspect_ratio > 2.0 and area < 15000 and h < 80:
        return f"Too wide for tree (aspect={aspect_ratio:.2f}, h={h}, area={int(area)})"
    
    # 11. Massive solid rectangles inside houses (floors/walls).
    if area > 18000 and extent > 0.30 and solidity > 0.55:
        return (
            f"Huge solid rectangle (area={int(area)}, extent={extent:.2f}, "
            f"solidity={solidity:.2f})"
        )
    
    # If none of the above matched, we accept the shape as "tree-ish" enough.
    return None


def capture_region(game_area):
    """
    Captures a rectangular screen region and returns a BGRA numpy array.
    
    Args:
        game_area: Dict with 'top', 'left', 'width', 'height'
    """
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(game_area))
    return screen_img


def read_text_ocr(game_area, psm=7):
    """
    Uses OCR (pytesseract) to read text from a small HUD region.
    
    Args:
        game_area: Dict with 'top', 'left', 'width', 'height'
        psm: Tesseract page segmentation mode (7 = single text line)
    
    Returns:
        Raw text string, or empty string if OCR is not available.
    """
    if not _HAS_OCR:
        return ""
    # Small capture delay like other grabs to avoid perfect cadence.
    _maybe_capture_delay()
    img_bgra = capture_region(game_area)
    # Convert BGRA -> RGB for pytesseract
    img_rgb = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2RGB)
    pil_img = Image.fromarray(img_rgb)
    try:
        text = pytesseract.image_to_string(pil_img, config=f"--psm {psm}")
    except Exception:
        return ""
    return text
