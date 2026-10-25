"""Manual-only Pygame screen for Bloxorz."""
from __future__ import annotations

import pygame

from config import settings
from core.interfaces import GameState, Level, Orientation, TileType
from core.legacy_adapter import apply_move, initial_state, is_goal, would_break_fragile
from rendering.block_renderer import BlockRenderer
from rendering.board_renderer import BoardRenderer
from ui.button import Button
from ui.dependencies import get_levels, get_mode_badge_text
from ui.result_screen import ResultOverlay


class GameScreen:
    """Coordinates level navigation, manual movement and rendering."""

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.board_rect = pygame.Rect(0, 0, settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT)
        self.sidebar_rect = pygame.Rect(
            settings.BOARD_AREA_WIDTH, 0, settings.SIDEBAR_WIDTH, settings.WINDOW_HEIGHT
        )

        self.font_title = pygame.font.Font(None, 28)
        self.font_section = pygame.font.Font(None, 20)
        self.font_body = pygame.font.Font(None, 18)
        self.font_mono = pygame.font.Font(None, 16)
        self.font_large = pygame.font.Font(None, 36)

        self.board_renderer = BoardRenderer(self.board_rect.width, self.board_rect.height)
        self.block_renderer = BlockRenderer(self.board_renderer)

        self.levels: list[Level] = get_levels()
        self.level_index = 0
        self.level = self.levels[0]
        self.current_state: GameState = initial_state(self.level)
        self.initial_state: GameState = self.current_state
        self.moves_count = 0
        self.outcome_status: str | None = None

        self.buttons: list[Button] = []
        self._init_buttons()

    def _init_buttons(self) -> None:
        bx = self.sidebar_rect.left + 20
        bw = self.sidebar_rect.width - 40
        y = 145
        half_w = (bw - 10) // 2

        self.btn_prev_lvl = Button((bx, y, half_w, 32), "< Prev Level", self.prev_level)
        self.btn_next_lvl = Button((bx + half_w + 10, y, half_w, 32), "Next Level >", self.next_level)
        y += 42
        self.btn_restart = Button((bx, y, bw, 32), "Restart Stage (R)", self.restart_level)
        y += 42
        self.btn_toggle_cube = Button(
            (bx, y, bw, 32),
            "Toggle Cube (SPACE)",
            lambda: self.handle_manual_move("SPACE"),
            enabled=False,
        )
        y += 70
        qtr_w = (bw - 10) // 2
        self.btn_solve_bfs = Button(
            (bx, y, qtr_w, 34), "Solve BFS", enabled=False, primary=True
        )
        self.btn_solve_dfs = Button(
            (bx + qtr_w + 10, y, qtr_w, 34), "Solve DFS", enabled=False, primary=True
        )
        y += 42
        self.btn_solve_ucs = Button(
            (bx, y, qtr_w, 34), "Solve UCS", enabled=False, primary=True
        )
        self.btn_solve_astar = Button(
            (bx + qtr_w + 10, y, qtr_w, 34), "Solve A*", enabled=False, primary=True
        )
        self.buttons = [
            self.btn_prev_lvl,
            self.btn_next_lvl,
            self.btn_restart,
            self.btn_toggle_cube,
            self.btn_solve_bfs,
            self.btn_solve_dfs,
            self.btn_solve_ucs,
            self.btn_solve_astar,
        ]

    def load_level(self, index: int) -> None:
        self.level_index = index % len(self.levels)
        self.level = self.levels[self.level_index]
        self.outcome_status = None
        self.moves_count = 0
        self.initial_state = initial_state(self.level)
        self.current_state = self.initial_state

    def next_level(self) -> None:
        self.load_level(self.level_index + 1)

    def prev_level(self) -> None:
        self.load_level(self.level_index - 1)

    def restart_level(self) -> None:
        self.outcome_status = None
        self.moves_count = 0
        self.current_state = self.initial_state

    def handle_manual_move(self, action: str) -> None:
        if self.outcome_status is not None:
            return

        next_state = apply_move(self.current_state, action, self.level)
        if next_state is None:
            if would_break_fragile(self.current_state, action, self.level):
                self.outcome_status = "LOST_FRAGILE"
                return
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
        for button in self.buttons:
            button.handle_event(event)

        if event.type != pygame.KEYDOWN:
            return
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
        del dt
        self.btn_toggle_cube.enabled = (
            self.current_state.block.is_split and self.outcome_status is None
        )

    def draw(self) -> None:
        self.surface.fill(settings.COLOR_BG)
        self.board_renderer.draw(self.surface, self.level, self.current_state, self.board_rect)
        self.block_renderer.draw(self.surface, self.current_state)

        if self.outcome_status is not None:
            ResultOverlay.draw(
                self.surface,
                self.board_rect,
                self.outcome_status,
                moves_count=self.moves_count,
                font_large=self.font_large,
                font_small=self.font_body,
            )
        self._draw_sidebar()

    def _draw_sidebar(self) -> None:
        pygame.draw.rect(self.surface, settings.COLOR_PANEL_BG, self.sidebar_rect)
        pygame.draw.line(
            self.surface,
            settings.COLOR_PANEL_BORDER,
            self.sidebar_rect.topleft,
            self.sidebar_rect.bottomleft,
            2,
        )

        bx = self.sidebar_rect.left + 20
        self.surface.blit(self.font_title.render("BLOXORZ", True, settings.COLOR_TEXT_MAIN), (bx, 20))
        self.surface.blit(
            self.font_body.render(f"{self.level.name} ({self.level.width}x{self.level.height})", True, settings.COLOR_TEXT_ACCENT),
            (bx, 52),
        )
        self.surface.blit(
            self.font_body.render(f"Difficulty: {self.level.difficulty}", True, settings.COLOR_TEXT_MUTED),
            (bx, 76),
        )
        split_tag = " [SPLIT]" if self.current_state.block.is_split else ""
        self.surface.blit(
            self.font_body.render(f"Moves: {self.moves_count}{split_tag}", True, settings.COLOR_TEXT_MAIN),
            (bx, 100),
        )
        self.surface.blit(
            self.font_mono.render(get_mode_badge_text(), True, settings.COLOR_TEXT_ACCENT),
            (bx, 124),
        )

        self.surface.blit(
            self.font_section.render("SOLVER (NOT AVAILABLE)", True, settings.COLOR_TEXT_MUTED),
            (bx, 285),
        )
        self.surface.blit(self.font_section.render("MANUAL CONTROLS", True, settings.COLOR_TEXT_MUTED), (bx, 420))
        controls = (
            "Arrows / WASD: Roll block",
            "SPACE: Switch split cube",
            "R: Restart   N: Next level",
        )
        for index, text in enumerate(controls):
            self.surface.blit(self.font_body.render(text, True, settings.COLOR_TEXT_MAIN), (bx, 450 + index * 24))

        self.surface.blit(self.font_section.render("LEVEL NOTE", True, settings.COLOR_TEXT_MUTED), (bx, 535))
        description = self.level.description or "Explore the board and reach the goal tile."
        words = description.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > 34 and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        for index, line in enumerate(lines[:5]):
            self.surface.blit(self.font_body.render(line, True, settings.COLOR_TEXT_MUTED), (bx, 565 + index * 22))

        advanced = ", ".join(self.level.advanced_controls)
        if advanced:
            self.surface.blit(self.font_section.render("ADVANCED", True, settings.COLOR_TEXT_MUTED), (bx, 635))
            self.surface.blit(self.font_mono.render(advanced, True, settings.COLOR_TEXT_ACCENT), (bx, 655))

        for button in self.buttons:
            button.draw(self.surface, self.font_body)
