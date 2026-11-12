# -*- coding: utf-8 -*-
"""Kiểm thử lõi một mặt hàng: đọc dữ liệu, dự báo, công thức tồn kho."""
import numpy as np
import pandas as pd
import pytest

from tinh_toan import loi
from conftest import chuoi_co_tet


def _dai(so_ngay=100):
    ngay = pd.date_range("2025-01-01", periods=so_ngay)
    return pd.DataFrame({"ngay": np.repeat(ngay.strftime("%d/%m/%Y"), 2),
                         "mat_hang": ["A", "B"] * so_ngay, "so_luong_ban": np.arange(2 * so_ngay) % 7})


def test_doc_dang_dai_va_dang_rong_cho_cung_ket_qua():
    dai = _dai()
    rong = dai.pivot(index="ngay", columns="mat_hang", values="so_luong_ban").reset_index()
    a, _ = loi.chuan_hoa_ban_hang(dai)
    b, _ = loi.chuan_hoa_ban_hang(rong)
    assert a.shape == (100, 2)
    pd.testing.assert_frame_equal(a.sort_index(axis=1), b.sort_index(axis=1), check_names=False)


def test_ngay_sai_va_so_am_bi_bao_loi():
    d = _dai()
    d.loc[3, "ngay"] = "không phải ngày"
    with pytest.raises(ValueError):
        loi.chuan_hoa_ban_hang(d)
    d = _dai()
    d.loc[3, "so_luong_ban"] = -1
    with pytest.raises(ValueError):
        loi.chuan_hoa_ban_hang(d)


def test_it_hon_60_ngay_bi_tu_choi():
    with pytest.raises(ValueError):
        loi.chuan_hoa_ban_hang(_dai(30))


def test_du_bao_khong_am_va_dung_do_dai():
    kq = loi.du_bao_nhu_cau(chuoi_co_tet(), 150)
    assert len(kq["d_hat"]) == 150 and len(kq["var"]) == 150
    assert (kq["d_hat"] > 0).all() and (kq["var"] >= kq["d_hat"] - 1e-9).all()


def test_he_so_tet_bat_duoc_dinh_mua_vu():
    mh = loi.hoc_mua_vu(chuoi_co_tet(bien_do=4.0))
    assert mh["he_so_tet"].max() > 2.5          # đỉnh thật gấp 5 lần, sau làm trơn vẫn phải rõ
    assert mh["so_mua_tet"] >= 2


def test_chinh_sach_rop_lon_hon_nhu_cau_trong_lead_time():
    d = np.full(200, 10.0)
    tp = pd.Series({"lead_time_ngay": 2, "do_lech_lead_time": 0.5, "muc_phuc_vu": 0.95, "ty_le_giu_hang_nam": 0.3,
                    "gia_von": 10000, "chi_phi_dat_hang": 70000, "han_dung_ngay": 90})
    cs = loi.chinh_sach(d, d.copy(), tp, 100)
    assert np.allclose(cs["rop"] - cs["ss"], 20.0)
    assert (cs["ss"] > 0).all() and (cs["q"] >= 1).all()
