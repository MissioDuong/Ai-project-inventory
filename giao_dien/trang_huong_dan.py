# -*- coding: utf-8 -*-
"""Trang 📖 Hướng dẫn & phương pháp: cách dùng, cơ sở tài liệu, thuật toán, câu hỏi thường gặp (nội dung tĩnh)."""
import streamlit as st
from giao_dien.kieu import tieu_de


def ve(ctx):
    """Vẽ trang Hướng dẫn."""
    tieu_de("📖", "Hướng dẫn & phương pháp", "Cách dùng, thuật toán và cơ sở tài liệu")
    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.markdown("##### Dùng thế nào")
        st.markdown("""
1. **📦 Mặt hàng & kho** *(một lần)*: tải file doanh số (mục 📂 Tải dữ liệu lên), rồi khai báo nơi nhập hàng,
   nơi cất hàng (nhiệt độ, sức chứa), từng mặt hàng.
2. **🛒 Hôm nay** *(mỗi ngày)*: sửa tồn kho, xem **danh sách đi chợ** theo từng nguồn hàng, vốn cần, cảnh báo.
3. **📈 Dự báo**: kiểm tra dự báo có hợp lý không trước khi tin khuyến nghị.
4. **🧪 Mô phỏng & so sánh**: cách nhập gộp tiết kiệm bao nhiêu so với các cách khác.

Số ngày kế hoạch và vốn mỗi ngày chỉnh ở ô **⚙️ Kế hoạch & vốn** dưới menu; hỏi đáp bằng nút **💬 Chat với trợ lý AI**.
""")
    with c2.container(border=True):
        st.markdown("##### Cơ sở tài liệu")
        st.markdown("""
- Ghare & Schrader (1963), tồn kho suy giảm mũ; Covert & Philip (1973), suy giảm Weibull.
- Nahmias (1982), *Perishable Inventory Theory: A Review*, Operations Research 30(4).
- Bakker, Riezebos & Teunter (2012), tổng quan hàng suy giảm, EJOR 221(2).
- Broekmeulen & van Donselaar (2009), hàng dễ hỏng, đặt theo lô, nhu cầu thay đổi, Computers & OR 36(11).
- Minner & Transchel (2010), hàng dễ hỏng có ràng buộc mức phục vụ, OR Spectrum 32(4).
- Balintfy (1964), can-order; Khouja & Goyal (2008), tổng quan JRP, EJOR 186(1).
- Karimi & Sadjadi (2025), EOQ nhiều mặt hàng suy giảm có ràng buộc vốn & sức chứa, EJIE 19(4).
- Quy tắc Q10 / Arrhenius cho hạn dùng phụ thuộc nhiệt độ.

Chi tiết: `tai_lieu/NGHIEN_CUU_HANG_THUC_PHAM.md`.
""")
    with st.container(border=True):
        st.markdown("##### Thuật toán")
        st.markdown("""
| Bước | Cách tính |
|---|---|
| Dự báo | Nhu cầu = mức nền × hệ số thứ × hệ số Tết × hệ số Trung thu (âm lịch đổi sang dương lịch) |
| Hạn còn khi nhận | (Hạn in − số ngày đã cũ khi nhận) × Q10^((nhiệt độ chuẩn − nhiệt độ khu)/10), hệ số trong [×0,3; ×1,5] |
| Hư hỏng | Mỗi ngày mất θ% số hàng đang có (suy giảm mũ); θ tăng khi cất nóng hơn chuẩn (cùng hệ số Q10) |
| Chi phí giữ hàng | Giá vốn × (lãi vốn + 365·θ) + 365 × tiền bảo quản × thể tích |
| Tồn an toàn, điểm đặt hàng | Z × độ bất định nhu cầu và thời gian giao hàng; ROP = nhu cầu trong thời gian chờ + tồn an toàn |
| Gộp chuyến | Có mặt hàng chạm ROP thì đi; mặt hàng cùng nguồn sắp chạm thì mua kèm |
| Lượng nhập | Đủ bán T* ngày, T* = 365·√(2·(chi phí chuyến + Σ chi phí dòng) / Σ nhu cầu năm × chi phí giữ); ≤ 60% hạn còn khi nhận; làm tròn theo quy cách |
| Ràng buộc | Vượt vốn (hôm nay) hoặc sức chứa (dự phóng lúc hàng về) thì giảm số ngày đủ bán cho tới khi vừa |
| Tồn khả dụng *(tuỳ chọn, mặc định tắt)* | Chỉ tính phần hàng bán kịp trước hạn khi quyết định. Mô phỏng không thấy lợi ích, có hại khi khách chọn hàng mới |
""")
    with st.container(border=True):
        st.markdown("##### ❓ Giải thích thuật ngữ và câu hỏi thường gặp")
        hoi_dap = [
            ("“Mức phục vụ 0,95” nghĩa là gì? Sao mô phỏng ra gần 100 %?",
             "Là mục tiêu **95 % số chu kỳ nhập hàng không bị hết hàng ngày nào** (cycle service level), dùng để tính tồn an toàn. "
             "**Tỷ lệ đáp ứng** (bán được / nhu cầu) luôn khoảng 99,9 % vì mỗi chu kỳ bán rất nhiều đơn vị, còn lần hết hàng thì ngắn. "
             "Chỉ số nên xem là **CSL đạt được** ở trang 🧪: thường 97–99 %, tức mô hình hơi thận trọng. Đặt 0,95 cho chi phí thấp "
             "nhất trên dữ liệu mẫu; 0,90 nếu hết hàng chỉ mất lãi, 0,98 nếu khách hay bỏ đi."),
            ("“D rẻ hơn C khoảng 20 %” là so với cái gì, trong điều kiện nào?",
             "So với cách nhập EOQ theo dự báo nhưng **mỗi mặt hàng tự đặt riêng** (C), khi **cả hai cùng bị giới hạn vốn và sức chứa**, "
             "cùng nhu cầu và cùng thời gian giao hàng, trên **dữ liệu mô phỏng** với tham số giả định. Tính bằng tiền là khoảng "
             "2,3 triệu đ/năm cho 6 mặt hàng. Gần như toàn bộ phần tiết kiệm đến từ **gộp chuyến theo nguồn hàng**."),
            ("Chi phí chuyến được tính thế nào?",
             "Với **mọi** cách nhập: các đơn cùng nguồn, cùng ngày là **một chuyến**; chi phí chuyến chia đều cho các mặt hàng trong chuyến. "
             "Mỗi mặt hàng trong chuyến còn tốn thêm **chi phí dòng hàng** (đếm, kiểm, xếp kệ)."),
            ("Tồn khả dụng là gì, vì sao mặc định tắt?",
             "Là phần hàng **bán kịp trước khi hết hạn**. Ví dụ còn 100 gói hạn 5 ngày, mỗi ngày bán 10 gói thì chỉ 50 gói “khả dụng”, "
             "50 gói kia có thể phải bỏ. Mô phỏng cho thấy dùng con số này để quyết định đặt hàng **không giảm chi phí**, và còn "
             "**làm tăng** khi khách hay lựa hàng mới, nên mặc định tắt. Cột “Có thể hết hạn” vẫn luôn hiện để bạn bán đẩy hoặc giảm giá."),
            ("Thời gian được tính thế nào?",
             "Đặt hàng **cuối ngày**, hàng về **đầu ngày** sau lead time: lead time 1 ngày = sáng mai có hàng để bán. Trang Hôm nay "
             "lập kế hoạch cho đầu ngày bạn chọn, dùng điểm đặt hàng của cuối ngày hôm trước."),
            ("Tham số nào là số đo được, tham số nào là giả định?",
             "Doanh số là số liệu của bạn. Giá, hạn in, quy cách lấy từ bao bì và hoá đơn. **Hư hỏng %/ngày, Q10, nhiệt độ chuẩn, chi phí "
             "chuyến, chi phí dòng, tiền điện, lãi vốn** mặc định là **giả định**: hãy đo dần (đếm hàng hỏng mỗi tháng, ghi tiền xăng mỗi "
             "chuyến...)."),
            ("Vì sao D đặt nhiều dòng hàng hơn mà vẫn rẻ hơn?",
             "Vì đã đi một chuyến thì **mua kèm** các mặt hàng sắp cần. Thêm một dòng hàng tốn 5.000 đ, còn một chuyến riêng tốn "
             "30.000–60.000 đ. Bỏ mua kèm thì chi phí tăng khoảng 35 %."),
            ("Hạn thực tế được tính ra sao?",
             "(Hạn in − số ngày hàng đã cũ khi nhận) × hệ số nhiệt. Hệ số nhiệt = Q10^((nhiệt độ chuẩn − nhiệt độ chỗ cất)/10): "
             "cất nóng hơn khuyến nghị thì hạn ngắn lại (tối thiểu ×0,3), cất mát hơn thì dài ra (tối đa ×1,5, mức chặn này là giả định "
             "thận trọng)."),
            ("“Sức chứa” đo cái gì?",
             "Số lít hàng **đang thật sự nằm trong khu** (đo ngay sau khi hàng về). Khi quyết định đặt, app dự phóng chỗ trống **lúc hàng "
             "mới về** (đã trừ phần bán được trong thời gian chờ, ước lượng thận trọng)."),
            ("D có phải là EOQ không?",
             "Không hẳn. D là chính sách **đặt-tới-mức**: đi chợ khi có mặt hàng chạm điểm đặt hàng, mỗi mặt hàng nhập đủ bán T* ngày. "
             "Chỉ chu kỳ T* được tính theo công thức kiểu EOQ cho nhiều mặt hàng chung chi phí chuyến."),
        ]
        for cau, tra_loi in hoi_dap:
            with st.expander(cau):
                st.markdown(tra_loi)
    st.warning("Số mặc định và dữ liệu mô phỏng chỉ để minh hoạ. Với dữ liệu thật, hãy kiểm tra sai số dự báo ở trang 📈 "
               "và sửa tham số ở trang 📦 trước khi làm theo khuyến nghị.")
