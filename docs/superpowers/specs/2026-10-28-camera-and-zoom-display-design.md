# Camera Tracking and Dual-Mode Display Design Specification

**Feature:** Dynamic Camera Tracking & Panoramic/Focused Display Toggle  
**Date:** 2026-10-28  
**Module:** `rendering/board_renderer.py`, `rendering/isometric_board_renderer.py`, `ui/game_screen.py`, `rendering/icons.py`  
**Status:** In Review (Brainstorming Phase)  

---

## 1. Executive Summary & Problem Context

In Bloxorz, stage layouts vary significantly in physical footprint. Compact stages (Stages 1–10) fit comfortably within the standard $700 \times 680\text{px}$ board area at standard tile scale ($52\text{px}$). However, expansive stages—such as Stage 11 *Goal Abyss* ($21 \times 48$ grid span)—create display challenges:
- **2D Top-Down View:** Currently calculates layout scale from empty bounding box dimensions `(level.width, level.height)` and hard-clamps at a $24\text{px}$ minimum floor. On Stage 11, this produces a $1152\text{px}$ wide board, pushing `origin_x` to $-226\text{px}$ and overflowing into the sidebar and off the display screen.
- **3D Isometric View:** Bounds active cells down to $16\text{px}$, keeping the board inside the viewport, but shrinks tiles to $21\text{px}$. At that size, tactile switch pedestals, hazard stripes, and the rolling block become tiny and difficult to discern.

This design introduces a **Unified Camera System** with two distinct viewing modes:
1. **Panoramic Overview:** Scales the active stage footprint to fit the board area entirely for strategic planning.
2. **Focused Tracking View:** Renders at standard crisp $52\text{px}$ scale, with a smooth tracking camera centered on the active block (naturally tracking whichever cube is active in split mode).

---

## 2. Intent, Goals, Non-Goals, and Anti-Goals

### 2.1 Intent & Why
To deliver optimal puzzle playability regardless of stage dimensions: giving players macro-level puzzle awareness to evaluate switches and bridges across the entire board, while preserving crisp visual fidelity, tactile feedback, and readable mechanics up close.

### 2.2 Goals
- **Automatic Oversized Detection:** Mathematically determine if a level exceeds standard scale within the viewport (`fit_tile_size < settings.TILE_SIZE`).
- **Initial Presentation:**
  - Standard stages (Stages 1–10) load at standard $52\text{px}$ scale with the camera toggle disabled/grayed out.
  - Oversized stages (Stage 11) load initially in **Panoramic Overview** so players can survey the whole map.
- **Dual-Mode Toggle:** Allow players to switch between Panoramic and Focused Tracking views using either:
  - A compact $32 \times 32\text{px}$ HUD button in the top-left corner of the board area (`x = 16, y = 16`).
  - The `Z` keyboard hotkey.
- **Active Split Tracking:** In focused mode, camera smoothly tracks the active block during rolls; pressing `SPACE` to switch between split cubes smoothly shifts the camera focus to the newly active cube.
- **2D Active-Cell Bounding Fix:** Update 2D `compute_layout()` to bound only active cells (identical to the 3D renderer), eliminating empty-grid stretching.
- **Strict Viewport Clipping:** Protect sidebar panels and HUD elements using Pygame viewport clipping (`surface.set_clip(board_rect)`).

