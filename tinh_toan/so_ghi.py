# -*- coding: utf-8 -*-
"""Sổ kiểm kho: đo lượng bán khi chưa có file doanh số.

Người bán không cần ghi từng lần bán. Mỗi tối chỉ đếm hàng còn lại, ghi hàng mới nhập và hàng hỏng/bỏ đi; lượng bán
được suy ra:
    bán (từ lần đếm trước tới lần này) = tồn lần trước + nhập thêm − hỏng/bỏ − tồn lần này
Đếm cách vài ngày thì lượng bán được chia đều cho các ngày ở giữa. Lần đếm có đánh dấu "hết hàng" thì những ngày đó là
THIẾU DỮ LIỆU (bán ít vì không còn hàng chứ không phải vì ít khách), giống cột het_hang của file doanh số.

Kèm ước lượng ban đầu của người bán (bán ít nhất / thường / nhiều nhất mỗi ngày) để có điểm đặt hàng ngay từ ngày đầu.
Cách trộn ước lượng với số đo: loi.du_bao_khoi_dong. Đủ loi.NGAY_DAY_DU ngày đo thì chuyển sang dự báo mùa vụ đầy đủ.
"""
import datetime
import os

import numpy as np
import pandas as pd

from . import loi

COT_KIEM_KHO = ["ngay", "mat_hang", "ton_cuoi_ngay", "nhap_them", "hu_hong", "het_hang"]
COT_UOC_LUONG = ["mat_hang", "ban_it_nhat", "ban_thuong", "ban_nhieu_nhat"]
FILE_KIEM_KHO, FILE_UOC_LUONG = "kiem_kho.csv", "uoc_luong.csv"
FILE_THIET_LAP = {"mh": "mat_hang.csv", "nguon": "nguon_hang.csv", "khu": "khu_bao_quan.csv"}
_CO = {"1", "1.0", "x", "co", "có", "yes", "true", "y", "het"}


def kiem_kho_trong():
    return pd.DataFrame({"ngay": pd.Series(dtype="datetime64[ns]"), "mat_hang": pd.Series(dtype=str),
                         "ton_cuoi_ngay": pd.Series(dtype=float), "nhap_them": pd.Series(dtype=float),
                         "hu_hong": pd.Series(dtype=float), "het_hang": pd.Series(dtype=bool)})


def uoc_luong_trong():
    return pd.DataFrame({"mat_hang": pd.Series(dtype=str), **{c: pd.Series(dtype=float) for c in COT_UOC_LUONG[1:]}})


def _ten(s):
    return s.where(s.notna(), "").astype(str).str.strip().map(loi._nfc)


def _so(s):
    return pd.to_numeric(s, errors="coerce")


def _ngay(s):
    """Đọc từng ô ngày: sổ có thể trộn ngày đã lưu (2026-11-10) với ngày gõ tay hoặc từ file (10/11/2026)."""
    def mot(x):
        if isinstance(x, (datetime.date, np.datetime64)):
            return pd.Timestamp(x)
        if pd.isna(x):
            return pd.NaT
        t = str(x).strip()
        return pd.to_datetime(t, dayfirst="/" in t, errors="coerce")
    return pd.to_datetime(pd.Series([mot(x) for x in s], index=s.index, dtype=object), errors="coerce")


