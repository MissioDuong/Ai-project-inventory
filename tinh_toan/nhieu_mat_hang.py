# -*- coding: utf-8 -*-
"""
Mô hình NHIỀU MẶT HÀNG THỰC PHẨM: hạn dùng, hư hỏng, điều kiện bảo quản, nhập gộp theo nguồn hàng,
ràng buộc vốn và sức chứa từng khu bảo quản. Dùng chung lõi dự báo và công thức tồn kho trong loi.py.

CÁC THÀNH PHẦN (xem tai_lieu/NGHIEN_CUU_HANG_THUC_PHAM.md để biết cơ sở tài liệu):
  1. Hạn dùng hiệu dụng theo nhiệt độ bảo quản (quy tắc Q10):
       hạn_dùng_thực = hạn_dùng_in_trên_bao_bì × Q10^((T_chuẩn − T_khu)/10), chặn trong [×0,3; ×1,5]
       (T_chuẩn: nhiệt độ mà hạn in trên bao bì áp dụng; để nóng hơn thì hạn rút ngắn, lạnh hơn kéo dài có giới hạn)
  2. Hư hỏng / hao hụt mỗi ngày với tỷ lệ θ (ẩm, mốc, móp, chuột...), kiểu suy giảm mũ của Ghare & Schrader (1963).
     Chi phí giữ hàng hiệu dụng dùng trong EOQ: H = giá_vốn × (lãi_vốn + 365·θ) + 365 × chi_phí_bảo_quản × thể_tích.
  3. Vị thế tồn kho "khả dụng" (ý tưởng EWA của Broekmeulen & van Donselaar, 2009): chỉ tính phần hàng dự kiến
     bán được trước khi hết hạn và còn lại sau hao hụt trong thời gian chờ hàng, cộng hàng đang về.
  4. Nhập gộp theo nguồn hàng, chính sách can-order (Balintfy, 1964):
       - Có mặt hàng chạm ROP (mức PHẢI đặt) -> đi một chuyến tới nguồn hàng đó.
       - Trong chuyến, mọi mặt hàng cùng nguồn có vị thế <= mức CÓ THỂ đặt cũng được nhập luôn.
       - Mỗi mặt hàng nhập đủ bán T* ngày (chu kỳ chung, công thức EOQ cho nhiều mặt hàng chung chi phí chuyến),
         không quá 60% hạn dùng thực, làm tròn theo quy cách.
  5. Ràng buộc vốn mỗi ngày và sức chứa từng khu: tìm số ngày đủ bán τ lớn nhất sao cho mọi ràng buộc thoả mãn
     (cùng tinh thần nhân tử Lagrange cho EOQ nhiều mặt hàng có ràng buộc tài nguyên).
  6. Mô phỏng cả cửa hàng theo ngày: hàng về -> loại hàng hết hạn -> hao hụt -> bán FIFO -> quyết định đặt hàng.
"""
import math

import numpy as np
import pandas as pd

from . import loi

KEO_DAI_TOI_DA = 1.5           # bảo quản lạnh hơn khuyến nghị kéo dài hạn dùng tối đa 1,5 lần
RUT_NGAN_TOI_DA = 0.3
CHU_KY_TOI_DA = 60             # chu kỳ nhập gộp tối đa (ngày)
DU_BAO_THEM = 200              # số ngày dự báo thêm sau khung kế hoạch

COT_MAT_HANG = ["mat_hang", "gia_von", "gia_ban", "han_dung_ngay", "tuoi_khi_nhan_ngay", "ty_le_hu_hong_ngay", "q10", "nhiet_do_chuan_C", "khu_bao_quan",
                "the_tich_lit", "nguon_hang", "quy_cach", "ty_le_giu_hang_nam", "muc_phuc_vu", "chi_phi_dong"]
COT_NGUON = ["nguon_hang", "chi_phi_chuyen", "lead_time_ngay", "do_lech_lead_time"]
COT_KHU = ["khu_bao_quan", "nhiet_do_C", "suc_chua_lit", "chi_phi_bao_quan_lit_ngay", "chi_phi_co_dinh_ngay"]

# Giá trị minh hoạ cho bộ dữ liệu mô phỏng:
# (giá vốn, giá bán, hạn dùng, TUỔI KHI NHẬN (ngày hạn đã trôi qua lúc nhận), hư hỏng/ngày, Q10,
#  nhiệt độ chuẩn của hạn dùng, khu, thể tích lít/đv, nguồn hàng, quy cách)
_MH = {
    "Kẹo dừa Bến Tre (gói 200g)": (12000, 18000, 180, 30, 0.0001, 2.0, 30, "Kho khô", 0.30, "Chợ đầu mối", 10),
    "Bánh pía (hộp)": (28000, 40000, 30, 3, 0.001, 2.5, 25, "Tủ mát", 0.50, "Lò bánh pía", 1),
    "Mứt Tết (hộp)": (45000, 70000, 120, 20, 0.0003, 2.0, 30, "Kho khô", 0.80, "Chợ đầu mối", 1),
    "Bánh trung thu (cái)": (60000, 95000, 60, 5, 0.0005, 2.5, 25, "Tủ mát", 0.40, "Nhà phân phối bánh trung thu", 1),
    "Bánh quy / bánh gạo (gói)": (8000, 12000, 240, 40, 0.00005, 2.0, 30, "Kho khô", 0.40, "Chợ đầu mối", 10),
    "Kẹo lạc / kẹo mè xửng": (10000, 15000, 90, 15, 0.0003, 2.0, 30, "Kho khô", 0.20, "Chợ đầu mối", 10),
}
_MH_KHAC = (10000, 15000, 90, 10, 0.0003, 2.0, 30, "Kho khô", 0.50, "Chợ đầu mối", 1)
_NGUON = {"Chợ đầu mối": (60000, 1.0, 0.5), "Lò bánh pía": (30000, 2.0, 0.7),
          "Nhà phân phối bánh trung thu": (40000, 3.0, 1.0)}
_NGUON_KHAC = (60000, 2.0, 0.7)
# (khu, nhiệt độ, sức chứa lít, chi phí BIÊN đ/lít/ngày, chi phí CỐ ĐỊNH đ/ngày: tiền điện chạy tủ dù đầy hay vơi)
_KHU = [("Kho khô", 30.0, 500.0, 0.0, 0.0), ("Tủ mát", 12.0, 150.0, 2.0, 8000.0), ("Tủ lạnh", 4.0, 60.0, 4.0, 10000.0)]


