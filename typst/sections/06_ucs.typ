#import "../components.typ": styled_table, callout_note, algorithm_box

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
  phương đang điều khiển.
- *Hàm chuyển trạng thái:* `get_successors(state, level)` trả về các cặp
  `(action, next_state)` hợp lệ. Phần lõi đã loại các nước làm khối rơi ra
  ngoài bản đồ, vào ô trống hoặc cầu đang đóng, và các nước đứng thẳng trên
  ô dễ vỡ; đồng thời xử lý công tắc, tách và ghép khối.
- *Kiểm tra đích:* `is_goal(state, level)` đúng khi khối chưa tách, đang
  đứng và nằm trên ô đích. Một khối lập phương đơn lẻ trên ô đích không
  được tính là thắng.
- *Chi phí bước:* `step_cost(state, action, next_state, level)`, luôn dương
  .

Mỗi màn có số ô hữu hạn và số cầu hữu hạn, nên không gian trạng thái
hữu hạn.

== Hàm chi phí

=== Công thức

Gọi $s$ là trạng thái trước, $a$ là hành động và $t$ là trạng thái sau.
UCS dùng chi phí của lớp `StepCost`:

$ c(s,a,t) = e(s,a,t) + sum_(x in C(t)) p(x) + b(s,t). $

Trong đó $e$ là công sức của chính nước đi, $C(t)$ là tập ô mà khối chiếm
sau khi đi, $p(x)$ là mức phạt rủi ro của ô $x$ và $b(s,t)$ là mức phạt
khi nước đi làm thay đổi trạng thái cầu.

#styled_table(
  (2.6fr, 1fr),
  ([Loại nước đi], [Công sức $e$]),
  (
    [Đứng → nằm (lật đổ)], [1.0],
    [Nằm → đứng (dựng khối lên)], [1.5],
    [Nằm → nằm (lăn theo cạnh dài)], [1.2],
    [Di chuyển một khối lập phương khi đã tách], [0.8],
    [`SPACE`: đổi khối lập phương đang điều khiển], [0.3],
  ),
  align: (left, center),
  caption: [Công sức của từng loại nước đi.],
)

#styled_table(
  (2.6fr, 1fr),
  ([Tình huống], [Mức phạt]),
  (
    [Mỗi ô dễ vỡ bị chiếm], [+0.5],
    [Mỗi ô cầu bị chiếm], [+0.3],
    [Mỗi ô bị chiếm có ô kề (4 hướng) là khoảng trống], [+0.1],
    [Nước đi làm thay đổi `bridge_mask`], [+0.5],
  ),
  align: (left, center),
  caption: [Mức phạt rủi ro.],
)

=== Lý do chọn các hệ số

Đề bài không quy định chi phí; nếu mọi nước đi có chi phí 1 thì UCS cho
thứ tự tìm kiếm giống BFS. Các hệ số được chọn theo hai ý:

- *Công sức:* dựng khối lên phải nâng khối nên đắt nhất; lăn khi đang nằm
  tốn hơn lật đổ một chút; một khối lập phương chỉ nặng bằng nửa khối nên
  rẻ hơn; `SPACE` không di chuyển khối nhưng vẫn phải có chi phí dương để
  thuật toán không lặp `SPACE` vô hạn.
- *Rủi ro:* ô dễ vỡ, cầu và ô sát mép là những vị trí dễ dẫn tới thua; nước
  bấm công tắc thay đổi bản đồ nên được tính là thao tác tốn kém.

Mức phạt rủi ro nhỏ hơn hẳn công sức một nước đi. Vì vậy UCS vẫn ưu tiên
đường ngắn, và chỉ chọn đường an toàn hơn khi các đường có độ dài gần nhau.
Đây là mô hình định lượng do nhóm đặt ra, không phải phép đo vật lý.

=== Tính chất cần cho UCS

Mọi mức phạt đều không âm, nên với chính sách mặc định:

$ c(s,a,t) >= min(1.0, 1.5, 1.2, 0.8, 0.3) = 0.3 > 0. $

Chi phí dương là điều kiện để UCS bảo đảm lời giải tối ưu (mục sau).

