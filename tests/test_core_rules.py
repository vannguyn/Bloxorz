import json
from pathlib import Path

from core.block import Block, Cube, Direction, Orientation
from core.board import Board
from core.game_rules import can_activate_switch, is_legal_piece, is_win
from core.game_state import GameState


def board_from_level() -> Board:
    data = json.loads((Path(__file__).parents[1] / "levels" / "level_01.json").read_text(encoding="utf-8"))
    return Board.from_dict(data)


def test_orientation_transition_table():
    standing = Block((3, 3), Orientation.STANDING)
    assert standing.moved(Direction.RIGHT) == Block((4, 3), Orientation.HORIZONTAL)
    assert standing.moved(Direction.LEFT) == Block((1, 3), Orientation.HORIZONTAL)
    assert standing.moved(Direction.UP) == Block((3, 1), Orientation.VERTICAL)
    assert standing.moved(Direction.DOWN) == Block((3, 4), Orientation.VERTICAL)

    horizontal = Block((3, 3), Orientation.HORIZONTAL)
    assert horizontal.moved(Direction.LEFT) == Block((2, 3), Orientation.STANDING)
    assert horizontal.moved(Direction.RIGHT) == Block((5, 3), Orientation.STANDING)
    assert horizontal.moved(Direction.DOWN) == Block((3, 4), Orientation.HORIZONTAL)
    assert horizontal.moved(Direction.UP) == Block((3, 2), Orientation.HORIZONTAL)

    vertical = Block((3, 3), Orientation.VERTICAL)
    assert vertical.moved(Direction.UP) == Block((3, 2), Orientation.STANDING)
    assert vertical.moved(Direction.DOWN) == Block((3, 5), Orientation.STANDING)
    assert vertical.moved(Direction.LEFT) == Block((2, 3), Orientation.VERTICAL)
    assert vertical.moved(Direction.RIGHT) == Block((4, 3), Orientation.VERTICAL)
    assert len(Block((3, 3), Orientation.STANDING).cells) == 1
    assert len(horizontal.cells) == len(vertical.cells) == 2


def test_void_and_fragile_rules():
    board = Board(
        width=5,
        height=3,
        tiles=frozenset((x, y) for x in range(5) for y in range(3)),
        goal=(4, 2),
        fragile_tiles=frozenset({(2, 1), (3, 1)}),
    )
    states = board.initial_bridge_states()
    assert not is_legal_piece(board, Block((5, 0)), states)
    assert not is_legal_piece(board, Block((2, 1), Orientation.STANDING), states)
    assert not is_legal_piece(board, Block((1, 1), Orientation.HORIZONTAL), states)
    assert is_legal_piece(board, Block((2, 1), Orientation.HORIZONTAL), states)

    full_board = Board(
        width=3,
        height=3,
        tiles=frozenset((x, y) for x in range(3) for y in range(3)),
        goal=(2, 2),
    )
    assert not is_legal_piece(full_board, Block((2, 1), Orientation.HORIZONTAL), {})
    assert not is_legal_piece(full_board, Block((1, 2), Orientation.VERTICAL), {})


def test_goal_requires_standing_block():
    board = Board(width=4, height=2, tiles=frozenset((x, y) for x in range(4) for y in range(2)), goal=(3, 0))
    assert not is_win(board, Block((2, 0), Orientation.HORIZONTAL))
    assert not is_win(board, Block((3, 0), Orientation.VERTICAL))
    assert is_win(board, Block((3, 0), Orientation.STANDING))
    assert not is_win(board, Cube((3, 0)), single_cube_can_win=False)

    playable_board = Board(
        width=6,
        height=1,
        tiles=frozenset((x, 0) for x in range(6)),
        goal=(3, 0),
    )
    state = GameState.start(playable_board, (0, 0)).move(Direction.RIGHT)
    assert state is not None and state.status == "playing"
    won = state.move(Direction.RIGHT)
    assert won is not None and won.block == Block((3, 0), Orientation.STANDING)
    assert won.status == "won"
    assert won.move(Direction.LEFT) is None


