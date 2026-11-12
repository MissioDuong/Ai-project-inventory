# -*- coding: utf-8 -*-
"""Trợ lý AI: công cụ tính toán, vòng gọi công cụ (dùng client giả, không gọi mạng), thông báo lỗi."""
import json
from types import SimpleNamespace as NS

import pandas as pd
import pytest

from tinh_toan import nhieu_mat_hang as nm
from tro_ly_ai import tro_ly as tl


@pytest.fixture()
def boi_canh(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    ds = list(kh["mat_hang"])
    ton = pd.DataFrame({"mat_hang": ds, "ton_kho": [3] * len(ds), "han_con_lai": [20] * len(ds), "hang_dang_ve": [0] * len(ds)})
    bang, don, sc = nm.ke_hoach_hom_nay(kh, 5, ton, 1e7)
    return {"kh": kh, "bang": bang, "don": don, "suc_chua": sc, "ngay": pd.Timestamp(kh["ngay"][5]), "von": 1e7,
            "nguon_du_lieu": "mô phỏng"}


def test_cong_cu_danh_sach_di_cho_khop_ke_hoach(boi_canh):
    kq = tl.CongCu(boi_canh).danh_sach_di_cho()
    tong = sum(q * boi_canh["kh"]["info"].loc[i, "gia_von"] for qs, _ in boi_canh["don"].values() for i, q in qs.items())
    assert kq["can_di_cho"] and kq["tong_tien_can"] == round(tong)
    json.dumps(kq, ensure_ascii=False)                          # phải gửi được cho API


def test_cong_cu_tim_mat_hang_theo_ten_mot_phan(boi_canh):
    cc = tl.CongCu(boi_canh)
    assert cc.goi("tinh_trang_mat_hang", {"mat_hang": "mứt"})["mat_hang"] == "Mứt Tết (hộp)"
    assert "loi" in cc.goi("tinh_trang_mat_hang", {"mat_hang": "bánh"})        # mơ hồ: nhiều mặt hàng
    assert "loi" in cc.goi("khong_ton_tai", {})
    assert cc.goi("du_bao_nhu_cau", {"mat_hang": "trung thu", "so_ngay": 500})["so_ngay"] == 120


def _client_gia(cac_buoc):
    """Client giả: lần lượt trả về các message trong cac_buoc."""
    ghi = []

    def create(**kw):
        ghi.append(kw)
        return NS(choices=[NS(message=cac_buoc[len(ghi) - 1])])
    return NS(chat=NS(completions=NS(create=create))), ghi


def test_vong_goi_cong_cu(boi_canh):
    goi = NS(id="c1", type="function", function=NS(name="tinh_trang_mat_hang", arguments='{"mat_hang": "kẹo dừa"}'))
    client, ghi = _client_gia([NS(content=None, tool_calls=[goi]), NS(content="Kẹo dừa cần nhập.", tool_calls=None)])
    tra_loi, da_goi = tl.tra_loi(client, "mo-hinh-thu", [], "Kẹo dừa thế nào?", boi_canh)
    assert tra_loi == "Kẹo dừa cần nhập."
    assert da_goi[0][0] == "tinh_trang_mat_hang" and da_goi[0][2]["mat_hang"].startswith("Kẹo dừa")
    tin_cong_cu = [m for m in ghi[1]["messages"] if m["role"] == "tool"]   # kết quả công cụ được gửi lại cho mô hình
    assert tin_cong_cu and json.loads(tin_cong_cu[0]["content"])["mat_hang"].startswith("Kẹo dừa")
    assert ghi[0]["tools"] == tl.CongCu.DINH_NGHIA and ghi[0]["messages"][0]["role"] == "system"


def test_giai_thich_hom_nay_gui_du_lieu_tinh_san(boi_canh):
    client, ghi = _client_gia([NS(content="- Đi chợ đầu mối", tool_calls=None)])
    assert tl.giai_thich_hom_nay(client, "mo-hinh-thu", boi_canh) == "- Đi chợ đầu mối"
    assert "danh_sach_di_cho" in ghi[0]["messages"][1]["content"]


def test_loi_than_thien():
    class RateLimitError(Exception):
        pass
    assert "hết tín dụng" in tl.loi_than_thien(RateLimitError("Error code: 429 - insufficient_quota"))
    class AuthenticationError(Exception):
        pass
    assert "không hợp lệ" in tl.loi_than_thien(AuthenticationError("bad"))


def test_doc_cau_hinh_uu_tien_bien_moi_truong(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-thu")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-thu")
    assert tl.doc_cau_hinh() == ("sk-thu", "gpt-thu")


# ---------------- AI sửa dữ liệu ----------------
def _du_lieu(kh):
    ds = list(kh["mat_hang"])
    mh = nm.mat_hang_mac_dinh(ds)
    mh["ty_le_hu_hong_ngay"] *= 100
    mh["ty_le_giu_hang_nam"] *= 100
    return {"mh": mh, "nguon": nm.nguon_mac_dinh(mh["nguon_hang"]), "khu": nm.khu_mac_dinh(),
            "ton": pd.DataFrame({"mat_hang": ds, "ton_kho": [5] * len(ds), "han_con_lai": [20] * len(ds),
                                 "hang_dang_ve": [0] * len(ds)}), "von": 1e7}


def test_bo_sua_hop_le_va_khong_doi_ban_goc(ke_hoach_mo_phong):
    dl = _du_lieu(ke_hoach_mo_phong)
    b = tl.BoSua(dl)
    kq = b.sua_mat_hang("mứt", "gia_von", 50000)
    assert kq["da_sua"] and kq["cu"] == 45000 and kq["moi"] == 50000
    assert dl["mh"].set_index("mat_hang").loc["Mứt Tết (hộp)", "gia_von"] == 45000          # bản gốc giữ nguyên
    assert b.dl["mh"].set_index("mat_hang").loc["Mứt Tết (hộp)", "gia_von"] == 50000
    assert b.sua_ton_kho("kẹo dừa", "ton_kho", 120)["da_sua"]
    assert b.dat_von_moi_ngay(8e6)["moi"] == 8000000
    assert len(b.thay_doi) == 3


@pytest.mark.parametrize("ham, ts", [
    ("sua_mat_hang", {"mat_hang": "mứt", "truong": "gia_von", "gia_tri": -5}),            # ngoài khoảng
    ("sua_mat_hang", {"mat_hang": "bánh", "truong": "gia_von", "gia_tri": 5}),            # tên mơ hồ
    ("sua_mat_hang", {"mat_hang": "mứt", "truong": "khu_bao_quan", "gia_tri": "Kho ma"}), # khu không có
    ("sua_mat_hang", {"mat_hang": "mứt", "truong": "tuoi_khi_nhan_ngay", "gia_tri": 500}),  # vượt hạn dùng -> kiem_tra chặn
    ("sua_mat_hang", {"mat_hang": "mứt", "truong": "ten_la", "gia_tri": 1}),              # trường không cho sửa
    ("sua_khu_bao_quan", {"khu": "Tủ mát", "truong": "suc_chua_lit", "gia_tri": "nhiều"}),  # không phải số
])
def test_bo_sua_tu_choi_gia_tri_sai(ke_hoach_mo_phong, ham, ts):
    b = tl.BoSua(_du_lieu(ke_hoach_mo_phong))
    kq = getattr(b, ham)(**ts)
    assert "loi" in kq and not b.thay_doi


def test_tra_loi_co_sua_va_tinh_lai(boi_canh, ke_hoach_mo_phong):
    goi_sua = NS(id="s1", type="function", function=NS(name="sua_ton_kho",
                                                         arguments='{"mat_hang": "kẹo dừa", "truong": "ton_kho", "gia_tri": 999}'))
    goi_doc = NS(id="d1", type="function", function=NS(name="tinh_trang_mat_hang", arguments='{"mat_hang": "kẹo dừa"}'))
    client, ghi = _client_gia([NS(content=None, tool_calls=[goi_sua]), NS(content=None, tool_calls=[goi_doc]),
                               NS(content="Đã cập nhật.", tool_calls=None)])
    b = tl.BoSua(_du_lieu(ke_hoach_mo_phong))
    kh = ke_hoach_mo_phong

    def tinh_lai(dl):
        bang, don, sc = nm.ke_hoach_hom_nay(kh, 5, dl["ton"], dl["von"])
        return {**boi_canh, "bang": bang, "don": don, "suc_chua": sc}
    tra_loi, da_goi = tl.tra_loi(client, "m", [], "kẹo dừa còn 999 gói", boi_canh, bo_sua=b, tinh_lai=tinh_lai)
    assert tra_loi == "Đã cập nhật." and b.thay_doi[0]["moi"] == 999
    assert da_goi[1][2]["dang_co"] == 999                       # công cụ đọc thấy số liệu SAU khi sửa
    ten_cong_cu = {t["function"]["name"] for t in ghi[0]["tools"]}
    assert "sua_mat_hang" in ten_cong_cu and "dat_von_moi_ngay" in ten_cong_cu


def test_khong_cho_sua_thi_khong_co_cong_cu_ghi(boi_canh):
    client, ghi = _client_gia([NS(content="ok", tool_calls=None)])
    tl.tra_loi(client, "m", [], "hi", boi_canh)
    assert not any(t["function"]["name"].startswith("sua_") for t in ghi[0]["tools"])


def test_phan_tich_gui_so_lieu(boi_canh):
    client, ghi = _client_gia([NS(content="- Nhận xét", tool_calls=None)])
    assert tl.phan_tich(client, "m", "dự báo", {"tong": 123}, boi_canh) == "- Nhận xét"
    assert '"tong": 123' in ghi[0]["messages"][1]["content"]
