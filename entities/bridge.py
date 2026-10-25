"""Bridge entity definitions shared by the board model and rendering layer."""

from __future__ import annotations

from dataclasses import dataclass

from core.block import Position


@dataclass(frozen=True, slots=True)
class Bridge:
    id: str
    tiles: frozenset[Position]
    initial_state: str = "closed"

    def __post_init__(self) -> None:
        if self.initial_state not in {"open", "closed"}:
            raise ValueError(f"Bridge {self.id!r} has invalid initial_state")