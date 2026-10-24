"""
Interactive Button widget for Pygame-CE.
Supports hover, press, enabled/disabled states, tooltips and callbacks.
"""
from __future__ import annotations

from typing import Callable
import pygame
from config import settings


class Button:
    """A styled clickable button for the Pygame UI."""

    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        text: str,
        on_click: Callable[[], None] | None = None,
        *,
        enabled: bool = True,
        primary: bool = False,
        font_size: int = 16,
    ):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.enabled = enabled
        self.primary = primary
        self.font_size = font_size

        self.is_hovered = False
        self.is_pressed = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Processes mouse movement and clicks. Returns True if button was clicked."""
        if not self.enabled:
            self.is_hovered = False
            self.is_pressed = False
            return False

        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True
                return False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed and self.rect.collidepoint(event.pos):
                self.is_pressed = False
                if self.on_click:
                    self.on_click()
                return True
            self.is_pressed = False

        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font | None = None) -> None:
        """Renders the button onto the given surface."""
        # Determine background color
        if not self.enabled:
            bg_color = settings.COLOR_BTN_DISABLED
            border_color = (40, 45, 58)
            text_color = settings.COLOR_TEXT_MUTED
        elif self.is_pressed:
            bg_color = settings.COLOR_BTN_ACTIVE
            border_color = settings.COLOR_TEXT_ACCENT
            text_color = settings.COLOR_TEXT_MAIN
        elif self.is_hovered:
            bg_color = settings.COLOR_BTN_PRIMARY_HOVER if self.primary else settings.COLOR_BTN_HOVER
            border_color = settings.COLOR_TEXT_ACCENT
            text_color = (255, 255, 255)
        else:
            bg_color = settings.COLOR_BTN_PRIMARY if self.primary else settings.COLOR_BTN_DEFAULT
            border_color = (65, 75, 100)
            text_color = settings.COLOR_TEXT_MAIN

        pygame.draw.rect(surface, bg_color, self.rect, border_radius=6)
        pygame.draw.rect(surface, border_color, self.rect, 1, border_radius=6)

        if font:
            text_surf = font.render(self.text, True, text_color)
            text_rect = text_surf.get_rect(center=self.rect.center)
            surface.blit(text_surf, text_rect)
