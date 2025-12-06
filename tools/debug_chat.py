"""
Chat Area Debug Tool
Helps you visualize what the bot sees in the chat area and debug the
"can't light fire here" message detection with multi-scale matching.
"""
import sys
import os
import cv2
import numpy as np
import mss
import pyautogui

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
from firemaking import CHAT_AREA, CANT_FIRE_TEMPLATE_PATH

# Create debug output directory
DEBUG_OUTPUT_DIR = "debug"
if not os.path.exists(DEBUG_OUTPUT_DIR):
    os.makedirs(DEBUG_OUTPUT_DIR)


def capture_chat_area():
    """Capture and save the chat area so you can see what the bot sees."""
    print("=" * 60)
    print("Chat Area Debug Tool")
    print("=" * 60)
    print(f"\nCurrent Chat Area: {CHAT_AREA}")
    print("\nCapturing chat area...")

    with mss.mss() as sct:
        screen_img = np.array(sct.grab(CHAT_AREA))
        screen_bgr = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)

    debug_path = os.path.join(DEBUG_OUTPUT_DIR, "chat_area_debug.png")
    cv2.imwrite(debug_path, screen_bgr)
    print(f"✓ Saved chat area to: {debug_path}")
    print(f"  Size: {screen_bgr.shape[1]}x{screen_bgr.shape[0]} pixels")
    print(f"  Channels: {screen_bgr.shape[2]}")
    print("\n⚠ Check the image - it should show the chat area where messages appear.")
    print("   If the chat area is wrong, use tools/calibrate_chat.py to recalibrate.")

    return screen_bgr


def test_cant_fire_template_matching(screen_bgr):
    """Test template matching for the 'can't fire' message with different thresholds and scales."""
    print("\n" + "=" * 60)
    print("Testing 'Can't Fire' Template Matching")
    print("=" * 60)

    if not os.path.exists(CANT_FIRE_TEMPLATE_PATH):
        print(f"✖ Can't fire template not found: {CANT_FIRE_TEMPLATE_PATH}")
        print("\nTo create the template:")
        print("1. Trigger the 'can't light a fire here' message.")
        print("2. Capture the chat message using: python tools/capture_template.py")
        print("3. Save it as: cant_fire.png in the templates folder")
        return None, None, {}

    # Load template (handle RGBA/grayscale)
    template = cv2.imread(CANT_FIRE_TEMPLATE_PATH, cv2.IMREAD_UNCHANGED)
    if template is None:
        print(f"✖ Could not load can't fire template: {CANT_FIRE_TEMPLATE_PATH}")
        return None, None, {}

    if len(template.shape) == 2:  # grayscale
        template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
    elif template.shape[2] == 4:  # RGBA
        template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)

    print(f"Template shape: {template.shape}")
    print(f"Chat area shape: {screen_bgr.shape}")
    # Focus analysis on bottom 40% of chat where new messages appear
    h = screen_bgr.shape[0]
    start_y = int(h * 0.6)
    screen_bgr = screen_bgr[start_y:, :]

    thresholds = [0.4, 0.45, 0.5, 0.55, 0.6, 0.65]
    scales = [1.0, 0.95, 1.05, 0.9]
    matches_by_threshold = {}

    for threshold in thresholds:
        matches_by_threshold[threshold] = []
        for scale in scales:
            scaled_tpl = template
            if scale != 1.0:
                scaled_tpl = cv2.resize(
                    template,
                    (max(1, int(template.shape[1] * scale)), max(1, int(template.shape[0] * scale))),
                    interpolation=cv2.INTER_AREA,
                )
            result = cv2.matchTemplate(screen_bgr, scaled_tpl, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)

            for pt in zip(*locations[::-1]):  # Switch x and y coordinates
                matches_by_threshold[threshold].append({
                    "x": pt[0],
                    "y": pt[1],
                    "confidence": float(result[pt[1], pt[0]]),
                    "scale": scale,
                })

        matches = matches_by_threshold[threshold]
        if matches:
            print(f"  Threshold {threshold:.2f}: Found {len(matches)} match(es)")
            for i, match in enumerate(matches):
                print(
                    f"    Match {i+1}: Position ({match['x']}, {match['y']}), "
                    f"Confidence: {match['confidence']:.3f}, Scale: {match['scale']:.2f}"
                )
        else:
            print(f"  Threshold {threshold:.2f}: No matches found")

    # Find the best threshold (lowest threshold with matches)
    best_threshold = None
    for threshold in sorted(thresholds):
        if matches_by_threshold[threshold]:
            best_threshold = threshold
            break

    if best_threshold is None:
        print("\n⚠ No matches found at any threshold!")
        print("   Possible issues:")
        print("   1. The template doesn't match the actual error message.")
        print("   2. The chat area doesn't include where the message appears.")
        print("   3. The message hasn't appeared yet (trigger it first).")
        print("   4. The template needs to be recaptured.")
    else:
        print(f"\n✓ Best threshold: {best_threshold:.2f} (found {len(matches_by_threshold[best_threshold])} match(es))")

    return template, best_threshold, matches_by_threshold


