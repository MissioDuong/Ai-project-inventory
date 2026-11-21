# -*- coding: utf-8 -*-
"""Tiện ích giao diện: hàm tính có cache, định dạng tiền, ghép bảng tải lên, bảng sửa được giữ trạng thái khi chuyển trang."""
import numpy as np
import pandas as pd
import streamlit as st

from tinh_toan import loi
from tinh_toan import nhieu_mat_hang as nm

ss = st.session_state


@st.cache_data(show_spinner="Đang dự báo nhu cầu...")
def du_bao(ban_hang, so_ngay, xu_huong=False, uoc_luong=None):
    return nm.du_bao_tat_ca(ban_hang, so_ngay, xu_huong, uoc_luong)


@st.cache_data(show_spinner="Đang kiểm định dự báo theo mùa...")
def kiem_dinh(y, xu_huong=False):
    return loi.kiem_dinh_theo_mua(y, xu_huong=xu_huong)


@st.cache_data(show_spinner="Đang mô phỏng cả cửa hàng...")
def mo_phong(ban_hang, mh, nguon, khu, so_ngay, von, n_ngay, n_lan, ap_rang_buoc, xu_huong=False, ty_le_lifo=0.0,
             dung_ton_kha_dung=False, uoc_luong=None):
    """ap_rang_buoc=True: mọi chính sách cùng bị giới hạn vốn và sức chứa (so sánh công bằng).
    Luôn chạy thêm C+G (C + gộp chuyến, cùng ràng buộc với D) để tách đóng góp của từng thành phần."""
    nm.DUNG_TON_KHA_DUNG = dung_ton_kha_dung
    kh = nm.ke_hoach(ban_hang, mh, nguon, khu, so_ngay, du_bao=du_bao(ban_hang, so_ngay, xu_huong, uoc_luong),
                     xu_huong=xu_huong, uoc_luong=uoc_luong)
    ds = list(kh["mat_hang"])
    W = min(30, n_ngay // 4)                                   # bỏ giai đoạn khởi động khỏi chỉ số
    rows, mau = [], {}
    for r in range(n_lan):
        rng = np.random.default_rng(1000 + r)
        # nhu cầu có cả sai số dự báo (nhị thức âm, phương sai a·d + b·d²), không chỉ nhiễu Poisson
        nc = {m: nm.sinh_nhu_cau(kh["mat_hang"][m]["d_hat"][:n_ngay], kh["mat_hang"][m]["var"][:n_ngay], rng) for m in ds}
        lts = nm.sinh_lead_times(kh["info"], n_ngay, rng)
        for p in ["A", "B", "C", "C+G", "C+G+E", "D"]:
            rb = True if p in ("C+G", "C+G+E", "D") else ap_rang_buoc
            sim, sk, ch = nm.mo_phong_cua_hang(kh, p, nc, lts, von_moi_ngay=von, seed=r, rang_buoc=rb, ty_le_lifo=ty_le_lifo)
            c = nm.chi_phi_cua_hang(kh, sim, sk, ch, von, bo_ngay_dau=W)
            c.update(lan=r, chinh_sach=p)
            rows.append(c)
            if p == "C" and ap_rang_buoc is False:            # thêm C có ràng buộc để ablation luôn cùng điều kiện
                sim2, sk2, ch2 = nm.mo_phong_cua_hang(kh, "C", nc, lts, von_moi_ngay=von, seed=r, rang_buoc=True,
                                                      ty_le_lifo=ty_le_lifo)
                c2 = nm.chi_phi_cua_hang(kh, sim2, sk2, ch2, von, bo_ngay_dau=W)
                c2.update(lan=r, chinh_sach="C_rb")
                rows.append(c2)
            if r == 0:
                mau[p] = (sim, sk)
    return pd.DataFrame(rows), mau


def mau_cot(df, bang_mau):
    """Danh sách màu cho st.line_chart / st.bar_chart: Streamlit gán màu theo tên cột ĐÃ XẾP chữ cái, không theo thứ tự cột."""
    return [bang_mau[c] for c in sorted(df.columns)]


def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def tien(x):
    return f"{x:,.0f} đ".replace(",", ".")


def ghep_bang(up, mac_dinh, khoa):
    """Ghép bảng người dùng tải lên vào bảng mặc định theo cột khoá; thiếu cột/dòng thì giữ mặc định."""
    up = up.copy()
    chuan = {c.lower(): c for c in mac_dinh.columns}            # khớp tên cột không phân biệt hoa/thường
    up.columns = [chuan.get(loi._bo_dau(c), loi._bo_dau(c)) for c in up.columns]
    if khoa not in up.columns:
        raise ValueError(f"File cần có cột '{khoa}'.")
    up[khoa] = up[khoa].astype(str).map(loi._nfc)
    kq = mac_dinh.set_index(khoa)
    for _, r in up.iterrows():
        if r[khoa] not in kq.index:
            kq.loc[r[khoa]] = mac_dinh.iloc[0].drop(khoa) if khoa != "mat_hang" else np.nan
        for c in mac_dinh.columns:
            if c != khoa and c in up.columns and pd.notna(r[c]):
                kq.loc[r[khoa], c] = r[c]
    kq = kq.reset_index()
    # mặt hàng: giữ đúng danh sách trong dữ liệu bán hàng; nguồn hàng / khu: dùng đúng các dòng trong file
    return kq[kq[khoa].isin(mac_dinh[khoa] if khoa == "mat_hang" else up[khoa])].reset_index(drop=True)


def mh_hien(m):
    h = m.copy()
    h["ty_le_hu_hong_ngay"] = h["ty_le_hu_hong_ngay"] * 100
    h["ty_le_giu_hang_nam"] = h["ty_le_giu_hang_nam"] * 100
    return h


def mh_mo_hinh(h):
    m = h.copy()
    m["ty_le_hu_hong_ngay"] = m["ty_le_hu_hong_ngay"] / 100
    m["ty_le_giu_hang_nam"] = m["ty_le_giu_hang_nam"] / 100
    return m


def dat_bang(ten, df):
    """Thay nội dung một bảng sửa được (ví dụ khi đổi dữ liệu hoặc tải file)."""
    ss[f"{ten}_cur"] = df.reset_index(drop=True)
    ss[f"{ten}_moi"] = True


def bang_sua(ten, **kw):
    """data_editor giữ được chỉnh sửa khi chuyển trang (Streamlit xoá trạng thái widget không hiển thị)."""
    if ss.get("_vao_trang") or ss.get(f"{ten}_moi") or f"{ten}_base" not in ss:
        ss[f"{ten}_base"] = ss[f"{ten}_cur"].copy()
        ss[f"{ten}_ver"] = ss.get(f"{ten}_ver", 0) + 1
        ss[f"{ten}_moi"] = False
    out = st.data_editor(ss[f"{ten}_base"], key=f"{ten}_ed{ss[f'{ten}_ver']}", **kw)
    ss[f"{ten}_cur"] = out
    return out
