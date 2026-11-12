# -*- coding: utf-8 -*-
"""Giai đoạn 4: tuổi khi nhận, hư hỏng theo nhiệt độ, khách chọn hàng mới, không đảo thứ tự giao hàng, sức chứa thực."""
import numpy as np
import pytest

from tinh_toan import nhieu_mat_hang as nm
from conftest import kich_ban


def _info(mh_sua=None):
    ds = ["Bánh pía (hộp)", "Kẹo dừa Bến Tre (gói 200g)"]
    mh = nm.mat_hang_mac_dinh(ds)
    if mh_sua:
        mh_sua(mh)
    return nm.chuan_bi(mh, nm.nguon_mac_dinh(mh["nguon_hang"]), nm.khu_mac_dinh())


def test_tuoi_khi_nhan_rut_ngan_han_con():
    def sua(mh):
        mh["tuoi_khi_nhan_ngay"] = [10, 90]
        mh["khu_bao_quan"] = "Kho khô"                          # 30 °C: bánh pía chuẩn 25 °C -> nóng hơn
    info = _info(sua)
    keo = info.loc["Kẹo dừa Bến Tre (gói 200g)"]
    assert keo["han_con_khi_nhan"] == 180 - 90                    # kho khô đúng nhiệt độ chuẩn: chỉ trừ tuổi
    pia = info.loc["Bánh pía (hộp)"]
    assert pia["han_con_khi_nhan"] < 30 - 10                      # cất nóng hơn chuẩn: còn ngắn hơn nữa


def test_theta_tang_khi_cat_nong():
    def nong(mh):
        mh["khu_bao_quan"] = "Kho khô"
    lanh, nong_ = _info(), _info(nong)
    m = "Bánh pía (hộp)"
    assert nong_.loc[m, "ty_le_hu_hong_ngay"] > lanh.loc[m, "ty_le_hu_hong_ngay"]
    assert lanh.loc[m, "theta_goc"] == nong_.loc[m, "theta_goc"]


def test_file_cu_khong_co_cot_tuoi_van_chay():
    mh = nm.mat_hang_mac_dinh(["Bánh pía (hộp)"]).drop(columns="tuoi_khi_nhan_ngay")
    assert nm.kiem_tra(mh, nm.nguon_mac_dinh(mh["nguon_hang"]), nm.khu_mac_dinh()) == []
    assert nm.chuan_bi(mh, nm.nguon_mac_dinh(mh["nguon_hang"]), nm.khu_mac_dinh())["tuoi_khi_nhan_ngay"].iloc[0] == 0


def test_khach_chon_hang_moi_lam_tang_het_han(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, 120)
    het = {}
    for lifo in (0.0, 1.0):
        sim, _, _ = nm.mo_phong_cua_hang(kh, "C", nc, lts, ty_le_lifo=lifo, ton0={m: 400.0 for m in nc})
        het[lifo] = sim["het_han"].sum()
    assert het[1.0] > het[0.0]                                    # bán hàng mới trước thì lô cũ nằm lại tới hết hạn


def test_khong_dao_thu_tu_giao_hang(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, 120)
    sim, _, _ = nm.mo_phong_cua_hang(kh, "C", nc, lts)
    for ng, g in kh["info"].groupby("nguon_hang"):
        don = sim[sim["mat_hang"].isin(g.index) & (sim["dat_hang"] > 0)].drop_duplicates("ngay").sort_values("ngay")
        assert (np.diff(don["ve_ngay"].values) >= 0).all()


def test_bang_suc_chua_la_cho_thuc(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, 60)
    sim, sk, _ = nm.mo_phong_cua_hang(kh, "D", nc, lts, von_moi_ngay=1e7)
    info = kh["info"]
    for z in kh["khu"].index:
        ky_vong = (sim.assign(v=sim["ton_sau_ve"] * sim["mat_hang"].map(info["the_tich_lit"]))
                   [sim["mat_hang"].map(info["khu_bao_quan"]) == z].groupby("ngay")["v"].sum())
        assert np.allclose(sk.set_index("ngay")[z].reindex(ky_vong.index).values, ky_vong.values)


def test_ton_dau_mac_dinh_vua_suc_chua(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, 5)
    _, sk, _ = nm.mo_phong_cua_hang(kh, "D", nc, lts)
    for z in kh["khu"].index:
        cap = float(kh["khu"].loc[z, "suc_chua_lit"])
        if cap > 0:
            assert sk.loc[0, z] <= cap + 1e-6


def test_D_mac_dinh_khong_dung_ton_kha_dung():
    assert nm.DUNG_TON_KHA_DUNG is False and nm.CAU_HINH["D"][1] is None
