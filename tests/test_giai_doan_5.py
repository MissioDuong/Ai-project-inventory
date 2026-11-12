# -*- coding: utf-8 -*-
"""Giai đoạn 5: hệ số bội k_i, hệ số can-order, phân bổ vốn theo mức khẩn cấp, chi phí cố định của kho."""
import pandas as pd
import pytest

from tinh_toan import nhieu_mat_hang as nm
from conftest import kich_ban


def _kh_hai_mat_hang(ban_hang_mo_phong, chi_phi_dong_cham):
    """Hai mặt hàng cùng nguồn: một bán nhanh, một bán chậm có chi phí dòng hàng lớn -> nên có k > 1."""
    ds = ["Bánh quy / bánh gạo (gói)", "Bánh trung thu (cái)"]
    mh = nm.mat_hang_mac_dinh(ds)
    mh["nguon_hang"] = "Chợ đầu mối"
    mh["khu_bao_quan"] = "Kho khô"
    mh.loc[mh["mat_hang"] == ds[1], "chi_phi_dong"] = chi_phi_dong_cham
    return nm.ke_hoach(ban_hang_mo_phong[ds], mh, nm.nguon_mac_dinh(mh["nguon_hang"]), nm.khu_mac_dinh(), 60), ds


def test_he_so_boi_lon_hon_1_khi_chi_phi_dong_lon(ban_hang_mo_phong):
    kh, ds = _kh_hai_mat_hang(ban_hang_mo_phong, 400_000)
    T, k = nm.chu_ky_chung(kh, ds, 0, tra_k=True)
    assert k[ds[0]] == 1 and k[ds[1]] >= 2
    goc = nm.DUNG_HE_SO_BOI
    try:
        nm.DUNG_HE_SO_BOI = False
        T0, k0 = nm.chu_ky_chung(kh, ds, 0, tra_k=True)
    finally:
        nm.DUNG_HE_SO_BOI = goc
    assert set(k0.values()) == {1}
    assert T <= T0                                             # mặt hàng chậm tách ra nhịp riêng thì chu kỳ chung ngắn lại


def test_he_so_can_order_0_it_mua_kem_hon(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, 120)
    goc = nm.HE_SO_CAN_ORDER
    dong = {}
    try:
        for hs in (0.0, 0.5):
            nm.HE_SO_CAN_ORDER = hs
            sim, sk, ch = nm.mo_phong_cua_hang(kh, "D", nc, lts, von_moi_ngay=1e7)
            dong[hs] = nm.chi_phi_cua_hang(kh, sim, sk, ch)
    finally:
        nm.HE_SO_CAN_ORDER = goc
    assert dong[0.0]["so_chuyen"] > dong[0.5]["so_chuyen"]     # không mua kèm thì phải đi nhiều chuyến hơn


def test_muc_khan_cap_xep_nguon_sap_het_truoc(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    info = kh["info"]
    nhom = {ng: list(g.index) for ng, g in info.groupby("nguon_hang")}
    vt = {i: 1000.0 for i in info.index}
    sap_het = nhom["Lò bánh pía"][0]
    vt[sap_het] = 0.0
    thu_tu = sorted(nhom, key=lambda n: nm.muc_khan_cap(kh, nhom[n], 0, vt))
    assert thu_tu[0] == "Lò bánh pía"


def test_chi_phi_co_dinh_bao_rieng_khong_cong_vao_tong(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, 50)
    sim, sk, ch = nm.mo_phong_cua_hang(kh, "D", nc, lts)
    c = nm.chi_phi_cua_hang(kh, sim, sk, ch)
    co_dinh = sum(kh["khu"].loc[z, "chi_phi_co_dinh_ngay"] for z in set(kh["info"]["khu_bao_quan"])) * 50
    assert c["chi_phi_co_dinh_kho"] == pytest.approx(co_dinh)
    assert c["tong"] == pytest.approx(sum(c[k] for k in ["chi_phi_chuyen", "chi_phi_dong_hang", "lai_von", "bao_quan",
                                                        "hu_hong", "het_han", "loi_nhuan_mat"]))


def test_file_khu_cu_khong_co_chi_phi_co_dinh():
    khu = nm.khu_mac_dinh().drop(columns="chi_phi_co_dinh_ngay")
    mh = nm.mat_hang_mac_dinh(["Bánh pía (hộp)"])
    assert nm.kiem_tra(mh, nm.nguon_mac_dinh(mh["nguon_hang"]), khu) == []
    assert isinstance(nm.bo_sung_cot_khu(khu), pd.DataFrame) and "chi_phi_co_dinh_ngay" in nm.bo_sung_cot_khu(khu)
