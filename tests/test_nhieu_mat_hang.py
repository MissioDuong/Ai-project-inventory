# -*- coding: utf-8 -*-
"""Kiểm thử mô hình nhiều mặt hàng: hạn dùng, tồn khả dụng, nhập gộp, mô phỏng."""
import numpy as np
import pytest

from tinh_toan import nhieu_mat_hang as nm
from conftest import kich_ban

T = 120


def test_han_dung_theo_nhiet_do():
    assert nm.han_dung_hieu_dung(100, 2.0, 30, 30) == 100
    assert nm.han_dung_hieu_dung(100, 2.0, 40, 30) == 50          # nóng thêm 10°C, Q10 = 2: còn một nửa
    assert nm.han_dung_hieu_dung(100, 2.0, 0, 30) == 150          # lạnh hơn: kéo dài tối đa ×1,5


def test_vi_the_kha_dung_bo_phan_se_het_han():
    # 100 đv còn hạn 5 ngày, mỗi ngày bán 10 -> chỉ bán kịp 50; cộng 20 đang về
    vt, bo = nm.vi_the_kha_dung([(100, 5)], 20, np.full(30, 10.0), theta=0.0, L=1)
    assert vt == pytest.approx(70) and bo == pytest.approx(50)


def test_doc_du_lieu_thu_dung_ten_cot_chu_hoa(bo_thu):
    _, mh, _, kz = bo_thu
    assert mh.set_index("mat_hang").loc["Socola thanh (thanh 50g)", "nhiet_do_chuan_C"] == 20
    assert kz.set_index("khu_bao_quan").loc["Kho khô", "nhiet_do_C"] == 31
    assert nm.kiem_tra(*bo_thu[1:]) == []


def test_hang_han_dung_dai_khong_loi_du_bao(bo_thu):
    bh, mh, ng, kz = bo_thu
    kh = nm.ke_hoach(bh, mh, ng, kz, 120)                      # có bánh quy hạn 365 ngày
    for v in kh["mat_hang"].values():
        assert len(v["rop"]) == 120 and np.isfinite(v["rop"]).all()


@pytest.mark.parametrize("cs", list("ABCD"))
def test_can_bang_ton_kho(ke_hoach_mo_phong, cs):
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, T)
    ton0 = {m: 50.0 for m in nc}
    sim, _, _ = nm.mo_phong_cua_hang(kh, cs, nc, lts, von_moi_ngay=1e7, ton0=ton0)
    for m, g in sim.groupby("mat_hang"):
        lech = ton0[m] + g["hang_ve"].sum() - g["ban"].sum() - g["het_han"].sum() - g["hu_hong"].sum() - g["ton_kho"].iloc[-1]
        assert abs(lech) < 1e-6, f"{cs}/{m}: lệch {lech}"
        assert (g["ban"] <= g["nhu_cau"] + 1e-9).all() and (g["ton_kho"] >= -1e-9).all()


def test_D_khong_vuot_von_va_suc_chua(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, T)
    von = 5e6
    sim, sk, ch = nm.mo_phong_cua_hang(kh, "D", nc, lts, von_moi_ngay=von)
    c = nm.chi_phi_cua_hang(kh, sim, sk, ch, von)
    assert c["ngay_vuot_von"] == 0
    assert c["von_lon_nhat_mot_ngay"] <= von + 1e-6


def test_ke_hoach_hom_nay_tra_ve_du_lieu_hop_le(ke_hoach_mo_phong):
    import pandas as pd
    kh = ke_hoach_mo_phong
    ds = list(kh["mat_hang"])
    ton = pd.DataFrame({"mat_hang": ds, "ton_kho": [0] * len(ds), "han_con_lai": [30] * len(ds), "hang_dang_ve": [0] * len(ds)})
    bang, don, suc_chua = nm.ke_hoach_hom_nay(kh, 5, ton, 1e7)
    assert len(bang) == len(ds)
    assert (bang["nhap"] > 0).all()                             # hết sạch hàng thì mặt hàng nào cũng phải nhập
    assert sum(sum(q * kh["info"].loc[i, "gia_von"] for i, q in d[0].items()) for d in don.values()) <= 1e7 + 1e-6


@pytest.mark.parametrize("cs", ["A", "B", "C", "C+G", "D"])
def test_moi_chinh_sach_co_rang_buoc_khong_vuot(ke_hoach_mo_phong, cs):
    """P1 (A1): khi bật ràng buộc, mọi chính sách không vượt vốn mỗi ngày.
    P4 (B4): sức chứa được quyết định theo DỰ PHÓNG lúc hàng về, còn vi phạm đo theo chỗ THỰC; bán thấp hơn dự báo
    vẫn có thể làm tràn kho, nên cho phép tối đa 2 % số ngày."""
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, T)
    von = 4e6
    sim, sk, ch = nm.mo_phong_cua_hang(kh, cs, nc, lts, von_moi_ngay=von, rang_buoc=True)
    c = nm.chi_phi_cua_hang(kh, sim, sk, ch, von)
    assert c["ngay_vuot_von"] == 0
    assert c["ngay_vuot_suc_chua"] <= 0.02 * T


def test_cat_theo_rang_buoc_uu_tien_mat_hang_sap_het(ke_hoach_mo_phong):
    kh = ke_hoach_mo_phong
    a, b = list(kh["mat_hang"])[:2]
    don = {a: 100, b: 100}
    vi_tri = {a: 0.0, b: 1e4}                                  # a sắp hết, b còn rất nhiều
    gv = kh["info"].loc[[a, b], "gia_von"]
    von = 50 * gv[a]                                           # chỉ đủ tiền cho khoảng 50 đv của a
    moi, rb = nm.cat_theo_rang_buoc(kh, don, vi_tri, 0, None, von)
    assert rb == "vốn"
    assert moi.get(a, 0) > 0 and moi.get(b, 0) == 0
    assert sum(q * gv[i] for i, q in moi.items()) <= von + 1e-6


def test_phan_bo_chi_phi_chuyen_khop_tong(ke_hoach_mo_phong):
    """P1 (B1): chi phí chuyến chia cho từng mặt hàng phải cộng lại đúng bằng tổng chi phí chuyến."""
    kh = ke_hoach_mo_phong
    nc, lts = kich_ban(kh, T)
    sim, sk, ch = nm.mo_phong_cua_hang(kh, "C", nc, lts)
    c = nm.chi_phi_cua_hang(kh, sim, sk, ch)
    assert sim["phi_chuyen"].sum() == pytest.approx(c["chi_phi_chuyen"])
    assert nm.chi_phi_theo_mat_hang(kh, sim)["tong"].sum() == pytest.approx(c["tong"])