def chuan_hoa_kiem_kho(df):
    """Làm sạch sổ kiểm kho. Trả về (bảng, danh sách lỗi). Dòng chưa có tên hàng hoặc chưa nhập số đếm bị bỏ qua."""
    if df is None or len(df) == 0:
        return kiem_kho_trong(), []
    d = df.copy()
    for c in COT_KIEM_KHO:
        if c not in d.columns:
            d[c] = np.nan
    d = d[COT_KIEM_KHO].copy()
    d["mat_hang"] = _ten(d["mat_hang"])
    d["ton_cuoi_ngay"] = _so(d["ton_cuoi_ngay"])
    d = d[(d["mat_hang"] != "") & d["ton_cuoi_ngay"].notna()].copy()
    if d.empty:
        return kiem_kho_trong(), []
    loi_ = []
    d["ngay"] = _ngay(d["ngay"]).dt.normalize()
    if d["ngay"].isna().any():
        loi_.append(f"{int(d['ngay'].isna().sum())} dòng có ngày không hợp lệ (dùng dạng 2025-01-15 hoặc 15/01/2025).")
    for c in ("nhap_them", "hu_hong"):
        d[c] = _so(d[c]).fillna(0.0)
    for c, nhan in (("ton_cuoi_ngay", "Số đếm được"), ("nhap_them", "Nhập thêm"), ("hu_hong", "Hỏng/bỏ")):
        if (d[c] < 0).any():
            loi_.append(f"{nhan} không được âm ({', '.join(d.loc[d[c] < 0, 'mat_hang'].unique()[:3])}).")
    hh = d["het_hang"]
    d["het_hang"] = hh.fillna(False).astype(bool) if hh.dtype == bool else \
        (hh.astype(str).str.strip().str.lower().isin(_CO) | (_so(hh) > 0)).values
    if loi_:
        return d, loi_
    d = d.drop_duplicates(["ngay", "mat_hang"], keep="last").sort_values(["mat_hang", "ngay"]).reset_index(drop=True)
    d[["ton_cuoi_ngay", "nhap_them", "hu_hong"]] = d[["ton_cuoi_ngay", "nhap_them", "hu_hong"]].astype(float)
    return d, []


def chuan_hoa_uoc_luong(df):
    """Làm sạch bảng mặt hàng + ước lượng bán mỗi ngày. Thiếu 'ít nhất' / 'nhiều nhất' thì lấy 0,5× / 1,5× mức thường.
    Trả về (bảng, danh sách lỗi)."""
    if df is None or len(df) == 0:
        return uoc_luong_trong(), []
    d = df.copy()
    for c in COT_UOC_LUONG:
        if c not in d.columns:
            d[c] = np.nan
    d = d[COT_UOC_LUONG].copy()
    d["mat_hang"] = _ten(d["mat_hang"])
    d = d[d["mat_hang"] != ""].copy()
    if d.empty:
        return uoc_luong_trong(), []
    for c in COT_UOC_LUONG[1:]:
        d[c] = _so(d[c])
    loi_ = []
    trung = d.loc[d["mat_hang"].duplicated(), "mat_hang"].unique()
    if len(trung):
        loi_.append(f"Mặt hàng bị trùng tên: {', '.join(trung)}.")
    thieu = d.loc[~(d["ban_thuong"] > 0), "mat_hang"].tolist()
    if thieu:
        loi_.append(f"Chưa có số 'bán thường mỗi ngày' (phải lớn hơn 0): {', '.join(thieu)}.")
    d["ban_it_nhat"] = d["ban_it_nhat"].fillna(d["ban_thuong"] * 0.5)
    d["ban_nhieu_nhat"] = d["ban_nhieu_nhat"].fillna(d["ban_thuong"] * 1.5)
    if (d[COT_UOC_LUONG[1:]] < 0).any().any():
        loi_.append("Số bán ước lượng không được âm.")
    sai = d.loc[(d["ban_it_nhat"] > d["ban_thuong"]) | (d["ban_thuong"] > d["ban_nhieu_nhat"]), "mat_hang"].tolist()
    if sai:
        loi_.append(f"Cần 'ít nhất' ≤ 'thường' ≤ 'nhiều nhất': {', '.join(sai)}.")
    return d.reset_index(drop=True), loi_


def cap_nhat_kiem_kho(kk, moi):
    """Thêm các lần đếm mới vào sổ; cùng ngày + cùng mặt hàng thì lần mới thay lần cũ."""
    return chuan_hoa_kiem_kho(pd.concat([kk, moi], ignore_index=True))


