#import "../../components.typ": algorithm_box, callout_note, callout_warning

= Thuật toán Depth-First Search (DFS)

== Ý tưởng

DFS đi sâu theo một nhánh trước, chỉ quay lui khi hết đường. Cài đặt dùng ngăn xếp LIFO ở dạng lặp (không đệ quy) để tránh tràn ngăn xếp gọi hàm ở các màn có nhiều trạng thái.

Một trạng thái được đánh dấu đã thăm khi được lấy ra khỏi ngăn xếp, đồng thời cạnh cha được ghi vào `came_from` ngay lúc đó. Nhờ vậy đường đi trả về chính là nhánh DFS thật sự, không bị lẫn với các nhánh khác. Các trạng thái con được đẩy theo thứ tự ngược để hành động đầu tiên trong `get_successors` được thử trước, giúp kết quả tất định.

== Mã giả

#algorithm_box(
  [Depth-First Search (DFS) cho Bloxorz],
  input: [màn chơi `level`, trạng thái đầu `start`],
  output: [một dãy hành động hợp lệ tới đích, hoặc vô nghiệm],
  steps: (
    [`stack = [(start, None, None)]`; `expanded = 0`],
    [*trong khi* `stack` không rỗng:],
    [#h(1.2em) `(state, parent, action) = stack.pop()`],
    [#h(1.2em) nếu `state` đã có trong `came_from` thì bỏ qua],
    [#h(1.2em) `came_from[state] = (parent, action)`],
    [#h(1.2em) nếu `is_goal(state)` thì trả về đường đi dựng lại từ `came_from`],
    [#h(1.2em) `expanded += 1`],
    [#h(1.2em) *với mỗi* `(act, nxt)` trong `reversed(get_successors(state, level))`:],
    [#h(2.4em) nếu `nxt` chưa có trong `came_from` thì `stack.push((nxt, state, act))`],
    [trả về vô nghiệm (ngăn xếp cạn)],
  ),
)

== Cài đặt

Vòng lặp chính trong `solvers/DFS.py`:

```python
while stack:
    state, parent, action = stack.pop()
    if state in came_from:
        continue
    came_from[state] = None if parent is None else (parent, action)

    if is_goal(state, level):
        return make_result(reconstruct_path(came_from, state), expanded)

    expanded += 1
    for act, nxt in reversed(get_successors(state, level)):
        if nxt not in came_from:
            stack.append((nxt, state, act))
```

Bài kiểm tra đích được thực hiện khi lấy trạng thái ra khỏi ngăn xếp, và nút đích không được tính vào số nút mở rộng.

== Tính chất

- *Đầy đủ*: nhờ tập trạng thái đã thăm và không gian trạng thái hữu hạn, DFS không bị kẹt trong chu trình và tìm được lời giải nếu có.
- *Không tối ưu*: lời giải đầu tiên tìm được có thể dài hơn nhiều so với lời giải ngắn nhất.
- *Phụ thuộc thứ tự hành động*: kết quả phụ thuộc vào thứ tự `U, D, L, R` mà `get_successors` trả về và vào hình dạng của màn chơi.
- *Bộ nhớ*: về lý thuyết, DFS dạng cây chỉ cần $O(b m)$ với $m$ là độ sâu tối đa. Tuy nhiên bản cài đặt của nhóm vẫn lưu `came_from` cho mọi trạng thái đã thăm (để chống chu trình và dựng đường đi), nên bộ nhớ vẫn tăng theo số trạng thái đã khám phá.

#callout_warning[
  DFS chỉ cho một lời giải hợp lệ, không bảo đảm ngắn nhất. Nếu cần đường đi ngắn hơn mà vẫn giữ tinh thần tìm kiếm theo chiều sâu, có thể dùng Iterative Deepening Search (IDS) thay cho DFS, đề bài cho phép lựa chọn này.
]
