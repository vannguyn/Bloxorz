"""Luật Bloxorz độc lập với GUI.

``GameState`` dùng các hàm ở đây để quyết định một nước đi có hợp lệ hay
không. Vì vậy animation hoặc giao diện không được tự ý thay đổi trạng thái:
mọi nước đi đều phải đi qua cùng một bộ luật này.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .block import Block, Cube, Piece, Position, cells_of
from .board import Board, Switch
from .movement import move_block, move_cube


# Chuỗi này có thể hiển thị trong UI/report hoặc dùng làm ghi chú ngay trong code.
CORE_RULES_NOTE = """
BLOXORZ CORE NOTE
1. Một Block đứng chiếm 1 ô; nằm ngang hoặc dọc chiếm 2 ô.
2. Mỗi phím Up/Down/Left/Right tạo đúng một successor theo bảng chuyển
   orientation trong Block.moved(). Nước đi bị từ chối nếu có ô ngoài board,
   ô void, bridge đang đóng, hoặc block đứng trên fragile tile.
3. Block chỉ thắng khi đang STANDING đúng trên goal; block nằm ngang/dọc
   trên goal chưa thắng. Một cube đơn cũng không thắng nếu split_rules cấm.
4. Soft switch nhận mọi phần của block; heavy và split chỉ nhận block đứng.
   Cube đơn chỉ được kích hoạt loại được khai báo trong split_rules.
5. Switch chỉ chạy khi block ENTER switch (ô mới chiếm), nên đứng yên trên
   switch không làm toggle lặp lại. Bridge đóng được xem như void; bridge mở
   được xem như floor. Toggle đảo trạng thái, permanent đặt trạng thái cố định.
6. Split switch đổi block thành hai Cube ở destinations. Hai cube được điều
   khiển luân phiên; khi kề nhau và merge_when_adjacent bật, chúng nhập lại
   thành Block.
7. Solver phải đưa orientation, vị trí cube đang điều khiển, vị trí cube còn
   lại, bridge states và các switch đã lock vào state key.
""".strip()


def occupied_cells(piece_or_pieces: Piece | Iterable[Piece]) -> tuple[Position, ...]:
    if isinstance(piece_or_pieces, (Block, Cube)):
        return piece_or_pieces.cells
    return cells_of(piece_or_pieces)


def is_legal_piece(board: Board, piece: Piece | Iterable[Piece], bridge_states: Mapping[str, str]) -> bool:
    """Kiểm tra block/cube có được toàn bộ mặt sàn đỡ hay không."""
    pieces = (piece,) if isinstance(piece, (Block, Cube)) else tuple(piece)
    if not pieces:
        return False
    all_cells = occupied_cells(pieces)
    if len(all_cells) != sum(len(item.cells) for item in pieces):
        return False  # Hai cube không được chồng lên nhau.
    if not board.supports(all_cells, bridge_states):
        return False
    # Fragile chỉ chịu được khi trọng lượng được phân bố: standing/cube là rơi.
    if any(position in board.fragile_tiles for position in all_cells):
        if any(isinstance(item, Cube) or (isinstance(item, Block) and item.is_standing) for item in pieces):
            return False
    return True


def is_legal_move(board: Board, piece: Piece, direction: str, bridge_states: Mapping[str, str]) -> bool:
    """Kiểm tra candidate sau roll, không làm thay đổi state hiện tại."""
    candidate = move_cube(piece, direction) if isinstance(piece, Cube) else move_block(piece, direction)
    return is_legal_piece(board, candidate, bridge_states)


def is_win(board: Board, piece: Piece | Iterable[Piece], *, single_cube_can_win: bool = False) -> bool:
    """Goal test đúng theo đề: chỉ block đứng trên goal mới thắng."""
    if isinstance(piece, Block):
        return piece.is_standing and piece.position == board.goal
    if isinstance(piece, Cube):
        return single_cube_can_win and piece.position == board.goal
    return False


def can_activate_switch(board: Board, switch: Switch, piece: Piece) -> bool:
    """Xác định switch có nhận được lực của piece hiện tại không."""
    if switch.position not in piece.cells:
        return False
    if isinstance(piece, Cube):
        return switch.type in board.split_rules.single_cube_activates and switch.type not in board.split_rules.single_cube_cannot_activate
    if switch.type == "soft":
        return True
    return switch.type in {"heavy", "split"} and piece.is_standing


def entered_switches(board: Board, old_cells: Iterable[Position], new_cells: Iterable[Position]) -> tuple[Switch, ...]:
    """Các switch mà piece vừa bước vào; không lặp trigger khi đứng yên."""
    old = set(old_cells)
    entered = set(new_cells) - old
    return tuple(switch for switch in board.switches.values() if switch.position in entered)


def are_adjacent(first: Position, second: Position) -> bool:
    return abs(first[0] - second[0]) + abs(first[1] - second[1]) == 1
