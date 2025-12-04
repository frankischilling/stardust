"""
Player Stats Configuration
Input your character's current skill levels here.
This helps the bot determine what actions are available to you.
"""

# ============================================================================
# SKILL LEVELS
# ============================================================================
# Update these with your character's current skill levels
# These are used to determine what actions the bot can perform

# Combat Skills
ATTACK_LEVEL = 1
STRENGTH_LEVEL = 1
DEFENCE_LEVEL = 1
HITPOINTS_LEVEL = 10
RANGED_LEVEL = 1
PRAYER_LEVEL = 1
MAGIC_LEVEL = 1

# Gathering Skills
WOODCUTTING_LEVEL = 1        # IMPORTANT: Required for woodcutting bot
MINING_LEVEL = 1
FISHING_LEVEL = 1

# Production Skills
COOKING_LEVEL = 1
FIREMAKING_LEVEL = 1
SMITHING_LEVEL = 1
CRAFTING_LEVEL = 1
FLETCHING_LEVEL = 1

# Other Skills (for future features)
AGILITY_LEVEL = 1
HERBLORE_LEVEL = 1
THIEVING_LEVEL = 1
SLAYER_LEVEL = 1
FARMING_LEVEL = 1
RUNECRAFT_LEVEL = 1
CONSTRUCTION_LEVEL = 1
HUNTER_LEVEL = 1

# ============================================================================
# CALCULATED VALUES
# ============================================================================

def get_combat_level():
    """
    Calculates combat level based on combat stats.
    Formula: floor((Attack + Strength) / 2 + Defence / 2 + Hitpoints / 2 + Prayer / 2 + Magic / 2 + Ranged / 2)
    """
    base = (ATTACK_LEVEL + STRENGTH_LEVEL) / 2
    base += DEFENCE_LEVEL / 2
    base += HITPOINTS_LEVEL / 2
    base += PRAYER_LEVEL / 2
    base += MAGIC_LEVEL / 2
    base += RANGED_LEVEL / 2
    return int(base)

COMBAT_LEVEL = get_combat_level()

# ============================================================================
# SKILL-BASED AVAILABILITY CHECKS
# ============================================================================

# ============================================================================
# TREE TYPE DATA
# ============================================================================
# Complete list of all tree types with their requirements and properties
# Courtesy of https://oldschool.runescape.wiki/w/Woodcutting

