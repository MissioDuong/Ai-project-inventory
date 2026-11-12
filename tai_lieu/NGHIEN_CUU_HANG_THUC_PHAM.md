# Tồn kho thực phẩm nhiều mặt hàng: tổng quan tài liệu và cách đưa vào thuật toán

*Lập ngày 11/11/2026. Các nguồn dưới đây đã được kiểm tra thông tin xuất bản (tạp chí, số, trang) qua trang chỉ mục.
Nhiều bài chỉ đọc được tóm tắt; những chỗ diễn giải chi tiết thuật toán có ghi chú khi chưa đọc được toàn văn.*

---

## 1. Hai đặc điểm của hàng thực phẩm trong lý thuyết tồn kho

Tài liệu chia hàng "dễ hỏng" (perishable / deteriorating) thành hai kiểu, và bánh kẹo ở chợ có **cả hai**:

| Kiểu | Ý nghĩa | Ví dụ ở sạp bánh kẹo | Tài liệu gốc |
|---|---|---|---|
| **Hạn dùng cố định** (fixed lifetime) | Hàng dùng tốt tới hạn rồi bỏ toàn bộ | Bánh pía, bánh trung thu có hạn in trên bao bì | Nahmias (1982) |
| **Suy giảm liên tục** (continuous / exponential decay) | Mỗi ngày mất một tỷ lệ θ số hàng | Kẹo chảy, bánh ẩm, mốc, móp, chuột cắn | Ghare & Schrader (1963) |

