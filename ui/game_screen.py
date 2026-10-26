"""
Main Game Screen coordinating Board, Block, Input, UI Buttons, and Solver Integration.
Implements the 60 FPS event-update-draw loop and maintains main-thread safety.
"""
from __future__ import annotations

import pygame
from config import settings
from core.interfaces import GameState, Level, Orientation, SolverResult, TileType
from rendering.board_renderer import BoardRenderer
from rendering.block_renderer import BlockRenderer
from rendering.isometric_board_renderer import IsometricBoardRenderer
from rendering.isometric_block_renderer import IsometricBlockRenderer
from rendering.animation import SolutionReplayer
from ui.button import Button
from ui.icons import (
    draw_network_icon,
    draw_tree_icon,
    draw_database_icon,
    draw_star_icon,
    draw_play_icon,
    draw_step_back_icon,
    draw_pause_icon,
    draw_step_forward_icon,
    draw_speed_icon,
    draw_metrics_icon,
    draw_eye_icon,
)
from ui.legend_bar import LegendBar
from ui.result_screen import ResultOverlay
from ui.solver_bridge import AsyncSolverBridge, SolverBridgeState
from ui.dependencies import (
    apply_move,
    is_goal,
    get_levels,
    get_mode_badge_text,
)


class GameScreen:
    """Coordinates manual play, rendering, solver execution, and replay."""

    SPEED_PRESETS = [0.5, 1.0, 2.0, 4.0]

    def __init__(self, surface: pygame.Surface, levels: list[Level] | None = None):
        self.surface = surface
        self.board_rect = pygame.Rect(0, 0, settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT)
        self.sidebar_rect = pygame.Rect(
            settings.BOARD_AREA_WIDTH, 0, settings.SIDEBAR_WIDTH, settings.WINDOW_HEIGHT
        )

        # Fonts (Use default font to guarantee cross-platform availability without warnings)
        self.font_title = pygame.font.Font(None, 28)
        self.font_section = pygame.font.Font(None, 20)
        self.font_body = pygame.font.Font(None, 18)
        self.font_mono = pygame.font.Font(None, 16)
        self.font_large = pygame.font.Font(None, 36)

        # Renderers
        self.board_renderer = BoardRenderer(self.board_rect.width, self.board_rect.height)
        self.block_renderer = BlockRenderer(self.board_renderer)
        self.iso_board_renderer = IsometricBoardRenderer(self.board_rect.width, self.board_rect.height)
        self.iso_block_renderer = IsometricBlockRenderer(self.iso_board_renderer)

        # View mode: "2D" (default) or "3D"
        self.view_mode = "2D"

        # Algorithm selection & Legend Bar
        self.selected_algo: str = "BFS"
        self.legend_bar = LegendBar()

        # Available levels
        self.levels: list[Level] = list(levels) if levels is not None else get_levels()
        self.level_index = 0
        self.level: Level = self.levels[0]

        # State & Session
        init_mask = getattr(self.level, "initial_bridge_mask", 0)
        self.current_state: GameState = GameState(block=self.level.start, bridge_mask=init_mask)
        self.initial_state: GameState = self.current_state
        self.moves_count = 0
        self.outcome_status: str | None = None  # None, "WIN", "LOST_FALL", "LOST_FRAGILE", "UNSOLVABLE"

        # Solver & Replay
        self.solver_bridge = AsyncSolverBridge()
        self.latest_result: SolverResult | None = None
        self.replayer: SolutionReplayer | None = None

        # Playback speed settings
        self.speed_preset_idx = 1  # Default 1.0x

        # Build UI Buttons
        self.buttons: list[Button] = []
        self._init_buttons()

    def _init_buttons(self) -> None:
        card_x = self.sidebar_rect.left + 14
        card_w = self.sidebar_rect.width - 28

        # --- Top Level Switcher / View Controls ---
        top_btn_w = (card_w - 8) // 2
        self.btn_prev_lvl = Button((card_x, 78, top_btn_w, 28), "< Prev Level", self.prev_level)
        self.btn_next_lvl = Button((card_x + top_btn_w + 8, 78, top_btn_w, 28), "Next Level >", self.next_level)

        self.btn_restart = Button((card_x, 110, top_btn_w, 28), "Restart (R)", self.restart_level)
        self.btn_view_mode = Button(
            (card_x + top_btn_w + 8, 110, top_btn_w, 28),
            f"View: {self.view_mode}",
            self.cycle_view_mode,
            icon_drawer=draw_eye_icon,
            icon_position="right",
        )

        # --- Card 1: Algorithm (2x2 grid) ---
        algo_w = (card_w - 20 - 8) // 2
        algo_h = 30
        c1_left = card_x + 10
        c2_left = c1_left + algo_w + 8
        r1_y = 176
        r2_y = 212

        self.btn_algo_bfs = Button(
            (c1_left, r1_y, algo_w, algo_h),
            "BFS",
            lambda: self.select_algo("BFS"),
            icon_drawer=draw_network_icon,
            selected=(self.selected_algo == "BFS"),
        )
        self.btn_algo_dfs = Button(
            (c2_left, r1_y, algo_w, algo_h),
            "DFS",
            lambda: self.select_algo("DFS"),
            icon_drawer=draw_tree_icon,
            selected=(self.selected_algo == "DFS"),
        )
        self.btn_algo_ucs = Button(
            (c1_left, r2_y, algo_w, algo_h),
            "UCS",
            lambda: self.select_algo("UCS"),
            icon_drawer=draw_database_icon,
            selected=(self.selected_algo == "UCS"),
        )
        self.btn_algo_astar = Button(
            (c2_left, r2_y, algo_w, algo_h),
            "A*",
            lambda: self.select_algo("A*"),
            icon_drawer=draw_star_icon,
            selected=(self.selected_algo in ("A*", "ASTAR")),
        )

        # Backward compatibility aliases
        self.btn_solve_bfs = self.btn_algo_bfs
        self.btn_solve_dfs = self.btn_algo_dfs
        self.btn_solve_ucs = self.btn_algo_ucs
        self.btn_solve_astar = self.btn_algo_astar
        self.algo_buttons = {
            "BFS": self.btn_algo_bfs,
            "DFS": self.btn_algo_dfs,
            "UCS": self.btn_algo_ucs,
            "A*": self.btn_algo_astar,
            "ASTAR": self.btn_algo_astar,
        }

        # --- Card 2: Playback Controls ---
        inner_w = card_w - 20
        self.btn_solve_action = Button(
            (card_x + 10, 290, inner_w, 32),
            f"Solve ({self.selected_algo})",
            self.trigger_selected_solve,
            primary=True,
            icon_drawer=draw_play_icon,
        )
        self.btn_cancel = self.btn_solve_action  # Alias for backward compatibility

        # Step replay row: [◀◀ Step] [❚❚ Pause] [Step Forward ▶▶]
        step_w = (inner_w - 12) // 3
        step_w_mid = inner_w - 2 * step_w - 12
        self.btn_replay_prev = Button(
            (card_x + 10, 328, step_w, 28),
            "Step",
            self.replay_prev_step,
            icon_drawer=draw_step_back_icon,
            enabled=False,
        )
        self.btn_replay_toggle = Button(
            (card_x + 10 + step_w + 6, 328, step_w_mid, 28),
            "Pause",
            self.replay_toggle_play,
            icon_drawer=draw_pause_icon,
            enabled=False,
        )
        self.btn_replay_next = Button(
            (card_x + 10 + step_w + 6 + step_w_mid + 6, 328, step_w, 28),
            "Step",
            self.replay_next_step,
            icon_drawer=draw_step_forward_icon,
            enabled=False,
        )

        # Playback speed button
        self.btn_speed = Button(
            (card_x + 10, 362, inner_w, 28),
            f"Speed: {self.SPEED_PRESETS[self.speed_preset_idx]}x",
            self.cycle_speed,
            icon_drawer=draw_speed_icon,
            enabled=True,
        )

        self.buttons = [
            self.btn_prev_lvl,
            self.btn_next_lvl,
            self.btn_restart,
            self.btn_view_mode,
            self.btn_algo_bfs,
            self.btn_algo_dfs,
            self.btn_algo_ucs,
            self.btn_algo_astar,
            self.btn_solve_action,
            self.btn_replay_prev,
            self.btn_replay_toggle,
            self.btn_replay_next,
            self.btn_speed,
        ]

    def select_algo(self, algo: str) -> None:
        """Selects an active algorithm and updates button selection highlights and solve action label."""
        self.selected_algo = algo
        target = "A*" if algo in ("A*", "ASTAR") else algo
        self.btn_algo_bfs.selected = (target == "BFS")
        self.btn_algo_dfs.selected = (target == "DFS")
        self.btn_algo_ucs.selected = (target == "UCS")
        self.btn_algo_astar.selected = (target == "A*")
        if self.solver_bridge.state != SolverBridgeState.RUNNING:
            self.btn_solve_action.text = f"Solve ({self.selected_algo})"

    def trigger_selected_solve(self) -> None:
        """Triggers or cancels solver based on current bridge state."""
        if self.solver_bridge.state == SolverBridgeState.RUNNING:
            self.cancel_solve()
        else:
            self.trigger_solve(self.selected_algo)

    def load_level(self, index: int) -> None:
        self.level_index = index % len(self.levels)
        self.level = self.levels[self.level_index]
        self.solver_bridge.cancel()
        self.replayer = None
        self.latest_result = None
        self.outcome_status = None
        self.moves_count = 0
        init_mask = getattr(self.level, "initial_bridge_mask", 0)
        self.initial_state = GameState(block=self.level.start, bridge_mask=init_mask)
        self.current_state = self.initial_state

    def next_level(self) -> None:
        self.load_level(self.level_index + 1)

    def prev_level(self) -> None:
        self.load_level(self.level_index - 1)

    def restart_level(self) -> None:
        self.solver_bridge.cancel()
        self.replayer = None
        self.outcome_status = None
        self.moves_count = 0
        self.current_state = self.initial_state

    def trigger_solve(self, algo: str) -> None:
        if self.solver_bridge.state == SolverBridgeState.RUNNING:
            return
        self.select_algo(algo)
        self.replayer = None
        self.latest_result = None
        self.outcome_status = None
        self.solver_bridge.start_solve(algo, self.level, self.current_state)

    def cancel_solve(self) -> None:
        self.solver_bridge.cancel()

    def replay_toggle_play(self) -> None:
        if self.replayer:
            self.replayer.toggle_pause()
            if not self.replayer.is_playing:
                self.btn_replay_toggle.text = "Play"
                self.btn_replay_toggle.icon_drawer = draw_play_icon
            else:
                self.btn_replay_toggle.text = "Pause"
                self.btn_replay_toggle.icon_drawer = draw_pause_icon

    def replay_prev_step(self) -> None:
        if self.replayer:
            self.replayer.step_backward()

    def replay_next_step(self) -> None:
        if self.replayer:
            self.replayer.step_forward()

    def cycle_speed(self) -> None:
        self.speed_preset_idx = (self.speed_preset_idx + 1) % len(self.SPEED_PRESETS)
        mult = self.SPEED_PRESETS[self.speed_preset_idx]
        self.btn_speed.text = f"Speed: {mult}x"
        if self.replayer:
            self.replayer.set_speed_multiplier(mult)

    def cycle_view_mode(self) -> None:
        """Toggles view mode between 2D top-down and 3D isometric view."""
        self.view_mode = "3D" if self.view_mode == "2D" else "2D"
        if hasattr(self, "btn_view_mode"):
            self.btn_view_mode.text = f"View: {self.view_mode}"

    def handle_manual_move(self, action: str) -> None:
        """Processes manual roll or spacebar cube toggle."""
        if self.outcome_status is not None or self.solver_bridge.state == SolverBridgeState.RUNNING:
            return

        # If replayer is active, cancel it when user makes manual move
        if self.replayer:
            self.replayer = None

        next_state = apply_move(self.current_state, action, self.level)
        if next_state is None:
            # Check why it's illegal
            if self.current_state.block.orientation == Orientation.STANDING:
                stand_cell = (self.current_state.block.r, self.current_state.block.c)
                if self.level.tiles.get(stand_cell) == TileType.FRAGILE:
                    self.outcome_status = "LOST_FRAGILE"
                    return
            self.outcome_status = "LOST_FALL"
            return

        self.current_state = next_state
        self.moves_count += 1

        if is_goal(self.current_state, self.level):
            self.outcome_status = "WIN"

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handles keyboard and mouse events."""
        # 1. Pass to UI buttons
        for btn in self.buttons:
            btn.handle_event(event)

        # 2. Key presses for manual gameplay
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.handle_manual_move("U")
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.handle_manual_move("D")
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.handle_manual_move("L")
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.handle_manual_move("R")
            elif event.key == pygame.K_SPACE:
                self.handle_manual_move("SPACE")
            elif event.key == pygame.K_r:
                self.restart_level()
            elif event.key == pygame.K_n:
                self.next_level()
            elif event.key == pygame.K_v:
                self.cycle_view_mode()

    def update(self, dt: float) -> None:
        """Polls async solver and updates replay animations."""
        # 1. Poll solver worker
        if self.solver_bridge.state == SolverBridgeState.RUNNING:
            res = self.solver_bridge.poll()
            if res:
                self.latest_result = res
                if res.success and res.path:
                    current_speed = self.SPEED_PRESETS[self.speed_preset_idx]
                    self.replayer = SolutionReplayer(
                        self.level,
                        self.current_state,
                        res.path,
                        speed_multiplier=current_speed,
                    )
                    self.btn_replay_toggle.text = "Pause"
                    self.btn_replay_toggle.icon_drawer = draw_pause_icon
                else:
                    self.outcome_status = "UNSOLVABLE"

        # 2. Update button enabled & label states
        is_solving = (self.solver_bridge.state == SolverBridgeState.RUNNING)
        if is_solving:
            self.btn_solve_action.text = "Cancel Search"
            self.btn_solve_action.icon_drawer = draw_pause_icon
            self.btn_solve_action.primary = False
        else:
            self.btn_solve_action.text = f"Solve ({self.selected_algo})"
            self.btn_solve_action.icon_drawer = draw_play_icon
            self.btn_solve_action.primary = True

        self.btn_algo_bfs.enabled = not is_solving
        self.btn_algo_dfs.enabled = not is_solving
        self.btn_algo_ucs.enabled = not is_solving
        self.btn_algo_astar.enabled = not is_solving

        has_replayer = (self.replayer is not None)
        self.btn_replay_prev.enabled = has_replayer
        self.btn_replay_toggle.enabled = has_replayer
        self.btn_replay_next.enabled = has_replayer
        self.btn_speed.enabled = True

        # 3. Update Replay
        if self.replayer:
            self.replayer.update(dt)
            self.current_state = self.replayer.current_state
            if self.replayer.is_playing:
                self.btn_replay_toggle.text = "Pause"
                self.btn_replay_toggle.icon_drawer = draw_pause_icon
            else:
                self.btn_replay_toggle.text = "Play"
                self.btn_replay_toggle.icon_drawer = draw_play_icon

            if self.replayer.is_finished and is_goal(self.current_state, self.level):
                self.outcome_status = "WIN"

    def draw(self) -> None:
        """Paints the board, block, sidebar, legend bar, and status overlays."""
        # Clear background
        self.surface.fill(settings.COLOR_BG)

        # 1. Draw Board & Block
        if self.view_mode == "3D":
            self.iso_board_renderer.draw(self.surface, self.level, self.current_state, self.board_rect)
            self.iso_block_renderer.draw(self.surface, self.current_state)
        else:
            self.board_renderer.draw(self.surface, self.level, self.current_state, self.board_rect)
            self.block_renderer.draw(self.surface, self.current_state)

        # 2. Draw Win/Loss Overlay if applicable
        if self.outcome_status is not None:
            ResultOverlay.draw(
                self.surface,
                self.board_rect,
                self.outcome_status,
                moves_count=self.moves_count,
                font_large=self.font_large,
                font_small=self.font_body,
            )

        # 3. Draw Legend Bar docked at the bottom of the board area
        self.legend_bar.draw(self.surface, self.board_rect, self.font_mono)

        # 4. Draw Sidebar Panel
        self._draw_sidebar()

    def _draw_sidebar(self) -> None:
        # Background
        pygame.draw.rect(self.surface, settings.COLOR_PANEL_BG, self.sidebar_rect)
        pygame.draw.line(
            self.surface,
            settings.COLOR_PANEL_BORDER,
            self.sidebar_rect.topleft,
            self.sidebar_rect.bottomleft,
            2,
        )

        card_x = self.sidebar_rect.left + 14
        card_w = self.sidebar_rect.width - 28

        # --- Header Info: Title, Level details, Moves count, Mode Badge ---
        t_surf = self.font_title.render("BLOXORZ SOLVER", True, settings.COLOR_TEXT_MAIN)
        self.surface.blit(t_surf, (card_x, 14))

        lvl_info = f"{self.level.name} ({self.level.width}x{self.level.height})"
        lvl_surf = self.font_body.render(lvl_info, True, settings.COLOR_TEXT_ACCENT)
        self.surface.blit(lvl_surf, (card_x, 40))

        split_tag = " [SPLIT]" if self.current_state.block.is_split else ""
        stats_info = f"Moves: {self.moves_count}{split_tag}"
        stats_surf = self.font_body.render(stats_info, True, settings.COLOR_TEXT_MAIN)
        self.surface.blit(stats_surf, (card_x, 58))

        badge_text = get_mode_badge_text()
        badge_color = (70, 210, 245) if badge_text == "[REAL]" else (255, 160, 40)
        badge_surf = self.font_mono.render(badge_text, True, badge_color)
        self.surface.blit(badge_surf, (card_x + card_w - badge_surf.get_width(), 58))

        # --- Card 1: Algorithm (2x2 grid container) ---
        card1_rect = pygame.Rect(card_x, 144, card_w, 106)
        pygame.draw.rect(self.surface, settings.COLOR_CARD_BG, card1_rect, border_radius=8)
        pygame.draw.rect(self.surface, settings.COLOR_CARD_BORDER, card1_rect, 1, border_radius=8)

        draw_network_icon(self.surface, pygame.Rect(card_x + 12, 154, 14, 14), settings.COLOR_CARD_HEADER)
        c1_title = self.font_section.render("Algorithm", True, settings.COLOR_CARD_HEADER)
        self.surface.blit(c1_title, (card_x + 32, 153))

        # --- Card 2: Playback Controls Container ---
        card2_rect = pygame.Rect(card_x, 258, card_w, 142)
        pygame.draw.rect(self.surface, settings.COLOR_CARD_BG, card2_rect, border_radius=8)
        pygame.draw.rect(self.surface, settings.COLOR_CARD_BORDER, card2_rect, 1, border_radius=8)

        draw_play_icon(self.surface, pygame.Rect(card_x + 12, 268, 14, 14), settings.COLOR_CARD_HEADER)
        c2_title = self.font_section.render("Playback", True, settings.COLOR_CARD_HEADER)
        self.surface.blit(c2_title, (card_x + 32, 267))

        if self.replayer:
            step_str = f"Step: {self.replayer.current_index}/{self.replayer.total_steps}"
            step_surf = self.font_mono.render(step_str, True, settings.COLOR_TEXT_ACCENT)
            self.surface.blit(step_surf, (card_x + card_w - 12 - step_surf.get_width(), 268))
        elif self.solver_bridge.state == SolverBridgeState.RUNNING:
            spin_txt = f"Searching ({self.solver_bridge.current_algo})..."
            st_surf = self.font_mono.render(spin_txt, True, (255, 215, 0))
            self.surface.blit(st_surf, (card_x + card_w - 12 - st_surf.get_width(), 268))
        elif self.solver_bridge.state == SolverBridgeState.CANCELLED:
            st_surf = self.font_mono.render("Search cancelled.", True, settings.COLOR_TEXT_MUTED)
            self.surface.blit(st_surf, (card_x + card_w - 12 - st_surf.get_width(), 268))

        # --- Card 3: Solution Metrics Telemetry Container ---
        card3_rect = pygame.Rect(card_x, 408, card_w, 154)
        pygame.draw.rect(self.surface, settings.COLOR_CARD_BG, card3_rect, border_radius=8)
        pygame.draw.rect(self.surface, settings.COLOR_CARD_BORDER, card3_rect, 1, border_radius=8)

        draw_metrics_icon(self.surface, pygame.Rect(card_x + 12, 418, 14, 14), settings.COLOR_CARD_HEADER)
        c3_title = self.font_section.render("Solution Metrics", True, settings.COLOR_CARD_HEADER)
        self.surface.blit(c3_title, (card_x + 32, 417))

        if self.latest_result:
            r = self.latest_result
            time_val = f"{r.search_time_ms:.1f} ms"
            mem_val = f"{r.peak_memory_kb:.1f} KB" if isinstance(r.peak_memory_kb, float) else f"{r.peak_memory_kb:,} KB"
            exp_val = f"{r.expanded_nodes:,} nodes"
            len_val = f"{r.solution_length} moves"
            cost_val = f"{r.cost:.0f}"
        else:
            time_val = "-- ms"
            mem_val = "-- KB"
            exp_val = "-- nodes"
            len_val = "-- moves"
            cost_val = "--"

        metrics_rows = [
            ("Time:", time_val),
            ("Memory:", mem_val),
            ("Expanded:", exp_val),
            ("Length:", len_val),
            ("Cost:", cost_val),
        ]

        for i, (key, val) in enumerate(metrics_rows):
            row_y = 440 + i * 21
            key_surf = self.font_mono.render(f"{key:<12}", True, settings.COLOR_METRIC_LABEL)
            val_surf = self.font_mono.render(val, True, settings.COLOR_METRIC_VALUE)
            self.surface.blit(key_surf, (card_x + 14, row_y))
            self.surface.blit(val_surf, (card_x + card_w - 14 - val_surf.get_width(), row_y))

        # --- Hotkeys Footer ---
        footer_y = 574
        h_surf1 = self.font_mono.render("Arrows / WASD: Roll | R: Restart", True, (110, 120, 140))
        h_surf2 = self.font_mono.render("Space: Switch Cube | N: Next Level", True, (110, 120, 140))
        h_surf3 = self.font_mono.render("V: Toggle 2D/3D", True, (110, 120, 140))
        self.surface.blit(h_surf1, (card_x, footer_y))
        self.surface.blit(h_surf2, (card_x, footer_y + 16))
        self.surface.blit(h_surf3, (card_x, footer_y + 32))

        # Render all buttons
        for btn in self.buttons:
            btn.draw(self.surface, self.font_body)
