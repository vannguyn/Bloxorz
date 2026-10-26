"""
Interactive Button widget for Pygame-CE.
Supports hover, press, enabled/disabled states, tooltips and callbacks.
"""
from __future__ import annotations

import inspect
from typing import Callable
import pygame
from config import settings


def _call_icon_drawer(
    drawer: Callable[..., None],
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
) -> None:
    """Invokes icon_drawer supporting both (surface, rect, color) and (surface, rect)."""
    try:
        sig = inspect.signature(drawer)
        params = list(sig.parameters.values())
        if len(params) >= 3 or any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params):
            drawer(surface, rect, color)
        else:
            drawer(surface, rect)
    except (ValueError, TypeError):
        try:
            drawer(surface, rect, color)
        except TypeError:
            drawer(surface, rect)


class Button:
    """A styled clickable button for the Pygame UI."""

    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        text: str = "",
        on_click: Callable[[], None] | None = None,
        *,
        enabled: bool = True,
        primary: bool = False,
        selected: bool = False,
        icon_drawer: Callable[[pygame.Surface, pygame.Rect, tuple[int, int, int]], None] | None = None,
        icon_position: str = "left",
        font_size: int = 16,
    ):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.enabled = enabled
        self.primary = primary
        self.selected = selected
        self.icon_drawer = icon_drawer
        self.icon_position = icon_position
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
        elif self.selected:
            bg_color = settings.COLOR_BTN_PRIMARY_HOVER if self.is_hovered else settings.COLOR_BTN_PRIMARY
            border_color = settings.COLOR_TEXT_ACCENT
            text_color = (255, 255, 255)
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

        icon_size = min(16, max(8, self.rect.height - 8))
        gap = 6

        if self.icon_drawer is not None and self.text:
            text_surf = font.render(self.text, True, text_color) if font else None
            text_w = text_surf.get_width() if text_surf else 0
            text_h = text_surf.get_height() if text_surf else 0

            total_w = icon_size + gap + text_w if text_surf else icon_size
            start_x = self.rect.left + (self.rect.width - total_w) // 2

            if self.icon_position == "right":
                if text_surf:
                    text_rect = pygame.Rect(
                        start_x,
                        self.rect.top + (self.rect.height - text_h) // 2,
                        text_w,
                        text_h,
                    )
                    surface.blit(text_surf, text_rect)

                icon_rect = pygame.Rect(
                    start_x + text_w + gap,
                    self.rect.top + (self.rect.height - icon_size) // 2,
                    icon_size,
                    icon_size,
                )
                _call_icon_drawer(self.icon_drawer, surface, icon_rect, text_color)

            else:
                icon_rect = pygame.Rect(
                    start_x,
                    self.rect.top + (self.rect.height - icon_size) // 2,
                    icon_size,
                    icon_size,
                )
                _call_icon_drawer(self.icon_drawer, surface, icon_rect, text_color)

                if text_surf:
                    text_rect = pygame.Rect(
                        start_x + icon_size + gap,
                        self.rect.top + (self.rect.height - text_h) // 2,
                        text_w,
                        text_h,
                    )
                    surface.blit(text_surf, text_rect)

        elif self.icon_drawer is not None and not self.text:
            icon_rect = pygame.Rect(
                self.rect.left + (self.rect.width - icon_size) // 2,
                self.rect.top + (self.rect.height - icon_size) // 2,
                icon_size,
                icon_size,
            )
            _call_icon_drawer(self.icon_drawer, surface, icon_rect, text_color)

        elif font and self.text:
            text_surf = font.render(self.text, True, text_color)
            text_rect = text_surf.get_rect(center=self.rect.center)
            surface.blit(text_surf, text_rect)
