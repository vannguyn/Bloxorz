"""
Main Application Entry Point for Bloxorz.
Initializes Pygame-CE, opens window, and runs the main 60 FPS event-update-draw loop.
"""
from __future__ import annotations

import sys
import pygame
from config import settings
from ui.game_screen import GameScreen


def main() -> None:
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


if __name__ == "__main__":
    main()
