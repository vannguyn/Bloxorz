// File tổng của phần A*: mở file này để preview hoặc export PDF.
// Sửa nội dung tại các file sections/ được include bên dưới.
// main.typ vẫn giữ nguyên mẫu ban đầu.

#import "components.typ": report_section
#show: report_section

#include "sections/01_gioithieu.typ"
#include "sections/02_kientruc_thietke.typ"
#include "sections/03_thuat_toan_ma_nguon.typ"
#include "sections/04_danhgia_phancong.typ"
#include "sections/05_thucnghiem.typ"

// Nếu ghép vào báo cáo có bibliography chung, chuyển dòng này sang file chính.
#bibliography("references.bib", style: "ieee")
