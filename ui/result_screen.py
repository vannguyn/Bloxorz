"""
Result and Game Over Overlay Screen for Bloxorz.
Draws victory, failure, and unsolvable status overlays clearly for the demo video.
"""
from __future__ import annotations

import pygame
from config import settings


class ResultOverlay:
    """Renders semi-transparent outcome overlays (Win, Loss, No Solution)."""

    @staticmethod
    def draw(
        surface: pygame.Surface,
        area_rect: pygame.Rect,
        status: str,  # "WIN" | "LOST_FALL" | "LOST_FRAGILE" | "UNSOLVABLE"
        moves_count: int = 0,
        font_large: pygame.font.Font | None = None,
        font_small: pygame.font.Font | None = None,
    ) -> None:
        # Create dark overlay surface
        overlay = pygame.Surface((area_rect.width, area_rect.height), pygame.SRCALPHA)
        overlay.fill((15, 18, 26, 175))

        banner_w = min(460, area_rect.width - 40)
        banner_h = 160
        bx = (area_rect.width - banner_w) // 2
        by = (area_rect.height - banner_h) // 2
        banner_rect = pygame.Rect(bx, by, banner_w, banner_h)

        if status == "WIN":
            border_color = settings.COLOR_TEXT_SUCCESS
            title_text = "STAGE CLEAR!"
            title_color = settings.COLOR_TEXT_SUCCESS
            sub_text = f"Completed in {moves_count} moves!  [R to Restart | N for Next]"
        elif status == "LOST_FRAGILE":
            border_color = settings.COLOR_TEXT_DANGER
            title_text = "FRAGILE TILE COLLAPSED!"
            title_color = settings.COLOR_TEXT_DANGER
            sub_text = "The block cannot stand upright on fragile tiles! [Press R]"
        elif status == "LOST_FALL":
            border_color = settings.COLOR_TEXT_DANGER
            title_text = "YOU FELL INTO THE VOID!"
            title_color = settings.COLOR_TEXT_DANGER
            sub_text = "The block lost support and plummeted. [Press R to Retry]"
        elif status == "UNSOLVABLE":
            border_color = (230, 160, 40)
            title_text = "NO SOLUTION FOUND"
            title_color = (245, 180, 50)
            sub_text = "The search concluded that this stage is unsolvable."
        else:
            border_color = settings.COLOR_PANEL_BORDER
            title_text = status
            title_color = settings.COLOR_TEXT_MAIN
            sub_text = "[Press R to Restart]"

        # Draw banner background on overlay
        pygame.draw.rect(overlay, (28, 33, 46), banner_rect, border_radius=10)
        pygame.draw.rect(overlay, border_color, banner_rect, 2, border_radius=10)

        # Draw titles
        if font_large:
            t_surf = font_large.render(title_text, True, title_color)
            t_rect = t_surf.get_rect(center=(banner_rect.centerx, banner_rect.top + 45))
            overlay.blit(t_surf, t_rect)

        if font_small:
            s_surf = font_small.render(sub_text, True, settings.COLOR_TEXT_MAIN)
            s_rect = s_surf.get_rect(center=(banner_rect.centerx, banner_rect.top + 105))
            overlay.blit(s_surf, s_rect)

        # Blit overlay onto the main surface
        surface.blit(overlay, area_rect.topleft)