def suy_ra_ban(kk):
    """Lượng bán mỗi ngày suy ra từ sổ kiểm kho (dạng dài). Trả về (bảng, cảnh báo).
    Cột: ngay, mat_hang, so_luong_ban (NaN = thiếu dữ liệu), het_hang, khoang_ngay (số ngày giữa hai lần đếm)."""
    rows, canh_bao = [], []
    for m, g in kk.sort_values("ngay").groupby("mat_hang", sort=False):
        g = g.reset_index(drop=True)
        for j in range(1, len(g)):
            truoc, nay = g.loc[j - 1], g.loc[j]
            k = int((nay["ngay"] - truoc["ngay"]).days)
            ban = truoc["ton_cuoi_ngay"] + nay["nhap_them"] - nay["hu_hong"] - nay["ton_cuoi_ngay"]
            if ban < -0.5:
                canh_bao.append(f"{m}, {nay['ngay']:%d/%m/%Y}: đếm được nhiều hơn số có thể có ({-ban:.0f} đv). Có thể quên ghi "
                                "hàng nhập thêm; khoảng này bị bỏ qua khi đo.")
                ngay_ban = np.nan
            else:
                ngay_ban = np.nan if nay["het_hang"] else max(ban, 0.0) / k
            for i in range(1, k + 1):
                rows.append({"ngay": truoc["ngay"] + pd.Timedelta(days=i), "mat_hang": m, "so_luong_ban": ngay_ban,
                             "het_hang": bool(nay["het_hang"]), "khoang_ngay": k})
    dai = pd.DataFrame(rows, columns=["ngay", "mat_hang", "so_luong_ban", "het_hang", "khoang_ngay"])
    n_hh = int(dai.drop_duplicates(["ngay", "mat_hang"])["het_hang"].sum()) if len(dai) else 0
    if n_hh:
        canh_bao.append(f"Có {n_hh} ngày–mặt hàng hết hàng: coi là thiếu dữ liệu, vì lượng bán những hôm đó thấp hơn nhu cầu thật.")
    return dai, canh_bao


def bang_ban_hang(kk, uoc, hom_nay):
    """Bảng bán hàng dạng rộng cho app (mỗi dòng một ngày, mỗi cột một mặt hàng; NaN = chưa đo được).
    Dừng ở HÔM QUA để kế hoạch bắt đầu từ hôm nay: tối nay đếm xong là quyết định đặt hàng cuối ngày hôm nay, cho nhu cầu
    từ ngày mai (đúng quy ước của mô hình). Lượng bán của hôm nay được dùng từ ngày mai. Trả về (bảng, cảnh báo)."""
    cuoi = pd.Timestamp(hom_nay).normalize() - pd.Timedelta(days=1)
    dai, canh_bao = suy_ra_ban(kk)
    dai = dai[dai["ngay"] <= cuoi]
    co_uoc = list(uoc["mat_hang"])
    ds = co_uoc + [m for m in dict.fromkeys(kk["mat_hang"]) if m not in set(co_uoc)]
    dau = min(kk["ngay"].min(), cuoi) if len(kk) else cuoi
    rong = pd.DataFrame(np.nan, index=pd.date_range(dau, cuoi, freq="D", name="ngay"), columns=ds, dtype=float)
    if len(dai):
        p = dai.pivot(index="ngay", columns="mat_hang", values="so_luong_ban")
        rong.loc[p.index, p.columns] = p.values
    bo = [m for m in ds if m not in set(co_uoc) and not np.isfinite(rong[m].values).any()]
    if bo:
        canh_bao.append(f"Chưa dự báo được {', '.join(bo)}: chưa có ước lượng ban đầu và chưa đo được ngày bán nào "
                        "(cần hai lần đếm, lần sau không hết hàng). Thêm ước lượng ở tab 🎯 hoặc đếm thêm.")
        rong = rong.drop(columns=bo)
    return rong, canh_bao


def uoc_dict(uoc):
    """{mặt hàng: (ít nhất, thường, nhiều nhất)} cho loi.du_bao_khoi_dong."""
    return {r["mat_hang"]: (float(r["ban_it_nhat"]), float(r["ban_thuong"]), float(r["ban_nhieu_nhat"]))
            for _, r in uoc.iterrows()}


