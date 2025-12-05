"""
Player behavior preferences (safe defaults).
Includes anti-detection tuning knobs for human-like behavior.
"""

# Preferred tree type (None = auto-select based on level in player_stats)
PREFERRED_TREE_TYPE = "marker"

# Log handling
LOG_DISPOSAL_METHOD = "bank"  # "bank" or "drop"

# Break behavior
ENABLE_BREAKS = True
BREAK_CHANCE = 0.02         # 2% chance to take a break each loop (reduced from 10%)
BREAK_DURATION_MIN = 30     # seconds
BREAK_DURATION_MAX = 120    # seconds

# Anti-detection behavior (human-like imperfections)
ANTI_DETECTION_ENABLED = True

# Mouse movement / clicks
CURSOR_JITTER_PX = 2               # small random offset on moves/clicks
CURSOR_OVERSHOOT_CHANCE = 0.25     # chance to overshoot then settle on target
CURSOR_MICRO_STUTTER_CHANCE = 0.20 # chance to add a tiny pre-click wiggle
MOVE_DURATION_RANGE = (0.08, 0.35) # base move duration range (seconds)

# Timing imperfections
ACTION_JITTER_RANGE = (0.04, 0.18) # random added/subtracted to sleeps
IDLE_CHANCE = 0.08                 # chance to pause briefly in loops
IDLE_DURATION_RANGE = (0.3, 2.0)   # short idle duration range (seconds)
THINKING_PAUSE_CHANCE = 0.04       # occasional longer hesitation
THINKING_PAUSE_RANGE = (2.0, 4.0)

# Screen capture pacing
CAPTURE_DELAY_RANGE = (0.00, 0.12) # random sleep before screen grabs

# Convenience wrappers to align with existing code paths
try:
    from config import player_stats
except Exception:
    player_stats = None

def get_available_tree_types():
    """
    Delegate to player_stats if available to avoid import errors in bots.
    """
    if player_stats and hasattr(player_stats, "get_available_tree_types"):
        return player_stats.get_available_tree_types()
    return []
