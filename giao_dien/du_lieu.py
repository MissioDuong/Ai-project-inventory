# -*- coding: utf-8 -*-
"""Nạp dữ liệu bán hàng (mô phỏng có sẵn, sổ kiểm kho, hoặc file người dùng) và khởi tạo các bảng thiết lập khi đổi dữ liệu."""
import io
import os

import pandas as pd
import streamlit as st

from tinh_toan import loi, so_ghi
from tinh_toan import nhieu_mat_hang as nm
from giao_dien.cau_hinh import DEMO, DL_CUA_TOI, DL_MO_PHONG, DL_SO_GHI, MO_TA_NGUON_DL, NGUON_DL, NHAP_LIEU, noi_luu_so
from giao_dien.kieu import tieu_de
from giao_dien.tien_ich import dat_bang, ghep_bang, mh_hien, mh_mo_hinh

ss = st.session_state
TEN_SO_GHI = "so_kiem_kho"                                     # ctx.ten_nguon khi dùng sổ kiểm kho
_WIDGET_GIU = ("db_mh", "mp_mh", "mp_khu", "di_cho", "mp_n_ngay", "mp_n_lan")


def _cb_dl_nguon():
    if ss.get("w_dl_nguon") in NGUON_DL:
        ss["nguon_du_lieu"] = ss["w_dl_nguon"]


def _cb_dl_file():
    f = ss.get("w_file_ban")
    if f is not None:                                           # lưu nội dung file để còn dùng khi sang trang khác
        ss["file_du_lieu"] = {"name": f.name, "data": f.getvalue()}
        ss["nguon_du_lieu"] = ss["w_dl_nguon"] = DL_CUA_TOI     # vừa tải file thì dùng luôn file đó


def chon_nguon_du_lieu():
    """Ô chọn app lấy số liệu bán hàng từ đâu (trang 📝 Nhập dữ liệu)."""
    if ss.get("w_dl_nguon") != ss["nguon_du_lieu"]:            # đồng bộ trước khi tạo widget (không truyền index)
        ss["w_dl_nguon"] = ss["nguon_du_lieu"]
    st.radio("App lấy số liệu bán hàng từ", NGUON_DL, captions=MO_TA_NGUON_DL, key="w_dl_nguon", on_change=_cb_dl_nguon,
             horizontal=True, label_visibility="collapsed")


def khung_tai_doanh_so():
    """Tải file doanh số có sẵn (CSV / Excel)."""
    c1, c2 = st.columns([3, 1])
    c1.file_uploader("File doanh số (CSV hoặc Excel)", type=["csv", "xlsx", "xls"], key="w_file_ban", on_change=_cb_dl_file)
    c2.download_button("⬇️ File mẫu doanh số", loi.mau_ban_hang_csv(), "mau_doanh_so.csv", "text/csv", use_container_width=True)
    if ss.get("file_du_lieu"):
        c2.caption(f"Đang có: **{ss['file_du_lieu']['name']}**")
        c2.button("🗑️ Bỏ file này", key="bo_file_ban", on_click=lambda: ss.pop("file_du_lieu", None), use_container_width=True)
    st.caption("Cột cần có: ngay (dạng 2025-01-15), mat_hang, so_luong_ban; tuỳ chọn het_hang (1 = hôm đó hết hàng). "
               "Mỗi ngày ghi đủ mỗi mặt hàng một dòng, kể cả hôm bán 0; cần ít nhất 60 ngày. "
               "Chưa có file như vậy? Dùng **Sổ kiểm kho** để app tự đo lượng bán.")


def dung_khi_chua_co_du_lieu(tieu, mo_ta, loi_=None):
    tieu_de("📂", tieu, mo_ta)
    if loi_:
        st.error(f"❌ {loi_}")
    st.info("Vào trang **📝 Nhập dữ liệu** để thêm mặt hàng, kiểm kho hoặc tải file doanh số. "
            "Muốn xem thử trước thì chọn **Dữ liệu mô phỏng (dùng thử)** ở trang đó.")
    st.button("📝 Đến trang Nhập dữ liệu", on_click=lambda: ss.update(trang=NHAP_LIEU), type="primary")
    st.stop()


