"""
Main Application Entry Point for Bloxorz.
Initializes Pygame-CE, opens window, and runs the main 60 FPS event-update-draw loop.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pygame
from config import settings
from ui.game_screen import GameScreen
from ui.menu_screen import MenuScreen
from ui.pause_screen import PauseScreen


PROJECT_ROOT = Path(__file__).resolve().parent
TEST_GROUPS = {
    "core": (
        "tests/test_movement.py",
        "tests/test_game_rules.py",
        "tests/test_core_rules.py",
    ),
    "levels": ("tests/test_levels.py",),
    "gui": ("tests/test_gui_smoke.py",),
    "all": ("tests",),
}


def run_tests(group: str) -> int:
    import pytest

    test_paths = [str(PROJECT_ROOT / path) for path in TEST_GROUPS[group]]
    return int(pytest.main(test_paths))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Bloxorz or a selected test group.")
    parser.add_argument(
        "--test",
        choices=(*TEST_GROUPS,),
        help="run tests for core logic, levels, GUI, or the whole test suite",
    )
    args = parser.parse_args()

    if args.test:
        return run_tests(args.test)

    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption(settings.WINDOW_TITLE)
    clock = pygame.time.Clock()

    running = True
    active_screen = "menu"
    game_screen: GameScreen | None = None

    def start_game() -> None:
        nonlocal game_screen, active_screen
        game_screen = GameScreen(screen)
        active_screen = "game"

    def resume_game() -> None:
        nonlocal active_screen
        active_screen = "game"

    def return_to_menu() -> None:
        nonlocal active_screen
        if game_screen is not None:
            game_screen.cancel_solve()
        active_screen = "menu"

    def quit_game() -> None:
        nonlocal running
        running = False

    menu_screen = MenuScreen(screen, start_game, quit_game)
    pause_screen = PauseScreen(screen, resume_game, return_to_menu)

    try:
        while running:
            dt = min(clock.tick(settings.FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif (
                    active_screen == "game"
                    and event.type == pygame.KEYDOWN
                    and pygame.key.name(event.key) == settings.PAUSE_KEY
                ):
                    active_screen = "pause"
                elif (
                    active_screen == "pause"
                    and event.type == pygame.KEYDOWN
                    and pygame.key.name(event.key) == settings.PAUSE_KEY
                ):
                    resume_game()
                elif active_screen == "menu":
                    menu_screen.handle_event(event)
                elif active_screen == "pause":
                    pause_screen.handle_event(event)
                elif active_screen == "game" and game_screen is not None:
                    game_screen.handle_event(event)

            if active_screen == "menu":
                menu_screen.draw()
            elif active_screen == "pause" and game_screen is not None:
                game_screen.draw()
                pause_screen.draw()
            elif game_screen is not None:
                game_screen.update(dt)
                game_screen.draw()

            pygame.display.flip()

    finally:
        if game_screen is not None:
            game_screen.solver_bridge.cancel()
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