#callout_note[
  Mức phạt của mỗi ô chỉ phụ thuộc bản đồ, nên `_precompute_cell_penalty`
  tính sẵn một bảng `ô → mức phạt` một lần ở đầu mỗi lần giải. Khi đó
  `step_cost` chỉ cộng công sức với vài phép tra bảng.
]

== Thuật toán và cài đặt

=== Ý tưởng

UCS luôn mở rộng trạng thái có chi phí tích lũy nhỏ nhất:

$ g(s) = sum_(i=1)^(k) c(s_(i-1), a_i, s_i), quad s_0 = "start", s_k = s. $

Hàng đợi ưu tiên sắp theo $g$. UCS là trường hợp riêng của A\* với hàm ước
lượng $h = 0$, và trùng với BFS khi mọi bước có cùng chi phí.

=== Mã giả

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

=== Cấu trúc dữ liệu

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

=== Xử lý phần tử cũ và thời điểm kiểm tra đích

`heapq` không có thao tác giảm khóa. Khi tìm được đường rẻ hơn tới một
trạng thái, thuật toán đưa thêm một bản mới vào hàng đợi; bản cũ có `g`
lớn hơn `best_cost` sẽ bị bỏ qua khi được lấy ra và không được tính vào
`expanded_nodes`.

Đích được kiểm tra khi trạng thái được *lấy ra* khỏi hàng đợi, không phải
khi vừa sinh ra. Lúc lấy ra, mọi phần tử còn lại có $g$ không nhỏ hơn, và
mọi chi phí đều dương, nên không còn đường nào rẻ hơn tới trạng thái đó.

=== Tính đúng đắn và độ phức tạp

- *Đầy đủ:* không gian trạng thái hữu hạn và mỗi trạng thái chỉ mở rộng
  một lần, nên nếu có lời giải thì UCS tìm ra.
- *Tối ưu:* với $c >= 0.3 > 0$, trạng thái được lấy ra lần đầu có $g$ bằng
  chi phí đường đi nhỏ nhất (lập luận kiểu Dijkstra). Áp dụng cho trạng
  thái đích, lời giải trả về có tổng chi phí nhỏ nhất.
- *Thời gian:* $O(E log E)$ với $E$ là số cạnh đã xét; mỗi trạng thái có
  tối đa 5 trạng thái kế tiếp nên $E <= 5N$, $N$ là số trạng thái tới được.
- *Bộ nhớ:* $O(N + E)$ cho `best_cost`, `came_from`, `expanded` và hàng đợi
  (có thể chứa phần tử cũ).

=== Cài đặt và cách chạy

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

=== Đoạn mã nguồn cốt lõi

Đoạn mã dưới đây thể hiện bước cập nhật chi phí và đưa trạng thái vào
hàng đợi trong `solvers/UCS.py`:

```python
for action, next_state in get_successors(state, level):
    if next_state in expanded:
        continue
    new_g = g + self.step_cost(state, action, next_state, level)
    if new_g < best_cost.get(next_state, float("inf")):
        best_cost[next_state] = new_g
        came_from[next_state] = (state, action)
        heapq.heappush(frontier, (new_g, next(counter), next_state))
```

Điều kiện cập nhật dùng tổng chi phí, không dùng số hành động. Vì vậy
thuật toán có thể chọn đường nhiều bước hơn nếu tổng chi phí thấp hơn.

== Thực nghiệm

#let all_records = csv("../data/all_algorithms.csv", row-type: dictionary)
#let records = all_records.filter(row => row.algorithm == "UCS")
#assert(records.len() == 11)
#assert(records.filter(row => row.cost == "").len() == 0)

=== Thiết lập và kết quả

UCS được đo trên cùng 11 level và từ cùng trạng thái đầu như BFS, DFS và
A\*.  Bộ nhớ đỉnh
được đo trong một lượt riêng. Lời giải được phát lại từng bước; trạng
thái đích, độ dài và tổng `StepCost` tính lại phải khớp kết quả trả về.
Chi phí tối ưu của UCS được đối chiếu thêm với A\* trên từng level.

Thời gian được đo bằng `perf_counter()` khi `tracemalloc` tắt; bộ nhớ
được đo bằng `tracemalloc` riêng. Hai phép đo này dùng cùng quy trình cho
cả bốn thuật toán; số đo bộ nhớ là đỉnh cấp phát, không phải tổng
RAM tiến trình.

