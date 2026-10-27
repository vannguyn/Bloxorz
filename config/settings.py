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
COLOR_GLASS_FILL = (245, 130, 45, 185)   # Amber-orange translucent glass fill with alpha
COLOR_GLASS_CRACK = (255, 255, 255, 230) # Radiating fracture cracks with alpha
COLOR_GLASS_SHADOW: tuple[int, int, int, int] = (140, 50, 10, 220)  # Glass fracture bevel under-shadow with alpha
COLOR_GLASS_BORDER = (255, 160, 60)      # Glass tile perimeter border

# Canonical 32x32 pixel-art crack coordinates for fragile glass tiles
FRAGILE_CRACK_WHITE: tuple[tuple[int, int], ...] = (
    (13, 1),
    (5, 2),
    (14, 2),
    (6, 3),
    (14, 3),
    (17, 3),
    (7, 4),
    (14, 4),
    (17, 4),
    (22, 4),
    (8, 5),
    (9, 5),
    (21, 5),
    (10, 7),
    (11, 7),
    (20, 7),
    (11, 8),
    (12, 8),
    (13, 8),
    (14, 8),
    (15, 8),
    (22, 8),
    (11, 9),
    (14, 9),
    (15, 9),
    (16, 9),
    (5, 10),
    (9, 10),
    (12, 10),
    (18, 10),
    (19, 10),
    (20, 10),
    (7, 11),
    (12, 11),
    (17, 11),
    (18, 11),
    (19, 11),
    (20, 11),
    (21, 11),
    (22, 11),
    (21, 12),
    (22, 12),
    (23, 12),
    (24, 12),
    (10, 13),
    (11, 13),
    (12, 13),
    (16, 13),
    (26, 13),
    (27, 13),
    (28, 13),
    (12, 14),
    (29, 14),
    (12, 15),
    (16, 15),
    (18, 15),
    (13, 16),
    (15, 16),
    (19, 16),
    (11, 17),
    (12, 17),
    (13, 17),
    (14, 17),
    (18, 17),
    (21, 17),
    (11, 18),
    (13, 18),
    (14, 18),
    (18, 18),
    (22, 18),
    (14, 19),
    (9, 20),
    (14, 20),
    (20, 20),
    (24, 20),
    (8, 21),
    (9, 21),
    (14, 21),
    (15, 22),
    (7, 23),
    (15, 23),
    (6, 24),
    (13, 24),
    (16, 24),
    (13, 25),
    (16, 25),
    (17, 26),
    (12, 27),
    (17, 27),
    (12, 28),
    (18, 28),
    (18, 29),
)

FRAGILE_CRACK_SHADOW: tuple[tuple[int, int], ...] = (
    (4, 2),
    (13, 2),
    (23, 2),
    (5, 3),
    (13, 3),
    (6, 4),
    (13, 4),
    (14, 5),
    (8, 6),
    (9, 6),
    (14, 6),
    (9, 7),
    (14, 7),
    (10, 8),
    (19, 8),
    (12, 9),
    (13, 9),
    (3, 10),
    (4, 10),
    (11, 10),
    (14, 10),
    (16, 10),
    (17, 10),
    (5, 11),
    (6, 11),
    (11, 11),
    (14, 11),
    (7, 12),
    (12, 12),
    (19, 12),
    (20, 12),
    (9, 13),
    (15, 13),
    (24, 13),
    (25, 13),
    (10, 14),
    (11, 14),
    (16, 14),
    (26, 14),
    (27, 14),
    (28, 14),
    (17, 15),
    (14, 16),
    (16, 16),
    (18, 16),
    (17, 17),
    (20, 17),
    (12, 18),
    (17, 18),
    (21, 18),
    (10, 19),
    (13, 19),
    (23, 19),
    (13, 20),
    (13, 21),
    (8, 22),
    (14, 22),
    (7, 24),
    (15, 24),
    (6, 25),
    (15, 25),
    (4, 26),
    (17, 28),
    (17, 29),
    (18, 30),
)

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
