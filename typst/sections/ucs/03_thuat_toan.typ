#import "../../components.typ": algorithm_box, styled_table

= Thuật toán và cài đặt

== Ý tưởng

UCS luôn mở rộng trạng thái có chi phí tích lũy nhỏ nhất:

$ g(s) = sum_(i=1)^(k) c(s_(i-1), a_i, s_i), quad s_0 = "start", s_k = s. $

Hàng đợi ưu tiên sắp theo $g$. UCS là trường hợp riêng của A\* với hàm ước
lượng $h = 0$, và trùng với BFS khi mọi bước có cùng chi phí.

== Mã giả

#algorithm_box(
  [Tìm kiếm chi phí đều trên đồ thị trạng thái Bloxorz],
  input: [Màn chơi, trạng thái bắt đầu, hàm chi phí dương `step_cost`.],
  output: [Dãy hành động có tổng chi phí nhỏ nhất, hoặc không có lời giải.],
  steps: (
    [Tính sẵn mức phạt của các ô; đặt `best_cost[start] = 0`, `came_from[start] = None`.],
    [Đưa `(0, counter, start)` vào hàng đợi ưu tiên `frontier`.],
    [Khi `frontier` còn phần tử: lấy phần tử `(g, _, state)` có `g` nhỏ nhất.],
    [Nếu `state` đã mở rộng hoặc `g > best_cost[state]`, bỏ qua (phần tử cũ).],
    [Đánh dấu `state` đã mở rộng, tăng `expanded_nodes`.],
    [Nếu `is_goal(state)`: dựng đường đi từ `came_from`, trả về chi phí `g`.],
    [Với mỗi `(action, next)` trong `get_successors(state)` mà `next` chưa mở rộng:],
    [#h(1em) `new_g = g + step_cost(state, action, next)`.],
    [#h(1em) Nếu `new_g < best_cost[next]`: cập nhật `best_cost`, `came_from`, đưa `(new_g, counter, next)` vào `frontier`.],
    [Nếu `frontier` cạn, trả về không có lời giải.],
  ),
)

== Cấu trúc dữ liệu

#styled_table(
  (1.2fr, 2.6fr),
  ([Biến], [Vai trò]),
  (
    [`frontier`], [Đống cực tiểu (`heapq`) chứa `(g, counter, state)`.],
    [`counter`], [Bộ đếm tăng dần, phân giải hòa `g` theo thứ tự đưa vào, tránh so sánh hai `GameState`.],
    [`best_cost`], [Chi phí nhỏ nhất đã biết để tới mỗi trạng thái.],
    [`came_from`], [`trạng thái → (trạng thái trước, hành động)`, dùng để dựng lời giải.],
    [`expanded`], [Tập trạng thái đã mở rộng; mỗi trạng thái chỉ mở rộng một lần.],
  ),
  align: (left, left),
  caption: [Cấu trúc dữ liệu của `UCSSolver.solve`.],
)

`GameState` là dataclass bất biến (`frozen=True`) nên dùng trực tiếp làm
khóa của `dict` và phần tử của `set`. Khóa gồm cả `bridge_mask`, nên các
cấu hình cầu khác nhau được phân biệt đúng.

== Xử lý phần tử cũ và thời điểm kiểm tra đích

`heapq` không có thao tác giảm khóa. Khi tìm được đường rẻ hơn tới một
trạng thái, thuật toán đưa thêm một bản mới vào hàng đợi; bản cũ có `g`
lớn hơn `best_cost` sẽ bị bỏ qua khi được lấy ra và không được tính vào
`expanded_nodes`.

Đích được kiểm tra khi trạng thái được *lấy ra* khỏi hàng đợi, không phải
khi vừa sinh ra. Lúc lấy ra, mọi phần tử còn lại có $g$ không nhỏ hơn, và
mọi chi phí đều dương, nên không còn đường nào rẻ hơn tới trạng thái đó.

== Tính đúng đắn và độ phức tạp

- *Đầy đủ:* không gian trạng thái hữu hạn và mỗi trạng thái chỉ mở rộng
  một lần, nên nếu có lời giải thì UCS tìm ra.
- *Tối ưu:* với $c >= 0.3 > 0$, trạng thái được lấy ra lần đầu có $g$ bằng
  chi phí đường đi nhỏ nhất (lập luận kiểu Dijkstra). Áp dụng cho trạng
  thái đích, lời giải trả về có tổng chi phí nhỏ nhất.
- *Thời gian:* $O(E log E)$ với $E$ là số cạnh đã xét; mỗi trạng thái có
  tối đa 5 trạng thái kế tiếp nên $E <= 5N$, $N$ là số trạng thái tới được.
- *Bộ nhớ:* $O(N + E)$ cho `best_cost`, `came_from`, `expanded` và hàng đợi
  (có thể chứa phần tử cũ).

== Cài đặt và cách chạy

`UCSSolver` kế thừa `StepCost` để lấy hàm chi phí và `Solver` để có giao
diện chung với các thuật toán khác. Đường đi được dựng bằng hàm dùng chung
`reconstruct_path`. Kết quả trả về là `SolverResult`:

- Tìm được: `path`, `solution_length = len(path)`, `cost = g`, `success = True`.
- Không tìm được: `path = None`, `solution_length = -1`,
  `cost = inf`, `success = False`.

`search_time_ms` và `peak_memory_kb` do `run_solver` điền. Giao diện
(`ui/dependencies.py`) trả về `UCSSolver` khi người dùng chọn UCS. Có thể
chạy độc lập từ thư mục gốc dự án:

```bash
python3 -m solvers.UCS          # tất cả các màn
python3 -m solvers.UCS 1 8 10   # chỉ các màn 1, 8, 10
```
