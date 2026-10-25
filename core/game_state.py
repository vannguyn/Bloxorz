"""Trạng thái game và transition dùng chung cho người chơi lẫn solver."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .block import Block, Cube, Direction, Orientation, Piece, Position, cells_of
from .board import Board
from .game_rules import (
    are_adjacent,
    can_activate_switch,
    entered_switches,
    is_legal_piece,
    is_win,
)
from .movement import move_block, move_cube


def _bridge_tuple(values: Mapping[str, str] | tuple[tuple[str, str], ...], board: Board) -> tuple[tuple[str, str], ...]:
    if isinstance(values, Mapping):
        values = tuple(values.items())
    source = dict(values)
    return tuple(sorted((bridge_id, source.get(bridge_id, bridge.initial_state)) for bridge_id, bridge in board.bridges.items()))


@dataclass(frozen=True, slots=True)
class GameState:
    """Một state đầy đủ cho search.

    Với state split, ``block`` là cube đang được điều khiển và
    ``second_cube`` là cube còn lại. Bridge configuration và locked switches
    nằm trong key vì cùng vị trí block nhưng cơ chế khác nhau là hai state khác.
    """

    board: Board
    block: Piece
    second_cube: Cube | None = None
    controlled_index: int = 0
    bridge_states: Mapping[str, str] | tuple[tuple[str, str], ...] = ()
    locked_switches: frozenset[str] = frozenset()
    status: str = "playing"
    moves: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "bridge_states", _bridge_tuple(self.bridge_states, self.board))
        object.__setattr__(self, "locked_switches", frozenset(self.locked_switches))
        if isinstance(self.block, Cube) and self.second_cube is None:
            raise ValueError("A split state must contain two cubes")
        if not isinstance(self.block, Cube) and self.second_cube is not None:
            raise ValueError("second_cube is only valid for a split state")
        if self.controlled_index not in {0, 1}:
            raise ValueError("controlled_index must be 0 or 1")

    @classmethod
    def start(cls, board: Board, position: Position, orientation: Orientation | str = Orientation.STANDING) -> "GameState":
        block = Block(position, orientation)
        states = board.initial_bridge_states()
        if not is_legal_piece(board, block, states):
            raise ValueError("Starting block is not supported by the board")
        return cls(board, block, bridge_states=states)

    @property
    def bridge_map(self) -> dict[str, str]:
        return dict(self.bridge_states)

    @property
    def is_split(self) -> bool:
        return isinstance(self.block, Cube)

    @property
    def pieces(self) -> tuple[Piece, ...]:
        if self.is_split:
            assert self.second_cube is not None
            if self.controlled_index == 0:
                return self.block, self.second_cube
            return self.second_cube, self.block
        return (self.block,)

    @property
    def occupied_cells(self) -> tuple[Position, ...]:
        return cells_of(self.pieces)

    @property
    def controlled_cube(self) -> Cube:
        if not self.is_split:
            raise ValueError("A normal block has no cube control")
        assert self.second_cube is not None
        return self.block if self.controlled_index == 0 else self.second_cube

    def key(self) -> tuple[Any, ...]:
        if self.is_split:
            assert self.second_cube is not None
            cube_a, cube_b = sorted((self.block.position, self.second_cube.position))
            piece_key = ("split", cube_a, cube_b, self.controlled_cube.position)
        else:
            assert isinstance(self.block, Block)
            piece_key = ("block", self.block.as_key())
        return piece_key + (self.bridge_states, tuple(sorted(self.locked_switches)), self.status)

    def is_won(self) -> bool:
        if self.is_split:
            return self.board.split_rules.single_cube_can_win and any(
                is_win(self.board, piece, single_cube_can_win=True) for piece in self.pieces
            )
        return is_win(self.board, self.block)

    def switch_control(self) -> "GameState":
        """Đổi cube điều khiển, tương ứng phím SPACE."""
        if not self.is_split:
            return self
        return GameState(
            self.board, self.block, self.second_cube,
            1 - self.controlled_index, self.bridge_states,
            self.locked_switches, self.status, self.moves,
        )

    def move(self, direction: Direction | str) -> "GameState | None":
        """Thực hiện một nước hợp lệ; trả ``None`` nếu block sẽ rơi.

        UI có thể dùng ``None`` để báo game over/illegal move. Solver chỉ cần
        bỏ successor đó, vì state rơi không thể dẫn tới goal.
        """
        if self.status != "playing":
            return None
        direction = Direction.coerce(direction)
        bridges = self.bridge_map
        old_cells = self.occupied_cells

        if self.is_split:
            moving = self.controlled_cube
            candidate = move_cube(moving, direction)
            other = self.second_cube if self.controlled_index == 0 else self.block
            assert isinstance(other, Cube)
            if not is_legal_piece(self.board, (candidate, other), bridges):
                return None
            if self.controlled_index == 0:
                next_block, next_other = candidate, other
            else:
                next_block, next_other = other, candidate
            next_bridges, locks = self._apply_entered_switches(
                old_cells, (next_block.position, next_other.position), candidate,
                bridges, self.locked_switches,
            )
            if self.board.split_rules.merge_when_adjacent and are_adjacent(next_block.position, next_other.position):
                merged = _merge_cubes(next_block, next_other)
                if merged is not None:
                    return GameState(
                        self.board, merged, bridge_states=next_bridges,
                        locked_switches=locks, status="won" if is_win(self.board, merged) else "playing",
                        moves=self.moves + 1,
                    )
            return GameState(
                self.board, next_block, next_other, self.controlled_index,
                next_bridges, locks, "playing", self.moves + 1,
            )

        assert isinstance(self.block, Block)
        candidate = move_block(self.block, direction)
        if not is_legal_piece(self.board, candidate, bridges):
            return None
        next_bridges, locks, split_destinations = self._apply_entered_switches(
            old_cells, candidate.cells, candidate, bridges, self.locked_switches,
            return_split=True,
        )
        if split_destinations is not None:
            first, second = (Cube(split_destinations[0]), Cube(split_destinations[1]))
            if first.position == second.position or not is_legal_piece(self.board, (first, second), dict(next_bridges)):
                return None
            return GameState(
                self.board, first, second, 0, next_bridges, locks,
                "playing", self.moves + 1,
            )
        won = is_win(self.board, candidate)
        return GameState(
            self.board, candidate, bridge_states=next_bridges,
            locked_switches=locks, status="won" if won else "playing", moves=self.moves + 1,
        )

    apply_move = move

    def _apply_entered_switches(
        self,
        old_cells: tuple[Position, ...],
        new_cells: tuple[Position, ...],
        triggering_piece: Piece,
        bridges: Mapping[str, str],
        locks: frozenset[str],
        *,
        return_split: bool = False,
    ) -> tuple[tuple[tuple[str, str], ...], frozenset[str]] | tuple[tuple[tuple[str, str], ...], frozenset[str], tuple[Position, Position] | None]:
        bridge_map = dict(bridges)
        locked = set(locks)
        split_destinations: tuple[Position, Position] | None = None
        for switch in entered_switches(self.board, old_cells, new_cells):
            effect = switch.effect
            if effect.trigger != "enter" or switch.id in locked or not can_activate_switch(self.board, switch, triggering_piece):
                continue
            if effect.type == "bridge":
                for bridge_id in effect.bridge_ids:
                    if bridge_id not in self.board.bridges:
                        raise ValueError(f"Switch {switch.id!r} references unknown bridge {bridge_id!r}")
                    if effect.mode == "toggle":
                        bridge_map[bridge_id] = "closed" if bridge_map[bridge_id] == "open" else "open"
                    elif effect.mode == "permanent":
                        if effect.state not in {"open", "closed"}:
                            raise ValueError(f"Permanent switch {switch.id!r} needs state open/closed")
                        bridge_map[bridge_id] = effect.state
                    else:
                        raise ValueError(f"Unknown bridge mode: {effect.mode!r}")
            elif effect.type == "split" and isinstance(triggering_piece, Block):
                if len(effect.destinations) != 2:
                    raise ValueError(f"Split switch {switch.id!r} needs two destinations")
                split_destinations = effect.destinations[0], effect.destinations[1]
            if effect.lock_after_activation:
                locked.add(switch.id)
        result = tuple(sorted(bridge_map.items()))
        if return_split:
            return result, frozenset(locked), split_destinations
        return result, frozenset(locked)


def _merge_cubes(first: Cube, second: Cube) -> Block | None:
    x1, y1 = first.position
    x2, y2 = second.position
    if y1 == y2 and abs(x1 - x2) == 1:
        return Block((min(x1, x2), y1), Orientation.HORIZONTAL)
    if x1 == x2 and abs(y1 - y2) == 1:
        return Block((x1, min(y1, y2)), Orientation.VERTICAL)
    return None