### 2.3 Non-Goals
- Free-form manual click-and-drag camera panning (the camera stays tethered to the player's active block to avoid cumbersome manual camera adjustments).
- Continuous pinch-to-zoom or arbitrary zoom percentages (the two discrete modes—Panoramic and 100% Focused—completely satisfy player needs without UI clutter).

### 2.4 Anti-Goals
- No fuzzy texture downscaling: all tiles, hazard stripes, and switches remain procedural vector/pixel graphics.
- No graphic bleeding into the sidebar, replay slider, or status headers.
- No jarring visual snapping on block rolls: camera movement uses a smooth exponential decay / lerp.

---

## 3. Approaches Evaluated & Trade-offs

| Approach | Architecture | Advantages | Drawbacks | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Approach 1: Unified Camera Offset with Smooth Easing & Viewport Clip** | Apply `(cam_x, cam_y)` translation offset to renderer origins. Keep procedural vector drawing direct to screen clipped to `board_rect`. | 100% crisp vector/pixel graphics; zero blur; minimal memory footprint; smooth 60 FPS lerp. | Requires small update step in game loop to smoothly interpolate camera coordinates. | **Selected (User Approved)** |
| **Approach 2: Full Off-Screen Virtual Megasurface** | Render entire oversized board to a large off-screen surface (~$2500 \times 1200\text{px}$) and blit/scale slices. | Renderers don't need camera offset logic. | Heavy memory consumption; `pygame.transform.smoothscale()` blurs pixel-art cracks and hazard stripes; re-blitting dynamic block animations is complex. | Rejected |
| **Approach 3: Instant-Snap Origin Translation** | Recalculate `origin_x, origin_y` directly on each move with zero interpolation. | Minimal math (no lerp). | Screen jumps abruptly by 52px on every keystroke, causing visual discomfort and disorienting motion. | Rejected |

---

## 4. Technical Architecture & Component Design

```
+--------------------------------------------------------------+---------------------------+
| BOARD AREA (700 x 680 px)                                    | SIDEBAR (340 px)          |
|                                                              |                           |
| [🔍/⤢ HUD] (16, 16, 32x32)                                   | Level controls            |
|                                                              |                           |
|                                                              | Card 1: Algorithms        |
|                   [ Active Block ]                           |                           |
|                  <-- Camera Target                           | Card 2: Playback          |
|                                                              |                           |
|                                                              | Card 3: Metrics           |
| [Legend Bar Docked at Bottom]                                | Hotkey footer             |
+--------------------------------------------------------------+---------------------------+
```

### 4.1 Oversized Detection Logic
A level is classified as `is_oversized` when its active cells require a tile size smaller than standard to fit within `BOARD_AREA_WIDTH - 2 * BOARD_MARGIN` and `BOARD_AREA_HEIGHT - 2 * BOARD_MARGIN`:

```python
# 2D Bounding
active_cells = level.active_cells  # tiles + open/closed bridges
span_c = max(c for r, c in active_cells) - min(c for r, c in active_cells) + 1
span_r = max(r for r, c in active_cells) - min(r for r, c in active_cells) + 1
fit_w = avail_w // span_c
fit_h = avail_h // span_r
is_oversized_2d = min(fit_w, fit_h) < settings.TILE_SIZE

# 3D Bounding
min_u = min(c - r - 1 for r, c in active_cells)
max_u = max(c - r + 1 for r, c in active_cells)
min_v = min(c + r for r, c in active_cells)
max_v = max(c + r + 2 for r, c in active_cells)
fit_3d_w = avail_w / ((max_u - min_u) * 0.5)
fit_3d_h = avail_h / ((max_v - min_v) * 0.25 + 1.35)
is_oversized_3d = min(fit_3d_w, fit_3d_h) < settings.TILE_SIZE

is_oversized = is_oversized_3d if view_mode == "3D" else is_oversized_2d
```

### 4.2 Camera State Machine (`GameScreen`)
- **Attributes:**
  - `is_oversized: bool`
  - `zoom_mode: str` (`"PANORAMIC"` or `"FOCUSED"`)
  - `camera_pos: list[float]` (`[x, y]`)
  - `target_camera_pos: list[float]` (`[x, y]`)
  - `camera_speed: float = 12.0` (exponential smoothing factor)
- **Transitions:**
  - `load_level(index)`:
    - Calculates `is_oversized`.
    - If `is_oversized`: `zoom_mode = "PANORAMIC"`, HUD button enabled.
    - If not `is_oversized`: `zoom_mode = "PANORAMIC"`, HUD button disabled (`enabled=False`).
    - Resets `camera_pos = [0.0, 0.0]`, `target_camera_pos = [0.0, 0.0]`.
  - `toggle_zoom()`:
    - Ignored if `not is_oversized`.
    - Flips `zoom_mode` between `"PANORAMIC"` and `"FOCUSED"`.
    - If switching to `"FOCUSED"`: immediately snaps or smoothly targets the active block.
    - If switching to `"PANORAMIC"`: targets `[0.0, 0.0]`.

### 4.3 Target Coordinate Calculation
In `"FOCUSED"` mode (`tile_size = settings.TILE_SIZE = 52`):
1. Compute the active block's screen center `(block_screen_x, block_screen_y)` based on its current grid position `(r, c)` (or active cube if split).
2. The ideal camera target is the delta needed to bring that position to viewport center:
   $$\text{target\_x} = \text{board\_rect.centerx} - \text{block\_screen\_x}$$
   $$\text{target\_y} = \text{board\_rect.centery} - \text{block\_screen\_y}$$
3. In `update(dt)`:
   $$\text{camera\_pos.x} += (\text{target\_x} - \text{camera\_pos.x}) \times \min(1.0, \text{dt} \times \text{camera\_speed})$$
   $$\text{camera\_pos.y} += (\text{target\_y} - \text{camera\_pos.y}) \times \min(1.0, \text{dt} \times \text{camera\_speed})$$

### 4.4 HUD Button Design & Icons (`rendering/icons.py`)
- **Location:** Top-left of board area: `pygame.Rect(16, 16, 32, 32)`.
- **States:**
  - **Disabled:** Subtle slate border `(45, 52, 70)`, dim icon `(80, 90, 110)`, no hover reaction.
  - **Active - In Panoramic:** Draws `draw_camera_focus_icon()` (crosshairs / target brackets `[ + ]`), tooltip / hint: "Focus (Z)".
  - **Active - In Focused:** Draws `draw_camera_overview_icon()` (expand/four arrows `⤢` or globe/grid), tooltip / hint: "Overview (Z)".

### 4.5 Viewport Protection
In `GameScreen.draw()`:
```python
# Clip rendering to board canvas
prev_clip = self.surface.get_clip()
self.surface.set_clip(self.board_rect)

# Render Board & Block with camera offset
if self.view_mode == "3D":
    self.iso_board_renderer.draw(self.surface, self.level, self.current_state, self.board_rect, camera_offset=self.camera_pos)
    self.iso_block_renderer.draw(self.surface, self.current_state, camera_offset=self.camera_pos)
else:
    self.board_renderer.draw(self.surface, self.level, self.current_state, self.board_rect, camera_offset=self.camera_pos)
    self.block_renderer.draw(self.surface, self.current_state, camera_offset=self.camera_pos)

# Restore clip for sidebar and HUD
self.surface.set_clip(prev_clip)

# Draw HUD controls on top
self.btn_camera_toggle.draw(self.surface)
```

---

## 5. Verification & Test Plan

1. **Oversized Detection Contract:**
   - Stages 1–10 must evaluate to `is_oversized == False` in both 2D and 3D.
   - Stage 11 must evaluate to `is_oversized == True` in both 2D and 3D.
2. **Button State Contract:**
   - On Stages 1–10, `btn_camera_toggle.enabled` is `False`.
   - On Stage 11, `btn_camera_toggle.enabled` is `True`.
3. **Toggle & Keyboard Shortcuts:**
   - Pressing `Z` or clicking the button on Stage 11 flips `zoom_mode` between `"PANORAMIC"` and `"FOCUSED"`.
   - Pressing `Z` or clicking on Stages 1–10 is a strict no-op.
4. **Active Block Tracking & Split-Cube Shifts:**
   - In focused mode, camera targets the single block's center during movement.
   - In split mode (e.g. Stage 8 or Stage 11), pressing `SPACE` updates the camera target to the newly active cube's position.
5. **Surface Clipping Smoke Test:**
   - Render Stage 11 in 2D and 3D focused mode; assert that pixels outside `board_rect` (e.g. in `sidebar_rect`) are not overwritten by board tiles.
6. **Regression Suite:**
   - All existing 145 GUI and engine tests continue to pass.
