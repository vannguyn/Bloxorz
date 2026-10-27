#import "../components.typ": callout_warning

= Thiết kế và chứng minh hàm ước lượng

== Vì sao không dùng Manhattan cộng chi phí tư thế

Một lần lăn có thể làm tọa độ neo của khối dịch hơn một ô. Khi tách,
khối còn có thể dịch chuyển tức thời tới vị trí xa. Vì vậy khoảng cách
Manhattan từ tọa độ neo cộng một điểm cho tư thế nằm không mặc nhiên là
cận dưới. Bản này dùng mô hình nới lỏng xét cả các đường dịch chuyển tức
thời ngay khi trạng thái hiện tại chưa tách, như trình bày trong
`docs/astar-heuristic.md`.

== Mô hình điểm và các điểm mốc

Thay khối bằng một điểm trên lưới không giới hạn. Mỗi bước trong mô hình
nới lỏng có chi phí 1 và đi tối đa 2 ô Manhattan, kể cả bước chéo (1,1).
Mô hình bỏ qua tư thế, khoảng trống, ô dễ vỡ, trạng thái cầu và điều kiện
kích hoạt công tắc. Mỗi công tắc tách khối có cạnh dịch chuyển tức thời
có hướng tới từng vị trí đích của nó, với chi phí bằng 0.

Khoảng cách di chuyển thông thường giữa hai điểm trong mô hình là:

$ w(p,q) = ceil((abs(p_1-q_1) + abs(p_2-q_2))/2). $

Chỉ giữ các điểm mốc gồm ô đích, vị trí công tắc tách khối và các vị trí
nhận khối sau khi tách. Nối mọi cặp bằng $w$, thêm cạnh dịch chuyển tức
thời với chi phí 0, rồi chạy Dijkstra trên đồ thị đảo từ ô đích.
Gọi $d(p)$ là khoảng cách từ điểm $p$ tới ô đích trong mô hình nới lỏng.
Với điểm bất kỳ, khoảng cách bằng giá trị nhỏ nhất của chi phí đi tới một
điểm mốc cộng khoảng cách còn lại của điểm mốc đó. Cách rút gọn này vẫn
xét mọi chuỗi dịch chuyển tức thời: một đường đi hoặc tới thẳng ô đích,
hoặc phải tới đầu của cạnh dịch chuyển tức thời đầu tiên.

Với $C(s)$ là tập một hoặc hai ô mà trạng thái thật đang chiếm, đặt:

$ H(s) = min_(p in C(s)) d(p), quad h(s) = 0.3 H(s). $

Khi đã tách, phép lấy giá trị nhỏ nhất xét cả hai khối lập phương, không
chỉ khối đang điều khiển. Một trạng thái chưa thắng vẫn có thể có $h=0$,
chẳng hạn khối nằm đè lên ô đích; đây vẫn là cận dưới hợp lệ.

== Chứng minh tính nhất quán và tính chấp nhận được

Tính nhất quán yêu cầu $h(s) <= c(s,a,t)+h(t)$ trên mỗi cạnh hợp lệ.
Tính chấp nhận được yêu cầu hàm ước lượng không vượt quá chi phí tối ưu
còn lại. Xét cạnh thật $s -> t$ có chi phí $c(s,a,t)$. Chọn ô $q$ thuộc
$C(t)$ sao cho $d(q)=H(t)$. Có một ô $p$ thuộc $C(s)$ với đường đi tới $q$
trong mô hình nới lỏng có chi phí tối đa 1:

- *Lăn khối:* theo bảng chuyển tư thế, mỗi ô mới cách ít nhất một ô cũ
  không quá 2 đơn vị Manhattan.
- *Di chuyển khối lập phương:* khối đang điều khiển dịch 1 ô, khối còn
  lại đứng yên.
- *Đổi điều khiển bằng SPACE:* tập ô không đổi nên có thể mô phỏng bằng
  đường đi có chi phí 0.
- *Ghép khối:* tập ô sau ghép trùng với tập ô của hai khối lập phương
  sau chuyển động.
- *Tách và dịch chuyển tức thời:* từ ô cũ tới công tắc trong tối đa một
  bước nới lỏng, rồi tới vị trí nhận khối với chi phí 0.
- *Cầu và công tắc:* thay đổi mặt nạ trạng thái không ảnh hưởng đến
  lập luận vì mô hình bỏ các ràng buộc cản đường.

Suy ra $H(s) <= d(p) <= 1+d(q) = 1+H(t)$. Vì chi phí thật ít nhất 0.3:

$ h(s) <= 0.3 + h(t) <= c(s,a,t) + h(t). $

Vậy hàm ước lượng nhất quán theo quy tắc chi phí hiện tại. Mọi chi phí
trong mô hình nới lỏng không âm nên $h(s)>=0$; tại trạng thái đích, tập ô
chỉ chứa ô đích nên giá trị ước lượng bằng 0. Cộng bất đẳng thức nhất quán
dọc một đường tới đích cho thấy giá trị ước lượng không lớn hơn chi phí
của đường đó. Do đó hàm cũng chấp nhận được.

== Chi phí tính toán và giới hạn

Với $K$ điểm mốc, đồ thị đầy đủ có $O(K^2)$ cạnh. Cài đặt Dijkstra với
hàng đợi ưu tiên dùng khoảng $O(K^2 log K)$ thời gian tiền xử lý. Bộ nhớ
đệm lưu $O(K)$ khoảng cách cho mỗi cấu hình; hàng đợi tạm có thể chứa
$O(K^2)$ phần tử. Mỗi lần đánh giá xét tối đa hai ô đang chiếm và $K$ điểm
mốc, cộng chi phí tạo khóa từ các công tắc tách khối. Bộ nhớ đệm LRU giữ
tối đa 32 cấu hình ô đích và các cạnh dịch chuyển tức thời.

#callout_warning(title: [Giới hạn của hàm ước lượng])[
Hàm ước lượng bỏ nhiều ràng buộc nên có thể yếu khi lời giải cần phối hợp
hai khối lập phương hoặc mở cầu. Không bảo đảm luôn giảm số nút hay thời
gian so với $h=0$. Khi quy tắc chi phí thay đổi, phải cập nhật cận dưới
và chứng minh lại; không tự động dùng hệ số 0.3 cho mọi quy tắc tùy chỉnh.
]
