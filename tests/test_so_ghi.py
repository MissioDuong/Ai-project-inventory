# -*- coding: utf-8 -*-
"""Sổ kiểm kho (đo lượng bán từ số đếm) và dự báo khởi động (ước lượng ban đầu trộn với số đo)."""
import numpy as np
import pandas as pd
import pytest

from tinh_toan import loi, so_ghi
from tinh_toan import nhieu_mat_hang as nm


def _kk(rows):
    df = pd.DataFrame(rows, columns=["ngay", "mat_hang", "ton_cuoi_ngay", "nhap_them", "hu_hong", "het_hang"])
    kk, loi_ = so_ghi.chuan_hoa_kiem_kho(df)
    assert not loi_
    return kk


def test_suy_ra_ban_tu_so_dem():
    kk = _kk([("2026-11-10", "A", 50, 0, 0, 0), ("2026-11-11", "A", 42, 0, 0, 0), ("2026-11-12", "A", 60, 30, 2, 0)])
    dai, cb = so_ghi.suy_ra_ban(kk)
    assert dai["so_luong_ban"].tolist() == [8.0, 10.0]          # 50−42 ; 42+30−2−60
    assert not cb


def test_dem_cach_ngay_chia_deu():
    kk = _kk([("2026-11-10", "A", 100, 0, 0, 0), ("2026-11-13", "A", 70, 0, 0, 0)])
    dai, _ = so_ghi.suy_ra_ban(kk)
    assert len(dai) == 3 and np.allclose(dai["so_luong_ban"], 10.0) and (dai["khoang_ngay"] == 3).all()


def test_het_hang_la_thieu_du_lieu_va_dem_am_bi_bo():
    kk = _kk([("2026-11-10", "A", 20, 0, 0, 0), ("2026-11-11", "A", 0, 0, 0, "x"),
              ("2026-11-10", "B", 10, 0, 0, 0), ("2026-11-11", "B", 25, 0, 0, 0)])    # B: quên ghi hàng nhập
    dai, cb = so_ghi.suy_ra_ban(kk)
    assert dai["so_luong_ban"].isna().all()
    assert any("hết hàng" in c for c in cb) and any("quên ghi" in c for c in cb)


def test_cung_ngay_lan_moi_thay_lan_cu():
    kk = _kk([("2026-11-10", "A", 50, 0, 0, 0)])
    kk2, loi_ = so_ghi.cap_nhat_kiem_kho(kk, pd.DataFrame({"ngay": ["10/11/2026"], "mat_hang": ["A"], "ton_cuoi_ngay": [45]}))
    assert not loi_ and len(kk2) == 1 and kk2["ton_cuoi_ngay"].iloc[0] == 45


def test_kiem_kho_bao_loi_so_am_va_bo_dong_trong():
    df = pd.DataFrame({"ngay": ["2026-11-10", "2026-11-10"], "mat_hang": ["A", "B"], "ton_cuoi_ngay": [-1, None]})
    kk, loi_ = so_ghi.chuan_hoa_kiem_kho(df)
    assert loi_ and len(kk) == 1                               # B chưa đếm: bỏ qua, không phải lỗi


def test_uoc_luong_dien_mac_dinh_va_bao_loi():
    uoc, loi_ = so_ghi.chuan_hoa_uoc_luong(pd.DataFrame({"mat_hang": [" Kẹo ", "Bánh"], "ban_thuong": [8, 4],
                                                         "ban_nhieu_nhat": [None, 10]}))
    assert not loi_
    assert uoc.set_index("mat_hang").loc["Kẹo"].tolist() == [4.0, 8.0, 12.0]
    _, loi_ = so_ghi.chuan_hoa_uoc_luong(pd.DataFrame({"mat_hang": ["A", "A", "B"], "ban_it_nhat": [9, 1, 1],
                                                       "ban_thuong": [8, 2, None]}))
    assert len(loi_) == 3                                      # trùng tên, thiếu mức thường, ít nhất > thường


def test_bang_ban_hang_dung_o_hom_qua_va_bo_hang_khong_du_bao_duoc():
    kk = _kk([("2026-11-10", "A", 50, 0, 0, 0), ("2026-11-12", "A", 40, 0, 0, 0), ("2026-11-12", "C", 9, 0, 0, 0),
              ("2026-11-20", "A", 30, 0, 0, 0)])
    uoc, _ = so_ghi.chuan_hoa_uoc_luong(pd.DataFrame({"mat_hang": ["B", "A"], "ban_thuong": [3, 6]}))
    rong, cb = so_ghi.bang_ban_hang(kk, uoc, "2026-11-20")
    assert list(rong.columns) == ["B", "A"]                    # C: một lần đếm, không ước lượng → bỏ, có cảnh báo
    assert rong.index[-1] == pd.Timestamp("2026-11-19") and rong.index[0] == pd.Timestamp("2026-11-10")
    assert rong["A"].sum() == pytest.approx(10 + 10 * 7 / 8)   # 13→20: 10 đv chia 8 ngày, ngày 20 (hôm nay) chưa tính
    assert rong["B"].isna().all()
    assert any("C" in c for c in cb)


