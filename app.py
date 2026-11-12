# -*- coding: utf-8 -*-
"""Ứng dụng Streamlit EOQ Bánh Kẹo Chợ: điều phối thứ tự dựng dữ liệu và chọn trang để vẽ.

File này CHỈ điều phối. Muốn sửa nội dung một trang → giao_dien/trang_*.py; tính toán → tinh_toan/; AI → tro_ly_ai/.
Chạy:  streamlit run app.py

Thứ tự mỗi lần Streamlit chạy lại script:
  1. Thanh bên (menu, vốn, số ngày, cấu hình AI)       → ctx.trang, so_ngay, von, xu_huong, ai_key, ai_mo_hinh, ds_mo_hinh
  2. Nạp doanh số + khởi tạo thiết lập khi đổi dữ liệu  → ctx.ban_hang, canh_bao, ten_nguon, skus, sig
  3. Trang 📦 phần thiết lập (nếu đang mở)            → người dùng sửa bảng mặt hàng / nguồn / khu
  4. Đọc + kiểm tra thiết lập                          → ctx.mh, nguon, khu, loi_tl (lỗi thì dừng)
  5. Dự báo + kế hoạch                                  → ctx.db, kh, info, bat_dau
  6. Vẽ trang đang chọn
"""
import streamlit as st

st.set_page_config(page_title="EOQ Bánh Kẹo Chợ", page_icon="🍬", layout="wide")   # phải là lệnh Streamlit đầu tiên

import pandas as pd  # noqa: E402

from tinh_toan import nhieu_mat_hang as nm  # noqa: E402
from giao_dien import (du_lieu, kieu, thanh_ben, trang_du_bao, trang_hom_nay, trang_huong_dan,  # noqa: E402
                       trang_mat_hang, trang_mo_phong, trang_tro_ly)
from giao_dien.cau_hinh import TRANG  # noqa: E402
from giao_dien.tien_ich import du_bao, mh_mo_hinh  # noqa: E402

ss = st.session_state
kieu.ap_dung_css()

# 1. Thanh bên
ctx = thanh_ben.ve()
dang_o_mat_hang = ctx.trang == TRANG[1]

# 2. Dữ liệu bán hàng
ctx.ban_hang, ctx.canh_bao, ctx.ten_nguon = du_lieu.nap_ban_hang(ctx)
ctx.skus = list(ctx.ban_hang.columns)
ctx.sig = du_lieu.khoi_tao_thiet_lap(ctx)

# 3. Trang 📦: phần thiết lập phải vẽ TRƯỚC khi đọc bảng, để chỉnh sửa có hiệu lực ngay
khung_ai_dm = trang_mat_hang.ve_thiet_lap(ctx) if dang_o_mat_hang else None

# 4. Thiết lập hiện tại
ctx.mh = mh_mo_hinh(ss["mh_cur"])
ctx.nguon = ss["nguon_cur"].dropna(how="all")
ctx.khu = nm.bo_sung_cot_khu(ss["khu_cur"].dropna(how="all"))
ctx.loi_tl = nm.kiem_tra(ctx.mh, ctx.nguon, ctx.khu)
if dang_o_mat_hang:
    trang_mat_hang.ve_han_dung(ctx)
if ctx.loi_tl:
    if not dang_o_mat_hang:
        st.error("Thiết lập chưa hợp lệ. Hãy sửa ở trang **📦 Mặt hàng & kho**:\n\n- " + "\n- ".join(ctx.loi_tl))
    st.stop()

# 5. Dự báo và kế hoạch dùng chung cho mọi trang
ctx.db = du_bao(ctx.ban_hang, ctx.so_ngay, ctx.xu_huong)
ctx.kh = nm.ke_hoach(ctx.ban_hang, ctx.mh, ctx.nguon, ctx.khu, ctx.so_ngay, du_bao=ctx.db, xu_huong=ctx.xu_huong)
ctx.info = ctx.kh["info"]
ctx.bat_dau = pd.Timestamp(ctx.kh["ngay"][0])

# 6. Vẽ trang
if dang_o_mat_hang:
    trang_mat_hang.ve_ai_sua(ctx, khung_ai_dm)
else:
    {TRANG[0]: trang_hom_nay.ve, TRANG[2]: trang_du_bao.ve, TRANG[3]: trang_mo_phong.ve,
     TRANG[4]: trang_huong_dan.ve, TRANG[5]: trang_tro_ly.ve}[ctx.trang](ctx)
