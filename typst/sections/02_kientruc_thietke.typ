#pagebreak()

= Mô hình hóa và kiến trúc

== Mô hình tìm kiếm

- *Trạng thái:* `GameState` chứa `BlockState` và `bridge_mask`. `BlockState`
  lưu tọa độ neo, tư thế, cờ tách khối, vị trí hai khối lập phương và
  chỉ số khối đang điều khiển. `bridge_mask` phân biệt các cấu hình cầu.
- *Trạng thái đầu:* trạng thái khối ban đầu của màn cùng với mặt nạ cầu
  ban đầu.
- *Hành động:* `U`, `D`, `L`, `R`; khi khối đã tách, hành động `SPACE`
  đổi khối lập phương được điều khiển.
- *Hàm chuyển:* `get_successors(state, level)` chỉ sinh các hành động hợp
  lệ. Luật lõi loại nước đi ra ngoài bàn, rơi vào ô trống hoặc cầu đóng,
  và đứng trên ô dễ vỡ; đồng thời cập nhật công tắc, cầu, trạng thái tách
  và ghép khối.
- *Kiểm tra đích:* `is_goal(state, level)` chỉ đúng khi khối chưa tách,
  đứng thẳng và ở ô đích.

Vì `GameState` là bất biến và có thể băm, solver dùng toàn bộ trạng thái
làm khóa để tránh lặp. Hai cấu hình có cùng tọa độ nhưng khác tư thế,
trạng thái cầu hoặc khối đang điều khiển là hai trạng thái khác nhau.
Không gian trạng thái hữu hạn do mỗi màn có hữu hạn ô và hữu hạn cầu.

== Kiến trúc chương trình

#figure(
  caption: [Các thành phần chính được dùng trong đồ án.],
  table(
    columns: (1.3fr, 2.7fr),
    align: (left, left),
    table.header([*Thành phần*], [*Trách nhiệm*]),
    [`core/interfaces.py`], [Định nghĩa `Level`, `GameState`, `BlockState` và `SolverResult`.],
    [`core/game_rules.py`], [Tính nước đi hợp lệ, sinh successor và kiểm tra điều kiện thắng.],
    [`solvers/common.py`], [Giao diện solver, hàm dựng đường đi, `StepCost` và đo hiệu năng.],
    [`solvers/BFS.py`, `solvers/DFS.py`, `solvers/UCS.py`, `solvers/astar.py`], [Cài đặt bốn phương pháp tìm kiếm.],
    [`ui/` và `rendering/`], [Giao diện người chơi, điều khiển, hoạt ảnh và hiển thị bàn cờ.],
    [`levels/`], [Đọc cấu hình JSON cho các màn chơi.],
  ),
)

== Đầu ra và số đo

Mỗi solver trả về `SolverResult`, gồm đường đi, trạng thái thành công,
tổng chi phí, độ dài lời giải và số nút mở rộng. `run_solver()` bổ sung
thời gian tìm kiếm bằng `time.perf_counter()` và bộ nhớ cấp phát Python
đỉnh bằng `tracemalloc` khi chạy qua giao diện. Trong benchmark báo cáo,
thời gian và bộ nhớ được đo ở hai lượt riêng để không làm `tracemalloc`
làm chậm phép đo thời gian; quy trình này được áp dụng đồng đều cho bốn
solver và mô tả trong các mục thực nghiệm.

Lời giải thành công được phát lại từ trạng thái đầu bằng `apply_move`.
Mỗi hành động phải hợp lệ, trạng thái cuối phải thỏa `is_goal`, và với
UCS và A\* có tổng chi phí phát lại phải khớp chi phí solver báo cáo.
