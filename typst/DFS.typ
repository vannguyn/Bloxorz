// File tổng của phần DFS: mở file này để preview hoặc export PDF (DFS.pdf).
// Sửa nội dung tại các file sections/ được include bên dưới.
// Số liệu thực nghiệm đọc từ data/dfs_results.csv, tạo bằng collect_bfs_dfs_results.py.
// Biểu đồ trong figures/ được sinh bằng make_charts_bfs_dfs.py.

#import "components.typ": report_section
#show: report_section

// Phần mô hình hóa bài toán (state, action, cost...) do nhóm trưởng viết ở báo cáo chính.
#include "sections/dfs/02_thuat_toan.typ"
#include "sections/dfs/03_thuc_nghiem.typ"
