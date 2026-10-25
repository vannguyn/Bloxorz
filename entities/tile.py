"""Immutable tile descriptions used by the core board and board renderer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.block import Position


class TileType(str, Enum):
    VOID = "void"
    FLOOR = "floor"
    GOAL = "goal"
    FRAGILE = "fragile"
    BRIDGE = "bridge"


@dataclass(frozen=True, slots=True)
class Tile:
    position: Position
    type: TileType
    bridge_id: str | None = None