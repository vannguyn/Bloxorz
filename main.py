"""
Main Application Entry Point for Bloxorz.
Initializes Pygame-CE, opens window, and runs the main 60 FPS event-update-draw loop.
"""
from __future__ import annotations

import argparse
import os
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface for launching or testing the game."""
    parser = argparse.ArgumentParser(
        description="Run Bloxorz or execute the project's pytest suite."
    )
    parser.add_argument(
        "--test",
        nargs="?",
        const="tests",
        metavar="PATH",
        help="run pytest; optionally provide a test file or directory",
    )
    parser.add_argument(
        "-k",
        "--test-filter",
        dest="test_filter",
        metavar="EXPR",
        help="pytest keyword expression used together with --test",
    )
    parser.add_argument(
        "-v",
        "--verbose-tests",
        action="store_true",
        help="show verbose pytest output when running tests",
    )
    parser.add_argument(
        "-q",
        "--quiet-tests",
        action="store_true",
        help="show compact pytest output when running tests",
    )
    return parser


def run_tests(
    target: str = "tests",
    test_filter: str | None = None,
    verbose: bool = False,
    quiet: bool = False,
) -> int:
    """Run pytest in headless mode and return pytest's exit code."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"

    import pytest

    pytest_args = [target]
    if test_filter:
        pytest_args.extend(["-k", test_filter])
    if verbose:
        pytest_args.append("-v")
    if quiet:
        pytest_args.append("-q")
    return int(pytest.main(pytest_args))


def run_game() -> None:
    """Start the normal interactive game loop."""
    import pygame

    from config import settings
    from ui.game_screen import GameScreen

    pygame.init()
    pygame.font.init()

    # Create display surface
    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption("Bloxorz Solver — AI Project 1")
    clock = pygame.time.Clock()

    game_screen = GameScreen(screen)
    running = True

    try:
        while running:
            # Cap at 60 FPS and compute delta time in seconds
            dt = clock.tick(settings.FPS) / 1000.0
            dt = min(dt, 0.05)  # Clamp against debug/drag stalls

            # Event pump
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                else:
                    game_screen.handle_event(event)

            # Update & Render
            game_screen.update(dt)
            game_screen.draw()
            pygame.display.flip()

    finally:
        # Clean up solver worker process if any
        game_screen.solver_bridge.cancel()
        pygame.quit()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the game or the requested test command."""
    args = build_parser().parse_args(argv)

    if args.test is not None:
        return run_tests(
            target=args.test,
            test_filter=args.test_filter,
            verbose=args.verbose_tests,
            quiet=args.quiet_tests,
        )

    if args.test_filter or args.verbose_tests or args.quiet_tests:
        raise SystemExit("test options require --test")

    run_game()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
