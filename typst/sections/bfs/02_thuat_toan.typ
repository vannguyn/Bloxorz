#import "../../components.typ": algorithm_box, callout_note

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
