# -*- coding: utf-8 -*-
"""Giai đoạn 6: trang Hôm nay nhận nhiều lô hàng cho mỗi mặt hàng."""
import pandas as pd

from tinh_toan import nhieu_mat_hang as nm


def _ton(kh, ton_kho=10, han=30):
    ds = list(kh["mat_hang"])
    return pd.DataFrame({"mat_hang": ds, "ton_kho": [ton_kho] * len(ds), "han_con_lai": [han] * len(ds),
                         "hang_dang_ve": [0] * len(ds)}), ds


def test_gom_lo_cong_don_va_xep_han_ngan_truoc(ke_hoach_mo_phong):
    ton, ds = _ton(ke_hoach_mo_phong)
    lo_them = pd.DataFrame({"mat_hang": [ds[0], ds[0]], "so_luong": [5, 7], "han_con_lai": [2, 90]})
    ton2, lo = nm.gom_lo(ton, lo_them)
    assert ton2.set_index("mat_hang").loc[ds[0], "ton_kho"] == 22
    assert [a[1] for a in lo[ds[0]]] == [2, 30, 90]
    assert ton2.set_index("mat_hang").loc[ds[1], "ton_kho"] == 10


def test_lo_sap_het_han_duoc_canh_bao(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    ton, ds = _ton(kh, ton_kho=5, han=60)
    m = ds[0]
    d_ngay = float(kh["mat_hang"][m]["d_hat"][5])
    lo_them = pd.DataFrame({"mat_hang": [m], "so_luong": [round(20 * d_ngay) + 50], "han_con_lai": [1]})
    bang, _, _ = nm.ke_hoach_hom_nay(kh, 5, ton, 1e7, lo_them=lo_them)
    r = bang.set_index("mat_hang").loc[m]
    assert r["so_lo"] == 2 and r["han_ngan_nhat"] == 1
    assert r["sap_het_han"] > 0                                # lô chỉ còn 1 ngày mà quá nhiều thì phải cảnh báo


def test_khong_co_lo_them_giu_nguyen_ket_qua(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    ton, _ = _ton(kh)
    a, _, _ = nm.ke_hoach_hom_nay(kh, 3, ton, 1e7)
    b, _, _ = nm.ke_hoach_hom_nay(kh, 3, ton, 1e7, lo_them=pd.DataFrame(columns=["mat_hang", "so_luong", "han_con_lai"]))
    pd.testing.assert_frame_equal(a, b)