- **Ghare & Schrader (1963)**, *A model for an exponentially decaying inventory*, J. Industrial Engineering 14(1), 238–243.
  Đây là mô hình EOQ đầu tiên cho hàng suy giảm: tồn kho thay đổi theo phương trình vi phân dI/dt = −θ·I − D.
  **Covert & Philip (1973)** mở rộng cho tỷ lệ suy giảm thay đổi theo thời gian (phân phối Weibull).
  Các nghiên cứu gần đây vẫn so sánh các nghiệm dạng đóng của mô hình này
  ([MDPI Sustainability 14(14):8389](https://www.mdpi.com/2071-1050/14/14/8389/xml)).
- **Nahmias (1982)**, *Perishable Inventory Theory: A Review*, Operations Research 30(4), 680–708
  ([EconPapers](https://econpapers.repec.org/RePEc:inm:oropre:v:30:y:1982:i:4:p:680-708)).
  Đây là tổng quan đầu tiên, bao gồm cả hai kiểu trên, cho một hoặc nhiều mặt hàng, nhu cầu tất định hoặc ngẫu nhiên.
- **Goyal & Giri (2001)**, rồi **Bakker, Riezebos & Teunter (2012)**, *Review of inventory systems with deterioration
  since 2001*, EJOR 221(2), 275–284 ([EconPapers](https://econpapers.repec.org/RePEc:eee:ejores:v:221:y:2012:i:2:p:275-284)).
  Hai bài phân loại mô hình theo đặc điểm hạn dùng và đặc điểm nhu cầu, cùng các yếu tố một/nhiều mặt hàng,
  một/hai kho, hết hàng mất doanh số hay chờ hàng... **Janssen, Claus & Sauer (2016)** cập nhật giai đoạn 2012–2015
  (Int. J. Production Economics 182, 86–112).

## 2. Hạn dùng phụ thuộc điều kiện bảo quản

- Tốc độ hư hỏng của thực phẩm tăng theo nhiệt độ. Có hai mô hình thường dùng:
  **Arrhenius** (cần năng lượng hoạt hoá của từng sản phẩm) và **Q10** (hạn dùng ngắn đi Q10 lần khi nóng thêm 10°C).
  Q10 thực tế hơn khi có nhiều loại sản phẩm và thiếu số liệu động học
  ([arXiv 2511.05920](https://arxiv.org/pdf/2511.05920)).
  Với thực phẩm làm lạnh hỏng do vi sinh vật, Q10 thường trong khoảng 2–10
  ([USPTO 6741523](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6741523)).
- Mô hình Arrhenius đã được kiểm chứng trong điều kiện nhiệt độ dao động, ví dụ tôm đông lạnh (Tsironi và cộng sự, 2009).
  Mô phỏng chuỗi lạnh cũng cho thấy phần lớn hạn dùng bị "tiêu" ngay trong khâu lưu thông
  ([typeset: frozen shrimp](https://typeset.io/pdf/shelf-life-modelling-of-frozen-shrimp-at-variable-4gw3cqvooe.pdf);
  [WUR](https://edepot.wur.nl/461413)).
- Cách áp dụng phổ biến trong quản lý tồn kho: theo dõi hạn còn lại của **từng lô**, rồi xuất lô sắp hết hạn trước (FEFO).

## 3. Quyết định đặt hàng cho hàng dễ hỏng

- **Broekmeulen & van Donselaar (2009)**, *A heuristic to manage perishable inventory with batch ordering,
  positive lead-times, and time-varying demand*, Computers & OR 36(11), 3013–3018
  ([doi:10.1016/j.cor.2009.01.017](https://doi.org/10.1016/j.cor.2009.01.017)).
  Bối cảnh của bài trùng với dự án này: đặt theo lô, có thời gian giao hàng, nhu cầu thay đổi theo thời gian.
  Các nghiên cứu sau gọi hướng này là chính sách **EWA (Estimated Withdrawal and Aging)**: khi tính vị thế tồn kho,
  ước lượng phần hàng sẽ bị rút ra do hết hạn và trừ đi trước khi quyết định
  ([ví dụ ở ngân hàng máu](https://www.scribd.com/document/692788567/Lowalekar-Ravichandran-2017)).
  *Ghi chú: chưa đọc được toàn văn, nên công thức trong dự án là cách triển khai đơn giản hoá ý tưởng này.*
- **Minner & Transchel (2010)**, *Periodic review inventory-control for perishable products under service-level
  constraints*, OR Spectrum 32(4), 979–996 ([MaRDI](https://portal.mardi4nfdi.de/wiki/Publication:708873)).
  Bài tính lượng đặt động cho hàng có hạn dùng, lead time dương, xuất FIFO hoặc LIFO, có ràng buộc mức phục vụ,
  và vượt các chính sách đặt-tới-mức thông thường. Bài giả định không có chi phí đặt hàng cố định.

## 4. Nhiều mặt hàng: nhập gộp và ràng buộc tài nguyên

- **Bài toán bổ sung hàng chung (Joint Replenishment Problem, JRP).** Nhiều mặt hàng dùng chung một chi phí đặt hàng
  "lớn" (chuyến đi) cộng chi phí "nhỏ" cho từng mặt hàng.
  Tổng quan: **Khouja & Goyal (2008)**, EJOR 186(1), 1–16
  ([EconPapers](https://econpapers.repec.org/RePEc:eee:ejores:v:186:y:2008:i:1:p:1-16)), và
  **Peng, Wang & Wang (2022)** cho giai đoạn 2006–2022 ([Springer](https://link.springer.com/article/10.1007/s44176-022-00010-3)).
  Khouja & Goyal nhận định việc tìm nghiệm tối ưu đã bão hoà, và đề xuất tập trung vào **mô hình thực tế, dễ triển khai**
  ([SciELO 2016](https://new.scielo.br/j/prod/a/Mdr7rS34Rb8RJ8Yc6HyzT8f/?lang=en)).
- **Chính sách can-order (Balintfy, 1964).** Khi một mặt hàng chạm mức *phải đặt*, cả đơn hàng được kích hoạt;
  các mặt hàng khác đang dưới mức *có thể đặt* được thêm vào cùng đơn.
- **JRP cho hàng suy giảm.** Ai và cộng sự (2017, IJPR 55(16)) làm JRP cho hàng suy giảm không tức thời và báo cáo tiết kiệm
  đáng kể so với đặt riêng từng mặt hàng ([IDEAS](https://ideas.repec.org/a/taf/tprsxx/v55y2017i16p4625-4642.html)).
  Castellano và cộng sự (2022) phối hợp bổ sung hàng, chọn mặt hàng và phân bổ chỗ trưng bày cho hàng suy giảm.
- **Ràng buộc vốn và sức chứa.**
  - EOQ nhiều mặt hàng có ràng buộc thường được giải bằng nhân tử Lagrange: Q_i = √(2·D_i·S_i / (h_i + 2λ·w_i)), với λ
    tìm bằng cách lặp tới khi vừa ràng buộc
    ([ví dụ](https://cec.nic.in/webpath/curriculum/Module/STAT/Paper15_T/18/downloads/script.pdf)).
  - **Karimi & Sadjadi (2025)**, Eur. J. Industrial Engineering 19(4), 454–501: EOQ nhiều mặt hàng suy giảm với cả
    ràng buộc vốn và sức chứa, giải bằng quy hoạch động
    ([IDEAS](https://ideas.repec.org/a/ids/eujine/v19y2025i4p454-501.html)).
  - Một nghiên cứu nhiều mặt hàng ngẫu nhiên khác có xét hạn dùng, sức chứa kho, giới hạn vốn, và so sánh đặt riêng,
    đặt gộp và kết hợp ([Barekeng](https://ojs3.unpatti.ac.id/index.php/barekeng/article/view/12759)).

---

## 5. Cách đưa vào thuật toán của dự án (`nhieu_mat_hang.py`)

| Tài liệu | Thành phần trong dự án | Công thức / quy tắc |
|---|---|---|
| Ghare & Schrader (1963) | Hư hỏng mỗi ngày θ | Mỗi lô mất Binomial(số lượng, θ) mỗi ngày; chi phí giữ trong EOQ là H = c·(r + 365θ) + bảo quản |
| Nahmias (1982), Bakker và cs. (2012) | Hạn dùng cố định theo lô | Mỗi lô có ngày hết hạn; hết hạn thì bỏ; bán FIFO (cũ trước, tương đương FEFO khi cùng hạn dùng) |
| Q10 / Arrhenius | Khu bảo quản có nhiệt độ | Hạn còn khi nhận = (hạn in − tuổi khi nhận) × Q10^((T_chuẩn − T_khu)/10), hệ số trong [×0,3; ×1,5]; θ hiệu dụng = θ ÷ cùng hệ số |
| Broekmeulen & van Donselaar (2009), EWA | Tồn khả dụng *(tuỳ chọn, mặc định tắt)* | Chỉ tính phần lô bán kịp trước hạn theo dự báo, trừ hao hụt trong thời gian chờ, cộng hàng đang về. Luôn dùng để **cảnh báo** “có thể hết hạn” |
| Minner & Transchel (2010) | Cách xuất hàng | FIFO hoặc pha trộn với LIFO (khách chọn hàng mới), tham số `ty_le_lifo` |
| Balintfy (1964), Khouja & Goyal (2008) | Gộp chuyến theo nguồn hàng | Có mặt hàng chạm ROP thì đi; mặt hàng cùng nguồn dưới ROP + nhu cầu (0,5 × T*) ngày thì mua kèm (hệ số 0,5 chọn bằng dò lưới) |
| JRP (chu kỳ chung, heuristic kiểu Silver) | Lượng nhập | Đủ bán k_i·T* ngày, T* = 365·√(2(S + Σ s_i/k_i) / Σ k_i D_i H_i); ≤ 60 % hạn còn khi nhận; làm tròn theo quy cách |
| Lagrange / Karimi & Sadjadi (2025) | Vốn mỗi ngày, sức chứa từng khu | Tìm số ngày đủ bán τ lớn nhất thoả mọi ràng buộc (tìm kiếm nhị phân), tương đương tăng λ cho tới khi vừa. Sức chứa kiểm tra theo dự phóng lúc hàng về |

**Kết quả mô phỏng sau khi chỉnh sửa theo phản biện** (chi tiết ở `DU_AN.md` mục 5). Dữ liệu mô phỏng, 6 mặt hàng, 3 nguồn hàng,
3 khu bảo quản, vốn 10 triệu/ngày, **mọi chính sách cùng ràng buộc**, bỏ 30 ngày khởi động, 20 lần lặp:
- D rẻ hơn C (EOQ động đặt riêng) **22,4 % ± 3,2**, thắng 20/20 lần; dữ liệu thử: 18,8 % ± 9,5, thắng 19/20 lần.
- **Phân tích từng thành phần**: gộp chuyến −2,3 triệu đ; tồn khả dụng khoảng 0 (−0,01 triệu ± 0,15). Trong kịch bản
  hàng nhập về đã cũ một nửa hạn **và** khách chọn hàng mới, tồn khả dụng **tăng** chi phí 0,26 triệu, nên đã tắt khỏi quyết định.
- Mua kèm (can-order) là cốt lõi: bỏ mua kèm thì chi phí tăng khoảng 35 %.
- Dự báo căn theo âm lịch: ở đỉnh Tết sai 29 % (dữ liệu mô phỏng), so với 71 % của cách “năm ngoái cùng ngày”.

## 6. Khoảng trống mà dự án có thể đóng góp (phạm vi nhỏ)

1. Phần lớn mô hình JRP cho hàng suy giảm giả định **nhu cầu không đổi**. Dự án kết hợp JRP + hạn dùng + hư hỏng
   + **nhu cầu mùa vụ âm lịch** + lead time ngẫu nhiên, đánh giá bằng mô phỏng.
2. Đánh giá **EWA trong bối cảnh nhập gộp** nhiều mặt hàng (các bài EWA đã thấy chủ yếu là một mặt hàng, ví dụ ngân hàng máu).
   Kết quả của dự án là **không có lợi ích khi đã gộp chuyến**, và có hại khi khách chọn hàng mới. Đây là một phát hiện âm tính đáng báo cáo.
3. **Bán lẻ siêu nhỏ** với ràng buộc vốn theo ngày và kho nhiều khu nhiệt độ (khô / tủ mát / tủ lạnh) là bối cảnh ít được nghiên cứu.

> Cần tra cứu thêm (Scopus, Google Scholar) để xác nhận các khoảng trống trên trước khi đưa vào báo cáo chính thức.

## 7. Giới hạn của triển khai hiện tại

- θ, Q10 và nhiệt độ chuẩn là **giả định minh hoạ**; cần đo thực tế (đếm hàng hỏng, ghi nhiệt độ tủ).
- Chưa mô hình hoá giảm giá hàng sắp hết hạn: app chỉ cảnh báo, chưa tối ưu mức giảm giá.
- Chưa có hàng thay thế, chiết khấu số lượng, số lượng đặt tối thiểu theo nhà cung cấp.
- Hệ số bội k_i đã có (heuristic kiểu Silver) nhưng với tham số mặc định đều bằng 1; mức can-order chọn chung cho mọi nguồn hàng.
- Độ ẩm chưa được mô hình hoá; vốn mỗi ngày là hằng số, chưa theo dòng tiền bán hàng.
