"""
Configuration settings for Bloxorz GUI.
Constants for display dimensions, colors, fonts, and controls.
"""

WINDOW_WIDTH = 1040
WINDOW_HEIGHT = 680
FPS = 60

# Layout dimensions
SIDEBAR_WIDTH = 340
BOARD_AREA_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH
BOARD_AREA_HEIGHT = WINDOW_HEIGHT

TILE_SIZE = 52
BOARD_MARGIN = 40

# Colors (RGB)
COLOR_BG = (20, 24, 34)
COLOR_PANEL_BG = (28, 33, 46)
COLOR_PANEL_BORDER = (45, 52, 70)

# Tiles
COLOR_FLOOR = (195, 205, 218)
COLOR_FLOOR_BORDER = (145, 155, 170)
COLOR_GOAL = (35, 38, 48)
COLOR_GOAL_RING = (255, 210, 50)
COLOR_GOAL_WALL_LEFT = (18, 22, 32)      # Left internal goal shaft wall (shaded dark)
COLOR_GOAL_WALL_RIGHT = (28, 34, 48)     # Right internal goal shaft wall (shaded mid-dark)
COLOR_GOAL_ABYSS = (6, 8, 12)            # Deep optical abyss void floor

COLOR_FRAGILE = (235, 120, 25)               # Solid orange fragile body (#EB7819)
COLOR_FRAGILE_BORDER = (195, 80, 20)         # Amber-orange border
COLOR_FRAGILE_STRIPE = (255, 185, 45)        # High-contrast yellow hazard warning stripe

COLOR_BRIDGE_CLOSED = (40, 45, 60)
COLOR_BRIDGE_CLOSED_BORDER = (75, 80, 95)
COLOR_BRIDGE_DOCK_RAIL = (35, 60, 80)    # Recessed docking rail wireframe at pit depth
COLOR_BRIDGE_DOCK_PIN = (45, 85, 110)    # Surface corner docking guide pin/bracket
COLOR_BRIDGE_OPEN = (100, 195, 175)
COLOR_BRIDGE_OPEN_BORDER = (60, 150, 130)

# Switches
COLOR_SWITCH_SOFT = (255, 215, 0)
COLOR_SWITCH_PEDESTAL = (70, 50, 10)     # Cylindrical base ring / bevel shadow for tactile switch
COLOR_SWITCH_HEAVY = (235, 75, 75)
COLOR_SWITCH_HEAVY_BASE = (45, 50, 60)   # Cast metal octagonal sub-plate base
COLOR_SWITCH_SPLIT = (65, 175, 245)

# Visual Patch Design Tokens (Amber Glass & Heavy Steel Patch)
COLOR_SPLIT_CYAN = (56, 189, 248)        # Split switch energy wing border
COLOR_SPLIT_DARK = (2, 132, 199)         # Split switch button body
COLOR_HEAVY_RED = (239, 68, 68)          # Heavy switch embossed steel cross surface
COLOR_HEAVY_DARKRED = (153, 27, 27)      # Heavy switch 3D extrusion shadow
COLOR_HEAVY_BASE = (71, 85, 105)         # Heavy switch industrial cast-metal base plate

# Block
COLOR_BLOCK = (205, 85, 35)
COLOR_BLOCK_TOP = (230, 110, 60)
COLOR_BLOCK_BORDER = (140, 50, 20)
COLOR_BLOCK_ACTIVE = (255, 235, 100)
COLOR_BLOCK_INACTIVE = (140, 110, 100)

# UI Elements
COLOR_TEXT_MAIN = (240, 243, 248)
COLOR_TEXT_MUTED = (140, 150, 170)
COLOR_TEXT_ACCENT = (70, 190, 245)
COLOR_TEXT_SUCCESS = (80, 215, 140)
COLOR_TEXT_DANGER = (250, 85, 85)

# Buttons
COLOR_BTN_DEFAULT = (48, 56, 76)
COLOR_BTN_HOVER = (62, 72, 98)
COLOR_BTN_ACTIVE = (38, 45, 62)
COLOR_BTN_DISABLED = (32, 36, 48)
COLOR_BTN_PRIMARY = (35, 115, 220)
COLOR_BTN_PRIMARY_HOVER = (50, 135, 245)

# Card Container & Metric Tokens
COLOR_CARD_BG: tuple[int, int, int] = (17, 24, 39)
COLOR_CARD_BORDER: tuple[int, int, int] = (31, 41, 55)
COLOR_CARD_HEADER: tuple[int, int, int] = (229, 231, 235)
COLOR_METRIC_LABEL: tuple[int, int, int] = (156, 163, 175)
COLOR_METRIC_VALUE: tuple[int, int, int] = (243, 244, 246)
