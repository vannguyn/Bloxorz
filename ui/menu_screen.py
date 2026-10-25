"""Start menu for the game."""

from __future__ import annotations

from collections.abc import Callable

import pygame

from config import settings
from ui.button import Button


class MenuScreen:
    def __init__(
        self,
        surface: pygame.Surface,
        on_start: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self.surface = surface
        self.on_quit = on_quit
        self.title_font = pygame.font.Font(None, 64)
        self.button_font = pygame.font.Font(None, 28)
        center_x = surface.get_width() // 2
        center_y = surface.get_height() // 2
        self.buttons = [
            Button((center_x - 120, center_y - 10, 240, 48), "Start Game", on_start, primary=True),
            Button((center_x - 120, center_y + 52, 240, 48), "Quit", on_quit),
        ]

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)

    def draw(self) -> None:
        self.surface.fill(settings.COLOR_BG)
        title = self.title_font.render("BLOXORZ", True, settings.COLOR_TEXT_MAIN)
        self.surface.blit(title, title.get_rect(center=(self.surface.get_width() // 2, self.surface.get_height() // 3)))
        for button in self.buttons:
            button.draw(self.surface, self.button_font)