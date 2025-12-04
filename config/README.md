# Player Configuration

This directory contains configuration files for your character's stats and bot settings.

## File Structure

- **`player_stats.py`** - Input your character's skill levels here
- **`player_config.py`** - Bot behavior preferences and settings

## Quick Setup

### 1. Update Your Stats

Open `config/player_stats.py` and update your skill levels:

```python
WOODCUTTING_LEVEL = 1        # IMPORTANT: Required for woodcutting bot
ATTACK_LEVEL = 1
STRENGTH_LEVEL = 1
# ... etc
```

**Most important for woodcutting:** Update `WOODCUTTING_LEVEL`

### 2. Configure Bot Preferences

Open `config/player_config.py` and set your preferences:

```python
PREFERRED_TREE_TYPE = None  # None = auto-select based on level
LOG_DISPOSAL_METHOD = "bank"  # "bank" or "drop"
ENABLE_BREAKS = True
```

The bot uses this information to:

- **Determine available actions** - Only shows/cuts trees you can actually cut based on your level
- **Auto-select best tree type** - Chooses the best tree for your level automatically
- **Configure behavior** - Controls breaks, log disposal method, etc.

### Example Configuration

```python
# For a level 1 character (can only cut regular trees)
WOODCUTTING_LEVEL = 1
TREE_TYPE = "regular"  # Auto-selected based on level

# For a level 30 character (can cut regular, oak, and willow)
WOODCUTTING_LEVEL = 30
# Will auto-select willow (best XP available)
```

### Key Settings

- **WOODCUTTING_LEVEL** - Your current Woodcutting level (required)
- **PREFERRED_TREE_TYPE** - Set to None for auto-select, or specify a type
- **LOG_DISPOSAL_METHOD** - "bank" or "drop"
- **ENABLE_BREAKS** - True/False to enable/disable AFK breaks
- **BREAK_CHANCE** - Probability of taking a break (0.0 to 1.0)

### Tree Level Requirements

- **Regular**: Level 1
- **Oak**: Level 15
- **Willow**: Level 30
- **Teak**: Level 35
- **Maple**: Level 45
- **Mahogany**: Level 50
- **Yew**: Level 60
- **Magic**: Level 75

The bot will automatically prevent you from trying to cut trees you can't access!