#styled_table(
  (1fr, 1fr, 0.65fr, 0.8fr, 0.8fr, 0.8fr, 0.8fr, 0.8fr, 0.8fr),
  ([Màn], [Nhóm], [Giải được], [Bước], [Chi phí], [Thời gian trung vị (ms)], [ĐLC thời gian (ms)], [Bộ nhớ đỉnh (KB)], [Nút mở rộng]),
  records.map(row => (
    [#row.level], [#row.group],
    if row.success == "True" [Có] else [Không],
    [#row.solution_length],
    [#calc.round(float(row.cost), digits: 2)],
    [#calc.round(float(row.time_ms_median), digits: 3)],
    [#calc.round(float(row.time_ms_stdev), digits: 3)],
    [#calc.round(float(row.peak_memory_kb_median), digits: 1)],
    [#row.expanded_nodes],
  )).flatten(),
  inset: 2pt,
  align: (left, left, center, right, right, right, right, right, right),
  caption: [Kết quả UCS trên level hiện hành; thời gian là trung vị #records.at(0).repeats lượt đo, bộ nhớ đo riêng một lượt.],
)

#figure(
  image("../figures/ucs_overview.png", width: 100%),
  caption: [Thời gian, bộ nhớ đỉnh, số nút mở rộng và độ dài lời giải của UCS trên từng level.],
)

=== Nhận xét

UCS tối ưu tổng `StepCost`, không tối ưu số bước. Do đó số bước trong
bảng có thể khác BFS khi lời giải nhiều bước có chi phí thấp hơn. So sánh
thời gian và bộ nhớ với solver khác cần dùng cùng các level, trạng thái
đầu và cách đo; bảng tổng hợp và biểu đồ ở phần đánh giá dùng đúng bộ dữ
liệu chung này.

#callout_note(title: [Hạn chế])[
  UCS không biết đích nằm ở đâu nên lan đều theo mọi hướng. Để giảm số nút
  cần một hàm ước lượng chấp nhận được, tức là chuyển sang A\*. Thuật toán
  cũng chưa có giới hạn thời gian hay số nút; trong giao diện, việc hủy
  được thực hiện bằng cách dừng tiến trình tìm kiếm.
]

== Đối chiếu các phần thực hiện

#styled_table(
  (1.4fr, 2.6fr),
  ([Nội dung], [Cách thực hiện và đối chiếu]),
  (
    [Mô hình hóa bài toán], [Dùng trạng thái, hàm chuyển và kiểm tra đích của phần lõi.],
    [Thiết kế chi phí], [Dùng `StepCost` chung, có chi phí chuyển động và mức phạt theo bản đồ.],
    [Cài đặt tìm kiếm], [Hàng đợi theo chi phí tích lũy, loại phần tử cũ, kiểm tra đích khi lấy ra.],
    [Dựng lời giải], [Dùng bảng cha và `reconstruct_path`; trả đúng `SolverResult`.],
    [Kiểm chứng kết quả], [Chương trình thu thập phát lại đường đi, kiểm tra đích và cộng lại chi phí.],
    [Đo hiệu năng], [Đo lặp qua `run_solver()`, tổng hợp trung vị từ các lần chạy.],
  ),
  align: (left, left),
  caption: [Đối chiếu nội dung báo cáo với phần cài đặt UCS.],
)

Bảng này mô tả cách thực hiện, không tự quy đổi thành tỷ lệ hoàn thành.
Phần đóng góp cá nhân và đánh giá mức độ hoàn thành cần được nhóm xác nhận.

== Kết luận

UCS tìm lời giải có tổng chi phí nhỏ nhất theo quy tắc `StepCost` trên
đồ thị trạng thái do phần lõi cung cấp. Số liệu ghi trong tệp thực nghiệm
cho thấy mục tiêu này có thể tạo lời giải khác với tối thiểu số bước,
đặc biệt ở màn có tách khối. Đổi lại, thuật toán có thể phải mở rộng nhiều
trạng thái vì không sử dụng thông tin ước lượng khoảng cách tới đích.
