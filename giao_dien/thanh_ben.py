# -*- coding: utf-8 -*-
"""Thanh bên: thương hiệu, menu trang, ô ⚙️ Kế hoạch & vốn, cấu hình trợ lý AI, nút chat."""
from types import SimpleNamespace

import streamlit as st

from tinh_toan import nhieu_mat_hang as nm
from tro_ly_ai import tro_ly as tl
from giao_dien.cau_hinh import DL_CUA_TOI, DL_MO_PHONG, TRANG

ss = st.session_state


def ve():
    """Vẽ thanh bên, trả về ngữ cảnh ban đầu: trang, so_ngay, von, xu_huong, ai_key, ai_mo_hinh, ds_mo_hinh, file_ban."""
    with st.sidebar:
        st.markdown('<div class="thuong-hieu"><div class="t1">🍬 EOQ Bánh Kẹo Chợ</div>'
                    '<div class="t2">Nhập hàng thông minh cho cả sạp thực phẩm</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="nhan-muc">MENU</div>', unsafe_allow_html=True)
        with st.container(key="menu"):
            trang = st.radio("Trang", TRANG, key="trang", label_visibility="collapsed")
        st.markdown('<div class="nhan-muc" style="margin-top:18px">CÀI ĐẶT</div>', unsafe_allow_html=True)
        chip = st.empty()
        with st.expander("⚙️ Kế hoạch & vốn", expanded=False):
            so_ngay = st.slider("Lập kế hoạch cho (ngày)", 30, 365, 120, step=10, key="so_ngay")
            # Giá trị khởi tạo một lần qua session (KHÔNG truyền value, để widget không bị coi là widget mới giữa các lần chạy)
            ss.setdefault("von", 10_000_000)
            if "_cho_von" in ss:                                   # thay đổi do AI sửa / hoàn tác
                ss["von"] = int(ss.pop("_cho_von"))
            von = st.number_input("Vốn nhập hàng tối đa mỗi ngày (đ)", min_value=0, step=500_000, format="%d", key="von",
                                  help="Tổng tiền hàng của tất cả các chuyến trong một ngày")
            dung_tkd = st.toggle("Trừ hàng sắp hết hạn khi quyết định (thử nghiệm)", value=False, key="dung_tkd",
                                 help="Tồn khả dụng: chỉ tính phần hàng bán kịp trước hạn khi quyết định đặt. Mô phỏng chưa thấy lợi ích "
                                      "và có hại khi khách hay chọn hàng mới, nên mặc định tắt. Cảnh báo 'có thể hết hạn' vẫn luôn hiện.")
            nm.DUNG_TON_KHA_DUNG = dung_tkd
            xu_huong = st.toggle("Dự báo có xu hướng tăng/giảm", value=False, key="xu_huong",
                                 help="Thêm xu hướng tuyến tính có hãm (ước lượng từ 180 ngày gần nhất). Kiểm định trên dữ liệu "
                                      "mẫu cho thấy không cải thiện, nên mặc định tắt; bật nếu lượng bán đang tăng/giảm rõ")
        # Trợ lý AI: key chỉ đọc từ .streamlit/secrets.toml hoặc biến môi trường, KHÔNG có ô nhập / hiển thị trên giao diện
        key_cfg, mo_hinh_cfg = tl.doc_cau_hinh()
        ds_mo_hinh = tl.MO_HINH_GOI_Y if mo_hinh_cfg in tl.MO_HINH_GOI_Y else [mo_hinh_cfg] + tl.MO_HINH_GOI_Y
        ss.setdefault("ai_mo_hinh_v", ds_mo_hinh[0])
        st.button("💬  Chat với trợ lý AI", key="nut_chat", use_container_width=True, type="primary",
                  on_click=lambda: ss.update(trang=TRANG[5]))
        if ss.get("nguon_du_lieu") not in (DL_MO_PHONG, DL_CUA_TOI):      # trạng thái cũ / không hợp lệ → về mặc định
            ss["nguon_du_lieu"] = DL_MO_PHONG
        file_ban = ss.get("file_du_lieu") if ss["nguon_du_lieu"] == DL_CUA_TOI else None
        chip.markdown(f'<div class="chip-hang"><span class="chip">📊 {"Mô phỏng" if file_ban is None else file_ban["name"][:18]}</span>'
                      f'<span class="chip">📅 {so_ngay} ngày</span><span class="chip">💰 {von / 1e6:g} tr/ngày</span></div>',
                      unsafe_allow_html=True)

    ss["_vao_trang"] = ss.get("_trang_cu") != trang
    ss["_trang_cu"] = trang
    return SimpleNamespace(trang=trang, so_ngay=so_ngay, von=von, xu_huong=xu_huong, ai_key=key_cfg,
                           ai_mo_hinh=ss["ai_mo_hinh_v"], ds_mo_hinh=ds_mo_hinh, file_ban=file_ban)
