"""Small level collection used by the game screen and future menu screens."""
from __future__ import annotations

from pathlib import Path

from core.interfaces import Level
from .level_loader import LEVELS_DIR, load_all_levels


class LevelManager:
    def __init__(self, directory: str | Path = LEVELS_DIR):
        self.directory = Path(directory)
        self.levels: list[Level] = load_all_levels(self.directory)
        self.index = 0

    @property
    def current(self) -> Level:
        return self.levels[self.index]

    def select(self, index: int) -> Level:
        self.index = index % len(self.levels)
        return self.current

    def next(self) -> Level:
        return self.select(self.index + 1)

    def previous(self) -> Level:
        return self.select(self.index - 1)

    def reload(self) -> None:
        self.levels = load_all_levels(self.directory)


__all__ = ["LevelManager"]
