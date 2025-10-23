"""Constants for the battle app."""

import os

# Pagination defaults
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20

# PokeAPI configuration
POKEAPI_BASE = os.environ.get("POKEAPI_BASE", "https://pokeapi.co/api/v2")

# Stat change stages from -6 to +6 (Pokemon battle mechanics)
# Used when applying stat changes from PokeAPI affecting_moves
STAT_CHANGE_MULTIPLIERS = {
    -6: 2 / 8,  # 0.25×
    -5: 2 / 7,  # 0.29×
    -4: 2 / 6,  # 0.33×
    -3: 2 / 5,  # 0.40×
    -2: 2 / 4,  # 0.50×
    -1: 2 / 3,  # 0.67×
    0: 1.0,  # 1.00× (no change)
    1: 3 / 2,  # 1.50×
    2: 4 / 2,  # 2.00×
    3: 5 / 2,  # 2.50×
    4: 6 / 2,  # 3.00×
    5: 7 / 2,  # 3.50×
    6: 8 / 2,  # 4.00×
}

# Battle stat weights
# Attacker uses offensive stats, defender uses defensive stats
ATTACKER_STAT_WEIGHTS = {
    "attack": 1.2,
    "special-attack": 1.1,
    "speed": 1.0,
}

DEFENDER_STAT_WEIGHTS = {
    "defense": 1.2,
    "special-defense": 1.1,
    "hp": 1.0,
}

# Other battle modifiers
TYPE_COUNT_BONUS = 5  # Bonus per extra type
BASE_EXPERIENCE_MULTIPLIER = 0.05  # Multiplier for base experience
STAT_CHANGE_FACTOR = 0.25  # Factor for applying stat changes (1.0 + change * factor)
