"""Small level collection manager used by the game UI."""

from __future__ import annotations

from pathlib import Path

from .level_loader import Level, load_levels


class LevelManager:
    def __init__(self, levels: list[Level] | None = None, directory: str | Path | None = None):
        self.levels = list(levels) if levels is not None else load_levels(directory)
        if not self.levels:
            raise ValueError("At least one level is required")
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


__all__ = ["LevelManager"]
