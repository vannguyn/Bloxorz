from core.block import Block, Orientation
from core.board import Board
from core.game_rules import is_legal_piece, is_win


def test_fragile_tile_support_depends_on_block_orientation() -> None:
    board = Board(
        width=3,
        height=1,
        tiles=frozenset({(0, 0), (1, 0), (2, 0)}),
        goal=(2, 0),
        fragile_tiles=frozenset({(1, 0)}),
    )

    assert not is_legal_piece(board, Block((1, 0)), {})
    assert is_legal_piece(board, Block((0, 0), Orientation.HORIZONTAL), {})


def test_goal_requires_standing_block() -> None:
    board = Board(width=2, height=1, tiles=frozenset({(0, 0), (1, 0)}), goal=(1, 0))

    assert is_win(board, Block((1, 0)))
    assert not is_win(board, Block((0, 0), Orientation.HORIZONTAL))