# ----------------------------------------------------------------------------
# 1. THAM SỐ MẶC ĐỊNH, KIỂM TRA, CHUẨN BỊ
# ----------------------------------------------------------------------------
def mat_hang_mac_dinh(ds):
    rows = []
    for m in ds:
        gv, gb, hd, tu, th, q10, tc, khu, tt, ng, qc = _MH.get(m, _MH_KHAC)
        rows.append([m, gv, gb, hd, tu, th, q10, tc, khu, tt, ng, qc, 0.25, 0.95, 5000])
    return pd.DataFrame(rows, columns=COT_MAT_HANG)


def nguon_mac_dinh(ds_nguon):
    return pd.DataFrame([[n, *_NGUON.get(n, _NGUON_KHAC)] for n in dict.fromkeys(ds_nguon)], columns=COT_NGUON)


def khu_mac_dinh():
    return pd.DataFrame(_KHU, columns=COT_KHU)


def bo_sung_cot_khu(khu):
    """File khu cũ (trước P5) chưa có chi phí cố định: coi là 0."""
    if "chi_phi_co_dinh_ngay" not in khu.columns:
        khu = khu.copy()
        khu["chi_phi_co_dinh_ngay"] = 0.0
    return khu


def bo_sung_cot(mh):
    """File danh mục cũ (trước P4) chưa có cột tuổi khi nhận: coi như hàng mới (0 ngày)."""
    if "tuoi_khi_nhan_ngay" not in mh.columns:
        mh = mh.copy()
        mh.insert(mh.columns.get_loc("han_dung_ngay") + 1, "tuoi_khi_nhan_ngay", 0)
    return mh


def kiem_tra(mh, nguon, khu):
    mh, khu = bo_sung_cot(mh), bo_sung_cot_khu(khu)
    loi_ = []
    if mh[COT_MAT_HANG].isna().any().any():
        loi_.append("Bảng mặt hàng còn ô trống.")
        return loi_
    thieu_nguon = sorted(set(mh["nguon_hang"]) - set(nguon["nguon_hang"]))
    if thieu_nguon:
        loi_.append(f"Nguồn hàng {thieu_nguon} chưa có trong bảng nguồn hàng.")
    thieu_khu = sorted(set(mh["khu_bao_quan"]) - set(khu["khu_bao_quan"]))
    if thieu_khu:
        loi_.append(f"Khu bảo quản {thieu_khu} chưa có trong bảng khu bảo quản.")
    for _, r in mh.iterrows():
        m = r["mat_hang"]
        if r["gia_von"] <= 0 or r["gia_ban"] <= 0:
            loi_.append(f"{m}: giá vốn và giá bán phải lớn hơn 0.")
        if r["han_dung_ngay"] < 3:
            loi_.append(f"{m}: hạn dùng phải từ 3 ngày trở lên.")
        if not 0 <= r["tuoi_khi_nhan_ngay"] <= r["han_dung_ngay"] - 3:
            loi_.append(f"{m}: tuổi khi nhận phải từ 0 đến (hạn dùng − 3) ngày.")
        if not 0 <= r["ty_le_hu_hong_ngay"] < 0.2:
            loi_.append(f"{m}: tỷ lệ hư hỏng mỗi ngày phải trong khoảng 0 đến dưới 0,2 (20%).")
        if r["q10"] < 1:
            loi_.append(f"{m}: hệ số Q10 phải từ 1 trở lên.")
        if r["the_tich_lit"] <= 0 or r["quy_cach"] < 1:
            loi_.append(f"{m}: thể tích phải > 0 và quy cách >= 1.")
        if r["ty_le_giu_hang_nam"] < 0 or not 0.5 <= r["muc_phuc_vu"] < 1:
            loi_.append(f"{m}: lãi vốn không được âm, mức phục vụ trong khoảng 0,5 đến dưới 1.")
    for _, r in nguon.iterrows():
        if r[COT_NGUON[1:]].isna().any() or r["chi_phi_chuyen"] < 0 or r["lead_time_ngay"] < 1 or r["do_lech_lead_time"] < 0:
            loi_.append(f"Nguồn '{r['nguon_hang']}': chi phí chuyến không âm, giao hàng từ 1 ngày, độ lệch không âm.")
    for _, r in khu.iterrows():
        if r[COT_KHU[1:]].isna().any() or r["suc_chua_lit"] < 0 or r["chi_phi_bao_quan_lit_ngay"] < 0 \
                or r["chi_phi_co_dinh_ngay"] < 0:
            loi_.append(f"Khu '{r['khu_bao_quan']}': sức chứa và chi phí bảo quản không được âm (sức chứa 0 = không giới hạn).")
    return loi_


def han_dung_hieu_dung(han_dung, q10, nhiet_do, nhiet_do_chuan=30.0):
    he_so = np.clip(np.power(np.asarray(q10, float), (np.asarray(nhiet_do_chuan, float) - np.asarray(nhiet_do, float)) / 10.0), RUT_NGAN_TOI_DA, KEO_DAI_TOI_DA)
    return np.maximum(3, np.floor(np.asarray(han_dung, float) * he_so)).astype(int)


