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


def _log_anti(msg):
    """Lightweight anti-detection runtime log."""
    if ANTI_DETECTION_ENABLED:
        print(f"[anti-detection] {msg}")

def find_all_colors(color_lower, color_upper, game_area, min_area=400, max_area=50000,
                    min_aspect_ratio=0.4, max_aspect_ratio=2.5, min_height=30,
                    max_width=300, max_height=400, exclude_ui_left=None, 
                    exclude_ui_bottom=None, exclude_ui_right_edge=None):
    """
    Finds ALL valid objects in the game area by HSV color range.
    
    Args:
        Same as find_color
    
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
    
    # Create mask for color range
    mask = cv2.inRange(screen_hsv, np.array(color_lower), np.array(color_upper))
    
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
        
        # Check maximum width/height (filters large UI panels)
        if w > max_width or h > max_height:
            continue
        
        # Check aspect ratio
        aspect_ratio = w / h
        if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
            continue
        
        # Filter out square/rectangular objects (furniture, chairs, etc.)
        # Trees are usually taller than wide, not square
        # BUT: Trees with canopies can appear square, so only filter if it's small AND short
        # Also: Far-away trees can be small, so be more lenient with very small objects
        # If object is roughly square (0.8 to 1.2) and small AND short, it's likely furniture
        # But allow very small objects (area < 400) to pass through - they might be far-away trees
        if 0.8 <= aspect_ratio <= 1.2 and area >= 400 and area < 3000 and h < 60:
            continue  # Likely furniture (chairs, tables, etc.) - small square objects (but not tiny)
        
        # Filter out very wide objects (furniture is often wide, trees are tall)
        # BUT: Trees with wide canopies can have aspect_ratio > 1.5, so only filter if small AND short
        # Also: Far-away trees can be small, so be more lenient with very small objects
        if aspect_ratio > 1.5 and area >= 400 and area < 3000 and h < 60:
            continue  # Likely furniture (benches, tables, etc.) - small wide objects (but not tiny)
        
        # Trees are usually taller than wide - prefer objects with height > width
        # But allow some flexibility for different tree shapes
        # If it's very wide and not very tall, it's likely furniture
        # But allow very small objects (area < 400) to pass - might be far-away trees
        if w > h * 1.3 and h < 50 and area >= 400:
            continue  # Too wide and short - likely furniture (but not tiny objects)
        
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
               max_width=300, max_height=400, exclude_ui_left=None, 
               exclude_ui_bottom=None, exclude_ui_right_edge=None):
    """
    Finds objects in the game area by HSV color range.
    
    Args:
        color_lower: Lower HSV bound tuple (H, S, V)
        color_upper: Upper HSV bound tuple (H, S, V)
        game_area: Dict with 'top', 'left', 'width', 'height'
        min_area: Minimum contour area to consider
        max_area: Maximum contour area to consider
        min_aspect_ratio: Minimum width/height ratio
        max_aspect_ratio: Maximum width/height ratio
        min_height: Minimum height in pixels
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        exclude_ui_left: X coordinate threshold - exclude objects to the right of this
    
    Returns:
        Tuple (x, y) of center point of largest valid object, or None if not found
    """
    # Small random delay before capture to avoid perfectly periodic sampling
    _maybe_capture_delay()
    # Capture game area
    with mss.mss() as sct:
        screen_img = np.array(sct.grab(game_area))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    
    # Convert to HSV
    screen_hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)
    
    # Create mask for color range
    mask = cv2.inRange(screen_hsv, np.array(color_lower), np.array(color_upper))
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
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
        
        # Check maximum width/height (filters large UI panels)
        if w > max_width or h > max_height:
            continue
        
        # Check aspect ratio
        aspect_ratio = w / h
        if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
            continue
        
        # Filter out square/rectangular objects (furniture, chairs, etc.)
        # Trees are usually taller than wide, not square
        # BUT: Trees with canopies can appear square, so only filter if it's small AND short
        # Also: Far-away trees can be small, so be more lenient with very small objects
        # If object is roughly square (0.8 to 1.2) and small AND short, it's likely furniture
        # But allow very small objects (area < 400) to pass through - they might be far-away trees
        if 0.8 <= aspect_ratio <= 1.2 and area >= 400 and area < 3000 and h < 60:
            continue  # Likely furniture (chairs, tables, etc.) - small square objects (but not tiny)
        
        # Filter out very wide objects (furniture is often wide, trees are tall)
        # BUT: Trees with wide canopies can have aspect_ratio > 1.5, so only filter if small AND short
        # Also: Far-away trees can be small, so be more lenient with very small objects
        if aspect_ratio > 1.5 and area >= 400 and area < 3000 and h < 60:
            continue  # Likely furniture (benches, tables, etc.) - small wide objects (but not tiny)
        
        # Trees are usually taller than wide - prefer objects with height > width
        # But allow some flexibility for different tree shapes
        # If it's very wide and not very tall, it's likely furniture
        # But allow very small objects (area < 400) to pass - might be far-away trees
        if w > h * 1.3 and h < 50 and area >= 400:
            continue  # Too wide and short - likely furniture (but not tiny objects)
        
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
        
        valid_contours.append((contour, area))
    
    if not valid_contours:
        return None
    
    # Sort by area (largest first) - prioritize larger objects
    valid_contours.sort(key=lambda x: x[1], reverse=True)
    
    # Get center of largest valid contour
    contour = valid_contours[0][0]
    M = cv2.moments(contour)
    if M["m00"] == 0:
        return None
    
    # Calculate center relative to game area
    cX = int(M["m10"] / M["m00"])
    cY = int(M["m01"] / M["m00"])
    
    # Convert to absolute screen coordinates
    abs_x = cX + game_area['left']
    abs_y = cY + game_area['top']
    
    return (abs_x, abs_y)

def visualize_color_detection(color_lower, color_upper, game_area, min_area=400, max_area=50000,
                              min_aspect_ratio=0.4, max_aspect_ratio=2.5, min_height=30,
                              max_width=300, max_height=400, exclude_ui_left=None,
                              exclude_ui_bottom=None, exclude_ui_right_edge=None,
                              output_dir="debug", save_images=True):
    """
    Visualizes what the bot detects when searching for objects by color.
    Creates debug images showing the detection process.
    
    Args:
        Same parameters as find_color()
        output_dir: Directory to save debug images
        save_images: Whether to save images to disk
    
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
    
    # Create mask for color range
    mask = cv2.inRange(screen_hsv, np.array(color_lower), np.array(color_upper))
    
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
        if w > max_width or h > max_height:
            all_contours[-1]['reason'] = f'Too large ({w}x{h} > {max_width}x{max_height})'
            invalid_contours.append(all_contours[-1])
            continue
        
        aspect_ratio = w / h
        if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
            all_contours[-1]['reason'] = f'Aspect ratio out of range ({aspect_ratio:.2f})'
            invalid_contours.append(all_contours[-1])
            continue
        
        # Filter out square/rectangular objects (furniture, chairs, etc.)
        # Trees are usually taller than wide, not square
        # BUT: Trees with canopies can appear square, so only filter if it's small AND short
        # Also: Far-away trees can be small, so be more lenient with very small objects
        # If object is roughly square (0.8 to 1.2) and small AND short, it's likely furniture
        # But allow very small objects (area < 400) to pass through - they might be far-away trees
        if 0.8 <= aspect_ratio <= 1.2 and area >= 400 and area < 3000 and h < 60:
            all_contours[-1]['reason'] = f'Square object (likely furniture, aspect={aspect_ratio:.2f}, area={int(area)}, h={h})'
            invalid_contours.append(all_contours[-1])
            continue
        
        # Filter out very wide objects (furniture is often wide, trees are tall)
        # BUT: Trees with wide canopies can have aspect_ratio > 1.5, so only filter if small AND short
        # Also: Far-away trees can be small, so be more lenient with very small objects
        if aspect_ratio > 1.5 and area >= 400 and area < 3000 and h < 60:
            all_contours[-1]['reason'] = f'Wide object (likely furniture, aspect={aspect_ratio:.2f}, area={int(area)}, h={h})'
            invalid_contours.append(all_contours[-1])
            continue
        
        # Trees are usually taller than wide - prefer objects with height > width
        # But allow some flexibility for different tree shapes
        # If it's very wide and not very tall, it's likely furniture
        # But allow very small objects (area < 400) to pass - might be far-away trees
        if w > h * 1.3 and h < 50 and area >= 400:
            all_contours[-1]['reason'] = f'Too wide and short (likely furniture, {w}x{h}, area={int(area)})'
            invalid_contours.append(all_contours[-1])
            continue
        
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
            'exclude_ui_right_edge': exclude_ui_right_edge
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
    
    # Template matching
    result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    if max_val < threshold:
        return None
    
    # Get center of match
    template_h, template_w = template.shape[:2]
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

