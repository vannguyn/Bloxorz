"""Core Bloxorz rules shared by the GUI and search solvers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .block import Block, Cube, Piece, Position, cells_of
from .board import Board, Switch


CORE_RULES_NOTE = """
BLOXORZ CORE NOTE
1. A standing block occupies one cell; a lying block occupies two cells.
2. A move is rejected when any occupied cell is outside the board, void, or a closed bridge.
3. A block wins only when it is standing on the goal.
4. Soft switches accept any block footprint; heavy and split switches need a standing block.
5. Switches trigger only when the block enters their cell.
6. A fragile surface is two adjacent cells. A lying block must cover both cells;
   standing on either one or covering only one causes the block to fall.
""".strip()


def occupied_cells(piece_or_pieces: Piece | Iterable[Piece]) -> tuple[Position, ...]:
    if isinstance(piece_or_pieces, (Block, Cube)):
        return piece_or_pieces.cells
    return cells_of(piece_or_pieces)


def is_legal_piece(board: Board, piece: Piece | Iterable[Piece], bridge_states: Mapping[str, str]) -> bool:
    """Return whether every piece cell is supported by the current board."""
    pieces = (piece,) if isinstance(piece, (Block, Cube)) else tuple(piece)
    if not pieces:
        return False

    all_cells = occupied_cells(pieces)
    if len(all_cells) != sum(len(item.cells) for item in pieces):
        return False
    if not board.supports(all_cells, bridge_states):
        return False

    # Fragile tiles are meaningful as pairs. Weight is distributed safely only
    # when one lying block covers both fragile cells in the pair.
    fragile_cells = set(all_cells).intersection(board.fragile_tiles)
    if fragile_cells:
        if len(pieces) != 1 or not isinstance(pieces[0], Block):
            return False
        block = pieces[0]
        if block.is_standing or len(fragile_cells) != len(block.cells):
            return False
        if not set(block.cells).issubset(board.fragile_tiles):
            return False
    return True


def is_legal_move(board: Board, piece: Piece, direction: str, bridge_states: Mapping[str, str]) -> bool:
    candidate = piece.moved(direction)
    return is_legal_piece(board, candidate, bridge_states)


def is_win(board: Board, piece: Piece | Iterable[Piece], *, single_cube_can_win: bool = False) -> bool:
    if isinstance(piece, Block):
        return piece.is_standing and piece.position == board.goal
    if isinstance(piece, Cube):
        return single_cube_can_win and piece.position == board.goal
    return False


def can_activate_switch(board: Board, switch: Switch, piece: Piece) -> bool:
    if switch.position not in piece.cells:
        return False
    if isinstance(piece, Cube):
        return switch.type in board.split_rules.single_cube_activates and switch.type not in board.split_rules.single_cube_cannot_activate
    if switch.type == "soft":
        return True
    return switch.type in {"heavy", "split"} and piece.is_standing


def entered_switches(board: Board, old_cells: Iterable[Position], new_cells: Iterable[Position]) -> tuple[Switch, ...]:
    entered = set(new_cells) - set(old_cells)
    return tuple(switch for switch in board.switches.values() if switch.position in entered)


def are_adjacent(first: Position, second: Position) -> bool:
    return abs(first[0] - second[0]) + abs(first[1] - second[1]) == 1
