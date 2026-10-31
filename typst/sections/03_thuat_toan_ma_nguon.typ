#pagebreak()

= Tổng quan các thuật toán

== BFS và DFS

BFS sử dụng hàng đợi FIFO, duyệt theo từng lớp độ sâu và bảo đảm lời giải
có số hành động ít nhất khi mỗi hành động được tính bằng một bước. DFS
sử dụng ngăn xếp LIFO, đi sâu theo một nhánh trước và có thể trả về lời
giải dài hơn; tập trạng thái đã thăm giúp tránh chu trình. Hai thuật toán
này tối ưu theo số hành động chứ không theo `StepCost`.

== UCS và A\*

UCS mở rộng trạng thái có chi phí tích lũy $g(n)$ thấp nhất. A\* ưu tiên
$f(n) = g(n) + h(n)$, trong đó $h(n)$ là cận dưới ước lượng chi phí còn
lại tới đích. Cả hai dùng chính sách `StepCost` chung; UCS dùng hàng đợi
ưu tiên theo $g$, còn A\* theo $f$. Tính tối ưu của A\* phụ thuộc vào tính
chấp nhận được của heuristic đối với chính sách chi phí đang dùng.

== Quy ước đọc các kết quả

Các mục BFS, DFS, UCS và A\* trình bày riêng mã giả, cấu trúc dữ liệu,
đặc tính, kết quả và giới hạn. Cả bốn cùng dùng 11 level hiện hành, trạng
thái đầu của từng level và một quy trình đo thống nhất trong
`typst/collect_all_results.py`. Mục 8 tổng hợp các chỉ số trên cùng bộ
test để việc so sánh có cùng điều kiện.

Đường đi và kết quả trong báo cáo được xem là hợp lệ khi phát lại qua luật
trò chơi. `SPACE` được tính là một hành động; với UCS/A\*, mọi hành động
cũng có chi phí dương theo `StepCost`. BFS tối ưu số hành động, trong khi
UCS/A\* tối ưu tổng `StepCost`; DFS không bảo đảm tối ưu.