def chuan_bi(mh, nguon, khu):
    """Ghép 3 bảng và tính các đại lượng dẫn xuất cho từng mặt hàng.
    P4: han_con_khi_nhan = (hạn in − tuổi khi nhận) × hệ số nhiệt độ (C1); θ hiệu dụng = θ / hệ số nhiệt độ (C2)."""
    m = bo_sung_cot(mh).merge(nguon, on="nguon_hang", how="left").merge(bo_sung_cot_khu(khu), on="khu_bao_quan", how="left")
    m["he_so_nhiet"] = np.clip(np.power(m["q10"].astype(float), (m["nhiet_do_chuan_C"] - m["nhiet_do_C"]) / 10.0),
                               RUT_NGAN_TOI_DA, KEO_DAI_TOI_DA)
    m["han_dung_thuc"] = han_dung_hieu_dung(m["han_dung_ngay"], m["q10"], m["nhiet_do_C"], m["nhiet_do_chuan_C"])
    m["han_con_khi_nhan"] = np.maximum(3, np.floor((m["han_dung_ngay"] - m["tuoi_khi_nhan_ngay"]) * m["he_so_nhiet"])).astype(int)
    m["theta_goc"] = m["ty_le_hu_hong_ngay"]
    m["ty_le_hu_hong_ngay"] = np.minimum(0.199, m["theta_goc"] / m["he_so_nhiet"])
    m["L"] = np.maximum(1, np.round(m["lead_time_ngay"])).astype(int)
    m["giu_ngay"] = m["gia_von"] * m["ty_le_giu_hang_nam"] / 365 + m["chi_phi_bao_quan_lit_ngay"] * m["the_tich_lit"]
    m["hu_hong_ngay"] = m["gia_von"] * m["ty_le_hu_hong_ngay"]
    # tỷ lệ giữ hàng/năm hiệu dụng: lãi vốn + hư hỏng + bảo quản (xấp xỉ EOQ cho hàng suy giảm: H + θ·c)
    m["ty_le_giu_hieu_dung"] = (m["ty_le_giu_hang_nam"] + 365 * m["ty_le_hu_hong_ngay"] +
                                365 * m["chi_phi_bao_quan_lit_ngay"] * m["the_tich_lit"] / m["gia_von"])
    return m.set_index("mat_hang")


def _tp(r, co_dien=False):
    """Bộ tham số kiểu loi.py cho một mặt hàng (co_dien=True: bỏ hư hỏng, bảo quản, hạn dùng thực)."""
    return pd.Series({"lead_time_ngay": r["lead_time_ngay"], "do_lech_lead_time": r["do_lech_lead_time"],
                      "muc_phuc_vu": r["muc_phuc_vu"], "gia_von": r["gia_von"], "gia_ban": r["gia_ban"],
                      "ty_le_giu_hang_nam": r["ty_le_giu_hang_nam"] if co_dien else r["ty_le_giu_hieu_dung"],
                      "chi_phi_dat_hang": r["chi_phi_chuyen"] + r["chi_phi_dong"],
                      "han_dung_ngay": r["han_dung_ngay"] if co_dien else r["han_con_khi_nhan"]})


def lam_tron(q, quy_cach):
    return 0 if q <= 1e-9 else int(math.ceil(q / quy_cach - 1e-9) * quy_cach)


# ----------------------------------------------------------------------------
# 2. KẾ HOẠCH: dự báo + SS, ROP, Q theo ngày cho từng mặt hàng
# ----------------------------------------------------------------------------
def du_bao_tat_ca(ban_hang, so_ngay, xu_huong=False):
    return {m: loi.du_bao_nhu_cau(ban_hang[m], so_ngay + DU_BAO_THEM, xu_huong) for m in ban_hang.columns}


def ke_hoach(ban_hang, mh, nguon, khu, so_ngay, du_bao=None, xu_huong=False):
    du_bao = du_bao or du_bao_tat_ca(ban_hang, so_ngay, xu_huong)
    info = chuan_bi(mh, nguon, khu)
    kq = {}
    for m in mh["mat_hang"]:
        r = info.loc[m]
        db = du_bao[m]
        can = so_ngay + max(loi.can_them_ngay(_tp(r)), int(r["L"]) + CHU_KY_TOI_DA + 2, int(r["han_dung_thuc"]) + 2)
        if len(db["d_hat"]) < can:                       # hàng hạn dùng dài cần dự báo xa hơn
            db = loi.du_bao_nhu_cau(ban_hang[m], can, xu_huong)
        cs = loi.chinh_sach(db["d_hat"], db["var"], _tp(r), so_ngay)
        b = loi.chinh_sach_eoq_tinh(ban_hang[m].values, _tp(r, co_dien=True))
        kq[m] = {**db, **cs, "q": np.array([lam_tron(x, r["quy_cach"]) for x in cs["q"]], float),
                 "cs": np.r_[0.0, np.cumsum(db["d_hat"])], "eoq_tinh": b,
                 "tb14": float(np.nanmean(ban_hang[m].values[-14:]))}
    return {"info": info, "mat_hang": kq, "so_ngay": so_ngay,
            "ngay": next(iter(kq.values()))["ngay"][:so_ngay], "khu": bo_sung_cot_khu(khu).set_index("khu_bao_quan")}


def _nc(v, t, a, b):
    """Tổng nhu cầu dự báo các ngày t+1+a .. t+b (tính từ ngày quyết định t)."""
    cs = v["cs"]
    hi = min(t + 1 + b, len(cs) - 1)
    lo = min(t + 1 + a, hi)
    return cs[hi] - cs[lo]


# ----------------------------------------------------------------------------
# 3. VỊ THẾ KHẢ DỤNG (bỏ phần hàng sẽ hết hạn trước khi bán được, trừ hao hụt)
# ----------------------------------------------------------------------------
def vi_the_kha_dung(cac_lo, hang_ve, d_tuong_lai, theta, L):
    """cac_lo: [(số lượng, số ngày còn hạn)] theo thứ tự bán (FIFO); hang_ve: tổng hàng đang về.
    Trả về (vị thế khả dụng, số lượng dự kiến hết hạn trước khi bán được)."""
    cum = np.cumsum(d_tuong_lai) if len(d_tuong_lai) else np.zeros(1)
    da_dung = dung = bo = 0.0
    for sl, con in cac_lo:
        k = int(min(max(con, 0), len(cum)))
        ban_duoc = min(sl, max(0.0, (cum[k - 1] if k > 0 else 0.0) - da_dung))
        da_dung += ban_duoc
        dung += ban_duoc
        bo += sl - ban_duoc
    return dung * (1 - theta) ** L + hang_ve, bo


# ----------------------------------------------------------------------------
# 4. NHẬP GỘP (can-order) CÓ RÀNG BUỘC VỐN VÀ SỨC CHỨA
# ----------------------------------------------------------------------------
HE_SO_CAN_ORDER = 0.5     # mức "có thể đặt" = ROP + nhu cầu (HE_SO_CAN_ORDER × T*) ngày; P5 dò lưới để chọn
DUNG_HE_SO_BOI = True     # P5 (B2): mặt hàng bán chậm / rẻ giữ được nhập đủ k_i·T* ngày