def test_closed_bridge_is_void_and_soft_switch_opens_it():
    board = Board.from_dict(
        {
            "width": 4,
            "height": 1,
            "tiles": [[0, 0], [1, 0], [2, 0]],
            "goal": [2, 0],
            "bridges": [{"id": "bridge", "tiles": [[3, 0]], "initial_state": "closed"}],
            "switches": [
                {
                    "id": "soft",
                    "type": "soft",
                    "position": [1, 0],
                    "effect": {
                        "type": "bridge",
                        "bridge_ids": ["bridge"],
                        "mode": "toggle",
                        "trigger": "enter",
                    },
                }
            ],
        }
    )
    state = GameState.start(board, (0, 0))
    assert not board.is_passable((3, 0), state.bridge_map)

    opened = state.move(Direction.RIGHT)
    assert opened is not None
    assert opened.bridge_map["bridge"] == "open"
    assert board.is_passable((3, 0), opened.bridge_map)

    left_switch = opened.move(Direction.LEFT)
    assert left_switch is not None
    closed = left_switch.move(Direction.RIGHT)
    assert closed is not None
    assert closed.bridge_map["bridge"] == "closed"
    assert not board.is_passable((3, 0), closed.bridge_map)


def test_switch_weight_rules():
    board = Board.from_dict(
        {
            "width": 7,
            "height": 7,
            "tiles": [[x, y] for x in range(7) for y in range(7)],
            "goal": [0, 0],
            "switches": [
                {"id": "soft", "type": "soft", "position": [2, 2]},
                {"id": "heavy", "type": "heavy", "position": [4, 4]},
                {"id": "split", "type": "split", "position": [5, 4]},
            ],
        }
    )
    soft = board.switch_at((2, 2))
    heavy = board.switch_at((4, 4))
    split = board.switch_at((5, 4))
    assert soft is not None and heavy is not None and split is not None

    assert can_activate_switch(board, soft, Block((2, 2), Orientation.HORIZONTAL))
    assert can_activate_switch(board, soft, Block((1, 2), Orientation.HORIZONTAL))
    assert not can_activate_switch(board, heavy, Block((3, 4), Orientation.HORIZONTAL))
    assert can_activate_switch(board, heavy, Block((4, 4), Orientation.STANDING))
    assert can_activate_switch(board, split, Block((5, 4), Orientation.STANDING))
    assert not can_activate_switch(board, split, Block((4, 4), Orientation.HORIZONTAL))
    assert can_activate_switch(board, soft, Cube((2, 2)))
    assert not can_activate_switch(board, heavy, Cube((4, 4)))
    assert not can_activate_switch(board, split, Cube((5, 4)))


def test_split_control_and_state_key_distinguish_controlled_cube():
    board = Board(width=5, height=1, tiles=frozenset((x, 0) for x in range(5)), goal=(4, 0))
    state = GameState(board, Cube((0, 0)), Cube((4, 0)))

    switched = state.switch_control()
    assert switched.controlled_cube == Cube((4, 0))
    moved = switched.move(Direction.LEFT)
    assert moved is not None
    assert moved.controlled_cube == Cube((3, 0))
    assert moved.block == Cube((0, 0))

    same_controlled_position = GameState(
        board, Cube((4, 0)), Cube((0, 0)), controlled_index=1
    )
    reversed_positions = GameState(board, Cube((4, 0)), Cube((0, 0)))
    assert state.key() == same_controlled_position.key()
    assert state.key() != reversed_positions.key()


def test_state_key_includes_orientation_and_bridge_state():
    board = Board.from_dict(
        {
            "width": 4,
            "height": 1,
            "tiles": [[0, 0], [1, 0], [2, 0]],
            "goal": [2, 0],
            "bridges": [{"id": "bridge", "tiles": [[3, 0]], "initial_state": "closed"}],
        }
    )
    standing = GameState(board, Block((0, 0)), bridge_states={"bridge": "closed"})
    lying = GameState(
        board,
        Block((0, 0), Orientation.HORIZONTAL),
        bridge_states={"bridge": "closed"},
    )
    bridge_open = GameState(board, Block((0, 0)), bridge_states={"bridge": "open"})

    assert standing.key() != lying.key()
    assert standing.key() != bridge_open.key()


def test_split_cubes_merge_when_adjacent():
    board = Board(width=4, height=2, tiles=frozenset((x, y) for x in range(4) for y in range(2)), goal=(3, 1))
    state = GameState(board, Cube((0, 0)), Cube((2, 0)), bridge_states={})
    merged = state.move(Direction.RIGHT)
    assert merged is not None
    assert merged.block == Block((1, 0), Orientation.HORIZONTAL)