def test_chi_co_uoc_luong_thi_dung_dung_uoc_luong():
    y = pd.Series([np.nan], index=pd.DatetimeIndex(["2026-11-20"]), name="A")
    db = loi.du_bao_nhu_cau(y, 30, uoc_luong=(4, 8, 12))
    assert db["meta"]["che_do"] == "uoc_luong" and np.allclose(db["d_hat"], 8)
    assert db["ngay"][0] == pd.Timestamp("2026-11-21")
    assert np.allclose(db["var"], 8 * (1 + 3 / loi.TRONG_SO_UOC_LUONG))   # (12−4)/4 = 2 → var 4 < Poisson 8


def test_tron_uoc_luong_voi_so_do_va_bot_than_trong():
    rng = np.random.default_rng(0)
    idx = pd.date_range("2026-09-01", periods=40)
    it_ngay = pd.Series(np.r_[[np.nan] * 33, rng.poisson(5, 7)], index=idx, name="A")
    nhieu_ngay = pd.Series(np.r_[[np.nan] * 5, rng.poisson(5, 35)], index=idx, name="A")
    a = loi.du_bao_nhu_cau(it_ngay, 10, uoc_luong=(5, 10, 15))
    b = loi.du_bao_nhu_cau(nhieu_ngay, 10, uoc_luong=(5, 10, 15))
    x = np.nanmean(it_ngay)
    assert a["meta"]["che_do"] == "dang_hoc"
    assert a["d_hat"][0] == pytest.approx((7 * 10 + 7 * x) / 14)
    assert a["meta"]["trong_so_do"] == pytest.approx(0.5)
    assert abs(b["d_hat"][0] - np.nanmean(nhieu_ngay)) < abs(a["d_hat"][0] - x) + 1e-9      # nhiều số đo → gần số đo hơn
    assert b["meta"]["he_so_than_trong"] < a["meta"]["he_so_than_trong"]


def test_du_ngay_do_thi_chuyen_sang_mo_hinh_mua_vu():
    idx = pd.date_range("2026-01-01", periods=loi.NGAY_DAY_DU)
    y = pd.Series(np.full(loi.NGAY_DAY_DU, 6.0), index=idx, name="A")
    db = loi.du_bao_nhu_cau(y, 10, uoc_luong=(1, 2, 3))
    assert db["meta"]["khoi_dong"] is False and db["meta"]["che_do"] == "day_du"
    with pytest.raises(ValueError):
        loi.du_bao_nhu_cau(pd.Series([np.nan], index=idx[:1], name="B"), 10)


def test_ke_hoach_chay_voi_so_kiem_kho():
    kk = _kk([("2026-11-10", "A", 50, 0, 0, 0), ("2026-11-14", "A", 30, 0, 0, 0)])
    uoc, _ = so_ghi.chuan_hoa_uoc_luong(pd.DataFrame({"mat_hang": ["A", "B"], "ban_thuong": [6, 2]}))
    rong, _ = so_ghi.bang_ban_hang(kk, uoc, "2026-11-20")
    mh = nm.mat_hang_mac_dinh(list(rong.columns))
    kh = nm.ke_hoach(rong, mh, nm.nguon_mac_dinh(mh["nguon_hang"]), nm.khu_mac_dinh(), 60, uoc_luong=so_ghi.uoc_dict(uoc))
    for m in ("A", "B"):
        v = kh["mat_hang"][m]
        assert np.isfinite(v["rop"]).all() and np.isfinite(v["ss"]).all() and v["rop"][0] > v["ss"][0] > 0
        assert np.isfinite(v["eoq_tinh"]["rop"]) and np.isfinite(v["tb14"])
    assert kh["ngay"][0] == pd.Timestamp("2026-11-20")         # kế hoạch bắt đầu từ hôm nay
    bang, don, _ = nm.ke_hoach_hom_nay(kh, 0, pd.DataFrame({"mat_hang": ["A", "B"], "ton_kho": [0, 50], "han_con_lai": [30, 30],
                                                           "hang_dang_ve": [0, 0]}), 10_000_000)
    assert bang.set_index("mat_hang").loc["A", "nhap"] > 0       # hết hàng thì phải nhập


def test_ngay_cham_diem_dat():
    d, rop = np.full(30, 5.0), np.full(30, 20.0)
    assert loi.ngay_cham_diem_dat(d, rop, 15) == 0
    assert loi.ngay_cham_diem_dat(d, rop, 40) == 4             # 40 − 4×5 = 20
    assert loi.ngay_cham_diem_dat(d, rop, 1000) is None


def test_ghi_doc_so_va_thiet_lap(tmp_path):
    kk = _kk([("2026-11-10", "A", 50, 0, 0, 0), ("2026-11-11", "A", 0, 0, 0, 1)])
    uoc, _ = so_ghi.chuan_hoa_uoc_luong(pd.DataFrame({"mat_hang": ["A"], "ban_thuong": [6]}))
    so_ghi.ghi_so(str(tmp_path), kk=kk, uoc=uoc)
    kk2, uoc2 = so_ghi.doc_so(str(tmp_path))
    pd.testing.assert_frame_equal(kk2, kk)
    pd.testing.assert_frame_equal(uoc2, uoc)
    mh = nm.mat_hang_mac_dinh(["A"])
    so_ghi.ghi_thiet_lap(str(tmp_path), mh, nm.nguon_mac_dinh(mh["nguon_hang"]), nm.khu_mac_dinh())
    assert so_ghi.doc_thiet_lap(str(tmp_path))["mh"]["gia_von"].iloc[0] == mh["gia_von"].iloc[0]
    assert so_ghi.doc_so(str(tmp_path / "chua_co"))[0].empty