def human_like_move(x, y):
    """
    Moves mouse to coordinates with human-like behavior (slight randomness).
    
    Args:
        x: Target X coordinate
        y: Target Y coordinate
    """
    # Add small random offset to make movement more human-like
    offset_x = random.uniform(-CURSOR_JITTER_PX, CURSOR_JITTER_PX)
    offset_y = random.uniform(-CURSOR_JITTER_PX, CURSOR_JITTER_PX)
    
    target_x = int(x + offset_x)
    target_y = int(y + offset_y)
    if ANTI_DETECTION_ENABLED:
        _log_anti(f"move target=({x},{y}) jitter=({target_x},{target_y})")

    # Optional overshoot then settle
    if ANTI_DETECTION_ENABLED and random.random() < CURSOR_OVERSHOOT_CHANCE:
        overshoot_x = target_x + random.randint(-6, 6)
        overshoot_y = target_y + random.randint(-6, 6)
        _log_anti(f"overshoot to ({overshoot_x},{overshoot_y})")
        pyautogui.moveTo(overshoot_x, overshoot_y,
                         duration=random.uniform(*MOVE_DURATION_RANGE))
        _tiny_pause()

    # Occasional micro-stutter before final move
    if ANTI_DETECTION_ENABLED and random.random() < CURSOR_MICRO_STUTTER_CHANCE:
        wiggle_x = target_x + random.randint(-3, 3)
        wiggle_y = target_y + random.randint(-3, 3)
        _log_anti(f"micro-stutter to ({wiggle_x},{wiggle_y})")
        pyautogui.moveTo(wiggle_x, wiggle_y,
                         duration=random.uniform(0.03, 0.07))
        _tiny_pause()
    
    # Final move with jittered duration
    pyautogui.moveTo(
        target_x,
        target_y,
        duration=random.uniform(*MOVE_DURATION_RANGE)
    )

def human_like_click(x, y, button='left'):
    """
    Clicks at coordinates with human-like behavior (random delays, slight movement).
    
    Args:
        x: Target X coordinate
        y: Target Y coordinate
        button: Mouse button ('left' or 'right')
    """
    # Move to location first
    human_like_move(x, y)
    
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
