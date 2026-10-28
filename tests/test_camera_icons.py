import pygame
from ui.icons import draw_camera_focus_icon, draw_camera_overview_icon
from ui.button import Button


def test_camera_icons_draw_without_error():
    surface = pygame.Surface((32, 32))
    rect = pygame.Rect(0, 0, 32, 32)
    draw_camera_focus_icon(surface, rect, (200, 200, 200))
    draw_camera_overview_icon(surface, rect, (200, 200, 200))
    # Must draw non-zero pixels
    assert pygame.transform.average_color(surface)[:3] != (0, 0, 0)


def test_button_disabled_state_suppresses_click():
    clicked = []
    btn = Button((0, 0, 32, 32), "", callback=lambda: clicked.append(True), enabled=False)
    # Simulate click
    event_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(16, 16))
    event_up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(16, 16))
    btn.handle_event(event_down)
    btn.handle_event(event_up)
    assert clicked == []
