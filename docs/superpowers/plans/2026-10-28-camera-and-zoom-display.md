# Dynamic Camera Tracking & Panoramic/Focused Display Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a unified camera system providing Panoramic Overview (auto-fit) and Focused Tracking View ($52\text{px}$ crisp scale with smooth block tracking), complete with a top-left HUD button (`Z` hotkey), active-cell bounding in 2D, and strict viewport clipping.

**Architecture:** A lightweight `CameraState` tracks mode (`PANORAMIC` vs. `FOCUSED`) and smooth exponential camera offsets `(cam_x, cam_y)`. Renderers accept the camera offset directly into origin calculations and clip drawing to `board_rect`. In focused mode, the camera smoothly targets the active block (shifting to the active cube upon `SPACE` in split mode). Standard stages (Stages 1–10) disable the HUD toggle; oversized stages (Stage 11) open in panoramic overview and enable toggling.

**Tech Stack:** Pygame-CE, Python 3.10+, Pytest

**Spec:** [`docs/superpowers/specs/2026-10-28-camera-and-zoom-display-design.md`](file:///home/quang/Workspace/24120127/NM_AI/Bloxorz/docs/superpowers/specs/2026-10-28-camera-and-zoom-display-design.md)

## Global Constraints
- `WINDOW_WIDTH = 1040`, `WINDOW_HEIGHT = 680`, `BOARD_AREA_WIDTH = 700`, `BOARD_AREA_HEIGHT = 680`, `TILE_SIZE = 52`, `BOARD_MARGIN = 40`.
- Pure procedural drawing: zero external raster image files or texture assets.
- Viewport boundary safety: all board and block drawing must be clipped to `board_rect` (`surface.set_clip(board_rect)`).
- Core game logic (`core/`) and level models (`levels/`) remain unmodified; layout calculations adapt to `level.tiles` and `level.bridges`.
- Cross-platform compatible (Linux/macOS/Windows) with zero font/audio warnings.

## Review Focus
1. **Empty-Grid Coordinate Bleed:** 2D renderer must bound only active cells `(tiles + bridges)` rather than `(level.width, level.height)` to prevent negative origin on sparse maps like Stage 11.
2. **Viewport Boundary Bleed:** In focused tracking mode on large boards, board tiles extending beyond `board_rect` must never draw into `sidebar_rect` or header bars.
3. **Split Cube Focus Switching:** When a block is split, pressing `SPACE` must immediately update the camera target to the newly active cube half.
4. **Disabled HUD State Invariance:** On Stages 1–10, clicking the HUD button or pressing `Z` must be a strict no-op with zero camera displacement.
5. **Replay Mode Consistency:** During solver replay playback and slider scrubbing, the camera must smoothly track the replayed block state in focused mode without jumping or drifting.

---

### Task 1: Active-Cell Bounding, Camera State, and Oversized Detection

**Files:**
- Create: `rendering/camera.py`
- Modify: `rendering/board_renderer.py:24-46`
- Test: `tests/test_camera_layout.py`

**Interfaces:**
- Consumes: `Level` model from `core.models`, `settings` from `config`
- Produces:
  - `rendering.camera.CameraMode`: Enum (`PANORAMIC = "PANORAMIC"`, `FOCUSED = "FOCUSED"`)
  - `rendering.camera.is_level_oversized(level: Level, avail_w: int, avail_h: int, is_3d: bool = False) -> bool`
  - `rendering.camera.CameraState`: Class tracking `mode`, `pos: list[float]`, `target_pos: list[float]`, `speed: float = 12.0`, `update(dt: float)`
  - `BoardRenderer.compute_layout(level: Level, area_rect: pygame.Rect | None = None) -> tuple[int, int, int]`: bounds active cells `(tiles + bridges)`.

- [ ] **Step 1: Write the failing tests for active-cell bounding and oversized detection**

```python
# tests/test_camera_layout.py
import pygame
import pytest
from config import settings
from levels.level_loader import load_level_from_json
from rendering.board_renderer import BoardRenderer
from rendering.camera import CameraMode, CameraState, is_level_oversized


def test_2d_active_cell_bounding_eliminates_negative_origin():
    level_11 = load_level_from_json("levels/level_11.json")
    renderer = BoardRenderer(settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT)
    origin_x, origin_y, tile_size = renderer.compute_layout(level_11)

    # Origin x must NOT be negative (previously -226 due to empty grid span)
    assert origin_x >= 0
    assert origin_y >= 0
    assert tile_size >= 12


def test_oversized_detection_contract():
    level_1 = load_level_from_json("levels/level_01.json")
    level_11 = load_level_from_json("levels/level_11.json")
    avail_w = settings.BOARD_AREA_WIDTH - 2 * settings.BOARD_MARGIN
    avail_h = settings.BOARD_AREA_HEIGHT - 2 * settings.BOARD_MARGIN

    # Standard level does NOT exceed standard scale
    assert is_level_oversized(level_1, avail_w, avail_h, is_3d=False) is False
    assert is_level_oversized(level_1, avail_w, avail_h, is_3d=True) is False

    # Stage 11 exceeds standard scale in both views
    assert is_level_oversized(level_11, avail_w, avail_h, is_3d=False) is True
    assert is_level_oversized(level_11, avail_w, avail_h, is_3d=True) is True


def test_camera_state_lerp():
    cam = CameraState(mode=CameraMode.FOCUSED, speed=10.0)
    cam.pos = [0.0, 0.0]
    cam.target_pos = [100.0, 200.0]
    cam.update(0.1)
    assert 0.0 < cam.pos[0] < 100.0
    assert 0.0 < cam.pos[1] < 200.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_camera_layout.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'rendering.camera'`

- [ ] **Step 3: Implement `rendering/camera.py` and update `BoardRenderer.compute_layout`**

1. In `rendering/camera.py`:
   - Define `CameraMode` enum (`PANORAMIC`, `FOCUSED`).
   - Define `is_level_oversized(level, avail_w, avail_h, is_3d)` by inspecting `all_cells = set(level.tiles.keys()) | {c for b in level.bridges.values() for c in b}`.
   - Define `CameraState` with `pos`, `target_pos`, `mode`, `update(dt)`.
2. In `rendering/board_renderer.py`:
   - Update `compute_layout()` to compute `min_c, max_c, min_r, max_r` from active cells `(tiles + bridges)` rather than `level.width, level.height`, centering active tiles in `avail_w, avail_h`.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_camera_layout.py -v`  
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add rendering/camera.py rendering/board_renderer.py tests/test_camera_layout.py
git commit -m "feat(rendering): add camera state and fix 2D layout active-cell bounding"
```

---

### Task 2: Procedural HUD Icons & Top-Left Camera Toggle Button

**Files:**
- Modify: `rendering/icons.py`
- Modify: `ui/button.py`
- Test: `tests/test_camera_icons.py`

**Interfaces:**
- Consumes: `pygame.Surface`, `pygame.Rect`, color tokens from `config.settings`
- Produces:
  - `rendering.icons.draw_camera_focus_icon(surface: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int])`
  - `rendering.icons.draw_camera_overview_icon(surface: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int])`
  - `Button.enabled: bool` correctly ignores hover / click events and draws with muted disabled colors.

- [ ] **Step 1: Write the failing tests for HUD icons and button disabled states**

```python
# tests/test_camera_icons.py
import pygame
from rendering.icons import draw_camera_focus_icon, draw_camera_overview_icon
from ui.button import Button


def test_camera_icons_draw_without_error():
    surface = pygame.Surface((32, 32))
    rect = pygame.Rect(0, 0, 32, 32)
    draw_camera_focus_icon(surface, rect, (200, 200, 200))
    draw_camera_overview_icon(surface, rect, (200, 200, 200))
    # Must draw non-zero pixels
    assert pygame.transform.average_color(surface)[:3] != (0, 0, 0)


def test_button_disabled_state_suppresses_click():
    clicked = []
    btn = Button((0, 0, 32, 32), "", callback=lambda: clicked.append(True), enabled=False)
    # Simulate click
    event_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(16, 16))
    event_up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(16, 16))
    btn.handle_event(event_down)
    btn.handle_event(event_up)
    assert clicked == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_camera_icons.py -v`  
Expected: FAIL with `ImportError: cannot import name 'draw_camera_focus_icon'`

- [ ] **Step 3: Implement HUD icons in `rendering/icons.py` and verify `Button` disabled handling**

1. In `rendering/icons.py`:
   - Implement `draw_camera_focus_icon`: draws four corner brackets `[ + ]` pointing inward to indicate focus/tracking.
   - Implement `draw_camera_overview_icon`: draws an outward-pointing expand/overview symbol `⤢` to indicate full panoramic view.
2. In `ui/button.py`:
   - Ensure disabled buttons render with subdued border `(45, 52, 70)` and text/icon `(80, 90, 110)` with zero hover highlighting.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_camera_icons.py -v`  
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add rendering/icons.py ui/button.py tests/test_camera_icons.py
git commit -m "feat(ui): add procedural camera HUD icons and disabled button styling"
```

---

### Task 3: Camera Tracking, Dual-Mode Toggle, and Viewport Clipping

**Files:**
- Modify: `rendering/board_renderer.py:48-70`
- Modify: `rendering/isometric_board_renderer.py:80-120`
- Modify: `ui/game_screen.py`
- Test: `tests/test_camera_navigation.py`

**Interfaces:**
- Consumes: `CameraState`, `CameraMode`, `is_level_oversized` from `rendering.camera`
- Produces:
  - `BoardRenderer.draw(..., camera_offset: tuple[float, float] = (0.0, 0.0))`
  - `IsometricBoardRenderer.draw(..., camera_offset: tuple[float, float] = (0.0, 0.0))`
  - `GameScreen.camera: CameraState`
  - `GameScreen.btn_camera_toggle: Button` (positioned at `Rect(16, 16, 32, 32)`)
  - `GameScreen.toggle_zoom_mode()`
  - Viewport clipped to `self.board_rect` via `surface.set_clip(self.board_rect)`.

- [ ] **Step 1: Write the failing tests for camera navigation and viewport clipping**

```python
# tests/test_camera_navigation.py
import pygame
from config import settings
from levels.level_loader import load_level_from_json
from rendering.camera import CameraMode
from ui.game_screen import GameScreen


def test_standard_level_disables_camera_toggle():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    levels = [load_level_from_json("levels/level_01.json")]
    screen = GameScreen(surface, levels=levels)
    screen.load_level(0)

    assert screen.btn_camera_toggle.enabled is False
    assert screen.camera.mode == CameraMode.PANORAMIC

    # Pressing Z or clicking must be a no-op
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    assert screen.camera.mode == CameraMode.PANORAMIC


def test_oversized_level_enables_toggle_and_starts_panoramic():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    levels = [load_level_from_json("levels/level_11.json")]
    screen = GameScreen(surface, levels=levels)
    screen.load_level(0)

    # Initial state is Panoramic
    assert screen.btn_camera_toggle.enabled is True
    assert screen.camera.mode == CameraMode.PANORAMIC

    # Toggle with Z key
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    assert screen.camera.mode == CameraMode.FOCUSED

    # Toggle back with click
    screen.btn_camera_toggle.callback()
    assert screen.camera.mode == CameraMode.PANORAMIC


def test_viewport_clipping_protects_sidebar():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    levels = [load_level_from_json("levels/level_11.json")]
    screen = GameScreen(surface, levels=levels)
    screen.load_level(0)
    screen.camera.mode = CameraMode.FOCUSED
    screen.draw()

    # Verify sidebar background is preserved
    sidebar_sample = surface.get_at((settings.BOARD_AREA_WIDTH + 20, 20))[:3]
    assert sidebar_sample == settings.COLOR_PANEL_BG
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_camera_navigation.py -v`  
Expected: FAIL with `AttributeError: 'GameScreen' object has no attribute 'btn_camera_toggle'`

- [ ] **Step 3: Implement camera navigation and viewport clipping**

1. In `rendering/board_renderer.py` and `rendering/isometric_board_renderer.py`:
   - Add `camera_offset: tuple[float, float] = (0.0, 0.0)` parameter to `draw()`, shifting effective origin by `(camera_offset[0], camera_offset[1])`.
2. In `ui/game_screen.py`:
   - Initialize `self.camera = CameraState()`.
   - Add `self.btn_camera_toggle = Button(pygame.Rect(16, 16, 32, 32), "", self.toggle_zoom_mode, icon_drawer=...)`.
   - Update `load_level()` to set `is_oversized` and update button icon / enabled state.
   - In `handle_event()`, handle `K_z` to invoke `self.toggle_zoom_mode()`.
   - In `update(dt)`, update camera target in focused mode based on active block coordinates, and call `self.camera.update(dt)`.
   - In `draw()`, wrap board rendering in `self.surface.set_clip(self.board_rect)` and restore clip before drawing sidebar and HUD button.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_camera_navigation.py -v`  
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add rendering/board_renderer.py rendering/isometric_board_renderer.py ui/game_screen.py tests/test_camera_navigation.py
git commit -m "feat(ui): integrate camera tracking, dual-mode toggle, and viewport clipping"
```

---

### Task 4: Split-Cube Tracking, Replay Integration, and Full Regression Suite

**Files:**
- Modify: `ui/game_screen.py:380-420`
- Modify: `tests/test_camera_navigation.py`
- Test: Full test suite (`tests/`)

**Interfaces:**
- Consumes: Split block state from `core.models.Block`
- Produces:
  - Camera target coordinates accurately center on `cube1` when `active_cube == 0` and `cube2` when `active_cube == 1`.
  - Solver replayer playback updates camera target step-by-step.
  - Full suite passes (145+ tests).

- [ ] **Step 1: Write the failing tests for split-cube tracking and replay tracking**

```python
# Add to tests/test_camera_navigation.py
def test_split_cube_camera_target_switch():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    levels = [load_level_from_json("levels/level_11.json")]
    screen = GameScreen(surface, levels=levels)
    screen.load_level(0)
    screen.camera.mode = CameraMode.FOCUSED

    # Mock a split state
    from core.models import Block
    screen.current_state.block = Block(
        is_split=True,
        cube1=(5, 5),
        cube2=(15, 15),
        active_cube=0
    )
    target_cube1 = screen._get_camera_target_for_block()

    # Switch active cube with SPACE
    event_space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    screen.handle_event(event_space)
    target_cube2 = screen._get_camera_target_for_block()

    assert screen.current_state.block.active_cube == 1
    assert target_cube1 != target_cube2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_camera_navigation.py::test_split_cube_camera_target_switch -v`  
Expected: FAIL with `AttributeError: 'GameScreen' object has no attribute '_get_camera_target_for_block'`

- [ ] **Step 3: Implement `_get_camera_target_for_block` and split-cube tracking in `ui/game_screen.py`**

- Implement helper `_get_camera_target_for_block()` that checks `current_state.block.is_split`:
  - If split, uses `current_state.block.active_cube` coordinates (`cube1` or `cube2`).
  - If assembled, uses `current_state.block.position`.
  - Calculates screen coordinate delta to center within `board_rect`.
- Ensure `SolutionReplayer` stepping and timeline slider dragging smoothly update camera target.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/test_camera_navigation.py -v`  
Expected: PASS

- [ ] **Step 5: Run full regression test suite**

Run: `./.venv/bin/pytest tests/ -q`  
Expected: All tests pass (149+ passed)

- [ ] **Step 6: Commit**

```bash
git add ui/game_screen.py tests/test_camera_navigation.py
git commit -m "feat(camera): add split-cube focus switching and full regression coverage"
```
