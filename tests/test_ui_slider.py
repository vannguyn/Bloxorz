import pygame
import pytest
from ui.slider import Slider


def test_slider_init_and_clamping():
    s = Slider(rect=(10, 10, 200, 20), min_val=0, max_val=10, value=5)
    assert s.value == 5
    assert not s.is_dragging
    assert not s.is_hovered


def test_slider_zero_range_no_division_by_zero():
    s = Slider(rect=(10, 10, 200, 20), min_val=0, max_val=0, value=0)
    assert s.progress_fraction == 0.0


def test_slider_drag_clamping_beyond_bounds():
    changed_vals = []
    s = Slider(rect=(100, 100, 100, 20), min_val=0, max_val=10, value=0, on_change=changed_vals.append)
    down_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (100, 105), "button": 1})
    assert s.handle_event(down_ev) is True
    move_ev = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (300, 105), "buttons": (1, 0, 0)})
    s.handle_event(move_ev)
    assert s.value == 10
    move_ev_neg = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (-50, 105), "buttons": (1, 0, 0)})
    s.handle_event(move_ev_neg)
    assert s.value == 0


def test_slider_ignores_clicks_outside_tight_margin():
    changed_vals = []
    s = Slider(rect=(100, 100, 100, 20), min_val=0, max_val=10, value=0, on_change=changed_vals.append)
    down_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (80, 105), "button": 1})
    handled = s.handle_event(down_ev)
    assert handled is False
    assert s.is_dragging is False
    assert len(changed_vals) == 0


def test_slider_on_drag_start_and_on_change_callbacks():
    started = []
    changed = []
    s = Slider(
        rect=(100, 100, 100, 20),
        min_val=0,
        max_val=10,
        value=2,
        on_drag_start=lambda: started.append(True),
        on_change=changed.append,
    )
    down_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (150, 105), "button": 1})
    handled = s.handle_event(down_ev)
    assert handled is True
    assert started == [True]
    assert s.value == 5
    assert changed == [5]


def test_slider_draw_headless():
    surface = pygame.Surface((300, 100))
    s = Slider(rect=(20, 20, 200, 20), min_val=0, max_val=10, value=4)
    s.draw(surface)


def test_slider_mouse_button_up_releases_drag():
    s = Slider(rect=(100, 100, 100, 20), min_val=0, max_val=10, value=0)
    down_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (150, 105), "button": 1})
    assert s.handle_event(down_ev) is True
    assert s.is_dragging is True

    up_ev = pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (150, 105), "button": 1})
    assert s.handle_event(up_ev) is True
    assert s.is_dragging is False

    # Second MOUSEBUTTONUP should return False because not dragging
    assert s.handle_event(up_ev) is False


def test_slider_disabled_ignores_events_and_draws():
    changed = []
    s = Slider(rect=(100, 100, 100, 20), min_val=0, max_val=10, value=3, enabled=False, on_change=changed.append)
    down_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (150, 105), "button": 1})
    assert s.handle_event(down_ev) is False
    assert s.is_dragging is False
    assert len(changed) == 0

    surface = pygame.Surface((300, 100))
    s.draw(surface)


def test_slider_value_and_max_val_property_clamping():
    s = Slider(rect=(100, 100, 100, 20), min_val=0, max_val=10, value=5)
    s.value = 15
    assert s.value == 10
    s.value = -5
    assert s.value == 0

    s.value = 8
    s.max_val = 6
    assert s.value == 6
    assert s.progress_fraction == 1.0


def test_slider_inverted_range_safeguard():
    s = Slider(rect=(100, 100, 100, 20), min_val=10, max_val=5, value=7)
    assert s.progress_fraction == 0.0


def test_slider_set_value_method():
    changed = []
    s = Slider(rect=(100, 100, 100, 20), min_val=0, max_val=10, value=0, on_change=changed.append)
    s.set_value(5)
    assert s.value == 5
    assert changed == [5]

    # Clamping beyond max_val
    s.set_value(25)
    assert s.value == 10
    assert changed == [5, 10]

    # Clamping below min_val
    s.set_value(-10)
    assert s.value == 0
    assert changed == [5, 10, 0]


def test_slider_hover_state_updates_on_mouse_motion():
    s = Slider(rect=(100, 100, 100, 20), min_val=0, max_val=10, value=0)
    assert not s.is_hovered

    # Hover inside
    ev_in = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (120, 110), "buttons": (0, 0, 0)})
    s.handle_event(ev_in)
    assert s.is_hovered

    # Hover outside
    ev_out = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (50, 50), "buttons": (0, 0, 0)})
    s.handle_event(ev_out)
    assert not s.is_hovered


def test_slider_ignores_non_left_clicks():
    changed = []
    s = Slider(rect=(100, 100, 100, 20), min_val=0, max_val=10, value=0, on_change=changed.append)

    # Right click (button 3)
    ev_right = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (150, 110), "button": 3})
    assert s.handle_event(ev_right) is False
    assert s.is_dragging is False
    assert len(changed) == 0

    # Middle click (button 2)
    ev_mid = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (150, 110), "button": 2})
    assert s.handle_event(ev_mid) is False
    assert s.is_dragging is False

