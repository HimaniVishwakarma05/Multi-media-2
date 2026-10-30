"""
settings.py - Every tunable number, colour and file path used by LUMI.

Change a value here (for example START_LIVES or ORB_POINTS), run the game
again, and the new rule takes effect. You do not need to edit gameplay code
to tune the game during a lab demonstration.
"""

import os

# ----------------------------------------------------------------------------
# File paths (built from this file's location, so the game runs from any folder)
# ----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUND_DIR = os.path.join(BASE_DIR, "assets", "sounds")
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")
HIGHSCORE_FILE = os.path.join(BASE_DIR, "highscore.json")

# ----------------------------------------------------------------------------
# Window
# ----------------------------------------------------------------------------
TITLE = "LUMI - The Cosmic Collector"
WIDTH = 960          # logical game width in pixels (the window uses this size)
HEIGHT = 640         # logical game height in pixels
FPS = 60             # target frames per second

# ----------------------------------------------------------------------------
# Colour palette (from the project brief)
# ----------------------------------------------------------------------------
MIDNIGHT_NAVY = (8, 11, 31)        # background
ELECTRIC_CYAN = (66, 245, 233)     # energy orbs and main accent colour
VIOLET = (155, 93, 229)            # asteroids and nebula glow
CORAL_RED = (255, 90, 110)         # danger, damage and game over
GOLDEN_YELLOW = (255, 209, 102)    # Time Crystal and score highlights
SHIELD_BLUE = (90, 170, 255)       # shield power-up and shield bubble
WHITE = (235, 242, 255)            # main text colour
GREY = (120, 130, 165)             # secondary text colour
PANEL = (16, 22, 52)               # menu and HUD panel colour

# ----------------------------------------------------------------------------
# Player (Lumi)
# ----------------------------------------------------------------------------
PLAYER_SPEED = 340                 # pixels per second
PLAYER_RADIUS = 16                 # collision circle radius in pixels
START_LIVES = 3
INVULNERABLE_TIME = 1.5            # seconds of protection after losing a life

# ----------------------------------------------------------------------------
# Match rules
# ----------------------------------------------------------------------------
GAME_DURATION = 120.0              # countdown timer in seconds
ORB_POINTS = 10                    # rule 1: collecting an energy orb
ASTEROID_PENALTY = 5               # rule 2: hitting an asteroid (score never drops below 0)
CRYSTAL_POINTS = 25                # rule 4: collecting a Time Crystal

# ----------------------------------------------------------------------------
# Collectibles and power-ups
# ----------------------------------------------------------------------------
ORB_RADIUS = 10
ORB_SPAWN_INTERVAL = 0.9           # seconds between new energy orbs
MAX_ORBS = 8                       # never more than this many orbs on screen

CRYSTAL_RADIUS = 13
CRYSTAL_SPAWN_INTERVAL = 22.0      # the Time Crystal appears rarely
CRYSTAL_SLOW_TIME = 5.0            # rule 4: how long hazards stay slowed (seconds)
CRYSTAL_SLOW_FACTOR = 0.4          # hazards move at 40 percent speed while slowed

SHIELD_RADIUS = 13
SHIELD_SPAWN_INTERVAL = 16.0       # how often a shield pick-up is attempted
SHIELD_BUBBLE_RADIUS = 28          # visual size of the shield around Lumi

# ----------------------------------------------------------------------------
# Hazards (asteroids) and dynamic difficulty (custom mechanic 3)
# ----------------------------------------------------------------------------
ASTEROID_MIN_RADIUS = 14
ASTEROID_MAX_RADIUS = 30
ASTEROID_BASE_SPEED = 120          # pixels per second at level 1
ASTEROID_SPEED_PER_LEVEL = 14      # extra speed added for each level
ASTEROID_BASE_SPAWN = 1.6          # seconds between asteroids at level 1
ASTEROID_MIN_SPAWN = 0.4           # fastest possible spawn interval
ASTEROID_SPAWN_DROP = 0.12         # spawn interval reduction per level
ASTEROID_BASE_MAX = 4              # hazards allowed on screen at level 1
ASTEROID_MAX_CAP = 14              # absolute maximum hazards on screen

MAX_LEVEL = 10
LEVEL_TIME_STEP = 20.0             # +1 level for every 20 seconds survived
LEVEL_SCORE_STEP = 80              # +1 level for every 80 points scored

# ----------------------------------------------------------------------------
# Audio
# ----------------------------------------------------------------------------
MUSIC_VOLUME = 0.35                # background music loudness (0.0 to 1.0)

# ----------------------------------------------------------------------------
# Background and visual effects
# ----------------------------------------------------------------------------
STAR_COUNT = 140                   # tiny stars in the scrolling starfield
PLANET_COUNT = 3                   # distant planets drawn in the background
