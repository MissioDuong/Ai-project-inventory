# -*- coding: utf-8 -*-
"""Kiểm thử khói giao diện: mọi trang của app.py chạy không lỗi (dữ liệu mô phỏng và sổ kiểm kho);
các nút AI xử lý đúng khi chưa có API key.

Không gọi OpenAI thật: doc_cau_hinh bị thay để trả về "không có key". Sổ kiểm kho đọc/ghi trong thư mục tạm (EOQ_THU_MUC_SO).
"""
import os

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from tinh_toan import so_ghi
from giao_dien.cau_hinh import (BIEU_DO, DL_SO_GHI, DU_DOAN, HOM_NAY, MO_PHONG, NHAP_LIEU, THIET_LAP, THU_MUC, TRANG,
                                TRO_LY)
from tro_ly_ai import tro_ly as tl

APP = os.path.join(THU_MUC, "app.py")


@pytest.fixture(autouse=True)
def khong_co_key(monkeypatch, tmp_path):
    monkeypatch.setattr(tl, "doc_cau_hinh", lambda: (None, tl.MO_HINH_MAC_DINH))
    monkeypatch.setenv("EOQ_THU_MUC_SO", str(tmp_path))         # không bao giờ ghi vào du_lieu_cua_toi/ thật


def mo(trang, **trang_thai):
    at = AppTest.from_file(APP, default_timeout=300)
    at.session_state["trang"] = trang
    for k, v in trang_thai.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


@pytest.mark.parametrize("trang", TRANG)
def test_moi_trang_chay_khong_loi(trang):
    at = mo(trang)
    assert any('<div class="t1">' in m.value for m in at.markdown)      # có tiêu đề trang


def _canh_bao_thieu_key(at):
    assert not at.exception, [e.message for e in at.exception]
    assert any("Chưa có OpenAI API key" in w.value for w in at.warning)


def test_nut_ai_trang_hom_nay():
    at = mo(HOM_NAY)
    at.button(key="ai_giai_thich").click().run()
    _canh_bao_thieu_key(at)


def test_nut_ai_phan_tich_du_doan():
    at = mo(DU_DOAN)
    next(b for b in at.button if (b.key or "").startswith("pt_db_")).click().run()
    _canh_bao_thieu_key(at)


def test_nut_ai_phan_tich_bieu_do():
    at = mo(BIEU_DO)
    next(b for b in at.button if (b.key or "").startswith("pt_bd_")).click().run()
    _canh_bao_thieu_key(at)


def test_ai_sua_thong_so_trang_thiet_lap():
    at = mo(THIET_LAP)
    at.text_input(key="ai_dm_yc").input("vốn 8 triệu").run()
    at.button(key="ai_dm_bam").click().run()
    _canh_bao_thieu_key(at)


def test_chat_tro_ly():
    at = mo(TRO_LY)
    at.chat_input[0].set_value("Hôm nay mua gì?").run()
    _canh_bao_thieu_key(at)


def test_mo_phong_khong_rang_buoc():
    at = mo(MO_PHONG)
    at.toggle(key="mp_ap_rb").set_value(False).run()
    assert not at.exception


def test_trang_cu_khong_con_thi_ve_hom_nay():
    at = mo("📦  Mặt hàng & kho")                                 # tên trang của menu cũ còn trong phiên
    assert at.session_state["trang"] == HOM_NAY


# ---- chế độ sổ kiểm kho ----
def _ghi_so_mau(thu_muc):
    hom_nay = pd.Timestamp.today().normalize()
    ngay = [hom_nay - pd.Timedelta(days=i) for i in (6, 5, 3, 0)]
    kk = pd.DataFrame({"ngay": ngay * 2, "mat_hang": ["Kẹo dừa"] * 4 + ["Bánh pía (hộp)"] * 4,
                       "ton_cuoi_ngay": [80, 72, 55, 40, 20, 17, 30, 22], "nhap_them": [0, 0, 0, 0, 0, 0, 20, 0],
                       "hu_hong": [0] * 8, "het_hang": [0] * 8})
    uoc = pd.DataFrame({"mat_hang": ["Kẹo dừa", "Bánh pía (hộp)", "Mứt Tết (hộp)"], "ban_thuong": [8, 3, 2]})
    so_ghi.ghi_so(thu_muc, kk=so_ghi.chuan_hoa_kiem_kho(kk)[0], uoc=so_ghi.chuan_hoa_uoc_luong(uoc)[0])


@pytest.mark.parametrize("trang", [HOM_NAY, NHAP_LIEU, DU_DOAN, BIEU_DO, THIET_LAP, MO_PHONG])
def test_che_do_so_kiem_kho(trang, tmp_path):
    _ghi_so_mau(str(tmp_path))
    at = mo(trang, nguon_du_lieu=DL_SO_GHI)
    assert any('<div class="t1">' in m.value for m in at.markdown)
    if trang == HOM_NAY:                                         # tồn kho mặc định = số đếm gần nhất
        ton = at.session_state["ton_cur"].set_index("mat_hang")["ton_kho"]
        assert ton["Kẹo dừa"] == 40 and ton["Bánh pía (hộp)"] == 22


def test_phien_moi_tu_dung_so_kiem_kho_neu_da_co(tmp_path):
    assert mo(HOM_NAY).session_state["nguon_du_lieu"] != DL_SO_GHI     # thư mục trống → mô phỏng
    _ghi_so_mau(str(tmp_path))
    assert mo(HOM_NAY).session_state["nguon_du_lieu"] == DL_SO_GHI


def test_so_kiem_kho_trong_dan_toi_trang_nhap_lieu():
    at = mo(HOM_NAY, nguon_du_lieu=DL_SO_GHI)                   # chưa có sổ nào trong thư mục tạm
    assert any(b.key is None and "Nhập dữ liệu" in b.label for b in at.button)


def test_luu_thiet_lap_so_kiem_kho(tmp_path):
    _ghi_so_mau(str(tmp_path))
    at = mo(THIET_LAP, nguon_du_lieu=DL_SO_GHI)
    at.button(key="tl_luu").click().run()
    assert not at.exception
    assert set(so_ghi.doc_thiet_lap(str(tmp_path))) == {"mh", "nguon", "khu"}