def chu_ky_chung(kh, ds, t, tra_k=False):
    """Chu kỳ chung T* (ngày) của nhóm mặt hàng cùng nguồn hàng, kèm hệ số bội k_i (heuristic kiểu Silver, 1976):
    mặt hàng có s_i/(D_i·H_i) nhỏ nhất (bán nhanh, đắt giữ) có k = 1; mặt hàng khác
    k_i = round( sqrt( s_i/(D_i·H_i) · D_1·H_1/(S + s_1) ) ) ≥ 1; rồi T* = 365·sqrt(2·(S + Σ s_i/k_i) / Σ k_i·D_i·H_i).
    Không dùng hệ số bội (DUNG_HE_SO_BOI = False) thì mọi k_i = 1: T* = 365·sqrt(2·(S + Σs) / Σ D·H)."""
    info, mh = kh["info"], kh["mat_hang"]
    S = float(info.loc[ds[0], "chi_phi_chuyen"])
    s_i = {i: float(info.loc[i, "chi_phi_dong"]) for i in ds}
    DH = {i: max(365.0 * _nc(mh[i], t, 0, 30) / 30.0 * info.loc[i, "gia_von"] * info.loc[i, "ty_le_giu_hieu_dung"], 1e-9)
          for i in ds}
    k = {i: 1 for i in ds}
    if DUNG_HE_SO_BOI and len(ds) > 1:
        dau = min(ds, key=lambda i: s_i[i] / DH[i])
        for i in ds:
            if i != dau:
                k[i] = max(1, int(round(math.sqrt(s_i[i] / DH[i] * DH[dau] / (S + s_i[dau])))))
    T = 365.0 * math.sqrt(2.0 * (S + sum(s_i[i] / k[i] for i in ds)) / sum(k[i] * DH[i] for i in ds))
    T = int(np.clip(round(T), 1, CHU_KY_TOI_DA))
    return (T, k) if tra_k else T


def muc_khan_cap(kh, ds, t, vi_the):
    """Số ngày đủ bán nhỏ nhất trong nhóm (dùng để xếp thứ tự phân bổ vốn giữa các nguồn hàng, P5 B5)."""
    mh = kh["mat_hang"]
    return min(vi_the[i] / max(_nc(mh[i], t, 0, 7) / 7.0, 1e-6) for i in ds)


def ban_truoc_khi_ve(v, t, L, z=1.0):
    """Lượng bán THẬN TRỌNG trước khi đơn đặt cuối ngày t về (đầu ngày t+L, tức bán được L−1 ngày):
    kỳ vọng − z·độ lệch chuẩn, không âm. Dùng để dự phóng chỗ trống lúc hàng về (P4, B4)."""
    if L <= 1:
        return 0.0
    hi = min(t + L, len(v["d_hat"]))
    mu = float(np.sum(v["d_hat"][t + 1:hi]))
    sd = float(np.sqrt(np.sum(v["var"][t + 1:hi])))
    return max(0.0, mu - z * sd)


def vi_pham_rang_buoc(kh, qs, dung_khu, von_con):
    """Trả về tên ràng buộc bị vi phạm ('vốn' / 'chỗ (khu)') hoặc None. dung_khu=None: không kiểm tra sức chứa."""
    info, khu = kh["info"], kh["khu"]
    if sum(q * info.loc[i, "gia_von"] for i, q in qs.items()) > von_con + 1e-6:
        return "vốn"
    if dung_khu is None:
        return None
    for z in khu.index:
        cap = float(khu.loc[z, "suc_chua_lit"])
        them = sum(q * info.loc[i, "the_tich_lit"] for i, q in qs.items() if info.loc[i, "khu_bao_quan"] == z)
        if cap > 0 and them > 0 and dung_khu.get(z, 0.0) + them > cap + 1e-6:
            return f"chỗ ({z})"
    return None


def cat_theo_rang_buoc(kh, don, vi_tri, t, dung_khu, von_con):
    """Cắt bớt đơn hàng của các chính sách đặt riêng (A, B, C) cho vừa vốn và sức chứa.
    Ưu tiên mặt hàng có số ngày đủ bán thấp nhất: tìm τ lớn nhất sao cho mỗi mặt hàng được nhập tới mức đủ bán
    τ ngày (không quá đơn gốc) mà vẫn thoả ràng buộc. Trả về (đơn mới, tên ràng buộc đã chặn hoặc None)."""
    if not don or vi_pham_rang_buoc(kh, don, dung_khu, von_con) is None:
        return don, None
    info, mh = kh["info"], kh["mat_hang"]
    d = {i: max(_nc(mh[i], t, 0, 30) / 30.0, 1e-6) for i in don}

    def thu(tau):
        return {i: min(q, lam_tron(max(0.0, tau * d[i] - vi_tri[i]), info.loc[i, "quy_cach"])) for i, q in don.items()}

    lo, hi = 0.0, max((vi_tri[i] + q) / d[i] for i, q in don.items())
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if vi_pham_rang_buoc(kh, thu(mid), dung_khu, von_con) is None else (lo, mid)
    moi = {i: q for i, q in thu(lo).items() if q > 0}
    return moi, vi_pham_rang_buoc(kh, don, dung_khu, von_con)


