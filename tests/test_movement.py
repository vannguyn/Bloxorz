from core.block import Block, Cube, Direction, Orientation
from core.movement import move_block, move_cube


def test_block_rolls_from_each_orientation() -> None:
    assert move_block(Block((3, 3)), "right") == Block((4, 3), Orientation.HORIZONTAL)
    assert move_block(Block((3, 3)), "up") == Block((3, 1), Orientation.VERTICAL)
    assert move_block(Block((3, 3), Orientation.HORIZONTAL), "left") == Block((2, 3))
    assert move_block(Block((3, 3), Orientation.VERTICAL), "down") == Block((3, 5))


def test_cube_moves_one_cell_in_each_direction() -> None:
    cube = Cube((3, 3))
    expected = {
        Direction.UP: Cube((3, 2)),
        Direction.DOWN: Cube((3, 4)),
        Direction.LEFT: Cube((2, 3)),
        Direction.RIGHT: Cube((4, 3)),
    }

    for direction, result in expected.items():
        assert move_cube(cube, direction) == result