"""Switch entities and their effects on game mechanisms."""

from __future__ import annotations

from dataclasses import dataclass

from core.block import Position


@dataclass(frozen=True, slots=True)
class SwitchEffect:
    type: str
    bridge_ids: tuple[str, ...] = ()
    mode: str | None = None
    state: str | None = None
    trigger: str = "enter"
    destinations: tuple[Position, ...] = ()
    lock_after_activation: bool = False


@dataclass(frozen=True, slots=True)
class Switch:
    id: str
    type: str
    position: Position
    effect: SwitchEffect