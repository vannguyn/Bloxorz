#import "../components.typ": styled_table

= Mô hình chi phí và cấu trúc dữ liệu

== Quy tắc tính chi phí dùng chung

Gọi $s$ là trạng thái trước, $a$ là hành động và $t$ là trạng thái sau.
Chi phí chuyển trạng thái gồm chi phí chuyển động cơ sở, chi phí bổ sung
trên các ô đích và chi phí thay đổi trạng thái cầu:

$ c(s,a,t) = e(s,a,t) + sum_(x in C(t)) p(x) + b(s,t). $

Trong đó $C(t)$ là tập ô mà trạng thái đích chiếm, $e$ là chi phí chuyển
động cơ sở, $p$ là chi phí bổ sung trên mỗi ô và $b$ là chi phí thay đổi
trạng thái cầu. Đây là mô hình định lượng của chương trình, không phải
phép đo năng lượng vật lý. Các hằng số được giữ theo quy tắc tính chi phí
được chuyển từ UCS sang `common.py`.

#styled_table(
  (2.6fr, 1fr),
  ([Loại chuyển động], [Chi phí cơ sở]),
  (
    [Đứng → nằm hoặc kích hoạt tách khối từ tư thế đứng], [1.0],
    [Nằm → đứng, khi kết quả chưa tách], [1.5],
    [Nằm → nằm], [1.2],
    [Di chuyển từ trạng thái đã tách], [0.8],
    [`SPACE`: đổi khối lập phương đang điều khiển], [0.3],
  ),
  align: (left, center),
  caption: [Chi phí cơ sở của mỗi hành động.],
)

Chi phí bổ sung gồm 0.5 cho mỗi ô dễ vỡ bị chiếm, 0.3 cho mỗi ô cầu bị
chiếm, 0.1 cho mỗi ô đích kề khoảng trống theo phép kiểm tra bản đồ, và
0.5 nếu mặt nạ trạng thái cầu thay đổi. Phép kiểm tra kề khoảng trống xét
bốn hướng; các ô cầu vẫn được xem là một phần của cấu trúc bản đồ.
Chi phí trên các ô đích vẫn được tính cho `SPACE`, đúng theo cài đặt hiện
tại. Thuật toán chỉ tính chi phí cho các trạng thái kế tiếp đã được phần
lõi chấp nhận, không biến một nước đi thua thành nước đi hợp lệ.

Mọi chi phí bổ sung đều không âm, nên với quy tắc mặc định:

$ c(s,a,t) >= c_min = 0.3 > 0. $

`StepCost(level)` tính trước chi phí bổ sung của các ô một lần cho mỗi lần
giải. A\* có thể nhận hàm tính chi phí tùy chỉnh; nếu không truyền kèm hàm
ước lượng riêng, thuật toán mặc định dùng $h=0$. Cận dưới 0.3 chỉ áp dụng
cho quy tắc mặc định, không tự động áp dụng cho quy tắc khác.

== Cấu trúc tìm kiếm

- *Hàng đợi ưu tiên:* dùng cấu trúc đống cực tiểu (min-heap), lưu các bộ
  `(f, counter, g, state)`.
- *Bảng chi phí tốt nhất:* `best_g[state]` lưu chi phí thấp nhất đã biết để
  tới một trạng thái.
- *Bảng cha:* `parents[state] = (previous_state, action)` dùng để dựng lời giải.
- *Bộ đếm thứ tự:* phân giải trường hợp hòa điểm theo thứ tự đưa vào hàng
  đợi, tránh phải so sánh trực tiếp các đối tượng trạng thái.

Không dùng riêng tọa độ làm khóa: hai trạng thái cùng vị trí nhưng khác
trạng thái cầu hoặc khối đang điều khiển có thể có các bước đi tiếp theo
khác nhau. Thuật toán không khóa vĩnh viễn trạng thái đã mở rộng, mà cho
phép xét lại khi tìm được đường đến có chi phí thấp hơn.
