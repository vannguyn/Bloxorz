"""Mô hình board và các tile/cơ chế của một stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .block import Position


def _position(value: Iterable[int]) -> Position:
    value = tuple(value)
    if len(value) != 2 or not all(isinstance(v, int) for v in value):
        raise ValueError(f"Invalid position: {value!r}")
    return value[0], value[1]


@dataclass(frozen=True, slots=True)
class Bridge:
    id: str
    tiles: frozenset[Position]
    initial_state: str = "closed"

    def __post_init__(self) -> None:
        if self.initial_state not in {"open", "closed"}:
            raise ValueError(f"Bridge {self.id!r} has invalid initial_state")


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


@dataclass(frozen=True, slots=True)
class SplitRules:
    control_switch_key: str = "SPACE"
    merge_when_adjacent: bool = True
    single_cube_can_win: bool = False
    single_cube_activates: frozenset[str] = frozenset({"soft"})
    single_cube_cannot_activate: frozenset[str] = frozenset({"heavy", "split"})


@dataclass(frozen=True, slots=True)
class Board:
    """Board bất biến để dùng chung an toàn trong các search solver."""

    width: int
    height: int
    tiles: frozenset[Position]
    goal: Position
    fragile_tiles: frozenset[Position] = frozenset()
    bridges: Mapping[str, Bridge] = field(default_factory=dict)
    switches: Mapping[str, Switch] = field(default_factory=dict)
    split_rules: SplitRules = field(default_factory=SplitRules)

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Board dimensions must be positive")
        if self.goal not in self.tiles and not any(self.goal in b.tiles for b in self.bridges.values()):
            raise ValueError("Goal must be a board tile or an openable bridge tile")
        if not self.fragile_tiles.issubset(self.tiles):
            raise ValueError("Every fragile tile must be listed in tiles")
        bridge_cells: set[Position] = set()
        for bridge in self.bridges.values():
            if bridge_cells.intersection(bridge.tiles):
                raise ValueError("A coordinate cannot belong to multiple bridges")
            bridge_cells.update(bridge.tiles)
        for switch in self.switches.values():
            if switch.position not in self.tiles:
                raise ValueError(f"Switch {switch.id!r} is not on a board tile")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Board":
        bridges: dict[str, Bridge] = {}
        for raw in data.get("bridges", []):
            bridge = Bridge(str(raw["id"]), frozenset(_position(p) for p in raw["tiles"]), raw.get("initial_state", "closed"))
            if bridge.id in bridges:
                raise ValueError(f"Duplicate bridge id: {bridge.id}")
            bridges[bridge.id] = bridge
        switches: dict[str, Switch] = {}
        for raw in data.get("switches", []):
            effect_raw = raw.get("effect", {})
            effect = SwitchEffect(
                type=effect_raw.get("type", "bridge"),
                bridge_ids=tuple(effect_raw.get("bridge_ids", ())),
                mode=effect_raw.get("mode"), state=effect_raw.get("state"),
                trigger=effect_raw.get("trigger", "enter"),
                destinations=tuple(_position(p) for p in effect_raw.get("destinations", ())),
                lock_after_activation=bool(effect_raw.get("lock_after_activation", False)),
            )
            switch = Switch(str(raw["id"]), str(raw["type"]), _position(raw["position"]), effect)
            if switch.id in switches:
                raise ValueError(f"Duplicate switch id: {switch.id}")
            switches[switch.id] = switch
        split_raw = data.get("split_rules", {})
        split_rules = SplitRules(
            control_switch_key=split_raw.get("control_switch_key", "SPACE"),
            merge_when_adjacent=bool(split_raw.get("merge_when_adjacent", True)),
            single_cube_can_win=bool(split_raw.get("single_cube_can_win", False)),
            single_cube_activates=frozenset(split_raw.get("single_cube_activates", ["soft"])),
            single_cube_cannot_activate=frozenset(split_raw.get("single_cube_cannot_activate", ["heavy", "split"])),
        )
        return cls(
            width=int(data["width"]), height=int(data["height"]),
            tiles=frozenset(_position(p) for p in data["tiles"]),
            goal=_position(data["goal"]),
            fragile_tiles=frozenset(_position(p) for p in data.get("fragile_tiles", [])),
            bridges=bridges, switches=switches, split_rules=split_rules,
        )

    def in_bounds(self, position: Position) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def bridge_at(self, position: Position) -> Bridge | None:
        return next((bridge for bridge in self.bridges.values() if position in bridge.tiles), None)

    def is_passable(self, position: Position, bridge_states: Mapping[str, str]) -> bool:
        if not self.in_bounds(position):
            return False
        bridge = self.bridge_at(position)
        if bridge is not None:
            return bridge_states.get(bridge.id, bridge.initial_state) == "open"
        return position in self.tiles

    def supports(self, cells: Iterable[Position], bridge_states: Mapping[str, str]) -> bool:
        return all(self.is_passable(cell, bridge_states) for cell in cells)

    def initial_bridge_states(self) -> dict[str, str]:
        return {bridge_id: bridge.initial_state for bridge_id, bridge in self.bridges.items()}

    def switch_at(self, position: Position) -> Switch | None:
        return next((switch for switch in self.switches.values() if switch.position == position), None)
