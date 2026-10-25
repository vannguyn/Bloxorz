"""Mô hình board và các tile/cơ chế của một stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .block import Position
from entities.bridge import Bridge
from entities.switch import Switch, SwitchEffect
from entities.tile import Tile, TileType


def _position(value: Iterable[int]) -> Position:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"Invalid position: {value!r}")
    value = tuple(value)
    if len(value) != 2 or not all(type(v) is int for v in value):
        raise ValueError(f"Invalid position: {value!r}")
    return value[0], value[1]


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
        if any(not self.in_bounds(position) for position in self.tiles):
            raise ValueError("Board tiles must be within board bounds")
        if any(not self.in_bounds(position) for position in self.fragile_tiles):
            raise ValueError("Fragile tiles must be within board bounds")
        if not self.in_bounds(self.goal):
            raise ValueError("Goal must be within board bounds")
        bridge_cells: set[Position] = set()
        for bridge in self.bridges.values():
            if not bridge.tiles:
                raise ValueError(f"Bridge {bridge.id!r} must contain at least one tile")
            if bridge_cells.intersection(bridge.tiles):
                raise ValueError("A coordinate cannot belong to multiple bridges")
            if bridge.tiles.intersection(self.tiles):
                raise ValueError("Bridge coordinates cannot overlap board tiles")
            if any(not self.in_bounds(position) for position in bridge.tiles):
                raise ValueError(f"Bridge {bridge.id!r} has a tile outside board bounds")
            bridge_cells.update(bridge.tiles)
        if self.goal not in self.tiles and not any(self.goal in b.tiles for b in self.bridges.values()):
            raise ValueError("Goal must be a board tile or an openable bridge tile")
        if not self.fragile_tiles.issubset(self.tiles):
            raise ValueError("Every fragile tile must be listed in tiles")
        for switch in self.switches.values():
            if switch.position not in self.tiles:
                raise ValueError(f"Switch {switch.id!r} is not on a board tile")
            if switch.type not in {"soft", "heavy", "split"}:
                raise ValueError(f"Switch {switch.id!r} has invalid type {switch.type!r}")
            if switch.effect.trigger != "enter":
                raise ValueError(f"Switch {switch.id!r} has unsupported trigger")
            if switch.effect.type == "bridge":
                if switch.effect.mode not in {"toggle", "permanent"}:
                    raise ValueError(f"Switch {switch.id!r} has invalid bridge mode")
                if not switch.effect.bridge_ids:
                    raise ValueError(f"Switch {switch.id!r} must reference a bridge")
                if any(bridge_id not in self.bridges for bridge_id in switch.effect.bridge_ids):
                    raise ValueError(f"Switch {switch.id!r} references an unknown bridge")
                if switch.effect.mode == "permanent" and switch.effect.state not in {"open", "closed"}:
                    raise ValueError(f"Switch {switch.id!r} needs a permanent open/closed state")
            elif switch.effect.type == "split":
                if len(switch.effect.destinations) != 2:
                    raise ValueError(f"Split switch {switch.id!r} needs two destinations")
                if any(not self.in_bounds(position) or position not in self.tiles
                       for position in switch.effect.destinations):
                    raise ValueError(f"Split switch {switch.id!r} has an invalid destination")
            else:
                raise ValueError(f"Switch {switch.id!r} has invalid effect type")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Board":
        if not isinstance(data, Mapping):
            raise ValueError("Board data must be an object")
        for key in ("width", "height", "tiles", "goal"):
            if key not in data:
                raise ValueError(f"Missing required board field: {key}")
        for key in ("width", "height"):
            if type(data[key]) is not int:
                raise ValueError(f"Board {key} must be an integer")
        for key in ("tiles", "fragile_tiles", "bridges", "switches"):
            if key in data and not isinstance(data[key], list):
                raise ValueError(f"Board {key} must be a list")
        split_raw = data.get("split_rules", {})
        if not isinstance(split_raw, Mapping):
            raise ValueError("split_rules must be an object")

        bridges: dict[str, Bridge] = {}
        for raw in data.get("bridges", []):
            if not isinstance(raw, Mapping):
                raise ValueError("Each bridge must be an object")
            if not isinstance(raw.get("id"), str) or not raw["id"]:
                raise ValueError("Bridge id must be a non-empty string")
            if not isinstance(raw.get("tiles"), list):
                raise ValueError(f"Bridge {raw['id']!r} tiles must be a list")
            bridge_positions = [_position(position) for position in raw["tiles"]]
            if len(set(bridge_positions)) != len(bridge_positions):
                raise ValueError(f"Bridge {raw['id']!r} contains duplicate tile coordinates")
            if "initial_state" in raw and not isinstance(raw["initial_state"], str):
                raise ValueError(f"Bridge {raw['id']!r} initial_state must be a string")
            bridge = Bridge(raw["id"], frozenset(bridge_positions), raw.get("initial_state", "closed"))
            if bridge.id in bridges:
                raise ValueError(f"Duplicate bridge id: {bridge.id}")
            bridges[bridge.id] = bridge
        switches: dict[str, Switch] = {}
        for raw in data.get("switches", []):
            if not isinstance(raw, Mapping):
                raise ValueError("Each switch must be an object")
            if not isinstance(raw.get("id"), str) or not raw["id"]:
                raise ValueError("Switch id must be a non-empty string")
            switch_type = raw.get("type")
            if not isinstance(switch_type, str) or switch_type not in {"soft", "heavy", "split"}:
                raise ValueError(f"Switch {raw['id']!r} has invalid type")
            if "position" not in raw:
                raise ValueError(f"Switch {raw['id']!r} is missing position")
            effect_raw = raw.get("effect", {})
            if not isinstance(effect_raw, Mapping):
                raise ValueError(f"Switch {raw['id']!r} effect must be an object")
            if not isinstance(effect_raw.get("bridge_ids", []), list):
                raise ValueError(f"Switch {raw['id']!r} bridge_ids must be a list")
            if not isinstance(effect_raw.get("destinations", []), list):
                raise ValueError(f"Switch {raw['id']!r} destinations must be a list")
            for key in ("type", "mode", "state", "trigger"):
                if key in effect_raw and not isinstance(effect_raw[key], str):
                    raise ValueError(f"Switch {raw['id']!r} effect.{key} must be a string")
            if not all(isinstance(bridge_id, str) for bridge_id in effect_raw.get("bridge_ids", [])):
                raise ValueError(f"Switch {raw['id']!r} bridge_ids must contain strings")
            lock_after_activation = effect_raw.get("lock_after_activation", False)
            if type(lock_after_activation) is not bool:
                raise ValueError(f"Switch {raw['id']!r} lock_after_activation must be boolean")
            effect = SwitchEffect(
                type=effect_raw.get("type", "bridge"),
                bridge_ids=tuple(effect_raw.get("bridge_ids", ())),
                mode=effect_raw.get("mode"), state=effect_raw.get("state"),
                trigger=effect_raw.get("trigger", "enter"),
                destinations=tuple(_position(p) for p in effect_raw.get("destinations", ())),
                lock_after_activation=lock_after_activation,
            )
            switch = Switch(raw["id"], switch_type, _position(raw["position"]), effect)
            if switch.id in switches:
                raise ValueError(f"Duplicate switch id: {switch.id}")
            switches[switch.id] = switch
        for key in ("merge_when_adjacent", "single_cube_can_win"):
            if key in split_raw and type(split_raw[key]) is not bool:
                raise ValueError(f"split_rules.{key} must be boolean")
        for key in ("single_cube_activates", "single_cube_cannot_activate"):
            if key in split_raw and not isinstance(split_raw[key], list):
                raise ValueError(f"split_rules.{key} must be a list")
            if key in split_raw and not all(isinstance(value, str) for value in split_raw[key]):
                raise ValueError(f"split_rules.{key} must contain strings")
        if "control_switch_key" in split_raw and not isinstance(split_raw["control_switch_key"], str):
            raise ValueError("split_rules.control_switch_key must be a string")
        tile_positions = [_position(position) for position in data["tiles"]]
        if len(set(tile_positions)) != len(tile_positions):
            raise ValueError("Board tiles contain duplicate coordinates")
        fragile_positions = [_position(position) for position in data.get("fragile_tiles", [])]
        if len(set(fragile_positions)) != len(fragile_positions):
            raise ValueError("Fragile tiles contain duplicate coordinates")
        split_rules = SplitRules(
            control_switch_key=split_raw.get("control_switch_key", "SPACE"),
            merge_when_adjacent=split_raw.get("merge_when_adjacent", True),
            single_cube_can_win=split_raw.get("single_cube_can_win", False),
            single_cube_activates=frozenset(split_raw.get("single_cube_activates", ["soft"])),
            single_cube_cannot_activate=frozenset(split_raw.get("single_cube_cannot_activate", ["heavy", "split"])),
        )
        return cls(
            width=int(data["width"]), height=int(data["height"]),
            tiles=frozenset(tile_positions),
            goal=_position(data["goal"]),
            fragile_tiles=frozenset(fragile_positions),
            bridges=bridges, switches=switches, split_rules=split_rules,
        )

    def in_bounds(self, position: Position) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def tile_at(self, position: Position) -> Tile:
        if not self.in_bounds(position) or (
            position not in self.tiles and self.bridge_at(position) is None
        ):
            return Tile(position, TileType.VOID)
        bridge = self.bridge_at(position)
        if bridge is not None:
            return Tile(position, TileType.BRIDGE, bridge.id)
        if position == self.goal:
            return Tile(position, TileType.GOAL)
        if position in self.fragile_tiles:
            return Tile(position, TileType.FRAGILE)
        return Tile(position, TileType.FLOOR)

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