TREE_DATA = {
    # Level 1 trees (all give logs, 25 XP, one log per tree)
    "regular": {"level": 1, "xp": 25, "wait_time": (2, 3), "logs_per_tree": 1},
    "evergreen": {"level": 1, "xp": 25, "wait_time": (2, 3), "logs_per_tree": 1},
    "dead": {"level": 1, "xp": 25, "wait_time": (2, 3), "logs_per_tree": 1},
    "dying": {"level": 1, "xp": 25, "wait_time": (2, 3), "logs_per_tree": 1},
    "jungle": {"level": 1, "xp": 25, "wait_time": (2, 3), "logs_per_tree": 1},
    "achey": {"level": 1, "xp": 25, "wait_time": (2, 3), "logs_per_tree": 1},
    
    # Special trees (require machete, members only)
    "light_jungle": {"level": 10, "xp": 32, "wait_time": (15, 25), "logs_per_tree": "varies", "requires_machete": True},
    "medium_jungle": {"level": 20, "xp": 55, "wait_time": (20, 30), "logs_per_tree": "varies", "requires_machete": True},
    "dense_jungle": {"level": 35, "xp": 80, "wait_time": (25, 35), "logs_per_tree": "varies", "requires_machete": True},
    
    # Standard training trees
    "oak": {"level": 15, "xp": 37.5, "wait_time": (25, 29), "logs_per_tree": "multiple"},
    "willow": {"level": 30, "xp": 67.5, "wait_time": (28, 32), "logs_per_tree": "multiple"},
    "teak": {"level": 35, "xp": 85, "wait_time": (28, 32), "logs_per_tree": "multiple"},
    "maple": {"level": 45, "xp": 100, "wait_time": (58, 62), "logs_per_tree": "multiple"},
    "mahogany": {"level": 50, "xp": 125, "wait_time": (58, 62), "logs_per_tree": "multiple"},
    "yew": {"level": 60, "xp": 175, "wait_time": (110, 118), "logs_per_tree": "multiple"},
    "magic": {"level": 75, "xp": 250, "wait_time": (230, 238), "logs_per_tree": "multiple"},
    
    # Special/rare trees
    "jatoba": {"level": 40, "xp": 92, "wait_time": (50, 60), "logs_per_tree": "multiple"},
    "juniper": {"level": 42, "xp": 35, "wait_time": (30, 40), "logs_per_tree": "multiple"},
    "hollow": {"level": 45, "xp": 82.5, "wait_time": (34, 38), "logs_per_tree": "multiple", "resource": "bark"},
    "arctic_pine": {"level": 54, "xp": 40, "wait_time": (82, 86), "logs_per_tree": "multiple"},
    "blisterwood": {"level": 62, "xp": 76, "wait_time": (50, 60), "logs_per_tree": "multiple"},
    "sulliuscep": {"level": 65, "xp": 127, "wait_time": (60, 80), "logs_per_tree": "multiple", "special": True},
    "camphor": {"level": 66, "xp": 143.5, "wait_time": (50, 60), "logs_per_tree": "multiple"},
    "ironwood": {"level": 80, "xp": 175, "wait_time": (230, 238), "logs_per_tree": "multiple"},
    "redwood": {"level": 90, "xp": 380, "wait_time": (260, 268), "logs_per_tree": "multiple", "special": True},
    "rosewood": {"level": 92, "xp": 212.5, "wait_time": (260, 268), "logs_per_tree": "multiple"},
}

def can_cut_tree_type(tree_type):
    """
    Checks if player can cut a specific tree type based on Woodcutting level.
    
    Args:
        tree_type: String name of tree type ("regular", "oak", "willow", etc.)
    
    Returns:
        True if player can cut this tree type, False otherwise
    """
    tree_info = TREE_DATA.get(tree_type.lower())
    if not tree_info:
        return False
    
    required_level = tree_info["level"]
    return WOODCUTTING_LEVEL >= required_level

def get_available_tree_types():
    """
    Returns a list of tree types the player can cut based on their Woodcutting level.
    Filters out special trees that require special tools (like machete).
    """
    available = []
    for tree_type, tree_info in TREE_DATA.items():
        if WOODCUTTING_LEVEL >= tree_info["level"]:
            # Skip trees that require special tools (for now)
            if not tree_info.get("requires_machete", False):
                available.append(tree_type)
    return sorted(available, key=lambda t: TREE_DATA[t]["level"])

def get_best_available_tree():
    """
    Returns the best tree type the player can cut (highest XP).
    Prioritizes higher level trees for better XP rates.
    Excludes special trees that require special mechanics.
    """
    available = get_available_tree_types()
    
    if not available:
        return "regular"  # Fallback
    
    # Sort by XP (highest first), then by level
    sorted_trees = sorted(
        available,
        key=lambda t: (TREE_DATA[t]["xp"], TREE_DATA[t]["level"]),
        reverse=True
    )
    
    # Prefer non-special trees
    for tree in sorted_trees:
        if not TREE_DATA[tree].get("special", False):
            return tree
    
    # If only special trees available, return the best one
    return sorted_trees[0] if sorted_trees else "regular"

def get_tree_info(tree_type):
    """
    Returns information about a specific tree type.
    
    Args:
        tree_type: String name of tree type
    
    Returns:
        Dictionary with tree information, or None if not found
    """
    return TREE_DATA.get(tree_type.lower())

