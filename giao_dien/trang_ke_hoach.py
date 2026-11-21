# -*- coding: utf-8 -*-
"""Trang Kế hoạch & vốn: số ngày lập kế hoạch, vốn nhập hàng mỗi ngày, các tuỳ chọn dự báo.

Giá trị thật nằm ở khoá thường của session_state (so_ngay, von, dung_tkd, xu_huong) do thanh_ben khởi tạo; ô nhập ở đây
dùng khoá riêng (w_*) và chép sang khi đổi, để giá trị không mất khi người dùng sang trang khác.
Trang này không cần dữ liệu bán hàng: app.py vẽ nó ngay sau điều hướng rồi dừng.
"""
import streamlit as st

from tinh_toan import nhieu_mat_hang as nm
from giao_dien.kieu import tieu_de

ss = st.session_state


def _chep(k):
    ss[k] = ss[f"w_{k}"]
    if k == "dung_tkd":
        nm.DUNG_TON_KHA_DUNG = bool(ss[k])


def _dong_bo(*ds):
    for k in ds:                                               # trước khi tạo ô nhập: lấy giá trị đang dùng (kể cả AI vừa sửa)
        if ss.get(f"w_{k}") != ss[k]:
            ss[f"w_{k}"] = ss[k]


def ve(ctx):
    """Vẽ trang Kế hoạch & vốn."""
    tieu_de("💰", "Kế hoạch & vốn", "Áp dụng cho mọi trang: danh sách đi chợ, dự đoán, biểu đồ, mô phỏng")
    _dong_bo("so_ngay", "von", "dung_tkd", "xu_huong")
    c1, c2 = st.columns(2, gap="large")
    with c1.container(border=True):
        st.markdown("##### Kế hoạch")
        st.slider("Lập kế hoạch cho (ngày)", 30, 365, step=10, key="w_so_ngay", on_change=_chep, args=("so_ngay",),
                  help="Số ngày app dự báo và tính điểm đặt hàng. Trang Hôm nay chọn được ngày trong khoảng này.")
        st.number_input("Vốn nhập hàng tối đa mỗi ngày (đ)", min_value=0, step=500_000, format="%d", key="w_von",
                        on_change=_chep, args=("von",), help="Tổng tiền hàng của tất cả các chuyến trong một ngày")
        st.caption(f"Đang dùng: **{ss['so_ngay']} ngày**, vốn **{ss['von']:,.0f} đ/ngày**".replace(",", "."))
    with c2.container(border=True):
        st.markdown("##### Tuỳ chọn dự báo")
        st.toggle("Dự báo có xu hướng tăng/giảm", key="w_xu_huong", on_change=_chep, args=("xu_huong",),
                  help="Thêm xu hướng tuyến tính có hãm (ước lượng từ 180 ngày gần nhất). Kiểm định trên dữ liệu mẫu cho thấy "
                       "không cải thiện, nên mặc định tắt; bật nếu lượng bán đang tăng/giảm rõ")
        st.toggle("Trừ hàng sắp hết hạn khi quyết định (thử nghiệm)", key="w_dung_tkd", on_change=_chep, args=("dung_tkd",),
                  help="Tồn khả dụng: chỉ tính phần hàng bán kịp trước hạn khi quyết định đặt. Mô phỏng chưa thấy lợi ích và có "
                       "hại khi khách hay chọn hàng mới, nên mặc định tắt. Cảnh báo 'có thể hết hạn' vẫn luôn hiện.")
        st.caption("Cả hai mặc định tắt. Chỉ bật khi bạn hiểu rõ tác dụng (xem trang Hướng dẫn).")