def dat_hang_gop(kh, ds, t, vi_the, dung_khu, von_con, bat_buoc_di=False):
    """Quyết định một chuyến cho nhóm `ds` (cùng nguồn hàng) tại ngày t.
    vi_the: {mặt hàng: vị thế}; dung_khu: {khu: lít đang dùng (tồn + đang về)}, None = bỏ qua sức chứa;
    von_con: vốn còn lại (inf = bỏ qua vốn). Trả về ({mặt hàng: số lượng}, thông tin)."""
    info, mh = kh["info"], kh["mat_hang"]
    phai = [i for i in ds if vi_the[i] <= mh[i]["rop"][t]]
    if not phai and not bat_buoc_di:
        return {}, None
    L = int(info.loc[ds[0], "L"])
    T, k = chu_ky_chung(kh, ds, t, tra_k=True)
    phu = {i: max(1, min(k[i] * T, CHU_KY_TOI_DA, int(0.6 * info.loc[i, "han_con_khi_nhan"]) - L)) for i in ds}
    co_the = [i for i in ds if vi_the[i] <= mh[i]["rop"][t] + _nc(mh[i], t, L, L + math.ceil(HE_SO_CAN_ORDER * T))]

    def sl(i, tau):
        muc_tieu = _nc(mh[i], t, 0, L + min(tau, phu[i])) + mh[i]["ss"][t]
        return lam_tron(max(0.0, muc_tieu - vi_the[i]), info.loc[i, "quy_cach"])

    def vi_pham(qs):
        return vi_pham_rang_buoc(kh, qs, dung_khu, von_con)

    def thu(tau):
        return {i: sl(i, tau) for i in co_the}

    T_max = max(phu[i] for i in co_the)                   # mặt hàng có k_i > 1 được đủ bán tới k_i·T*
    rang_buoc = vi_pham(thu(T_max))
    if rang_buoc is None:
        tau, qs = T_max, thu(T_max)
    elif vi_pham(thu(0)) is None:
        lo, hi = 0, T_max                                # τ lớn nhất còn thoả ràng buộc
        while lo < hi:
            mid = (lo + hi + 1) // 2
            lo, hi = (mid, hi) if vi_pham(thu(mid)) is None else (lo, mid - 1)
        tau, qs = lo, thu(lo)
    else:                                                # không đủ cả mức tối thiểu: chỉ nhập hàng phải đặt, co lại
        tau, qs = 0, {i: sl(i, 0) for i in phai}
        for _ in range(60):
            if vi_pham(qs) is None:
                break
            qs = {i: max(0, q - info.loc[i, "quy_cach"]) for i, q in qs.items()}
        rang_buoc = "thiếu " + (rang_buoc or "")
    qs = {i: q for i, q in qs.items() if q > 0}
    return qs, {"chu_ky": T, "so_ngay_du_ban": tau, "rang_buoc": rang_buoc, "phai_dat": phai, "co_the_dat": co_the,
                "he_so_boi": {i: k[i] for i in qs}}


# ----------------------------------------------------------------------------
# 5. KHUYẾN NGHỊ HÔM NAY CHO CẢ CỬA HÀNG
# ----------------------------------------------------------------------------
def gom_lo(ton, lo_them=None):
    """Gom các lô hàng của từng mặt hàng (P6, E2).
    ton: [mat_hang, ton_kho, han_con_lai, hang_dang_ve] (mỗi mặt hàng một dòng = lô chính);
    lo_them: [mat_hang, so_luong, han_con_lai] (tuỳ chọn, các lô khác có hạn khác nhau).
    Trả về (bảng ton với ton_kho = tổng các lô, {mặt hàng: [(số lượng, hạn còn), ...] xếp hạn ngắn trước})."""
    ton = ton.copy()
    lo = {r["mat_hang"]: [(float(r["ton_kho"]), float(r["han_con_lai"]))] if r["ton_kho"] > 0 else []
          for _, r in ton.iterrows()}
    if lo_them is not None and len(lo_them):
        for _, r in lo_them.dropna(subset=["mat_hang"]).iterrows():
            if r["mat_hang"] in lo and float(r.get("so_luong", 0) or 0) > 0:
                lo[r["mat_hang"]].append((float(r["so_luong"]), float(r.get("han_con_lai", 0) or 0)))
    lo = {m: sorted(x, key=lambda a: a[1]) for m, x in lo.items()}
    ton["ton_kho"] = ton["mat_hang"].map(lambda m: sum(a[0] for a in lo[m]))
    return ton, lo


def ke_hoach_hom_nay(kh, k, ton, von, di_cho=(), lo_them=None):
    """ton: DataFrame [mat_hang, ton_kho, han_con_lai, hang_dang_ve]; lo_them: các lô khác [mat_hang, so_luong, han_con_lai];
    di_cho: các nguồn hàng chắc chắn đi hôm nay. Quy ước thời gian: kế hoạch cho đầu ngày k dùng điểm đặt hàng của
    cuối ngày k−1 (ngày 0 dùng ngày 0). Trả về (bảng từng mặt hàng, {nguồn: (đơn hàng, thông tin)}, bảng sức chứa)."""
    info, mh, khu = kh["info"], kh["mat_hang"], kh["khu"]
    t = k - 1                                            # quyết định đầu ngày k = cuối ngày k-1
    ton, lo = gom_lo(ton, lo_them)
    tdf = ton.set_index("mat_hang")
    vt, bo, dong = {}, {}, []
    for i in tdf.index:
        r, v = tdf.loc[i], mh[i]
        d_tl = v["d_hat"][k:k + int(max([a[1] for a in lo[i]] + [info.loc[i, "han_con_khi_nhan"]])) + 1]
        vt_e, bo[i] = vi_the_kha_dung(lo[i], float(r["hang_dang_ve"]),
                                      d_tl, float(info.loc[i, "ty_le_hu_hong_ngay"]), int(info.loc[i, "L"]))
        # P4: mặc định quyết định theo tồn + đang về; phần "có thể hết hạn" (bo) luôn được tính để cảnh báo
        vt[i] = vt_e if DUNG_TON_KHA_DUNG else float(r["ton_kho"]) + float(r["hang_dang_ve"])
    dung_truoc = {z: 0.0 for z in khu.index}                 # đang chiếm chỗ thật (tồn hiện tại)
    dung = {z: 0.0 for z in khu.index}                       # dự phóng lúc hàng về (P4, B4)
    for i in tdf.index:
        z, vol = info.loc[i, "khu_bao_quan"], info.loc[i, "the_tich_lit"]
        dung_truoc[z] += float(tdf.loc[i, "ton_kho"]) * vol
        dl = ban_truoc_khi_ve(mh[i], max(t, 0), int(info.loc[i, "L"]))
        dung[z] += max(0.0, float(tdf.loc[i, "ton_kho"]) + float(tdf.loc[i, "hang_dang_ve"]) - dl) * vol
    dung_sau = dict(dung)
    don, von_con = {}, float(von)
    nhom_ng = {ng: list(g.index) for ng, g in info.loc[list(tdf.index)].groupby("nguon_hang")}
    # P5 (B5): nguồn có mặt hàng sắp hết nhất được dùng vốn trước (thay cho thứ tự chữ cái)
    for ng in sorted(nhom_ng, key=lambda n: muc_khan_cap(kh, nhom_ng[n], max(t, 0), vt)):
        qs, tt = dat_hang_gop(kh, nhom_ng[ng], max(t, 0), vt, dung, von_con, bat_buoc_di=ng in di_cho)
        if tt is not None:
            don[ng] = (qs, tt)
            von_con -= sum(q * info.loc[i, "gia_von"] for i, q in qs.items())
            for i, q in qs.items():
                dung[info.loc[i, "khu_bao_quan"]] += q * info.loc[i, "the_tich_lit"]
                dung_sau[info.loc[i, "khu_bao_quan"]] += q * info.loc[i, "the_tich_lit"]
    for i in tdf.index:
        r, v = tdf.loc[i], mh[i]
        ma, muc, nhan, giai_thich = loi.trang_thai(vt[i], float(r["ton_kho"]), v["rop"][max(t, 0)], v["ss"][max(t, 0)])
        q = next((d[0].get(i, 0) for d in don.values() if i in d[0]), 0)
        dong.append({"mat_hang": i, "nguon_hang": info.loc[i, "nguon_hang"], "khu": info.loc[i, "khu_bao_quan"],
                     "trang_thai": nhan, "muc": muc, "giai_thich": giai_thich,
                     "du_bao_ngay": float(v["d_hat"][k]), "ton_kho": float(r["ton_kho"]),
                     "vi_the_kha_dung": vt[i], "rop": float(v["rop"][max(t, 0)]), "ss": float(v["ss"][max(t, 0)]),
                     "sap_het_han": bo[i], "nhap": q, "von": q * float(info.loc[i, "gia_von"]),
                     "han_dung_thuc": int(info.loc[i, "han_dung_thuc"]), "han_con_khi_nhan": int(info.loc[i, "han_con_khi_nhan"]),
                     "so_lo": len(lo[i]), "han_ngan_nhat": min([a[1] for a in lo[i]], default=np.nan)})
    suc_chua = pd.DataFrame([{"khu": z, "suc_chua": float(khu.loc[z, "suc_chua_lit"]), "dang_dung": dung_truoc[z],
                              "sau_khi_nhap": dung_sau[z]} for z in khu.index])
    return pd.DataFrame(dong), don, suc_chua


