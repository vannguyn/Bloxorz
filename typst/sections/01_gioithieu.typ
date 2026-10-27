#import "../components.typ": styled_table, callout_note

= Bài toán và phạm vi thực hiện

== Phần thực hiện của thành viên số 5

*Thành viên số 5 — Võ Nhật Minh — MSSV: 24120202.*

Bloxorz là bài toán tìm chuỗi hành động đưa khối tới trạng thái thắng.
Hàm `core.game_rules.is_goal` xác định trạng thái đích: khối chưa tách và
đứng đúng ô đích. Thành viên số 5 phụ trách cài đặt A\*, xây dựng hàm ước
lượng (heuristic) và đánh giá lời giải trên đồ thị chuyển trạng thái do
phần lõi trò chơi cung cấp.

Trong phiên bản này, A\* tối thiểu hóa tổng chi phí, không nhất thiết tối
thiểu số hành động. Chi phí được tính bằng `StepCost` trong
`solvers/common.py`. Hành động `SPACE` cũng được tính vào chuỗi lời giải
và có chi phí.

== Đầu vào và đầu ra

Đầu vào gồm màn chơi `Level` và trạng thái bắt đầu `GameState`, có thể là
trạng thái ban đầu hoặc trạng thái hiện tại của người chơi. `GameState`
bất biến và có thể dùng làm khóa của bảng băm. Nó chứa thông tin về khối
và mặt nạ bit biểu diễn trạng thái các cầu. Thông tin khối gồm tư thế,
trạng thái tách, vị trí hai khối lập phương và khối đang được điều khiển.
Thuật toán dùng toàn bộ trạng thái làm khóa tìm kiếm.

Đầu ra là `SolverResult`, gồm chuỗi lời giải, trạng thái thành công, tổng
chi phí, số hành động, số lần mở rộng và các số đo thời gian, bộ nhớ.
Chuỗi lời giải dùng các ký hiệu `U`, `D`, `L`, `R`, `SPACE`. Nếu trạng thái
ban đầu đã thắng, chuỗi rỗng là lời giải hợp lệ có chi phí bằng 0.
Nếu hàng đợi tìm kiếm cạn, trường `path` là `None`, `solution_length` bằng
−1 và `cost` bằng vô cực.

== Ranh giới giữa các thành phần

#styled_table(
  (1fr, 2.4fr),
  ([Thành phần], [Trách nhiệm]),
  (
    [`core/interfaces.py`], [Các kiểu trạng thái, màn chơi và kết quả dùng chung.],
    [`core/game_rules.py`], [Sinh trạng thái kế tiếp hợp lệ và kiểm tra đích.],
    [`solvers/common.py`], [Quy tắc tính chi phí và hàm đo thời gian, bộ nhớ.],
    [`solvers/astar.py`], [Quản lý tìm kiếm, hàm ước lượng và dựng lời giải.],
    [`ui/solver_bridge.py`], [Chạy thuật toán trong tiến trình riêng và trả kết quả về giao diện.],
  ),
  align: (left, left),
  caption: [Phân chia trách nhiệm trong chương trình hiện tại.],
)

#callout_note(title: [Phạm vi bảo đảm tính đúng])[
A\* không tự cài lại luật công tắc, cầu hay tách và ghép khối. Tính tối ưu
được xét trên đồ thị do phần lõi hiện tại cung cấp, với màn chơi giữ cố định
trong mỗi lần giải. Việc phát lại một lời giải hợp lệ qua phần lõi không
thay thế kiểm thử độc lập các luật trò chơi.
]

Nội dung cài đặt được đối chiếu với `solvers/astar.py` và
`solvers/common.py`.
