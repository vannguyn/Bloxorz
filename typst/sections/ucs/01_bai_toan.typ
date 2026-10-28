= Tìm kiếm chi phí đều (UCS)

== Mục tiêu

Phần này trình bày thuật toán tìm kiếm chi phí đều (Uniform-Cost Search,
UCS) dùng để giải các màn Bloxorz. UCS tìm dãy hành động đưa khối từ trạng
thái bắt đầu tới đích sao cho tổng chi phí các bước là nhỏ nhất. Khác với
BFS chỉ đếm số bước, UCS dùng hàm chi phí `StepCost` dùng chung trong
`solvers/common.py`, nên có thể ưu tiên đường đi ít rủi ro hơn dù dài hơn.

Mã nguồn nằm trong `solvers/UCS.py`, gồm lớp `UCSSolver` kế thừa lớp trừu
tượng `Solver` và chính sách chi phí `StepCost`. Lớp này chỉ chứa thuật
toán tìm kiếm; luật chơi lấy từ `core/game_rules.py`, chi phí lấy từ
`solvers/common.py`.

== Mô hình hóa bài toán tìm kiếm

- *Trạng thái:* một `GameState` gồm `BlockState` (vị trí ô mốc `(r, c)`, tư
  thế đứng / nằm ngang / nằm dọc, cờ đã tách, vị trí hai khối lập phương và
  khối đang điều khiển) cùng `bridge_mask`, mặt nạ bit trạng thái đóng/mở
  của từng cầu. Hai trạng thái cùng vị trí khối nhưng khác trạng thái cầu
  là hai trạng thái khác nhau.
- *Trạng thái bắt đầu:* `GameState(level.start, level.initial_bridge_mask)`.
- *Hành động:* `U`, `D`, `L`, `R` lăn khối theo bốn hướng. Hành động `SPACE`
  chỉ hợp lệ khi khối đã bị tách bởi công tắc tách, dùng để đổi khối lập
  phương đang điều khiển (mục 2.5 của đề bài).
- *Hàm chuyển trạng thái:* `get_successors(state, level)` trả về các cặp
  `(action, next_state)` hợp lệ. Phần lõi đã loại các nước làm khối rơi ra
  ngoài bản đồ, vào ô trống hoặc cầu đang đóng, và các nước đứng thẳng trên
  ô dễ vỡ; đồng thời xử lý công tắc, tách và ghép khối.
- *Kiểm tra đích:* `is_goal(state, level)` đúng khi khối chưa tách, đang
  đứng và nằm trên ô đích. Một khối lập phương đơn lẻ trên ô đích không
  được tính là thắng.
- *Chi phí bước:* `step_cost(state, action, next_state, level)`, luôn dương
  (mục tiếp theo).

Mỗi màn có số ô hữu hạn và số cầu hữu hạn, nên không gian trạng thái
hữu hạn.
