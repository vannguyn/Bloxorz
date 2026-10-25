from __future__ import annotations

import pytest

from levels.level_loader import Level
from levels.level_manager import LevelManager


def valid_level_data() -> dict:
    return {
        "id": "test",
        "name": "Test",
        "width": 2,
        "height": 1,
        "start": {"position": [0, 0], "orientation": "standing"},
        "goal": [1, 0],
        "tiles": [[0, 0], [1, 0]],
    }


def test_load_valid_level_and_manager_navigation() -> None:
    level = Level.from_dict(valid_level_data())
    manager = LevelManager([level])

    assert manager.current is level
    assert manager.next() is level
    assert manager.previous() is level
    assert level.start_state.block.position == (0, 0)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("width", True, "width must be an integer"),
        ("tiles", [[2, 0]], "within board bounds"),
        ("goal", [2, 0], "within board bounds"),
        ("fragile_tiles", [[2, 0]], "within board bounds"),
    ],
)
def test_rejects_invalid_board_fields(field: str, value: object, message: str) -> None:
    data = valid_level_data()
    data[field] = value

    with pytest.raises(ValueError, match=message):
        Level.from_dict(data)


def test_rejects_invalid_start_and_switch_references() -> None:
    data = valid_level_data()
    data["start"]["position"] = [True, 0]
    with pytest.raises(ValueError, match="start.position"):
        Level.from_dict(data)

    data = valid_level_data()
    data["switches"] = [
        {
            "id": "switch",
            "type": "soft",
            "position": [0, 0],
            "effect": {
                "type": "bridge",
                "bridge_ids": ["missing"],
                "mode": "toggle",
            },
        }
    ]
    with pytest.raises(ValueError, match="unknown bridge"):
        Level.from_dict(data)


def test_rejects_duplicate_tile_coordinates() -> None:
    data = valid_level_data()
    data["tiles"] = [[0, 0], [0, 0], [1, 0]]

    with pytest.raises(ValueError, match="duplicate coordinates"):
        Level.from_dict(data)