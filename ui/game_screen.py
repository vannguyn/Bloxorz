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
from rendering.animation import SolutionReplayer
from ui.button import Button
from ui.result_screen import ResultOverlay
from ui.solver_bridge import AsyncSolverBridge, SolverBridgeState

# Swappable imports (mock core until M1 merge)
from tests.mocks import (
    apply_move,
    is_goal,
    mock_level_simple,
    mock_level_with_fragile,
    mock_level_with_bridge,
    mock_level_split,
)


class GameScreen:
    """Coordinates manual play, rendering, solver execution, and replay."""

    def __init__(self, surface: pygame.Surface):
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

        # Available levels
        self.levels: list[Level] = [
            mock_level_simple(),
            mock_level_with_fragile(),
            mock_level_with_bridge(),
            mock_level_split(),
        ]
        self.level_index = 0
        self.level: Level = self.levels[0]

        # State & Session
        self.current_state: GameState = GameState(block=self.level.start, bridge_mask=0)
        self.initial_state: GameState = self.current_state
        self.moves_count = 0
        self.outcome_status: str | None = None  # None, "WIN", "LOST_FALL", "LOST_FRAGILE", "UNSOLVABLE"

        # Solver & Replay
        self.solver_bridge = AsyncSolverBridge()
        self.latest_result: SolverResult | None = None
        self.replayer: SolutionReplayer | None = None

        # Build UI Buttons
        self.buttons: list[Button] = []
        self._init_buttons()

    def _init_buttons(self) -> None:
        bx = self.sidebar_rect.left + 20
        bw = self.sidebar_rect.width - 40
        y = 145

        # Level switcher
        half_w = (bw - 10) // 2
        self.btn_prev_lvl = Button((bx, y, half_w, 32), "< Prev Level", self.prev_level)
        self.btn_next_lvl = Button((bx + half_w + 10, y, half_w, 32), "Next Level >", self.next_level)
        y += 42

        # Restart
        self.btn_restart = Button((bx, y, bw, 32), "Restart Stage (R)", self.restart_level)
        y += 50

        # Solvers
        y += 24  # Space for section title
        qtr_w = (bw - 10) // 2
        self.btn_solve_bfs = Button((bx, y, qtr_w, 34), "Solve BFS", lambda: self.trigger_solve("BFS"), primary=True)
        self.btn_solve_dfs = Button((bx + qtr_w + 10, y, qtr_w, 34), "Solve DFS", lambda: self.trigger_solve("DFS"), primary=True)
        y += 42
        self.btn_solve_ucs = Button((bx, y, qtr_w, 34), "Solve UCS", lambda: self.trigger_solve("UCS"), primary=True)
        self.btn_solve_astar = Button((bx + qtr_w + 10, y, qtr_w, 34), "Solve A*", lambda: self.trigger_solve("ASTAR"), primary=True)
        y += 46

        # Cancel button (for running search)
        self.btn_cancel = Button((bx, y, bw, 32), "Cancel Search", self.cancel_solve, enabled=False)
        y += 48

        # Replay controls
        rep_btn_w = (bw - 20) // 3
        self.btn_replay_prev = Button((bx, y, rep_btn_w, 30), "< Step", self.replay_prev_step)
        self.btn_replay_toggle = Button((bx + rep_btn_w + 10, y, rep_btn_w, 30), "Pause", self.replay_toggle_play)
        self.btn_replay_next = Button((bx + (rep_btn_w + 10) * 2, y, rep_btn_w, 30), "Step >", self.replay_next_step)

        self.buttons = [
            self.btn_prev_lvl,
            self.btn_next_lvl,
            self.btn_restart,
            self.btn_solve_bfs,
            self.btn_solve_dfs,
            self.btn_solve_ucs,
            self.btn_solve_astar,
            self.btn_cancel,
            self.btn_replay_prev,
            self.btn_replay_toggle,
            self.btn_replay_next,
        ]

    def load_level(self, index: int) -> None:
        self.level_index = index % len(self.levels)
        self.level = self.levels[self.level_index]
        self.solver_bridge.cancel()
        self.replayer = None
        self.latest_result = None
        self.outcome_status = None
        self.moves_count = 0
        self.initial_state = GameState(block=self.level.start, bridge_mask=0)
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
        self.replayer = None
        self.latest_result = None
        self.outcome_status = None
        self.solver_bridge.start_solve(algo, self.level, self.current_state)

    def cancel_solve(self) -> None:
        self.solver_bridge.cancel()

    def replay_toggle_play(self) -> None:
        if self.replayer:
            self.replayer.toggle_pause()
            self.btn_replay_toggle.text = "Play" if not self.replayer.is_playing else "Pause"

    def replay_prev_step(self) -> None:
        if self.replayer:
            self.replayer.step_backward()

    def replay_next_step(self) -> None:
        if self.replayer:
            self.replayer.step_forward()

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

    def update(self, dt: float) -> None:
        """Polls async solver and updates replay animations."""
        # 1. Poll solver worker
        if self.solver_bridge.state == SolverBridgeState.RUNNING:
            res = self.solver_bridge.poll()
            if res:
                self.latest_result = res
                if res.success and res.path:
                    self.replayer = SolutionReplayer(self.level, self.current_state, res.path)
                    self.btn_replay_toggle.text = "Pause"
                else:
                    self.outcome_status = "UNSOLVABLE"

        # 2. Update button enabled states
        is_solving = (self.solver_bridge.state == SolverBridgeState.RUNNING)
        self.btn_cancel.enabled = is_solving
        self.btn_solve_bfs.enabled = not is_solving
        self.btn_solve_dfs.enabled = not is_solving
        self.btn_solve_ucs.enabled = not is_solving
        self.btn_solve_astar.enabled = not is_solving

        has_replayer = (self.replayer is not None)
        self.btn_replay_prev.enabled = has_replayer
        self.btn_replay_toggle.enabled = has_replayer
        self.btn_replay_next.enabled = has_replayer

        # 3. Update Replay
        if self.replayer:
            self.replayer.update(dt)
            self.current_state = self.replayer.current_state
            if self.replayer.is_finished and is_goal(self.current_state, self.level):
                self.outcome_status = "WIN"

    def draw(self) -> None:
        """Paints the board, block, sidebar, and status overlays."""
        # Clear background
        self.surface.fill(settings.COLOR_BG)

        # 1. Draw Board & Block
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

        # 3. Draw Sidebar Panel
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

        bx = self.sidebar_rect.left + 20
        y = 20

        # Title
        t_surf = self.font_title.render("BLOXORZ SOLVER", True, settings.COLOR_TEXT_MAIN)
        self.surface.blit(t_surf, (bx, y))
        y += 32

        # Level details
        lvl_info = f"{self.level.name} ({self.level.width}x{self.level.height})"
        lvl_surf = self.font_body.render(lvl_info, True, settings.COLOR_TEXT_ACCENT)
        self.surface.blit(lvl_surf, (bx, y))
        y += 24

        # Move count & status
        split_tag = " [SPLIT]" if self.current_state.block.is_split else ""
        stats_info = f"Moves: {self.moves_count}{split_tag}"
        stats_surf = self.font_body.render(stats_info, True, settings.COLOR_TEXT_MAIN)
        self.surface.blit(stats_surf, (bx, y))
        y += 24

        # Section: Controls
        y = 230
        sec_surf = self.font_section.render("SOLVER ALGORITHMS", True, settings.COLOR_TEXT_MUTED)
        self.surface.blit(sec_surf, (bx, y))

        # Status indicator
        status_y = 368
        if self.solver_bridge.state == SolverBridgeState.RUNNING:
            spin_txt = f"Searching ({self.solver_bridge.current_algo})..."
            st_surf = self.font_body.render(spin_txt, True, (255, 215, 0))
            self.surface.blit(st_surf, (bx, status_y))
        elif self.solver_bridge.state == SolverBridgeState.CANCELLED:
            st_surf = self.font_body.render("Search cancelled.", True, settings.COLOR_TEXT_MUTED)
            self.surface.blit(st_surf, (bx, status_y))

        # Replay Section Title
        rep_y = 398
        rep_lbl = self.font_section.render("SOLUTION REPLAY", True, settings.COLOR_TEXT_MUTED)
        self.surface.blit(rep_lbl, (bx, rep_y))

        if self.replayer:
            step_str = f"Step: {self.replayer.current_index}/{self.replayer.total_steps}"
            step_surf = self.font_body.render(step_str, True, settings.COLOR_TEXT_ACCENT)
            self.surface.blit(step_surf, (bx + 175, rep_y + 2))

        # Metrics Box
        box_y = 475
        box_h = 135
        box_rect = pygame.Rect(bx, box_y, self.sidebar_rect.width - 40, box_h)
        pygame.draw.rect(self.surface, (20, 24, 34), box_rect, border_radius=6)
        pygame.draw.rect(self.surface, settings.COLOR_PANEL_BORDER, box_rect, 1, border_radius=6)

        m_title = self.font_section.render("SEARCH METRICS", True, settings.COLOR_TEXT_MAIN)
        self.surface.blit(m_title, (bx + 12, box_y + 8))

        if self.latest_result:
            r = self.latest_result
            lines = [
                f"Time:       {r.search_time_ms:6.2f} ms",
                f"Memory:     {r.peak_memory_kb:6d} KB",
                f"Expanded:   {r.expanded_nodes:6d} nodes",
                f"Length:     {r.solution_length:6d} moves",
                f"Cost:       {r.cost:6.1f}",
            ]
        else:
            lines = [
                "Time:         -- ms",
                "Memory:       -- KB",
                "Expanded:     -- nodes",
                "Length:       -- moves",
                "Cost:         --",
            ]

        for i, line in enumerate(lines):
            line_surf = self.font_mono.render(line, True, settings.COLOR_TEXT_MUTED)
            self.surface.blit(line_surf, (bx + 12, box_y + 32 + i * 18))

        # Hotkeys footer
        footer_y = 625
        h_surf1 = self.font_mono.render("Arrows/WASD: Roll  |  R: Restart", True, (110, 120, 140))
        h_surf2 = self.font_mono.render("SPACE: Switch Cube |  N: Next Level", True, (110, 120, 140))
        self.surface.blit(h_surf1, (bx, footer_y))
        self.surface.blit(h_surf2, (bx, footer_y + 18))

        # Render all buttons
        for btn in self.buttons:
            btn.draw(self.surface, self.font_body)
