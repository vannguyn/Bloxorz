#import "../../components.typ": styled_table, callout_note

= Hàm chi phí

== Công thức

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

== Lý do chọn các hệ số

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

== Tính chất cần cho UCS

Mọi mức phạt đều không âm, nên với chính sách mặc định:

$ c(s,a,t) >= min(1.0, 1.5, 1.2, 0.8, 0.3) = 0.3 > 0. $

Chi phí dương là điều kiện để UCS bảo đảm lời giải tối ưu (mục sau).

#callout_note[
  Mức phạt của mỗi ô chỉ phụ thuộc bản đồ, nên `_precompute_cell_penalty`
  tính sẵn một bảng `ô → mức phạt` một lần ở đầu mỗi lần giải. Khi đó
  `step_cost` chỉ cộng công sức với vài phép tra bảng.
]
