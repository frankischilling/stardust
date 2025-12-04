"""
Player Configuration File
Input your character's preferences and bot behavior settings here.
For skill levels, see player_stats.py
"""
import player_stats

# Import stats from player_stats.py
# This keeps stats separate from preferences for easier management
WOODCUTTING_LEVEL = player_stats.WOODCUTTING_LEVEL
ATTACK_LEVEL = player_stats.ATTACK_LEVEL
STRENGTH_LEVEL = player_stats.STRENGTH_LEVEL
DEFENCE_LEVEL = player_stats.DEFENCE_LEVEL
HITPOINTS_LEVEL = player_stats.HITPOINTS_LEVEL
RANGED_LEVEL = player_stats.RANGED_LEVEL
PRAYER_LEVEL = player_stats.PRAYER_LEVEL
MAGIC_LEVEL = player_stats.MAGIC_LEVEL
MINING_LEVEL = player_stats.MINING_LEVEL
FISHING_LEVEL = player_stats.FISHING_LEVEL
COOKING_LEVEL = player_stats.COOKING_LEVEL
FIREMAKING_LEVEL = player_stats.FIREMAKING_LEVEL
COMBAT_LEVEL = player_stats.COMBAT_LEVEL

# --- Available Actions Based on Stats ---
# These functions use your stats from player_stats.py

def get_available_tree_types():
    """
    Returns a list of tree types the player can cut based on their Woodcutting level.
    """
    return player_stats.get_available_tree_types()

def get_recommended_tree_type():
    """
    Returns the best tree type the player can cut based on their level.
    Prioritizes higher XP trees that the player can access.
    """
    return player_stats.get_best_available_tree()

# --- Player Preferences ---

# Preferred tree type (leave as None to auto-select based on level)
# Options: "regular", "oak", "willow", "teak", "maple", "mahogany", "yew", "magic", or None
PREFERRED_TREE_TYPE = None  # None = auto-select based on level

# Bank location preference (for future pathfinding)
# Options: "nearest", "varrock", "lumbridge", "falador", "seers", "catherby", etc.
PREFERRED_BANK = "nearest"

# --- Equipment ---
# What items you have equipped/carried (for future features)

HAS_AXE = True              # Do you have an axe? (Required for woodcutting)
AXE_TYPE = "bronze"         # Type of axe: "bronze", "iron", "steel", "mithril", "adamant", "rune", "dragon"
                            # Higher tier axes cut faster

# --- Bot Behavior Settings ---

# Should the bot take breaks? (Makes it more human-like)
ENABLE_BREAKS = True

# Break frequency (0.0 to 1.0) - 0.1 = 10% chance of taking a break each cycle
BREAK_CHANCE = 0.1

# Break duration range (in seconds)
BREAK_DURATION_MIN = 30
BREAK_DURATION_MAX = 120

# Should the bot bank logs or drop them?
# Options: "bank" or "drop"
LOG_DISPOSAL_METHOD = "bank"  # "bank" = deposit in bank, "drop" = drop on ground

# --- Future Features (Placeholders) ---

# Combat stats (for future combat bot features)
COMBAT_LEVEL = 3            # Auto-calculated from combat stats

# Quest completion (for future quest bot features)
QUESTS_COMPLETED = []       # List of completed quest names

# Unlocked areas (for future pathfinding)
UNLOCKED_AREAS = ["lumbridge", "varrock"]  # Areas the player can access

