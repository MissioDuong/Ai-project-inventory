# -*- coding: utf-8 -*-
"""Ứng dụng Streamlit EOQ Bánh Kẹo Chợ: điều phối thứ tự dựng dữ liệu và chọn trang để vẽ.

File này CHỈ điều phối. Muốn sửa nội dung một trang → giao_dien/trang_*.py; tính toán → tinh_toan/; AI → tro_ly_ai/.
Chạy:  streamlit run app.py

Thứ tự mỗi lần Streamlit chạy lại script:
  1. Điều hướng (thanh nhóm + thanh bên), cài đặt kế hoạch → ctx.trang, so_ngay, von, xu_huong, ai_key, ai_mo_hinh, ...
     Trang Nhập dữ liệu và Kế hoạch & vốn vẽ ngay sau bước này rồi dừng: chúng không cần dự báo, và phải dùng được
     cả khi chưa có dữ liệu nào.
  2. Nạp doanh số + khởi tạo thiết lập khi đổi dữ liệu  → ctx.ban_hang, canh_bao, ten_nguon, uoc_luong, ton_dem, skus, sig
  3. Trang ⚙️ phần thiết lập (nếu đang mở)            → người dùng sửa bảng mặt hàng / nguồn / khu
  4. Đọc + kiểm tra thiết lập                          → ctx.mh, nguon, khu, loi_tl (lỗi thì dừng)
  5. Dự báo + kế hoạch                                  → ctx.db, kh, info, bat_dau
  6. Vẽ trang đang chọn
"""
import streamlit as st

st.set_page_config(page_title="EOQ Bánh Kẹo Chợ", page_icon="🍬", layout="wide")   # phải là lệnh Streamlit đầu tiên

import pandas as pd  # noqa: E402

from tinh_toan import nhieu_mat_hang as nm  # noqa: E402
from giao_dien import (du_lieu, kieu, thanh_ben, trang_bieu_do, trang_du_doan, trang_hom_nay,  # noqa: E402
                       trang_huong_dan, trang_ke_hoach, trang_mo_phong, trang_nhap_lieu, trang_thiet_lap, trang_tro_ly)
from giao_dien.cau_hinh import (BIEU_DO, DU_DOAN, HOM_NAY, HUONG_DAN, KE_HOACH, MO_PHONG, NHAP_LIEU,  # noqa: E402
                                THIET_LAP, TRO_LY)
from giao_dien.tien_ich import du_bao, mh_mo_hinh  # noqa: E402

ss = st.session_state
kieu.ap_dung_css()

# 1. Thanh bên
ctx = thanh_ben.ve()
if ctx.trang in (NHAP_LIEU, KE_HOACH):                     # hai trang này không cần dữ liệu bán hàng / dự báo
    du_lieu.giu_widget()
    {NHAP_LIEU: trang_nhap_lieu.ve, KE_HOACH: trang_ke_hoach.ve}[ctx.trang](ctx)
    st.stop()
dang_o_thiet_lap = ctx.trang == THIET_LAP

# 2. Dữ liệu bán hàng
ctx.ban_hang, ctx.canh_bao, ctx.ten_nguon, ctx.uoc_luong, ctx.ton_dem = du_lieu.nap_ban_hang(ctx)
ctx.skus = list(ctx.ban_hang.columns)
ctx.sig = du_lieu.khoi_tao_thiet_lap(ctx)

# 3. Trang ⚙️: phần thiết lập phải vẽ TRƯỚC khi đọc bảng, để chỉnh sửa có hiệu lực ngay
khung_ai_dm = trang_thiet_lap.ve_thiet_lap(ctx) if dang_o_thiet_lap else None

# 4. Thiết lập hiện tại
ctx.mh = mh_mo_hinh(ss["mh_cur"])
ctx.nguon = ss["nguon_cur"].dropna(how="all")
ctx.khu = nm.bo_sung_cot_khu(ss["khu_cur"].dropna(how="all"))
ctx.loi_tl = nm.kiem_tra(ctx.mh, ctx.nguon, ctx.khu)
if dang_o_thiet_lap:
    trang_thiet_lap.ve_han_dung(ctx)
if ctx.loi_tl:
    if not dang_o_thiet_lap:
        st.error("Thiết lập chưa hợp lệ. Hãy sửa ở trang **Mặt hàng & kho**:\n\n- " + "\n- ".join(ctx.loi_tl))
    st.stop()

# 5. Dự báo và kế hoạch dùng chung cho mọi trang
ctx.db = du_bao(ctx.ban_hang, ctx.so_ngay, ctx.xu_huong, ctx.uoc_luong)
ctx.kh = nm.ke_hoach(ctx.ban_hang, ctx.mh, ctx.nguon, ctx.khu, ctx.so_ngay, du_bao=ctx.db, xu_huong=ctx.xu_huong,
                     uoc_luong=ctx.uoc_luong)
ctx.info = ctx.kh["info"]
ctx.bat_dau = pd.Timestamp(ctx.kh["ngay"][0])

# 6. Vẽ trang
if dang_o_thiet_lap:
    trang_thiet_lap.ve_ai_sua(ctx, khung_ai_dm)
else:
    {HOM_NAY: trang_hom_nay.ve, DU_DOAN: trang_du_doan.ve, BIEU_DO: trang_bieu_do.ve, MO_PHONG: trang_mo_phong.ve,
     HUONG_DAN: trang_huong_dan.ve, TRO_LY: trang_tro_ly.ve}[ctx.trang](ctx)
