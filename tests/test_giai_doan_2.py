# -*- coding: utf-8 -*-
"""Giai đoạn 2: nhu cầu có sai số dự báo, bỏ giai đoạn khởi động, mức phục vụ đạt được."""
import numpy as np
import pandas as pd
import pytest

from tinh_toan import nhieu_mat_hang as nm
from conftest import kich_ban


def test_sinh_nhu_cau_dung_ky_vong_va_phuong_sai():
    rng = np.random.default_rng(0)
    d, v = np.full(200_000, 10.0), np.full(200_000, 30.0)
    x = nm.sinh_nhu_cau(d, v, rng)
    assert x.mean() == pytest.approx(10, rel=0.02)
    assert x.var() == pytest.approx(30, rel=0.05)
    assert (x >= 0).all()


def test_sinh_nhu_cau_ve_poisson_khi_phuong_sai_bang_ky_vong():
    x = nm.sinh_nhu_cau(np.full(100_000, 5.0), np.full(100_000, 5.0), np.random.default_rng(1))
    assert x.var() == pytest.approx(5, rel=0.05)


def test_bo_ngay_dau_loai_dung_so_ngay(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, 120)
    sim, sk, ch = nm.mo_phong_cua_hang(kh, "D", nc, lts, von_moi_ngay=1e7)
    du = nm.chi_phi_cua_hang(kh, sim, sk, ch, 1e7)
    bot = nm.chi_phi_cua_hang(kh, sim, sk, ch, 1e7, bo_ngay_dau=30)
    assert bot["lai_von"] < du["lai_von"]
    tay = sim[sim["ngay"] >= 30]
    assert bot["hu_hong"] == pytest.approx(float((tay["hu_hong"] * tay["mat_hang"].map(kh["info"]["gia_von"])).sum()))


def test_muc_phuc_vu_dat_duoc():
    # Một mặt hàng, hai lần hàng về (ngày 0 và 5): chu kỳ đầu có hết hàng, chu kỳ sau không
    sim = pd.DataFrame({"ngay": range(10), "mat_hang": "X", "nhu_cau": 10.0,
                        "ban": [10, 10, 5, 10, 10, 10, 10, 10, 10, 10], "hang_ve": [50, 0, 0, 0, 0, 50, 0, 0, 0, 0]})
    sim["thieu_hang"] = sim["nhu_cau"] - sim["ban"]
    kq = nm.muc_phuc_vu_dat_duoc(sim).loc["X"]
    assert kq["csl"] == pytest.approx(0.5) and kq["so_chu_ky"] == 2
    assert kq["ty_le_dap_ung"] == pytest.approx(95 / 100)
    assert kq["ngay_het_hang"] == pytest.approx(0.1)


def test_he_so_mat_khach_nhan_dung(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, 120)
    sim, sk, ch = nm.mo_phong_cua_hang(kh, "B", nc, lts)
    c1 = nm.chi_phi_cua_hang(kh, sim, sk, ch, he_so_mat_khach=1)
    c3 = nm.chi_phi_cua_hang(kh, sim, sk, ch, he_so_mat_khach=3)
    assert c3["loi_nhuan_mat"] == pytest.approx(3 * c1["loi_nhuan_mat"])
