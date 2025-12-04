"""
Test different thresholds to find the best one for log detection.
This helps reduce false positives.
"""
import sys
import os
# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
import bot_utils
from woodcutter import INVENTORY_AREA, LOG_ICON_PATH

print("=" * 60)
print("Threshold Testing Tool")
print("=" * 60)
print("\nTesting different thresholds to find the best balance")
print("between detecting logs and avoiding false positives.\n")

thresholds = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7]

print("Threshold | Found | Position")
print("-" * 60)

for threshold in thresholds:
    log_pos = bot_utils.find_image(LOG_ICON_PATH, threshold=threshold, game_area=INVENTORY_AREA)
    count = bot_utils.count_inventory_items(LOG_ICON_PATH, INVENTORY_AREA, threshold=threshold)
    
    if log_pos:
        print(f"  {threshold:.2f}   |  ✓    | {log_pos} (count: {count})")
    else:
        print(f"  {threshold:.2f}   |  ✗    | Not found (count: {count})")

print("\n" + "=" * 60)
print("Recommendation:")
print("=" * 60)
print("Choose the highest threshold that still finds your log.")
print("Higher threshold = fewer false positives, but might miss logs")
print("if lighting/conditions change slightly.")
print("\nIf you have 1 log but count shows many, try threshold 0.9 or 0.95")

