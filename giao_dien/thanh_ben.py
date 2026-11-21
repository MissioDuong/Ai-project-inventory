# -*- coding: utf-8 -*-
"""Điều hướng kiểu phần mềm quản lý: thanh nhóm ngang ở đầu trang + danh sách trang theo nhóm ở thanh bên.

Cài đặt kế hoạch (số ngày, vốn, ...) nằm ở trang Kế hoạch & vốn và được giữ trong session_state dưới khoá thường
(so_ngay, von, dung_tkd, xu_huong), nên mọi trang đọc được kể cả khi trang đó không vẽ ô nhập.
"""
from types import SimpleNamespace

import streamlit as st

from tinh_toan import so_ghi
from tinh_toan import nhieu_mat_hang as nm
from tro_ly_ai import tro_ly as tl
from giao_dien.cau_hinh import (DL_CUA_TOI, DL_MO_PHONG, DL_SO_GHI, MO_TA_TRANG, NGUON_DL, NHOM, NHOM_CUA, TRANG,
                                noi_luu_so)

ss = st.session_state
MAC_DINH_KE_HOACH = {"so_ngay": 120, "von": 10_000_000, "dung_tkd": False, "xu_huong": False}


def _chon(trang):
    ss["trang"] = trang


def _khoi_tao():
    if ss.get("trang") not in TRANG:                           # trạng thái cũ (tên trang trước khi đổi menu) → về Hôm nay
        ss["trang"] = TRANG[0]
    if ss.get("nguon_du_lieu") not in NGUON_DL:               # phiên mới: đã có sổ kiểm kho trên máy thì dùng sổ, không thì mô phỏng
        co_so = so_ghi.co_so(noi_luu_so())
        ss["nguon_du_lieu"] = DL_SO_GHI if co_so else DL_MO_PHONG
    for k, v in MAC_DINH_KE_HOACH.items():
        ss.setdefault(k, v)
    if "_cho_von" in ss:                                       # thay đổi do AI sửa / hoàn tác
        ss["von"] = int(ss.pop("_cho_von"))
    nm.DUNG_TON_KHA_DUNG = bool(ss["dung_tkd"])


def _css_dang_chon(trang):
    """Tô nút của trang và nhóm đang mở (khoá widget cố định theo vị trí trong TRANG / NHOM)."""
    i = TRANG.index(trang)
    g = [ten for ten, _ in NHOM].index(NHOM_CUA[trang])
    st.markdown(f"<style>.st-key-nav_{i} button {{ background: var(--xanh) !important; color: #fff !important; "
                f"font-weight: 700 !important; }} .st-key-nav_{i} button p {{ color: #fff !important; }} "
                f".st-key-thanh_tren .st-key-nhom_{g} .stButton button, .st-key-thanh_tren .st-key-nhom_{g} button "
                f"{{ background: #ffffff !important; border-color: #ffffff !important; }} "
                f".st-key-thanh_tren .st-key-nhom_{g} button p {{ color: var(--xanh) !important; font-weight: 700 !important; }}"
                f"</style>",
                unsafe_allow_html=True)


def ve():
    """Vẽ điều hướng, trả về ngữ cảnh ban đầu: trang, so_ngay, von, xu_huong, ai_key, ai_mo_hinh, ds_mo_hinh, file_ban."""
    _khoi_tao()
    trang = ss["trang"]
    key_cfg, mo_hinh_cfg = tl.doc_cau_hinh()                  # key chỉ đọc từ secrets.toml / biến môi trường
    ds_mo_hinh = tl.MO_HINH_GOI_Y if mo_hinh_cfg in tl.MO_HINH_GOI_Y else [mo_hinh_cfg] + tl.MO_HINH_GOI_Y
    ss.setdefault("ai_mo_hinh_v", ds_mo_hinh[0])
    file_ban = ss.get("file_du_lieu") if ss["nguon_du_lieu"] == DL_CUA_TOI else None

    with st.sidebar:
        st.markdown('<div class="thuong-hieu"><span class="t1">EOQ</span><span class="t2">Bánh Kẹo Chợ</span></div>',
                    unsafe_allow_html=True)
        for ten, ds in NHOM:
            st.markdown(f'<div class="nhom-menu">{ten}</div>', unsafe_allow_html=True)
            for t in ds:
                st.button(t, key=f"nav_{TRANG.index(t)}", on_click=_chon, args=(t,), help=MO_TA_TRANG[t],
                          use_container_width=True)
        _css_dang_chon(trang)                                  # đặt ở thanh bên để không chiếm chỗ trong trang

    nhan_dl = {DL_MO_PHONG: "Dữ liệu mô phỏng", DL_SO_GHI: "Sổ kiểm kho"}.get(ss["nguon_du_lieu"]) or \
        (file_ban["name"] if file_ban else "Chưa có file")
    with st.container(key="thanh_tren"):
        cot = st.columns([1] * len(NHOM) + [2.2], gap="small", vertical_alignment="center")
        for j, (ten, ds) in enumerate(NHOM):
            cot[j].button(ten, key=f"nhom_{j}", on_click=_chon, args=(ds[0],), use_container_width=True)
        cot[-1].markdown(f'<div class="thong-tin">{nhan_dl} · {ss["so_ngay"]} ngày · {ss["von"] / 1e6:g} tr/ngày</div>',
                         unsafe_allow_html=True)

    ss["_vao_trang"] = ss.get("_trang_cu") != trang
    ss["_trang_cu"] = trang
    return SimpleNamespace(trang=trang, so_ngay=int(ss["so_ngay"]), von=float(ss["von"]), xu_huong=bool(ss["xu_huong"]),
                           ai_key=key_cfg, ai_mo_hinh=ss["ai_mo_hinh_v"], ds_mo_hinh=ds_mo_hinh, file_ban=file_ban)
