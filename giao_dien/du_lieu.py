# -*- coding: utf-8 -*-
"""Nạp dữ liệu bán hàng (mô phỏng có sẵn hoặc file người dùng) và khởi tạo các bảng thiết lập khi đổi bộ dữ liệu."""
import io
import os

import pandas as pd
import streamlit as st

from tinh_toan import loi
from tinh_toan import nhieu_mat_hang as nm
from giao_dien.cau_hinh import DEMO, DL_CUA_TOI, DL_MO_PHONG, TRANG
from giao_dien.kieu import tieu_de
from giao_dien.tien_ich import dat_bang, mh_hien

ss = st.session_state


def _cb_dl_nguon():
    if ss.get("w_dl_nguon") in (DL_MO_PHONG, DL_CUA_TOI):
        ss["nguon_du_lieu"] = ss["w_dl_nguon"]


def _cb_dl_file():
    f = ss.get("w_file_ban")
    if f is not None:                                           # lưu nội dung file để còn dùng khi sang trang khác
        ss["file_du_lieu"] = {"name": f.name, "data": f.getvalue()}


def khung_tai_doanh_so():
    """Chọn nguồn dữ liệu bán hàng + tải file doanh số (đặt ở trang 📦 Mặt hàng & kho)."""
    st.markdown("**① Doanh số bán hàng**")
    st.radio("Dữ liệu bán hàng", [DL_MO_PHONG, DL_CUA_TOI], index=[DL_MO_PHONG, DL_CUA_TOI].index(ss["nguon_du_lieu"]),
             key="w_dl_nguon", on_change=_cb_dl_nguon, horizontal=True, label_visibility="collapsed")
    if ss["nguon_du_lieu"] == DL_CUA_TOI:
        c1, c2 = st.columns([3, 1])
        c1.file_uploader("File doanh số (CSV hoặc Excel)", type=["csv", "xlsx", "xls"], key="w_file_ban",
                         on_change=_cb_dl_file)
        c2.download_button("⬇️ File mẫu doanh số", loi.mau_ban_hang_csv(), "mau_doanh_so.csv", "text/csv",
                           use_container_width=True)
        if ss.get("file_du_lieu"):
            c2.caption(f"Đang dùng: **{ss['file_du_lieu']['name']}**")
            c2.button("🗑️ Bỏ file này", key="bo_file_ban", on_click=lambda: ss.pop("file_du_lieu", None),
                      use_container_width=True)
        st.caption("Cột cần có: ngay (dạng 2025-01-15), mat_hang, so_luong_ban; tuỳ chọn het_hang (1 = hôm đó hết hàng). "
                   "Mỗi ngày ghi đủ mỗi mặt hàng một dòng, kể cả hôm bán 0; cần ít nhất 60 ngày.")


def dung_khi_chua_co_du_lieu(trang, tieu, mo_ta, loi_=None):
    tieu_de("📂", tieu, mo_ta)
    if loi_:
        st.error(f"❌ {loi_}")
    if trang == TRANG[1]:
        with st.container(border=True):
            khung_tai_doanh_so()
    else:
        st.info("Vào trang **📦 Mặt hàng & kho** để tải file doanh số, hoặc chọn **Dữ liệu mô phỏng có sẵn** để dùng thử.")
        st.button("📦 Đến trang Mặt hàng & kho", on_click=lambda: ss.update(trang=TRANG[1]), type="primary")
    st.stop()


def nap_ban_hang(ctx):
    """Trả về (ban_hang, canh_bao, ten_nguon). Dừng trang (st.stop) nếu chưa có / không đọc được dữ liệu."""
    if ss["nguon_du_lieu"] == DL_MO_PHONG:
        if not os.path.exists(DEMO):
            st.error("Chưa có dữ liệu mô phỏng. Hãy chạy: python pipeline.py")
            st.stop()
        ban_hang, canh_bao = loi.chuan_hoa_ban_hang(pd.read_csv(DEMO))
        return ban_hang, canh_bao, "mo_phong"
    file_ban = ctx.file_ban
    if file_ban is None:
        dung_khi_chua_co_du_lieu(ctx.trang, "Chưa có dữ liệu", "Tải file doanh số của bạn ở trang 📦 Mặt hàng & kho")
    loi_doc = None
    try:                                                         # chỉ bọc phần đọc file, không bọc phần vẽ giao diện
        f_ban = io.BytesIO(file_ban["data"])
        f_ban.name = file_ban["name"]
        ban_hang, canh_bao = loi.chuan_hoa_ban_hang(loi.doc_file(f_ban))
    except ValueError as e:
        loi_doc = e
    if loi_doc is not None:
        dung_khi_chua_co_du_lieu(ctx.trang, "File doanh số chưa dùng được", "Sửa file theo hướng dẫn bên dưới rồi tải lại", loi_doc)
    return ban_hang, canh_bao, file_ban["name"]


def khoi_tao_thiet_lap(ctx):
    """Khởi tạo lại bảng mặt hàng / nguồn / khu khi đổi bộ dữ liệu; dọn giá trị widget không còn hợp lệ. Trả về sig."""
    skus = ctx.skus
    sig = f"{ctx.ten_nguon}|{'|'.join(skus)}"
    if ss.get("sig") != sig:
        ss["sig"] = sig
        mh0 = nm.mat_hang_mac_dinh(skus)
        dat_bang("mh", mh_hien(mh0))
        dat_bang("nguon", nm.nguon_mac_dinh(mh0["nguon_hang"]))
        dat_bang("khu", nm.khu_mac_dinh())
        ss.pop("ton_cur", None)
        for k in ("f_ng_id", "f_kz_id", "f_mh_id", "ngay_hn_v"):
            ss.pop(k, None)

    # Giữ giá trị các widget của trang khác khi chuyển trang; bỏ giá trị không còn hợp lệ
    for k, hop_le in {"db_mh": skus, "mp_mh": skus, "mp_khu": list(ss["khu_cur"]["khu_bao_quan"].dropna()),
                      "di_cho": None, "mp_n_ngay": None, "mp_n_lan": None}.items():
        if k in ss:
            if hop_le is not None and ss[k] not in hop_le:
                del ss[k]
            else:
                ss[k] = ss[k]
    if ss.get("mp_n_ngay", 0) > ctx.so_ngay:
        ss["mp_n_ngay"] = ctx.so_ngay
    return sig
