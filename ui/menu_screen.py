"""Start menu shown before the first Bloxorz game session."""
from __future__ import annotations

import pygame
from config import settings
from ui.button import Button


class MenuScreen:
    """Draws the launch screen and handles starting the game."""

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.started = False
        self.font_title = pygame.font.Font(None, 76)
        self.font_subtitle = pygame.font.Font(None, 26)
        self.font_hint = pygame.font.Font(None, 20)
        self.font_button = pygame.font.Font(None, 28)
        button_rect = pygame.Rect(0, 0, 240, 56)
        button_rect.center = (surface.get_width() // 2, surface.get_height() // 2 + 46)
        self.start_button = Button(
            button_rect,
            "START GAME",
            self._start_game,
            primary=True,
        )

    def _start_game(self) -> None:
        self.started = True

    def handle_event(self, event: pygame.event.Event) -> None:
        """Passes input to the start button."""
        self.start_button.handle_event(event)

    def draw(self) -> None:
        """Renders the game title, start button, and control hint."""
        self.surface.fill(settings.COLOR_BG)

        center_x = self.surface.get_width() // 2
        center_y = self.surface.get_height() // 2

        panel = pygame.Rect(0, 0, 520, 360)
        panel.center = (center_x, center_y)
        pygame.draw.rect(self.surface, settings.COLOR_CARD_BG, panel, border_radius=18)
        pygame.draw.rect(
            self.surface,
            settings.COLOR_PANEL_BORDER,
            panel,
            width=1,
            border_radius=18,
        )

        title = self.font_title.render("BLOXORZ", True, settings.COLOR_TEXT_MAIN)
        title_rect = title.get_rect(center=(center_x, center_y - 88))
        self.surface.blit(title, title_rect)

        accent = pygame.Rect(0, 0, 54, 4)
        accent.center = (center_x, title_rect.bottom + 12)
        pygame.draw.rect(self.surface, settings.COLOR_TEXT_ACCENT, accent, border_radius=2)

        subtitle = self.font_subtitle.render(
            "Roll the block. Find your way to the goal.",
            True,
            settings.COLOR_TEXT_MUTED,
        )
        subtitle_rect = subtitle.get_rect(center=(center_x, center_y - 24))
        self.surface.blit(subtitle, subtitle_rect)

        self.start_button.draw(self.surface, self.font_button)

        hint = self.font_hint.render(
            "Move with WASD or arrow keys  |  Esc to quit",
            True,
            settings.COLOR_TEXT_MUTED,
        )
        hint_rect = hint.get_rect(center=(center_x, panel.bottom - 34))
        self.surface.blit(hint, hint_rect)
