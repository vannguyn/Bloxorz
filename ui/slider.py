"""
Procedural Slider UI Component for Pygame-CE.
Provides draggable progress scrubbing with glow halos and custom callbacks.
"""
from __future__ import annotations

from typing import Callable
import pygame


class Slider:
    """
    A procedural slider widget for numeric scrubbing.
    Draws a dark bordered track, luminous cyan fill, and glowing thumb knob.
    """

    COLOR_TRACK_BG = (11, 30, 59)
    COLOR_TRACK_BORDER = (27, 59, 104)
    COLOR_FILL = (0, 229, 255)
    COLOR_THUMB_CENTER = (255, 255, 255)
    COLOR_THUMB_PERIMETER = (0, 229, 255)
    COLOR_THUMB_BRIGHT = (100, 240, 255)

    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        min_val: int = 0,
        max_val: int = 100,
        value: int = 0,
        on_change: Callable[[int], None] | None = None,
        on_drag_start: Callable[[], None] | None = None,
        *,
        enabled: bool = True,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self._min_val = int(min_val)
        self._max_val = int(max_val)
        self.on_change = on_change
        self.on_drag_start = on_drag_start
        self.enabled = enabled

        self.is_dragging: bool = False
        self.is_hovered: bool = False

        self._value = self._clamp_value(value)

        # Pre-render halo surfaces to avoid per-frame allocation
        active_r = 14
        self._halo_surf_active = pygame.Surface((active_r * 2 + 2, active_r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(
            self._halo_surf_active,
            (*self.COLOR_THUMB_BRIGHT[:3], 80),
            (self._halo_surf_active.get_width() // 2, self._halo_surf_active.get_height() // 2),
            active_r,
        )

        idle_r = 11
        self._halo_surf_idle = pygame.Surface((idle_r * 2 + 2, idle_r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(
            self._halo_surf_idle,
            (*self.COLOR_THUMB_PERIMETER[:3], 40),
            (self._halo_surf_idle.get_width() // 2, self._halo_surf_idle.get_height() // 2),
            idle_r,
        )

    def _clamp_value(self, val: int | float) -> int:
        """Clamps value between min_val and max_val safely."""
        int_val = int(round(val))
        if self._max_val > self._min_val:
            return max(self._min_val, min(self._max_val, int_val))
        return self._min_val

    @property
    def min_val(self) -> int:
        return self._min_val

    @min_val.setter
    def min_val(self, val: int) -> None:
        self._min_val = int(val)
        self._value = self._clamp_value(self._value)

    @property
    def max_val(self) -> int:
        return self._max_val

    @max_val.setter
    def max_val(self, val: int) -> None:
        self._max_val = int(val)
        self._value = self._clamp_value(self._value)

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, val: int | float) -> None:
        self._value = self._clamp_value(val)

    def set_value(self, val: int | float, trigger_callback: bool = True) -> None:
        """Sets slider value with clamping, optionally firing on_change if value changed."""
        new_val = self._clamp_value(val)
        changed = (new_val != self._value)
        self._value = new_val
        if changed and trigger_callback and self.on_change:
            self.on_change(self._value)

    @property
    def progress_fraction(self) -> float:
        """Normalized progress in [0.0, 1.0], safeguarding against zero/negative range."""
        if self._max_val <= self._min_val:
            return 0.0
        return max(0.0, min(1.0, (self._value - self._min_val) / (self._max_val - self._min_val)))

    def _pos_to_value(self, mouse_x: int) -> int:
        """Maps cursor screen X into an integer value clamped within [min_val, max_val]."""
        if self._max_val <= self._min_val or self.rect.width <= 0:
            return self._min_val
        relative_x = mouse_x - self.rect.left
        clamped_x = max(0, min(self.rect.width, relative_x))
        fraction = clamped_x / self.rect.width
        val = round(self._min_val + fraction * (self._max_val - self._min_val))
        return self._clamp_value(val)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handles mouse input for scrubbing.
        Returns True if the slider consumed or reacted to the event.
        """
        if not self.enabled:
            self.is_dragging = False
            self.is_hovered = False
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit_margin_x = 12
            hit_margin_y = 6
            hit_rect = pygame.Rect(
                self.rect.left - hit_margin_x,
                self.rect.top - hit_margin_y,
                self.rect.width + 2 * hit_margin_x,
                self.rect.height + 2 * hit_margin_y,
            )
            if hit_rect.collidepoint(event.pos):
                self.is_dragging = True
                if self.on_drag_start:
                    self.on_drag_start()
                new_val = self._pos_to_value(event.pos[0])
                self.value = new_val
                if self.on_change:
                    self.on_change(self.value)
                return True
            return False

        if event.type == pygame.MOUSEMOTION:
            hit_rect = self.rect.inflate(24, 12)
            self.is_hovered = hit_rect.collidepoint(event.pos)
            if self.is_dragging:
                new_val = self._pos_to_value(event.pos[0])
                if new_val != self.value:
                    self.value = new_val
                    if self.on_change:
                        self.on_change(self.value)
                return True
            return False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging:
                self.is_dragging = False
                return True
            return False

        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Renders track, filled progress bar, and thumb knob with glowing halo."""
        track_h = 8
        track_y = self.rect.y + (self.rect.height - track_h) // 2
        track_rect = pygame.Rect(self.rect.x, track_y, self.rect.width, track_h)

        if not self.enabled:
            bg_col = (18, 24, 38)
            border_col = (35, 45, 65)
            fill_col = (20, 90, 115)
            thumb_perimeter_col = (45, 80, 100)
            thumb_center_col = (130, 135, 145)
        else:
            bg_col = self.COLOR_TRACK_BG
            border_col = self.COLOR_TRACK_BORDER
            fill_col = self.COLOR_FILL
            is_active = self.is_dragging or self.is_hovered
            thumb_perimeter_col = self.COLOR_THUMB_BRIGHT if is_active else self.COLOR_THUMB_PERIMETER
            thumb_center_col = self.COLOR_THUMB_CENTER

        # 1. Track background & border
        pygame.draw.rect(surface, bg_col, track_rect, border_radius=4)
        pygame.draw.rect(surface, border_col, track_rect, width=1, border_radius=4)

        # 2. Filled progress track
        frac = self.progress_fraction
        fill_w = int(self.rect.width * frac)
        if fill_w > 0:
            fill_rect = pygame.Rect(self.rect.x, track_y, fill_w, track_h)
            radius = min(4, max(1, fill_w // 2)) if fill_w < 8 else 4
            pygame.draw.rect(surface, fill_col, fill_rect, border_radius=radius)

        # 3. Draggable thumb knob
        thumb_x = self.rect.x + fill_w
        thumb_y = self.rect.y + self.rect.height // 2
        thumb_radius = 8

        # Outer glow alpha halo
        if self.enabled:
            is_active = self.is_dragging or self.is_hovered
            halo_surf = self._halo_surf_active if is_active else self._halo_surf_idle
            surface.blit(
                halo_surf,
                (thumb_x - halo_surf.get_width() // 2, thumb_y - halo_surf.get_height() // 2),
            )

        # Cyan perimeter circle & white core
        pygame.draw.circle(surface, thumb_perimeter_col, (thumb_x, thumb_y), thumb_radius)
        pygame.draw.circle(surface, thumb_center_col, (thumb_x, thumb_y), 5)