# ----------------------------------------------------------------------------
# 6. MÔ PHỎNG CẢ CỬA HÀNG
# ----------------------------------------------------------------------------
TEN_CS = {"A": "A. Kinh nghiệm", "B": "B. EOQ cổ điển", "C": "C. EOQ động từng mặt hàng",
          "C+G": "C + gộp chuyến", "C+G+E": "C + gộp chuyến + tồn khả dụng",
          "D": "D. Nhập gộp + ràng buộc"}
# (gộp chuyến theo nguồn hàng, dùng tồn khả dụng EWA) cho từng chính sách
CAU_HINH = {"A": (False, False), "B": (False, False), "C": (False, False),
            "C+G": (True, False), "C+G+E": (True, True), "D": (True, None)}   # None: theo DUNG_TON_KHA_DUNG
# P4: tồn khả dụng (EWA) không có lợi ích đo được và có hại khi khách chọn hàng mới -> mặc định KHÔNG dùng để quyết định
DUNG_TON_KHA_DUNG = False


def mo_phong_cua_hang(kh, chinh_sach, nhu_cau, lead_times, von_moi_ngay=float("inf"), seed=0, ton0=None,
                      ngau_nhien_hu_hong=True, rang_buoc=None, ty_le_lifo=0.0):
    """nhu_cau: {mặt hàng: mảng T ngày}; lead_times: {nguồn hàng: mảng T ngày}.
    rang_buoc: True = giới hạn vốn mỗi ngày và sức chứa từng khu; None = mặc định (chỉ D bị giới hạn).
    Lưu ý (B1): C tính EOQ với S = chi phí chuyến + chi phí dòng như thể mỗi mặt hàng tự đi một chuyến; khi đánh giá,
    MỌI chính sách đều gộp các đơn cùng nguồn, cùng ngày thành một chuyến, chi phí chuyến chia đều cho các mặt hàng.
    ty_le_lifo: phần nhu cầu mỗi ngày do khách CHỌN HÀNG MỚI NHẤT (LIFO); phần còn lại bán hàng cũ trước (FIFO) (P4, C4).
    Hàng về: hạn còn = han_con_khi_nhan (đã trừ tuổi khi nhận); các chuyến cùng nguồn không về đảo thứ tự (P4, B3).
    Sức chứa: quyết định theo mức dự phóng LÚC HÀNG VỀ; bảng sức chứa ghi mức dùng THỰC (ngay sau khi hàng về) (P4, B4).
    Trả về (bảng theo ngày × mặt hàng, bảng sức chứa theo ngày, số chuyến theo nguồn)."""
    info, mh, khu = kh["info"], kh["mat_hang"], kh["khu"]
    gop, ewa = CAU_HINH[chinh_sach]
    if ewa is None:
        ewa = DUNG_TON_KHA_DUNG
    if rang_buoc is None:
        rang_buoc = chinh_sach == "D"
    von_ngay = von_moi_ngay if rang_buoc else float("inf")
    ds = list(nhu_cau)
    T = len(next(iter(nhu_cau.values())))
    rng = np.random.default_rng(seed)
    kho, duong = {}, {i: [] for i in ds}
    for i in ds:
        # P2 (A6): mặc định tồn đầu = ROP + Q/2 của ngày đầu (trạng thái "giữa chu kỳ"), như nhau cho mọi chính sách
        x0 = float(ton0[i]) if ton0 is not None else float(round(mh[i]["rop"][0] + mh[i]["q"][0] / 2))
        kho[i] = [[x0, int(info.loc[i, "han_con_khi_nhan"]) // 2]] if x0 > 0 else []
    if ton0 is None:                                           # trạng thái đầu phải khả thi: co lại cho vừa từng khu
        for z in khu.index:
            cap = float(khu.loc[z, "suc_chua_lit"])
            o_khu = [i for i in ds if info.loc[i, "khu_bao_quan"] == z and kho[i]]
            dung0 = sum(kho[i][0][0] * info.loc[i, "the_tich_lit"] for i in o_khu)
            if cap > 0 and dung0 > cap:
                for i in o_khu:
                    kho[i][0][0] = math.floor(kho[i][0][0] * cap / dung0)
    nhom = {ng: list(g.index) for ng, g in info.loc[ds].groupby("nguon_hang")}
    ve_cuoi = {ng: -1 for ng in nhom}
    da_qua = {i: np.zeros(T) for i in ds}
    so_chuyen = {ng: 0 for ng in nhom}
    rows, rows_khu = [], []
    for t in range(T):
        rec = {}
        for i in ds:
            th = float(info.loc[i, "ty_le_hu_hong_ngay"])
            ve = sum(x for d, x in duong[i] if d <= t)
            duong[i] = [(d, x) for d, x in duong[i] if d > t]
            if ve > 0:
                kho[i].append([ve, t + int(info.loc[i, "han_con_khi_nhan"])])
            het = sum(b[0] for b in kho[i] if b[1] <= t)
            kho[i] = [b for b in kho[i] if b[1] > t]
            ton_sau_ve = sum(b[0] for b in kho[i])
            hu = 0.0
            for b in kho[i]:
                x = float(rng.binomial(int(b[0]), th)) if ngau_nhien_hu_hong and b[0] >= 1 else b[0] * th
                b[0] -= x
                hu += x
            nc = float(nhu_cau[i][t])
            da_qua[i][t] = nc
            can_moi = nc * ty_le_lifo                          # khách chọn hàng mới nhất
            for b in reversed(kho[i]):
                if can_moi <= 1e-12:
                    break
                lay = min(b[0], can_moi)
                b[0] -= lay
                can_moi -= lay
            can = nc * (1 - ty_le_lifo) + can_moi              # phần còn lại bán hàng cũ trước (FIFO)
            for b in kho[i]:
                if can <= 1e-12:
                    break
                lay = min(b[0], can)
                b[0] -= lay
                can -= lay
            kho[i] = [b for b in kho[i] if b[0] > 1e-9]
            rec[i] = {"ngay": t, "mat_hang": i, "nhu_cau": nc, "ban": nc - can, "thieu_hang": can, "het_han": het,
                      "hu_hong": hu, "hang_ve": ve, "ton_kho": sum(b[0] for b in kho[i]), "dat_hang": 0.0,
                      "phi_chuyen": 0.0, "bi_cat": 0.0, "ve_ngay": -1, "ton_sau_ve": ton_sau_ve}
        dung_thuc = {z: 0.0 for z in khu.index}               # chỗ thật đang chiếm ngay sau khi hàng về
        dung = {z: 0.0 for z in khu.index}                    # dự phóng lúc hàng mới về (để quyết định)
        for i in ds:
            z, vol = info.loc[i, "khu_bao_quan"], info.loc[i, "the_tich_lit"]
            dung_thuc[z] += rec[i]["ton_sau_ve"] * vol
            dl = ban_truoc_khi_ve(mh[i], t, int(info.loc[i, "L"]))
            dung[z] += max(0.0, rec[i]["ton_kho"] + sum(x for _, x in duong[i]) - dl) * vol
        vi_tri = {i: rec[i]["ton_kho"] + sum(x for _, x in duong[i]) for i in ds}
        don = {}
        if gop:
            von_con = von_ngay
            vt = {}
            for i in ds:
                if ewa:
                    d_tl = mh[i]["d_hat"][t + 1:t + 2 + int(info.loc[i, "han_con_khi_nhan"])]
                    vt[i], _ = vi_the_kha_dung([(b[0], b[1] - t - 1) for b in kho[i]], sum(x for _, x in duong[i]),
                                               d_tl, float(info.loc[i, "ty_le_hu_hong_ngay"]), int(info.loc[i, "L"]))
                else:
                    vt[i] = vi_tri[i]
            # P5 (B5): nguồn có mặt hàng sắp hết nhất được dùng vốn trước
            for ng in sorted(nhom, key=lambda n: muc_khan_cap(kh, nhom[n], t, vt)):
                g = nhom[ng]
                qs, _tt = dat_hang_gop(kh, g, t, vt, dung if rang_buoc else None, von_con)
                for i, q in qs.items():
                    don[i] = q
                    von_con -= q * info.loc[i, "gia_von"]
                    dung[info.loc[i, "khu_bao_quan"]] += q * info.loc[i, "the_tich_lit"]
        else:
            for i in ds:
                v, qc = mh[i], info.loc[i, "quy_cach"]
                if chinh_sach == "A":
                    tb = float(np.mean(da_qua[i][max(0, t - 13):t + 1]))
                    rop, q = 7 * tb, max(1.0, round(14 * tb))
                elif chinh_sach == "B":
                    rop, q = v["eoq_tinh"]["rop"], v["eoq_tinh"]["q"]
                else:
                    rop, q = v["rop"][t], v["q"][t]
                if vi_tri[i] <= rop:
                    don[i] = lam_tron(max(1, math.ceil((rop - vi_tri[i]) / q)) * q, qc)
            if rang_buoc and don:
                goc = dict(don)
                don, _ = cat_theo_rang_buoc(kh, don, vi_tri, t, dung, von_ngay)
                for i, q in goc.items():
                    rec[i]["bi_cat"] = q - don.get(i, 0)
        for ng, g in nhom.items():
            co = [i for i in g if don.get(i, 0) > 0]
            if co:
                so_chuyen[ng] += 1
                ngay_ve = max(t + max(1, int(lead_times[ng][t])), ve_cuoi[ng])   # không về trước chuyến đặt trước
                ve_cuoi[ng] = ngay_ve
                for i in co:
                    duong[i].append((ngay_ve, float(don[i])))
                    rec[i]["dat_hang"] = float(don[i])
                    rec[i]["ve_ngay"] = ngay_ve
                    rec[i]["phi_chuyen"] = float(info.loc[i, "chi_phi_chuyen"]) / len(co)
        rows.extend(rec.values())
        rows_khu.append({"ngay": t, **dung_thuc})
    return pd.DataFrame(rows), pd.DataFrame(rows_khu), so_chuyen


def muc_phuc_vu_dat_duoc(sim):
    """P2 (A3): mức phục vụ thực tế của từng mặt hàng.
    - ty_le_dap_ung (fill rate) = lượng bán được / nhu cầu.
    - csl = tỷ lệ chu kỳ bổ sung (giữa hai lần hàng về liên tiếp) KHÔNG có ngày nào hết hàng.
    - ngay_het_hang = tỷ lệ ngày có nhu cầu không đáp ứng được."""
    kq = {}
    for m, g in sim.groupby("mat_hang"):
        g = g.sort_values("ngay")
        ve = g.loc[g["hang_ve"] > 0, "ngay"].tolist()
        thieu = g.set_index("ngay")["thieu_hang"] > 1e-9
        bien = ve + [int(g["ngay"].max()) + 1]
        chu_ky = [thieu.loc[a:b - 1].any() for a, b in zip(bien[:-1], bien[1:]) if b > a]
        kq[m] = {"ty_le_dap_ung": float(g["ban"].sum() / max(g["nhu_cau"].sum(), 1e-9)),
                 "csl": float(1 - np.mean(chu_ky)) if chu_ky else float("nan"),
                 "so_chu_ky": len(chu_ky), "ngay_het_hang": float(thieu.mean())}
    return pd.DataFrame(kq).T


def chi_phi_cua_hang(kh, sim, sim_khu, so_chuyen=None, von_moi_ngay=None, bo_ngay_dau=0, he_so_mat_khach=1.0):
    """Tổng chi phí và chỉ số của một lần mô phỏng.
    bo_ngay_dau: bỏ W ngày đầu (giai đoạn khởi động) khỏi mọi chỉ số (P2, A6).
    he_so_mat_khach: lợi nhuận mất do thiếu hàng × hệ số này (khách không quay lại / mất uy tín)."""
    info, khu = kh["info"], kh["khu"]
    sim = sim[sim["ngay"] >= bo_ngay_dau]
    if sim_khu is not None:
        sim_khu = sim_khu[sim_khu["ngay"] >= bo_ngay_dau]
    s = sim.merge(info[["gia_von", "gia_ban", "ty_le_giu_hang_nam", "chi_phi_bao_quan_lit_ngay", "the_tich_lit",
                        "chi_phi_dong", "nguon_hang"]], left_on="mat_hang", right_index=True)
    c = {
        "chi_phi_chuyen": float(s["phi_chuyen"].sum()),
        "chi_phi_dong_hang": float(((s["dat_hang"] > 0) * s["chi_phi_dong"]).sum()),
        "lai_von": float((s["ton_kho"] * s["gia_von"] * s["ty_le_giu_hang_nam"] / 365).sum()),
        "bao_quan": float((s["ton_kho"] * s["the_tich_lit"] * s["chi_phi_bao_quan_lit_ngay"]).sum()),
        "hu_hong": float((s["hu_hong"] * s["gia_von"]).sum()),
        "het_han": float((s["het_han"] * s["gia_von"]).sum()),
        "loi_nhuan_mat": float((s["thieu_hang"] * (s["gia_ban"] - s["gia_von"])).sum() * he_so_mat_khach),
    }
    c["tong"] = sum(c.values())
    so_ngay = int(sim["ngay"].nunique())
    dung_khu = set(info["khu_bao_quan"])
    c["chi_phi_co_dinh_kho"] = float(sum(khu.loc[z, "chi_phi_co_dinh_ngay"] for z in khu.index if z in dung_khu) * so_ngay)
    c["so_dong_dat"] = int((s["dat_hang"] > 0).sum())
    c["so_chuyen"] = int(s.loc[s["phi_chuyen"] > 0, ["ngay", "nguon_hang"]].drop_duplicates().shape[0])
    c["ty_le_dap_ung"] = float(s["ban"].sum() / max(s["nhu_cau"].sum(), 1e-9))
    mpv = muc_phuc_vu_dat_duoc(sim)
    c["csl"] = float(mpv["csl"].mean())
    c["ngay_het_hang"] = float(mpv["ngay_het_hang"].mean())
    vuot = np.zeros(len(sim_khu), bool) if sim_khu is not None else np.zeros(0, bool)
    for z in khu.index:
        cap = float(khu.loc[z, "suc_chua_lit"])
        if sim_khu is not None and cap > 0 and z in sim_khu:
            vuot |= (sim_khu[z] > cap + 1e-6).values
    c["ngay_vuot_suc_chua"] = int(vuot.sum())
    tien_nhap = (s["dat_hang"] * s["gia_von"]).groupby(s["ngay"]).sum()
    c["von_lon_nhat_mot_ngay"] = float(tien_nhap.max()) if len(tien_nhap) else 0.0
    c["ngay_vuot_von"] = int((tien_nhap > von_moi_ngay + 1e-6).sum()) if von_moi_ngay else 0
    return c


def sinh_nhu_cau(d_hat, var, rng):
    """P2 (A4): nhu cầu ngẫu nhiên có cả SAI SỐ DỰ BÁO: nhị thức âm với kỳ vọng d̂ và phương sai var (≥ d̂).
    Khi var ≈ d̂ thì về Poisson."""
    d = np.maximum(np.asarray(d_hat, float), 1e-9)
    v = np.maximum(np.asarray(var, float), d * (1 + 1e-6))
    n = d ** 2 / (v - d)
    return rng.negative_binomial(n, n / (n + d)).astype(float)


def chi_phi_theo_mat_hang(kh, sim):
    """Chi phí của từng mặt hàng; chi phí chuyến được chia đều cho các mặt hàng có trong chuyến (cột phi_chuyen)."""
    s = sim.merge(kh["info"][["gia_von", "gia_ban", "ty_le_giu_hang_nam", "chi_phi_bao_quan_lit_ngay", "the_tich_lit",
                              "chi_phi_dong"]], left_on="mat_hang", right_index=True)
    s = s.assign(chuyen=s["phi_chuyen"], dong=(s["dat_hang"] > 0) * s["chi_phi_dong"],
                 lai_von=s["ton_kho"] * s["gia_von"] * s["ty_le_giu_hang_nam"] / 365,
                 bao_quan=s["ton_kho"] * s["the_tich_lit"] * s["chi_phi_bao_quan_lit_ngay"],
                 hu=s["hu_hong"] * s["gia_von"], het=s["het_han"] * s["gia_von"],
                 mat=s["thieu_hang"] * (s["gia_ban"] - s["gia_von"]))
    g = s.groupby("mat_hang")[["chuyen", "dong", "lai_von", "bao_quan", "hu", "het", "mat"]].sum()
    g["tong"] = g.sum(axis=1)
    return g


def sinh_lead_times(info, T, rng):
    return {ng: np.maximum(1, np.round(rng.normal(float(g["lead_time_ngay"].iloc[0]),
                                                  float(g["do_lech_lead_time"].iloc[0]), T))).astype(int)
            for ng, g in info.groupby("nguon_hang")}
