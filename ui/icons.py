"""Procedural vector icons for Bloxorz GUI.

Renders crisp, resolution-independent vector icons directly onto Pygame surfaces
using pygame.draw primitives without any external asset dependencies.
"""
from __future__ import annotations

import math
import pygame

__all__ = [
    "draw_network_icon",
    "draw_tree_icon",
    "draw_database_icon",
    "draw_star_icon",
    "draw_play_icon",
    "draw_step_back_icon",
    "draw_pause_icon",
    "draw_step_forward_icon",
    "draw_speed_icon",
    "draw_metrics_icon",
]


def draw_network_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw a 3-node connected network graph representing BFS traversal."""
    if rect.width <= 0 or rect.height <= 0:
        return

    w, h = rect.width, rect.height
    r = max(2, int(min(w, h) * 0.14))
    lw = max(1, int(min(w, h) * 0.08))

    p0 = (rect.centerx, rect.top + int(h * 0.24))
    p1 = (rect.left + int(w * 0.24), rect.bottom - int(h * 0.24))
    p2 = (rect.right - int(w * 0.24), rect.bottom - int(h * 0.24))

    pygame.draw.line(surface, color, p0, p1, lw)
    pygame.draw.line(surface, color, p0, p2, lw)
    pygame.draw.line(surface, color, p1, p2, lw)

    pygame.draw.circle(surface, color, p0, r)
    pygame.draw.circle(surface, color, p1, r)
    pygame.draw.circle(surface, color, p2, r)


def draw_tree_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw a branching tree hierarchy (root to 2 children) representing DFS traversal."""
    if rect.width <= 0 or rect.height <= 0:
        return

    w, h = rect.width, rect.height
    r = max(2, int(min(w, h) * 0.14))
    lw = max(1, int(min(w, h) * 0.08))

    root = (rect.centerx, rect.top + int(h * 0.22))
    left_child = (rect.left + int(w * 0.24), rect.bottom - int(h * 0.24))
    right_child = (rect.right - int(w * 0.24), rect.bottom - int(h * 0.24))

    pygame.draw.line(surface, color, root, left_child, lw)
    pygame.draw.line(surface, color, root, right_child, lw)

    pygame.draw.circle(surface, color, root, r)
    pygame.draw.circle(surface, color, left_child, r)
    pygame.draw.circle(surface, color, right_child, r)


def draw_database_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw 3 vertically stacked cylindrical database discs representing UCS."""
    if rect.width <= 0 or rect.height <= 0:
        return

    w = int(rect.width * 0.76)
    disc_h = max(3, int(rect.height * 0.22))
    x = rect.left + (rect.width - w) // 2

    y0 = rect.top + int(rect.height * 0.10)
    y1 = rect.top + int(rect.height * 0.39)
    y2 = rect.top + int(rect.height * 0.68)

    for y in (y0, y1, y2):
        disc_rect = pygame.Rect(x, y, w, disc_h)
        pygame.draw.ellipse(surface, color, disc_rect)


def draw_star_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw a 5-point geometric star polygon representing A* search."""
    if rect.width <= 0 or rect.height <= 0:
        return

    cx, cy = rect.centerx, rect.centery
    outer_r = min(rect.width, rect.height) * 0.45
    inner_r = outer_r * 0.42

    points: list[tuple[float, float]] = []
    for i in range(10):
        angle = -math.pi / 2 + i * (math.pi / 5)
        radius = outer_r if i % 2 == 0 else inner_r
        px = cx + radius * math.cos(angle)
        py = cy + radius * math.sin(angle)
        points.append((px, py))

    pygame.draw.polygon(surface, color, points)