def lan_dem_cuoi(kk, truoc_ngay=None):
    """Lần đếm gần nhất của mỗi mặt hàng (tuỳ chọn: trước một ngày). Index = mặt hàng; cột ngay, ton_cuoi_ngay."""
    d = kk if truoc_ngay is None else kk[kk["ngay"] < pd.Timestamp(truoc_ngay)]
    if not len(d):
        return pd.DataFrame(columns=["ngay", "ton_cuoi_ngay"])
    return d.sort_values("ngay").groupby("mat_hang").tail(1).set_index("mat_hang")[["ngay", "ton_cuoi_ngay"]]


def tom_tat_do_luong(kk, uoc, rong):
    """Mỗi mặt hàng đã đo được bao nhiêu ngày, mức bán đo được, ước lượng, và mức app đang dùng để dự báo."""
    ud, cuoi = uoc_dict(uoc), lan_dem_cuoi(kk)
    rows = []
    for m in rong.columns:
        y = rong[m]
        v = y.values[np.isfinite(y.values)]
        meta = loi.du_bao_nhu_cau(y, 7, uoc_luong=ud.get(m))
        rows.append({"mat_hang": m, "so_ngay_do": len(v), "ban_tb_do": float(v.mean()) if len(v) else np.nan,
                     "ban_thuong_uoc": ud[m][1] if m in ud else np.nan, "muc_dang_dung": float(np.mean(meta["d_hat"])),
                     "che_do": meta["meta"]["che_do"], "lan_dem_cuoi": cuoi.loc[m, "ngay"] if m in cuoi.index else pd.NaT,
                     "ton_cuoi": float(cuoi.loc[m, "ton_cuoi_ngay"]) if m in cuoi.index else np.nan})
    return pd.DataFrame(rows)


# ---- đọc / ghi file trên máy (thư mục do giao diện chọn, không đưa lên git) ----
def _doc_csv(duong_dan):
    return pd.read_csv(duong_dan, encoding="utf-8-sig") if os.path.exists(duong_dan) else None


def doc_so(thu_muc):
    """(sổ kiểm kho, bảng ước lượng) đã lưu; chưa có file thì trả bảng trống. File hỏng thì ném ValueError."""
    kk, l1 = chuan_hoa_kiem_kho(_doc_csv(os.path.join(thu_muc, FILE_KIEM_KHO)))
    uoc, l2 = chuan_hoa_uoc_luong(_doc_csv(os.path.join(thu_muc, FILE_UOC_LUONG)))
    if l1 or l2:
        raise ValueError("Sổ đã lưu có lỗi: " + " ".join(l1 + l2))
    return kk, uoc


def ghi_so(thu_muc, kk=None, uoc=None):
    os.makedirs(thu_muc, exist_ok=True)
    if kk is not None:
        out = kk.copy()
        out["ngay"] = pd.to_datetime(out["ngay"]).dt.strftime("%Y-%m-%d")
        out["het_hang"] = out["het_hang"].astype(int)
        out[COT_KIEM_KHO].to_csv(os.path.join(thu_muc, FILE_KIEM_KHO), index=False, encoding="utf-8-sig")
    if uoc is not None:
        uoc[COT_UOC_LUONG].to_csv(os.path.join(thu_muc, FILE_UOC_LUONG), index=False, encoding="utf-8-sig")


def doc_thiet_lap(thu_muc):
    """{'mh' | 'nguon' | 'khu': bảng} đã lưu (bảng mặt hàng theo đơn vị của mô hình), chỉ những file có trên máy."""
    return {k: df for k, f in FILE_THIET_LAP.items() if (df := _doc_csv(os.path.join(thu_muc, f))) is not None}


def ghi_thiet_lap(thu_muc, mh, nguon, khu):
    os.makedirs(thu_muc, exist_ok=True)
    for k, df in (("mh", mh), ("nguon", nguon), ("khu", khu)):
        df.to_csv(os.path.join(thu_muc, FILE_THIET_LAP[k]), index=False, encoding="utf-8-sig")
