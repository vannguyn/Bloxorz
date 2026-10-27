"""Unit tests for UI design tokens and procedural vector icons."""
import pytest
import pygame

from config import settings


@pytest.fixture(scope="session", autouse=True)
def init_pygame():
    """Initializes pygame headless for testing."""
    pygame.init()
    yield
    pygame.quit()


def test_card_color_tokens_defined_in_settings():
    """Verify card container color tokens are correctly defined in settings."""
    assert hasattr(settings, "COLOR_CARD_BG")
    assert settings.COLOR_CARD_BG == (17, 24, 39)

    assert hasattr(settings, "COLOR_CARD_BORDER")
    assert settings.COLOR_CARD_BORDER == (31, 41, 55)

    assert hasattr(settings, "COLOR_CARD_HEADER")
    assert settings.COLOR_CARD_HEADER == (229, 231, 235)

    assert hasattr(settings, "COLOR_METRIC_LABEL")
    assert settings.COLOR_METRIC_LABEL == (156, 163, 175)

    assert hasattr(settings, "COLOR_METRIC_VALUE")
    assert settings.COLOR_METRIC_VALUE == (243, 244, 246)


def _assert_icon_draws_pixels(draw_fn, target_color=(255, 200, 100)):
    """Helper to verify an icon renderer draws non-empty pixels matching target color."""
    surface = pygame.Surface((32, 32), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    rect = pygame.Rect(4, 4, 24, 24)

    # Test default color call
    default_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    default_surf.fill((0, 0, 0, 0))
    draw_fn(default_surf, rect)

    # Verify default drawn pixels exist
    drawn_count_default = 0
    for x in range(32):
        for y in range(32):
            if default_surf.get_at((x, y))[3] > 0:
                drawn_count_default += 1
    assert drawn_count_default > 0, f"{draw_fn.__name__} drew 0 pixels with default color"

    # Test explicit color call
    draw_fn(surface, rect, target_color)

    drawn_pixels = []
    color_matched = False
    for x in range(32):
        for y in range(32):
            pixel = surface.get_at((x, y))
            if pixel[3] > 0:
                drawn_pixels.append((x, y, pixel))
                if pixel[:3] == target_color:
                    color_matched = True

    assert len(drawn_pixels) > 0, f"{draw_fn.__name__} drew 0 pixels with explicit color"
    assert color_matched, f"{draw_fn.__name__} did not draw pixels matching target color {target_color}"

    # Also test drawing in a small rect (e.g. 12x12) without crashing
    small_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    small_surf.fill((0, 0, 0, 0))
    draw_fn(small_surf, pygame.Rect(2, 2, 12, 12), target_color)


def test_algorithm_icons():
    """Verify algorithm icons: network, tree, database, star."""
    from ui.icons import (
        draw_network_icon,
        draw_tree_icon,
        draw_database_icon,
        draw_star_icon,
    )

    for fn in (draw_network_icon, draw_tree_icon, draw_database_icon, draw_star_icon):
        _assert_icon_draws_pixels(fn)


def test_playback_icons():
    """Verify playback control icons: play, step_back, pause, step_forward, speed."""
    from ui.icons import (
        draw_play_icon,
        draw_step_back_icon,
        draw_pause_icon,
        draw_step_forward_icon,
        draw_speed_icon,
    )

    for fn in (
        draw_play_icon,
        draw_step_back_icon,
        draw_pause_icon,
        draw_step_forward_icon,
        draw_speed_icon,
    ):
        _assert_icon_draws_pixels(fn)


def test_metrics_icon():
    """Verify metrics histogram icon."""
    from ui.icons import draw_metrics_icon

    _assert_icon_draws_pixels(draw_metrics_icon)


def test_all_icons_exported():
    """Verify all 10 icons are exposed in ui.icons.__all__."""
    import ui.icons as icons_mod

    expected_names = [
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

    for name in expected_names:
        assert hasattr(icons_mod, name), f"ui.icons missing {name}"
        assert name in icons_mod.__all__, f"{name} not in ui.icons.__all__"
        assert callable(getattr(icons_mod, name))
