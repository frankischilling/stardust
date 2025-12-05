"""
Visualize the minimap capture region and optional path offsets; helps calibrate
DEFAULT_MINIMAP_AREA so the center aligns with your player dot.

Example:
  python tools/debug_pathfinding.py --offset -40,-60 --offset -80,-120
Outputs debug/minimap_debug.png with the minimap crop, center dot, and offset markers.
"""

import argparse
import os
import sys
from typing import List, Tuple

import cv2
import mss
import numpy as np

# Allow imports when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pathfinding_utils lives in scripts/
from scripts.pathfinding_utils import (
    DEFAULT_MINIMAP_AREA,
    clamp_to_minimap,
    get_minimap_center,
)


def _capture_minimap(area: dict) -> np.ndarray:
    with mss.mss() as sct:
        img = np.array(sct.grab(area))
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def _parse_offsets(raw_offsets: List[str]) -> List[Tuple[int, int]]:
    offsets: List[Tuple[int, int]] = []
    for raw in raw_offsets:
        try:
            dx_str, dy_str = raw.split(",")
            offsets.append((int(dx_str.strip()), int(dy_str.strip())))
        except Exception:
            raise argparse.ArgumentTypeError(f"Invalid offset '{raw}'. Use format dx,dy (e.g., -40,-60).")
    return offsets


def _parse_area(raw_area: str):
    try:
        left, top, width, height = [int(p.strip()) for p in raw_area.split(",")]
        return {"left": left, "top": top, "width": width, "height": height}
    except Exception:
        raise argparse.ArgumentTypeError(
            f"Invalid area '{raw_area}'. Use left,top,width,height (e.g., 1610,15,280,230)."
        )


def main():
    parser = argparse.ArgumentParser(description="Capture minimap region and overlay optional offsets.")
    parser.add_argument(
        "--output",
        default=os.path.join("debug", "minimap_debug.png"),
        help="Output image path (default: debug/minimap_debug.png)",
    )
    parser.add_argument(
        "--area",
        default=None,
        help="Override minimap area as left,top,width,height (default uses pathfinding_utils.DEFAULT_MINIMAP_AREA).",
    )
    parser.add_argument(
        "--offset",
        action="append",
        default=[],
        help="Offset in pixels relative to minimap center (dx,dy). Repeatable.",
    )
    args = parser.parse_args()

    area = _parse_area(args.area) if args.area else DEFAULT_MINIMAP_AREA
    offsets = _parse_offsets(args.offset)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    img = _capture_minimap(area)

    center_x, center_y = get_minimap_center(area)
    center_local = (int(center_x - area["left"]), int(center_y - area["top"]))

    # Outline the capture box to confirm bounds
    cv2.rectangle(img, (1, 1), (area["width"] - 2, area["height"] - 2), (0, 0, 255), 1)

    # Crosshair at center
    cv2.line(img, (center_local[0], 0), (center_local[0], area["height"]), (0, 0, 255), 1)
    cv2.line(img, (0, center_local[1]), (area["width"], center_local[1]), (0, 0, 255), 1)

    # Draw center point
    cv2.circle(img, center_local, 4, (0, 0, 255), thickness=-1)
    cv2.putText(img, "center", (center_local[0] + 6, center_local[1] + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)

    # Draw offset targets
    for idx, (dx, dy) in enumerate(offsets):
        tx, ty = clamp_to_minimap(center_x + dx, center_y + dy, area)
        local_x = int(tx - area["left"])
        local_y = int(ty - area["top"])
        cv2.circle(img, (local_x, local_y), 4, (0, 255, 0), thickness=-1)
        cv2.putText(
            img,
            f"{idx+1}:{dx},{dy}",
            (local_x + 6, local_y + 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

    cv2.imwrite(args.output, img)
    print(f"Saved minimap debug image to {args.output}")
    print(f"Minimap area: {area}")
    print(f"Center (screen): ({center_x}, {center_y})")
    if offsets:
        for idx, (dx, dy) in enumerate(offsets):
            tx, ty = clamp_to_minimap(center_x + dx, center_y + dy, area)
            print(f"  Offset {idx+1}: ({dx},{dy}) -> target screen ({tx},{ty})")


if __name__ == "__main__":
    main()

