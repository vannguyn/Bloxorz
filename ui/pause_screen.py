"""Pause overlay with resume and return-to-menu actions."""

from __future__ import annotations

from collections.abc import Callable

import pygame

from config import settings
from ui.button import Button


class PauseScreen:
    def __init__(
        self,
        surface: pygame.Surface,
        on_resume: Callable[[], None],
        on_menu: Callable[[], None],
    ) -> None:
        self.surface = surface
        self.title_font = pygame.font.Font(None, 48)
        self.button_font = pygame.font.Font(None, 24)
        center_x = surface.get_width() // 2
        center_y = surface.get_height() // 2
        self.buttons = [
            Button((center_x - 120, center_y - 4, 240, 44), "Resume", on_resume, primary=True),
            Button((center_x - 120, center_y + 52, 240, 44), "Main Menu", on_menu),
        ]

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)

    def draw(self) -> None:
        overlay = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        overlay.fill((15, 18, 26, 190))
        self.surface.blit(overlay, (0, 0))

        title = self.title_font.render("PAUSED", True, settings.COLOR_TEXT_MAIN)
        self.surface.blit(title, title.get_rect(center=(self.surface.get_width() // 2, self.surface.get_height() // 2 - 62)))
        for button in self.buttons:
            button.draw(self.surface, self.button_font)