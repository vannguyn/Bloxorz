"""
Floating Dock Legend Bar for the Bloxorz game board.
Renders procedural visual chips explaining key board elements.
"""
from __future__ import annotations

from typing import Callable
import pygame
from config import settings


def _draw_chip_block(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """1. Orange rect for player block."""
    color = (245, 130, 45)
    pygame.draw.rect(surface, color, rect, border_radius=2)
    pygame.draw.rect(surface, (190, 85, 25), rect, 1, border_radius=2)


def _draw_chip_goal(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """2. Gold circle for goal tile."""
    color = (255, 215, 0)
    radius = min(rect.width, rect.height) // 2
    pygame.draw.circle(surface, color, rect.center, radius)
    pygame.draw.circle(surface, (200, 160, 0), rect.center, radius, 1)


def _draw_chip_fragile(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """3. Amber rect with radiating micro white crack for fragile tile."""
    amber_color = (235, 130, 40)
    pygame.draw.rect(surface, amber_color, rect, border_radius=2)
    pygame.draw.rect(surface, (180, 85, 20), rect, 1, border_radius=2)

    crack_color = (255, 255, 255)
    p1 = (rect.left + max(2, rect.width // 4), rect.top + 2)
    p2 = (rect.left + rect.width // 2, rect.top + rect.height // 2)
    p3 = (rect.left + max(3, rect.width // 3), rect.bottom - 3)
    p4 = (rect.right - max(2, rect.width // 4), rect.bottom - 2)
    pygame.draw.lines(surface, crack_color, False, [p1, p2, p3, p4], 1)


def _draw_chip_closed_bridge(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """4. Dark rect with red X for closed bridge."""
    dark_bg = (40, 45, 60)
    pygame.draw.rect(surface, dark_bg, rect, border_radius=2)
    pygame.draw.rect(surface, (70, 75, 95), rect, 1, border_radius=2)

    red_x = (239, 68, 68)
    pad = max(2, rect.width // 4)
    pygame.draw.line(
        surface,
        red_x,
        (rect.left + pad, rect.top + pad),
        (rect.right - pad, rect.bottom - pad),
        2,
    )
    pygame.draw.line(
        surface,
        red_x,
        (rect.left + pad, rect.bottom - pad),
        (rect.right - pad, rect.top + pad),
        2,
    )


def _draw_chip_split_switch(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """5. Cyan arched wings for split switch."""
    cyan_color = (56, 189, 248)
    cx, cy = rect.centerx, rect.centery
    w, h = rect.width, rect.height

    span_x = max(2, w // 4)
    span_y = max(3, h // 3)
    gap = max(1, w // 8)

    left_wing = [
        (cx - gap, cy - span_y),
        (cx - gap - span_x, cy),
        (cx - gap, cy + span_y),
    ]
    right_wing = [
        (cx + gap, cy - span_y),
        (cx + gap + span_x, cy),
        (cx + gap, cy + span_y),
    ]
    pygame.draw.lines(surface, cyan_color, False, left_wing, 2)
    pygame.draw.lines(surface, cyan_color, False, right_wing, 2)


class LegendBar:
    """A floating dock legend pill bar explaining the visual entities in Bloxorz."""

    CHIPS: list[tuple[str, Callable[[pygame.Surface, pygame.Rect], None]]] = [
        ("Block", _draw_chip_block),
        ("Goal", _draw_chip_goal),
        ("Fragile Tile", _draw_chip_fragile),
        ("Closed Bridge", _draw_chip_closed_bridge),
        ("Split Switch", _draw_chip_split_switch),
    ]

    def __init__(self) -> None:
        self.last_rect: pygame.Rect | None = None

    def draw(
        self,
        surface: pygame.Surface,
        area_rect: pygame.Rect,
        font: pygame.font.Font | None = None,
    ) -> pygame.Rect:
        """Renders the horizontal pill bar docked at bottom of area_rect."""
        if font is None:
            font = pygame.font.Font(None, 16)

        text_color = getattr(settings, "COLOR_CARD_HEADER", (229, 231, 235))
        bg_color = getattr(settings, "COLOR_CARD_BG", (17, 24, 39))
        border_color = getattr(settings, "COLOR_CARD_BORDER", (31, 41, 55))

        icon_size = 14
        icon_text_gap = 6
        padding_x = 16
        bar_height = 34

        chips_data = []
        total_chips_content_w = 0
        for label, drawer in self.CHIPS:
            text_surf = font.render(label, True, text_color)
            w = icon_size + icon_text_gap + text_surf.get_width()
            total_chips_content_w += w
            chips_data.append((label, drawer, text_surf, w))

        default_spacing = 16
        num_gaps = max(1, len(self.CHIPS) - 1)
        needed_w = total_chips_content_w + num_gaps * default_spacing + padding_x * 2

        if needed_w > area_rect.width - 20:
            bar_w = max(100, area_rect.width - 20)
            spacing = max(4, (bar_w - padding_x * 2 - total_chips_content_w) // num_gaps)
        else:
            bar_w = needed_w
            spacing = default_spacing

        bar_x = area_rect.left + (area_rect.width - bar_w) // 2
        bar_y = area_rect.bottom - 46
        bar_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_height)
        self.last_rect = bar_rect

        # Draw container pill
        pygame.draw.rect(surface, bg_color, bar_rect, border_radius=14)
        pygame.draw.rect(surface, border_color, bar_rect, 1, border_radius=14)

        # Draw chips
        cur_x = bar_rect.left + padding_x
        for _label, drawer, text_surf, chip_w in chips_data:
            icon_rect = pygame.Rect(
                cur_x,
                bar_rect.centery - icon_size // 2,
                icon_size,
                icon_size,
            )
            drawer(surface, icon_rect)

            text_y = bar_rect.centery - text_surf.get_height() // 2
            surface.blit(text_surf, (cur_x + icon_size + icon_text_gap, text_y))
            cur_x += chip_w + spacing

        return bar_rect


__all__ = ["LegendBar"]
