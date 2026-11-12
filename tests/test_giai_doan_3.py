# -*- coding: utf-8 -*-
"""Giai đoạn 3: nhu cầu bị kiểm duyệt (ngày vắng mặt, hết hàng), kiểm định theo mùa, xu hướng."""
import numpy as np
import pandas as pd

from tinh_toan import loi
from conftest import chuoi_co_tet


def _dai(so_ngay=120):
    ngay = pd.date_range("2025-01-01", periods=so_ngay)
    return pd.DataFrame({"ngay": np.repeat(ngay.strftime("%Y-%m-%d"), 2), "mat_hang": ["A", "B"] * so_ngay,
                         "so_luong_ban": [5, 3] * so_ngay})


def test_ngay_vang_mat_la_thieu_du_lieu_con_so_0_ghi_ro_van_la_0():
    d = _dai()
    d = d[d["ngay"] != "2025-01-10"]                              # ngày nghỉ: không có dòng nào
    d.loc[(d["ngay"] == "2025-01-11") & (d["mat_hang"] == "A"), "so_luong_ban"] = 0   # bán 0 ghi rõ
    d = d[~((d["ngay"] == "2025-01-12") & (d["mat_hang"] == "B"))]                     # B vắng, A vẫn có
    rong, cb = loi.chuan_hoa_ban_hang(d)
    assert np.isnan(rong.loc["2025-01-10", "A"]) and np.isnan(rong.loc["2025-01-10", "B"])
    assert rong.loc["2025-01-11", "A"] == 0
    assert rong.loc["2025-01-12", "B"] == 0                        # ngày có bán hàng nhưng B không có dòng = bán 0
    assert any("THIẾU DỮ LIỆU" in c for c in cb)


def test_cot_het_hang_bien_thanh_thieu_du_lieu():
    d = _dai()
    d["het_hang"] = ""
    d.loc[(d["ngay"] == "2025-02-01") & (d["mat_hang"] == "B"), "het_hang"] = "x"
    rong, cb = loi.chuan_hoa_ban_hang(d)
    assert np.isnan(rong.loc["2025-02-01", "B"]) and rong.loc["2025-02-01", "A"] == 5
    assert any("hết hàng" in c for c in cb)


def test_du_bao_bo_qua_nan():
    y = chuoi_co_tet()
    y.iloc[::17] = np.nan
    kq = loi.du_bao_nhu_cau(y, 100)
    assert np.isfinite(kq["d_hat"]).all() and np.isfinite(kq["var"]).all()
    assert np.isfinite(kq["meta"]["wape_du_bao"])
    assert 0.05 < kq["mo_hinh"]["ty_le_thieu_du_lieu"] < 0.07


def test_kiem_dinh_theo_mua_mo_hinh_thang_cach_nam_ngoai_cung_ngay():
    y = chuoi_co_tet(so_ngay=1100, bat_dau="2022-01-01", bien_do=5.0)
    kd = loi.kiem_dinh_theo_mua(y)
    tet = kd[kd["mua"] == "Tết"]
    assert len(tet) >= 2                                           # Tết 2023 và 2024 có đủ lịch sử trước mốc
    # Tết đổi ngày dương lịch giữa các năm nên "năm ngoái cùng ngày" lệch đỉnh; mô hình căn theo âm lịch phải tốt hơn
    assert (tet["wape_dinh_mo_hinh"] < tet["wape_dinh_nam_ngoai"]).all()


def test_xu_huong_bat_duoc_chuoi_tang():
    ngay = pd.date_range("2024-01-01", periods=500)
    y = pd.Series(10 + 0.02 * np.arange(500) + np.random.default_rng(3).normal(0, 0.5, 500), index=ngay)
    co = loi.du_bao_nhu_cau(y, 120, xu_huong=True)
    khong = loi.du_bao_nhu_cau(y, 120, xu_huong=False)
    assert co["mo_hinh"]["do_doc"] > 0
    assert co["d_hat"][-7:].mean() > khong["d_hat"][-7:].mean()
