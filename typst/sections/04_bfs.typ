#import "../components.typ": styled_table, algorithm_box, callout_note, callout_warning

#pagebreak()

= Thuật toán Breadth-First Search (BFS)

== Ý tưởng

BFS duyệt các trạng thái theo từng lớp độ sâu: mọi trạng thái cách trạng thái đầu $k$ hành động được mở rộng trước các trạng thái cách $k + 1$ hành động. Cài đặt dùng hàng đợi FIFO (`collections.deque`) và từ điển `came_from` làm tập đã thăm.

Bài kiểm tra đích được thực hiện ngay khi sinh trạng thái con, thay vì lúc lấy ra khỏi hàng đợi. Cách này giảm số nút phải mở rộng mà vẫn giữ được tính tối ưu, vì mọi hành động đều có chi phí 1.

== Mã giả

#algorithm_box(
  [Breadth-First Search (BFS) cho Bloxorz],
  input: [màn chơi `level`, trạng thái đầu `start`],
  output: [dãy hành động ngắn nhất tới đích, hoặc vô nghiệm],
  steps: (
    [nếu `is_goal(start)` thì trả về dãy rỗng],
    [`came_from[start] = None`; `queue = [start]`; `expanded = 0`],
    [*trong khi* `queue` không rỗng:],
    [#h(1.2em) `state = queue.popleft()`; `expanded += 1`],
    [#h(1.2em) *với mỗi* `(action, nxt)` trong `get_successors(state, level)`:],
    [#h(2.4em) nếu `nxt` đã có trong `came_from` thì bỏ qua],
    [#h(2.4em) `came_from[nxt] = (state, action)`],
    [#h(2.4em) nếu `is_goal(nxt)` thì trả về đường đi dựng lại từ `came_from`],
    [#h(2.4em) `queue.append(nxt)`],
    [trả về vô nghiệm (hàng đợi cạn)],
  ),
)

== Cài đặt

Vòng lặp chính trong `solvers/BFS.py`:

```python
came_from = {start: None}
queue = deque([start])
expanded = 0

while queue:
    state = queue.popleft()
    expanded += 1
    for action, nxt in get_successors(state, level):
        if nxt in came_from:
            continue
        came_from[nxt] = (state, action)
        if is_goal(nxt, level):
            return make_result(reconstruct_path(came_from, nxt), expanded)
        queue.append(nxt)
```

Nếu trạng thái đầu đã là đích, solver trả về dãy rỗng. Nếu hàng đợi cạn mà chưa gặp đích, solver trả về `path=None`, tức màn chơi vô nghiệm. Đường đi được dựng lại bằng `reconstruct_path` trong `solvers/common.py`, dùng chung với các solver khác.

== Tính chất

- *Đầy đủ*: nếu có lời giải thì BFS tìm được, vì không gian trạng thái hữu hạn.
- *Tối ưu*: vì mọi hành động có chi phí 1, lời giải tìm được có số hành động ít nhất.
- *Độ phức tạp*: với hệ số nhánh $b <= 4$ (hoặc $b <= 5$ khi khối bị tách) và độ sâu lời giải $d$, thời gian và bộ nhớ đều ở mức $O(b^d)$. Nhờ tập trạng thái đã thăm, cả hai còn bị chặn trên bởi số trạng thái đạt được $|S|$.
- *Nhược điểm chính*: phải giữ toàn bộ biên tìm kiếm và mọi trạng thái đã thăm trong bộ nhớ, nên bộ nhớ tăng nhanh theo kích thước không gian trạng thái.

#callout_note[
  Số nút mở rộng thực tế (xem phần thực nghiệm) nhỏ hơn rất nhiều so với $b^d$, vì nhiều chuỗi hành động khác nhau dẫn tới cùng một trạng thái và bị loại bởi `came_from`.
]

#pagebreak()

= Thực nghiệm BFS

== Thiết lập

BFS được chạy từ trạng thái đầu của từng level trong cùng bộ dữ liệu 11
màn với DFS, UCS và A\*. Các nhóm level được phân theo cơ chế hiện diện:
cơ bản, có ô dễ vỡ, có công tắc/cầu, hoặc kết hợp ô dễ vỡ với công tắc.
 Bộ nhớ đỉnh được đo một lần riêng cho từng solver và
level. Mọi lời giải được phát lại qua luật trò chơi để kiểm tra tính hợp
lệ và đích đến.

Thời gian được đo bằng `perf_counter()` quanh `solve()` khi
`tracemalloc` tắt, áp dụng như nhau cho cả bốn solver. Đo bộ nhớ dùng một
lượt riêng với `tracemalloc`; số đo là đỉnh cấp phát, không phải
toàn bộ RAM tiến trình. Nút mở rộng được đếm theo quy ước riêng của BFS:
trạng thái lấy khỏi hàng đợi; trạng thái đích được nhận lúc sinh nên
không tính vào số nút mở rộng.

== Kết quả

#let all_rows = csv("../data/all_algorithms.csv", row-type: dictionary)
#let rows = all_rows.filter(row => row.algorithm == "BFS")
#assert(rows.len() == 11)
#let data = rows.map(r => (
  [#r.level],
  [#r.group],
  if r.success == "True" [Có] else [Không],
  [#calc.round(float(r.time_ms_median), digits: 3)],
  [#calc.round(float(r.time_ms_stdev), digits: 3)],
  [#calc.round(float(r.peak_memory_kb_median), digits: 1)],
  [#r.expanded_nodes],
  [#r.solution_length],
)).flatten()

#styled_table(
  (1fr, 1fr, 0.65fr, 0.9fr, 0.9fr, 0.9fr, 0.9fr, 0.9fr),
  ([Màn], [Nhóm], [Giải được], [Thời gian trung vị (ms)], [ĐLC thời gian (ms)], [Bộ nhớ đỉnh (KB)], [Nút mở rộng], [Độ dài lời giải]),
  data,
  inset: 3pt,
  caption: [Kết quả BFS trên bộ level hiện hành; thời gian là trung vị #rows.at(0).repeats lượt đo, bộ nhớ đo riêng một lượt.],
)

#figure(
  image("../figures/bfs_overview.png", width: 100%),
  caption: [Thời gian, bộ nhớ đỉnh, số nút mở rộng và độ dài lời giải của BFS trên từng level.],
)

== Nhận xét

BFS tối ưu số hành động vì mỗi nước đi có cùng chi phí một bước. Bảng
ghi kết quả đo mới cho từng level, thay cho các số liệu cũ không còn đồng
bộ với level hiện tại. Những level có nhiều trạng thái hợp lệ hơn có thể
làm hàng đợi và bộ nhớ tăng; kết quả cụ thể cần được đọc cùng nhóm cơ chế
và so sánh trong bảng tổng hợp bốn thuật toán.

== Kết luận

BFS phù hợp khi mục tiêu là lời giải có ít hành động nhất. Đổi lại, nó
không tối ưu theo `StepCost`, và mức dùng bộ nhớ phụ thuộc lượng trạng thái
được giữ trong hàng đợi và tập đã thăm.