def draw_play_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw a right-pointing solid triangle for playback start."""
    if rect.width <= 0 or rect.height <= 0:
        return

    w, h = rect.width, rect.height
    pad_x = int(w * 0.20)
    pad_y = int(h * 0.18)
    offset = max(1, int(w * 0.05))

    p1 = (rect.left + pad_x + offset, rect.top + pad_y)
    p2 = (rect.right - pad_x + offset, rect.centery)
    p3 = (rect.left + pad_x + offset, rect.bottom - pad_y)

    pygame.draw.polygon(surface, color, [p1, p2, p3])


def draw_step_back_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw a left-pointing dual chevron for stepping backward."""
    if rect.width <= 0 or rect.height <= 0:
        return

    w, h = rect.width, rect.height
    line_w = max(1, int(w * 0.12))

    p1 = (rect.left + int(w * 0.46), rect.top + int(h * 0.18))
    p2 = (rect.left + int(w * 0.16), rect.centery)
    p3 = (rect.left + int(w * 0.46), rect.bottom - int(h * 0.18))

    p4 = (rect.left + int(w * 0.82), rect.top + int(h * 0.18))
    p5 = (rect.left + int(w * 0.52), rect.centery)
    p6 = (rect.left + int(w * 0.82), rect.bottom - int(h * 0.18))

    pygame.draw.lines(surface, color, False, [p1, p2, p3], line_w)
    pygame.draw.lines(surface, color, False, [p4, p5, p6], line_w)


def draw_pause_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw dual vertical pause bars."""
    if rect.width <= 0 or rect.height <= 0:
        return

    w, h = rect.width, rect.height
    bar_w = max(2, int(w * 0.18))
    gap = max(2, int(w * 0.20))
    bar_h = max(4, int(h * 0.65))

    total_w = 2 * bar_w + gap
    start_x = rect.left + (w - total_w) // 2
    y = rect.top + (h - bar_h) // 2
    rad = max(1, bar_w // 4)

    pygame.draw.rect(surface, color, pygame.Rect(start_x, y, bar_w, bar_h), border_radius=rad)
    pygame.draw.rect(surface, color, pygame.Rect(start_x + bar_w + gap, y, bar_w, bar_h), border_radius=rad)


def draw_step_forward_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw a right-pointing dual chevron for stepping forward."""
    if rect.width <= 0 or rect.height <= 0:
        return

    w, h = rect.width, rect.height
    line_w = max(1, int(w * 0.12))

    p1 = (rect.left + int(w * 0.18), rect.top + int(h * 0.18))
    p2 = (rect.left + int(w * 0.48), rect.centery)
    p3 = (rect.left + int(w * 0.18), rect.bottom - int(h * 0.18))

    p4 = (rect.left + int(w * 0.54), rect.top + int(h * 0.18))
    p5 = (rect.left + int(w * 0.84), rect.centery)
    p6 = (rect.left + int(w * 0.54), rect.bottom - int(h * 0.18))

    pygame.draw.lines(surface, color, False, [p1, p2, p3], line_w)
    pygame.draw.lines(surface, color, False, [p4, p5, p6], line_w)


def draw_speed_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw a speedometer arc gauge and dial needle."""
    if rect.width <= 0 or rect.height <= 0:
        return

    line_w = max(1, int(rect.width * 0.08))
    gauge_rect = pygame.Rect(rect.left, rect.top, rect.width, rect.height)

    # Arc spanning the top dial
    pygame.draw.arc(surface, color, gauge_rect, -0.4, math.pi + 0.4, line_w)

    cx, cy = rect.centerx, rect.centery + int(rect.height * 0.05)
    needle_len = rect.width * 0.35
    angle = math.radians(50)
    nx = cx + int(needle_len * math.cos(angle))
    ny = cy - int(needle_len * math.sin(angle))

    pygame.draw.line(surface, color, (cx, cy), (nx, ny), max(1, line_w))
    pygame.draw.circle(surface, color, (cx, cy), max(2, int(rect.width * 0.08)))


def draw_metrics_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw 3 ascending histogram columns representing metrics."""
    if rect.width <= 0 or rect.height <= 0:
        return

    w, h = rect.width, rect.height
    pad_x = max(1, int(w * 0.12))
    pad_y = max(1, int(h * 0.12))
    uw = w - 2 * pad_x
    uh = h - 2 * pad_y

    num_bars = 3
    bar_w = max(2, int(uw * 0.24))
    gap = (uw - num_bars * bar_w) // (num_bars - 1)
    height_ratios = [0.35, 0.65, 0.95]
    base_y = rect.bottom - pad_y

    for i, ratio in enumerate(height_ratios):
        bar_h = max(2, int(uh * ratio))
        bx = rect.left + pad_x + i * (bar_w + gap)
        by = base_y - bar_h
        pygame.draw.rect(
            surface,
            color,
            pygame.Rect(bx, by, bar_w, bar_h),
            border_radius=max(1, bar_w // 4),
        )
