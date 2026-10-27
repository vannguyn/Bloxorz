#import "../components.typ": algorithm_box

= Thuật toán A\* và cách tích hợp

== Hàm ưu tiên

$ f(s) = g(s) + h(s). $

$g(s)$ là chi phí thực tế của đường từ trạng thái bắt đầu tới $s$; $h(s)$
là cận dưới của chi phí còn lại. Hàng đợi ưu tiên lấy phần tử có $f$ nhỏ
nhất. Nếu hòa $f$, phần tử được đưa vào trước được xét trước, theo bộ đếm
thứ tự và thứ tự sinh trạng thái kế tiếp của phần lõi.

== Mã giả

#algorithm_box(
  [A\* trên đồ thị trạng thái với chi phí không đều],
  input: [Màn chơi cố định, trạng thái bắt đầu, hàm chi phí và hàm ước lượng không vượt chi phí còn lại.],
  output: [Lời giải có chi phí tối ưu, hoặc thông báo không có lời giải khi hàng đợi cạn.],
  steps: (
    [Chuẩn bị hàm chi phí; đặt `best_g[start] = 0`, cha của trạng thái bắt đầu là rỗng.],
    [Đưa `(h(start), counter, 0, start)` vào hàng đợi.],
    [Khi hàng đợi còn phần tử: lấy phần tử có ưu tiên nhỏ nhất.],
    [Bỏ qua phần tử nếu `g` không còn bằng `best_g[state]`.],
    [Tăng bộ đếm; nếu `is_goal(state, level)`, dựng lời giải và trả chi phí `g`.],
    [Xét từng cặp `(action, child)` từ `get_successors(state, level)`.],
    [Tính `new_g = g + cost(state, action, child, level)`.],
    [Nếu `new_g` nhỏ hơn chi phí tốt nhất của `child`, cập nhật chi phí và cha.],
    [Đưa `(new_g + h(child), counter, new_g, child)` vào hàng đợi, kể cả khi trạng thái đó đã mở rộng.],
    [Nếu hàng đợi cạn, trả kết quả không có lời giải.],
  ),
)

== Loại phần tử cũ, mở lại trạng thái và điều kiện tối ưu

`heapq` không hỗ trợ giảm trực tiếp khóa ưu tiên của một phần tử đang có.
Vì vậy khi cải thiện $g$, thuật toán đưa thêm phần tử mới vào hàng đợi và
giữ phần tử cũ. Khi phần tử cũ được lấy ra, phép kiểm tra chi phí loại bỏ
nó mà không tăng `expanded_nodes`.

Thuật toán chấp nhận đích khi lấy một phần tử còn hiệu lực khỏi hàng đợi,
không phải ngay khi vừa sinh ra trạng thái đích. Việc mở lại trạng thái
cho phép sử dụng hàm ước lượng chấp nhận được nhưng chưa nhất quán.
Với chi phí dương hiện tại, hàm ước lượng không vượt chi phí còn lại và
đồ thị trạng thái hữu hạn, thuật toán tìm được lời giải có chi phí tối ưu
nếu lời giải tồn tại.

A\* kiểm tra chi phí và giá trị ước lượng hữu hạn, chi phí dương, giá trị
ước lượng không âm và bằng 0 tại đích. Các phép kiểm tra khi chạy không
chứng minh được tính chấp nhận được của hàm ước lượng tùy chỉnh; người
thiết kế hàm phải chứng minh điều kiện này.

== Cách gọi từ chương trình

```python
from core.interfaces import GameState
from levels.level_loader import load_level
from solvers.astar import AStarSolver
from solvers.common import run_solver

level = load_level("level_01")
start = GameState(level.start, level.initial_bridge_mask)
result = run_solver(AStarSolver(), level, start)
```

`solve()` tạo `SolverResult`; `run_solver()` bổ sung số đo thời gian và
bộ nhớ. Trong giao diện, bộ kết nối chọn thuật toán và chạy hàm đo đạc
trong tiến trình riêng. Luồng giao diện nhận kết quả để phát lại lời giải.
Thao tác hủy hiện được thực hiện bằng cách dừng tiến trình tìm kiếm;
thuật toán chưa có giới hạn thời gian, số nút hoặc cơ chế nhận yêu cầu hủy
nội bộ. Các giao diện dự kiến trong tài liệu thiết kế không được xem là
tính năng đã triển khai.