def nap_ban_hang(ctx):
    """Trả về (ban_hang, canh_bao, ten_nguon, uoc_luong, ton_dem). Dừng trang (st.stop) nếu chưa có / không đọc được dữ liệu.
    uoc_luong: {mặt hàng: (ít, thường, nhiều)} chỉ có khi dùng sổ kiểm kho; ton_dem: {mặt hàng: số đếm gần nhất}."""
    if ss["nguon_du_lieu"] == DL_MO_PHONG:
        if not os.path.exists(DEMO):
            st.error("Chưa có dữ liệu mô phỏng. Hãy chạy: python pipeline.py")
            st.stop()
        ban_hang, canh_bao = loi.chuan_hoa_ban_hang(pd.read_csv(DEMO))
        return ban_hang, canh_bao, "mo_phong", None, None
    if ss["nguon_du_lieu"] == DL_SO_GHI:
        loi_doc = None
        try:
            kk, uoc = so_ghi.doc_so(noi_luu_so())
        except ValueError as e:
            loi_doc = e
        if loi_doc is not None:
            dung_khi_chua_co_du_lieu("Sổ kiểm kho có lỗi", "Sửa sổ ở trang 📝 Nhập dữ liệu → 📒 Sổ đã ghi", loi_doc)
        ban_hang, canh_bao = so_ghi.bang_ban_hang(kk, uoc, pd.Timestamp.today().normalize())
        if ban_hang.shape[1] == 0:
            dung_khi_chua_co_du_lieu("Sổ kiểm kho chưa có mặt hàng",
                                     "Thêm mặt hàng và ước lượng bán mỗi ngày ở trang 📝 Nhập dữ liệu", None)
        ton = so_ghi.lan_dem_cuoi(kk)
        return ban_hang, canh_bao, TEN_SO_GHI, so_ghi.uoc_dict(uoc), ton["ton_cuoi_ngay"].astype(float).to_dict()
    file_ban = ctx.file_ban
    if file_ban is None:
        dung_khi_chua_co_du_lieu("Chưa có file doanh số", "Tải file ở trang 📝 Nhập dữ liệu → 📂 File doanh số")
    loi_doc = None
    try:                                                         # chỉ bọc phần đọc file, không bọc phần vẽ giao diện
        f_ban = io.BytesIO(file_ban["data"])
        f_ban.name = file_ban["name"]
        ban_hang, canh_bao = loi.chuan_hoa_ban_hang(loi.doc_file(f_ban))
    except ValueError as e:
        loi_doc = e
    if loi_doc is not None:
        dung_khi_chua_co_du_lieu("File doanh số chưa dùng được", "Sửa file theo hướng dẫn ở trang 📝 Nhập dữ liệu rồi tải lại",
                                 loi_doc)
    return ban_hang, canh_bao, file_ban["name"], None, None


def _thiet_lap_moi(ctx, mh0):
    """Bảng thiết lập khi đổi sang bộ dữ liệu khác: mặc định, hoặc bản đã lưu trên máy nếu đang dùng sổ kiểm kho."""
    nguon0, khu0 = nm.nguon_mac_dinh(mh0["nguon_hang"]), nm.khu_mac_dinh()
    if ctx.ten_nguon == TEN_SO_GHI:
        da_luu = so_ghi.doc_thiet_lap(noi_luu_so())
        try:
            if "mh" in da_luu:
                mh0 = ghep_bang(da_luu["mh"], mh0, "mat_hang")
            if "nguon" in da_luu:
                nguon0 = ghep_bang(da_luu["nguon"], nguon0, "nguon_hang")
            if "khu" in da_luu:
                khu0 = ghep_bang(da_luu["khu"], khu0, "khu_bao_quan")
        except ValueError as e:
            st.warning(f"Không đọc được thiết lập đã lưu, dùng giá trị mặc định: {e}")
    return mh0, nguon0, khu0


def khoi_tao_thiet_lap(ctx):
    """Khởi tạo bảng mặt hàng / nguồn / khu khi đổi bộ dữ liệu; dọn giá trị widget không còn hợp lệ. Trả về sig.
    Cùng nguồn dữ liệu mà chỉ thêm/bớt mặt hàng (ví dụ thêm hàng vào sổ kiểm kho) thì giữ thiết lập đã sửa."""
    skus = ctx.skus
    sig = f"{ctx.ten_nguon}|{'|'.join(skus)}"
    if ss.get("sig") != sig:
        cung_nguon = ss.get("sig", "").split("|")[0] == ctx.ten_nguon and "mh_cur" in ss
        mh0 = nm.mat_hang_mac_dinh(skus)
        if cung_nguon:
            mh_moi = ghep_bang(mh_mo_hinh(ss["mh_cur"]), mh0, "mat_hang")
            dat_bang("mh", mh_hien(mh_moi))
            ng = ss["nguon_cur"].dropna(how="all")
            thieu = [n for n in dict.fromkeys(mh_moi["nguon_hang"]) if n not in set(ng["nguon_hang"])]
            if thieu:
                dat_bang("nguon", pd.concat([ng, nm.nguon_mac_dinh(thieu)], ignore_index=True))
        else:
            mh0, nguon0, khu0 = _thiet_lap_moi(ctx, mh0)
            dat_bang("mh", mh_hien(mh0))
            dat_bang("nguon", nguon0)
            dat_bang("khu", khu0)
            for k in ("f_ng_id", "f_kz_id", "f_mh_id", "ngay_hn_v"):
                ss.pop(k, None)
        ss["sig"] = sig
        ss.pop("ton_cur", None)

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


def giu_widget():
    """Giữ giá trị widget của các trang khác khi đang ở trang không dựng dữ liệu (📝 Nhập dữ liệu)."""
    for k in _WIDGET_GIU:
        if k in ss:
            ss[k] = ss[k]
