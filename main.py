"""Chạy kiểm thử nhanh các core rules của Bloxorz.

File này không mở GUI. Nó tạo các board nhỏ, thực hiện các nước đi và
assert kết quả theo đề bài. Chạy bằng:

    python main.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

from core.block import Block, Cube, Direction, Orientation
from core.board import Board
from core.game_rules import can_activate_switch, is_legal_piece, is_win
from core.game_state import GameState


ROOT = Path(__file__).resolve().parent


def load_sample_board() -> Board:
    level_path = ROOT / "levels" / "level_01.json"
    data = json.loads(level_path.read_text(encoding="utf-8"))
    return Board.from_dict(data)


def full_board(width: int, height: int, goal: tuple[int, int]) -> Board:
    """Tạo board kín để kiểm thử các luật không liên quan đến level JSON."""
    tiles = frozenset((x, y) for x in range(width) for y in range(height))
    return Board(width=width, height=height, tiles=tiles, goal=goal)


def test_orientation_rules() -> None:
    """Kiểm tra bảng chuyển orientation của block."""
    standing = Block((3, 3), Orientation.STANDING)
    assert standing.moved(Direction.RIGHT) == Block((4, 3), Orientation.HORIZONTAL)
    assert standing.moved(Direction.LEFT) == Block((1, 3), Orientation.HORIZONTAL)
    assert standing.moved(Direction.UP) == Block((3, 1), Orientation.VERTICAL)
    assert standing.moved(Direction.DOWN) == Block((3, 4), Orientation.VERTICAL)

    horizontal = Block((3, 3), Orientation.HORIZONTAL)
    assert horizontal.moved(Direction.RIGHT) == Block((5, 3), Orientation.STANDING)
    assert horizontal.moved(Direction.UP) == Block((3, 2), Orientation.HORIZONTAL)

    vertical = Block((3, 3), Orientation.VERTICAL)
    assert vertical.moved(Direction.DOWN) == Block((3, 5), Orientation.STANDING)
    assert vertical.moved(Direction.LEFT) == Block((2, 3), Orientation.VERTICAL)


def test_void_edge_and_fragile_rules() -> None:
    board = load_sample_board()
    bridge_states = board.initial_bridge_states()

    # (0, 0) là void; block cũng không được đi ra ngoài board.
    assert not is_legal_piece(board, Block((0, 0)), bridge_states)
    assert not is_legal_piece(board, Block((0, 0), Orientation.HORIZONTAL), bridge_states)

    # Fragile chỉ cho phép block nằm đè qua, không cho block đứng.
    assert not is_legal_piece(board, Block((3, 2), Orientation.STANDING), bridge_states)
    assert is_legal_piece(board, Block((2, 2), Orientation.HORIZONTAL), bridge_states)

    # Bridge đóng behave như void.
    assert not board.is_passable((4, 1), bridge_states)

    bounds_board = full_board(3, 3, (2, 2))
    assert not is_legal_piece(bounds_board, Block((2, 1), Orientation.HORIZONTAL), {})
    assert not is_legal_piece(bounds_board, Block((1, 2), Orientation.VERTICAL), {})


def test_goal_rule() -> None:
    board = full_board(4, 2, (3, 0))
    assert not is_win(board, Block((2, 0), Orientation.HORIZONTAL))
    assert is_win(board, Block((3, 0), Orientation.STANDING))
    assert not is_win(board, Cube((3, 0)))

    playable_board = full_board(6, 1, (3, 0))
    state = GameState.start(playable_board, (0, 0)).move(Direction.RIGHT)
    assert state is not None and state.status == "playing"
    won = state.move(Direction.RIGHT)
    assert won is not None and won.block == Block((3, 0), Orientation.STANDING)
    assert won.status == "won"
    assert won.move(Direction.LEFT) is None


def test_soft_toggle_bridge() -> None:
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
    next_state = state.move(Direction.RIGHT)

    assert next_state is not None
    assert next_state.bridge_map["bridge"] == "open"
    assert board.is_passable((3, 0), next_state.bridge_map)

    # Đi ra rồi vào lại switch sẽ toggle bridge về closed.
    leave_switch = next_state.move(Direction.LEFT)
    assert leave_switch is not None
    toggle_again = leave_switch.move(Direction.RIGHT)
    assert toggle_again is not None
    assert toggle_again.bridge_map["bridge"] == "closed"


def test_heavy_permanent_switch() -> None:
    board = Board.from_dict(
        {
            "width": 5,
            "height": 1,
            "tiles": [[0, 0], [1, 0], [2, 0], [3, 0]],
            "goal": [3, 0],
            "bridges": [{"id": "bridge", "tiles": [[4, 0]], "initial_state": "closed"}],
            "switches": [
                {
                    "id": "heavy",
                    "type": "heavy",
                    "position": [1, 0],
                    "effect": {
                        "type": "bridge",
                        "bridge_ids": ["bridge"],
                        "mode": "permanent",
                        "state": "open",
                        "lock_after_activation": True,
                        "trigger": "enter",
                    },
                }
            ],
        }
    )
    state = GameState.start(board, (1, 0))
    not_heavy_yet = state.move(Direction.RIGHT)
    assert not_heavy_yet is not None
    assert not_heavy_yet.bridge_map["bridge"] == "closed"

    # Quay lại ô heavy ở tư thế đứng thì switch mới được kích hoạt.
    activated = not_heavy_yet.move(Direction.LEFT)
    assert activated is not None
    assert activated.bridge_map["bridge"] == "open"
    assert "heavy" in activated.locked_switches


def test_split_and_merge_rules() -> None:
    board = Board.from_dict(
        {
            "width": 5,
            "height": 1,
            "tiles": [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]],
            "goal": [4, 0],
            "switches": [
                {
                    "id": "split",
                    "type": "split",
                    "position": [1, 0],
                    "effect": {
                        "type": "split",
                        "destinations": [[0, 0], [4, 0]],
                        "trigger": "enter",
                    },
                }
            ],
        }
    )

    # Block rời switch rồi quay lại theo tư thế đứng để kích hoạt split.
    state = GameState.start(board, (1, 0))
    moved_away = state.move(Direction.RIGHT)
    assert moved_away is not None
    split_state = moved_away.move(Direction.LEFT)
    assert split_state is not None
    assert split_state.is_split
    assert split_state.block == Cube((0, 0))
    assert split_state.second_cube == Cube((4, 0))

    # Hai cube kề nhau sẽ nhập thành block 1 x 1 x 2.
    merge_board = full_board(4, 2, (3, 1))
    cubes = GameState(merge_board, Cube((0, 0)), Cube((2, 0)))
    merged = cubes.move(Direction.RIGHT)
    assert merged is not None
    assert merged.block == Block((1, 0), Orientation.HORIZONTAL)

    # The state key must identify which physical cube is currently controlled.
    controlled = cubes.switch_control()
    assert controlled.controlled_cube == Cube((2, 0))
    moved_controlled = controlled.move(Direction.RIGHT)
    assert moved_controlled is not None
    assert moved_controlled.controlled_cube == Cube((3, 0))
    assert moved_controlled.block == Cube((0, 0))
    same_controlled_position = GameState(
        merge_board, Cube((2, 0)), Cube((0, 0)), controlled_index=1
    )
    reversed_cubes = GameState(merge_board, Cube((2, 0)), Cube((0, 0)))
    assert cubes.key() == same_controlled_position.key()
    assert cubes.key() != reversed_cubes.key()


def test_state_key_rules() -> None:
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


def test_switch_weight_rules() -> None:
    board = load_sample_board()
    soft = board.switch_at((2, 2))
    heavy = board.switch_at((4, 4))
    split = board.switch_at((5, 4))
    assert soft is not None and heavy is not None and split is not None

    assert can_activate_switch(board, soft, Block((2, 2), Orientation.HORIZONTAL))
    assert not can_activate_switch(board, heavy, Block((3, 4), Orientation.HORIZONTAL))
    assert can_activate_switch(board, heavy, Block((4, 4), Orientation.STANDING))
    assert can_activate_switch(board, soft, Cube((2, 2)))
    assert not can_activate_switch(board, heavy, Cube((4, 4)))
    assert not can_activate_switch(board, split, Cube((5, 4)))


def run_test(name: str, test: Callable[[], None]) -> bool:
    try:
        test()
    except Exception as error:  # noqa: BLE001 - báo lỗi test rõ ràng trên terminal.
        print(f"[FAIL] {name}: {error}")
        return False
    print(f"[PASS] {name}")
    return True


def main() -> int:
    tests = [
        ("Orientation transitions", test_orientation_rules),
        ("Void, edge and fragile tiles", test_void_edge_and_fragile_rules),
        ("Victory condition", test_goal_rule),
        ("Soft switch + toggle bridge", test_soft_toggle_bridge),
        ("Heavy switch + permanent bridge", test_heavy_permanent_switch),
        ("Split and merge", test_split_and_merge_rules),
        ("Switch weight rules", test_switch_weight_rules),
        ("Complete search-state identity", test_state_key_rules),
    ]
    passed = sum(run_test(name, test) for name, test in tests)
    print(f"\nResult: {passed}/{len(tests)} rule groups passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
