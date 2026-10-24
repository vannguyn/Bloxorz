= Kết quả thực nghiệm và Tự đánh giá

== Kết quả kiểm thử trên các bộ dữ liệu

Tóm tắt kết quả chạy thử nghiệm chương trình trên các trường hợp kiểm thử (test cases):

#figure(
  caption: [Bảng kết quả kiểm thử chương trình],
  table(
    columns: (auto, 1fr, auto, auto),
    align: (center, left, center, center),
    
    inset: (col, row) => if row == 0 {
      (top: 8pt, bottom: 8pt, rest: 5pt)
    } else if row == 1 {
      (top: 8pt, bottom: 4pt, rest: 5pt)
    } else {
      4pt
    },

    stroke: none,
    table.hline(stroke: 1pt),
    table.header(
      [*Test Case*],
      [*Mô tả dữ liệu thử nghiệm*],
      [*Kết quả mong đợi*],
      [*Đánh giá*],
    ),
    table.hline(stroke: 0.5pt),
    [01], [Dữ liệu mảng rỗng $A = []$], [Trả về $-1$], [Đạt],
    [02], [Phần tử nằm ở đầu mảng], [Trả về vị trí $0$], [Đạt],
    [03], [Phần tử không tồn tại trong mảng], [Trả về $-1$], [Đạt],
    [04], [Mảng lớn có $10^6$ phần tử], [Thời gian $< 0.1 "s"$], [Đạt],
    table.hline(stroke: 1pt),
  ),
) <tab:test_results>

== Bảng tự đánh giá mức độ hoàn thành

Sinh viên tự đánh giá tỷ lệ hoàn thành các yêu cầu của bài tập:

#figure(
  caption: [Tự đánh giá mức độ hoàn thành yêu cầu],
  table(
    columns: (auto, 1fr, auto),
    align: (center, left, center),
    inset: 5pt,
    stroke: none,
    table.hline(stroke: 1pt),
    table.header(
      [*STT*],
      [*Yêu cầu của đề bài*],
      [*Mức độ hoàn thành*],
    ),
    table.hline(stroke: 0.5pt),
    [1], [Cài đặt đúng thuật toán và cấu trúc dữ liệu yêu cầu], [100%],
    [2], [Xử lý đầy đủ các trường hợp ngoại lệ (Edge cases)], [100%],
    [3], [Tối ưu hóa thời gian thực thi và bộ nhớ sử dụng], [100%],
    [4], [Viết báo cáo rõ ràng, mạch lạc đúng chuẩn quy định], [100%],
    table.hline(stroke: 1pt),
  ),
) <tab:self_eval>

== Kết luận

Chương trình đã hoàn thành đầy đủ các yêu cầu đề ra, chạy ổn định và vượt qua toàn bộ các bộ dữ liệu kiểm thử.
