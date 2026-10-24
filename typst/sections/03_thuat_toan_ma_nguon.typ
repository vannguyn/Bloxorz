#import "../components.typ": *

= Cài đặt và Mã nguồn chính

== Mã giả giải thuật

Trình bày các bước thực hiện của thuật toán chính:

#algorithm_box(
  [Thuật toán tìm kiếm phần tử],
  [Mảng đã sắp xếp $A$, giá trị cần tìm $x$.],
  [Vị trí của $x$ trong mảng, hoặc $-1$ nếu không tìm thấy.],
  (
    [$l <- 0$, $r <- |A| - 1$],
    [*while* $l <= r$ *do*],
    [#h(1.2em)$m <- floor((l + r) \/ 2)$],
    [#h(1.2em)*if* $A[m] = x$ *then*],
    [#h(2.4em)*return* $m$],
    [#h(1.2em)*else if* $A[m] < x$ *then*],
    [#h(2.4em)$l <- m + 1$],
    [#h(1.2em)*else*],
    [#h(2.4em)$r <- m - 1$],
    [#h(1.2em)*end if*],
    [*end while*],
    [*return* $-1$],
  ),
)

== Đoạn mã nguồn cốt lõi

Sinh viên chèn đoạn mã nguồn chính quan trọng nhất (tránh chèn toàn bộ mã nguồn quá dài):

#figure(
  caption: [Hàm tìm kiếm nhị phân bằng Python],
)[
```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```
]

#pagebreak()
#callout_tip(title: [Lưu ý khi nộp bài])[
  Mã nguồn nộp kèm cần có chú thích (comment) rõ ràng ở các hàm chính và tuân thủ chuẩn đặt tên biến.
]
