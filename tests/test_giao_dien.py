# -*- coding: utf-8 -*-
"""Kiểm thử khói giao diện: mọi trang của app.py chạy không lỗi; các nút AI xử lý đúng khi chưa có API key.

Không gọi OpenAI thật: doc_cau_hinh bị thay để trả về "không có key".
"""
import os

import pytest
from streamlit.testing.v1 import AppTest

from giao_dien.cau_hinh import TRANG, THU_MUC
from tro_ly_ai import tro_ly as tl

APP = os.path.join(THU_MUC, "app.py")


@pytest.fixture(autouse=True)
def khong_co_key(monkeypatch):
    monkeypatch.setattr(tl, "doc_cau_hinh", lambda: (None, tl.MO_HINH_MAC_DINH))


def mo(trang):
    at = AppTest.from_file(APP, default_timeout=300)
    at.session_state["trang"] = trang
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


@pytest.mark.parametrize("trang", TRANG)
def test_moi_trang_chay_khong_loi(trang):
    at = mo(trang)
    assert any(f'<div class="t1">' in m.value for m in at.markdown)      # có tiêu đề trang


def _canh_bao_thieu_key(at):
    assert not at.exception, [e.message for e in at.exception]
    assert any("Chưa có OpenAI API key" in w.value for w in at.warning)


def test_nut_ai_trang_hom_nay():
    at = mo(TRANG[0])
    at.button(key="ai_giai_thich").click().run()
    _canh_bao_thieu_key(at)


def test_nut_ai_phan_tich_du_bao():
    at = mo(TRANG[2])
    next(b for b in at.button if (b.key or "").startswith("pt_db_")).click().run()
    _canh_bao_thieu_key(at)


def test_ai_sua_thong_so_trang_mat_hang():
    at = mo(TRANG[1])
    at.text_input(key="ai_dm_yc").input("vốn 8 triệu").run()
    at.button(key="ai_dm_bam").click().run()
    _canh_bao_thieu_key(at)


def test_chat_tro_ly():
    at = mo(TRANG[5])
    at.chat_input[0].set_value("Hôm nay mua gì?").run()
    _canh_bao_thieu_key(at)


def test_mo_phong_khong_rang_buoc():
    at = mo(TRANG[3])
    at.toggle(key="mp_ap_rb").set_value(False).run()
    assert not at.exception
