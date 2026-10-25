"""Load playable levels and create their initial core state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from core.block import Orientation, Position
from core.board import Board
from core.game_state import GameState


@dataclass(frozen=True, slots=True)
class Level:
    """Metadata around an immutable :class:`core.board.Board`.

    The board and all transitions remain owned by ``core``.  This small
    wrapper only carries data that belongs to a level file (name and start
    position) so the GUI does not need a second game-state model.
    """

    id: str
    name: str
    board: Board
    start_position: Position
    start_orientation: Orientation = Orientation.STANDING

    @property
    def width(self) -> int:
        return self.board.width

    @property
    def height(self) -> int:
        return self.board.height

    @property
    def start_state(self) -> GameState:
        return GameState.start(self.board, self.start_position, self.start_orientation)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, source: str = "level") -> "Level":
        if not isinstance(data, Mapping):
            raise ValueError(f"{source}: root must be a JSON object")
        raw_start = data.get("start")
        if not isinstance(raw_start, Mapping):
            raise ValueError(f"{source}: missing start object")
        raw_position = raw_start.get("position")
        if not isinstance(raw_position, (list, tuple)) or len(raw_position) != 2:
            raise ValueError(f"{source}: start.position must contain two integers")
        if not all(type(value) is int for value in raw_position):
            raise ValueError(f"{source}: start.position must contain two integers")
        if "orientation" in raw_start and not isinstance(raw_start["orientation"], str):
            raise ValueError(f"{source}: start.orientation must be a string")
        try:
            orientation = Orientation(str(raw_start.get("orientation", "standing")).lower())
        except ValueError as exc:
            raise ValueError(f"{source}: invalid start orientation") from exc

        board = Board.from_dict(data)
        position = (raw_position[0], raw_position[1])
        level_id = data.get("id", Path(source).stem)
        name = data.get("name", level_id)
        if not isinstance(level_id, str) or not level_id:
            raise ValueError(f"{source}: id must be a non-empty string")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{source}: name must be a non-empty string")
        level = cls(
            id=level_id,
            name=name,
            board=board,
            start_position=position,
            start_orientation=orientation,
        )
        # Validate the start at load time, rather than failing on first GUI frame.
        level.start_state
        return level


def load_level(path: str | Path) -> Level:
    level_path = Path(path)
    with level_path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, Mapping):
        raise ValueError(f"{level_path}: root must be a JSON object")
    return Level.from_dict(data, source=str(level_path))


def load_levels(directory: str | Path | None = None) -> list[Level]:
    level_dir = Path(directory) if directory is not None else Path(__file__).parent
    paths = sorted(level_dir.glob("level_*.json"))
    if not paths:
        raise FileNotFoundError(f"No level_*.json files found in {level_dir}")
    return [load_level(path) for path in paths]


__all__ = ["Level", "load_level", "load_levels"]
