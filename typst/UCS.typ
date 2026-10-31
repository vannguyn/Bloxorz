// File tổng của phần UCS: mở file này để preview hoặc export PDF (UCS.pdf).
// Sửa nội dung tại các file sections/ucs/ được include bên dưới.
// Số liệu thực nghiệm đọc từ data/ucs_results.csv, tạo bằng collect_ucs_results.py.

#import "components.typ": report_section
#show: report_section

#include "sections/ucs/01_bai_toan.typ"
#include "sections/ucs/02_chi_phi.typ"
#include "sections/ucs/03_thuat_toan.typ"
#include "sections/ucs/04_thuc_nghiem.typ"