def visualize_matches(screen_bgr, template, threshold, matches_by_threshold):
    """Visualize template matches on the chat area."""
    if template is None:
        print("\n⚠ Cannot visualize - template not loaded")
        return

    vis_img = screen_bgr.copy()

    colors = [
        (0, 255, 0),
        (0, 255, 255),
        (255, 165, 0),
        (0, 165, 255),
        (255, 0, 255),
        (255, 0, 0),
    ]

    threshold_list = sorted(matches_by_threshold.keys())

    for idx, threshold in enumerate(threshold_list):
        matches = matches_by_threshold[threshold]
        color = colors[idx % len(colors)]

        for match in matches:
            x, y = match["x"], match["y"]
            conf = match["confidence"]
            scale = match.get("scale", 1.0)

            h, w = template.shape[:2]
            if scale != 1.0:
                w = max(1, int(w * scale))
                h = max(1, int(h * scale))
            cv2.rectangle(vis_img, (x, y), (x + w, y + h), color, 2)

            text = f"{conf:.2f} (s:{scale:.2f})"
            cv2.putText(vis_img, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    # Draw legend
    legend_y = 20
    for idx, threshold in enumerate(threshold_list):
        color = colors[idx % len(colors)]
        matches = matches_by_threshold[threshold]
        text = f"Threshold {threshold:.2f}: {len(matches)} match(es)"
        cv2.putText(vis_img, text, (10, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        legend_y += 25

    vis_path = os.path.join(DEBUG_OUTPUT_DIR, "chat_matches_debug.png")
    cv2.imwrite(vis_path, vis_img)
    print(f"\n✓ Saved visualization to: {vis_path}")
    print("   Colors correspond to thresholds (lower = more permissive).")


def main():
    print("=" * 60)
    print("Chat Debug Tool")
    print("=" * 60)
    print("\nThis tool helps you debug why the bot might not be detecting")
    print("the 'can't light fire here' message in chat.")
    print("\nMake sure:")
    print("  - RuneScape is open and the chat is visible")
    print("  - You have tried to light a fire in an invalid location")
    print("  - The error message is visible in chat")
    print("  - You have created the cant_fire.png template")

    input("\nPress ENTER to start debugging...")

    screen_bgr = capture_chat_area()
    template, best_threshold, matches_by_threshold = test_cant_fire_template_matching(screen_bgr)
    visualize_matches(screen_bgr, template, best_threshold, matches_by_threshold)

    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)
    print(f"1. Check '{os.path.join(DEBUG_OUTPUT_DIR, 'chat_area_debug.png')}' - does it show the chat area?")
    print(f"2. Check '{os.path.join(DEBUG_OUTPUT_DIR, 'chat_matches_debug.png')}' - are there any colored boxes?")
    print("3. If chat area is wrong, run: python tools/calibrate_chat.py")
    print("4. If no matches found:")
    print("   - Make sure the error message is visible in chat")
    print("   - Recapture the template: python tools/capture_template.py")
    print("   - Make sure the template matches the exact message text")
    print("5. If matches are found but bot still doesn't detect, lower thresholds slightly in firemaking.py.")


if __name__ == "__main__":
    main()
