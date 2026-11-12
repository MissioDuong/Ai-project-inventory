# -*- coding: utf-8 -*-
"""
Lõi tính toán dùng chung cho app.py và pipeline.py (không phụ thuộc Streamlit, để dễ kiểm thử).

LUỒNG END-TO-END:
  dữ liệu bán hàng -> dự báo nhu cầu (thống kê mùa vụ) -> tồn kho an toàn, ROP, EOQ động
  -> đặt hàng -> giao hàng (lead time) -> bán lẻ (FIFO, hạn dùng) -> chi phí.

DỰ BÁO (không dùng học máy, tính được bằng Excel):
  nhu cầu(ngày) = mức nền × hệ số thứ trong tuần × hệ số Tết(số ngày tới Tết) × hệ số Trung thu(số ngày tới Trung thu)
  - Mức nền: trung bình lượng bán những ngày ngoài mùa vụ gần đây (đã bỏ ảnh hưởng thứ trong tuần).
  - Hệ số mùa vụ: trung bình tỷ lệ (lượng bán / mức nền) tại cùng khoảng cách tới Tết (hoặc Trung thu)
    qua các năm trong dữ liệu, làm trơn 5 ngày. Tết, Trung thu theo âm lịch đã quy đổi sang dương lịch.

QUY TẮC TỒN KHO (theo sơ đồ "Inventory Level with Reorder Point and Safety Stock"):
  1. Tồn kho thực tế (Stock On-hand)  = hàng đang có trong kho/trên kệ.
  2. Mức tồn kho tổng (Stock Level)   = tồn kho thực tế + hàng đã đặt đang trên đường về.
  3. Tồn kho an toàn (Safety Stock)   = Z · sqrt( Σ phương sai nhu cầu trong lead time + (nhu cầu/ngày)² · Var(lead time) ).
  4. Điểm đặt hàng lại (ROP)          = nhu cầu dự báo trong lead time + tồn kho an toàn.
  5. Khi mức tồn kho TỔNG <= ROP  ->  đặt hàng n·Q* (n sao cho vượt ROP). Mức tổng nhảy lên NGAY lúc đặt,
     còn tồn kho thực tế chỉ tăng sau lead time (hàng về).
  6. Q* = EOQ động = sqrt(2·D·S/H), D quy năm từ dự báo 30 ngày tới, bị chặn bởi 60% hạn dùng.
  7. Cảnh báo: tồn kho thực tế < tồn kho an toàn là vùng nguy hiểm; = 0 là hết hàng.
  8. Hàng bán theo FIFO (cũ trước); hàng quá hạn bị loại.
"""
import io
import math
import unicodedata
from statistics import NormalDist

import numpy as np
import pandas as pd

# Ngày mùng 1 Tết Nguyên đán và Rằm tháng Tám (Trung thu) theo dương lịch
TET = pd.to_datetime(["2018-02-16", "2019-02-05", "2020-01-25", "2021-02-12", "2022-02-01", "2023-01-22",
                      "2024-02-10", "2025-01-29", "2026-02-17", "2027-02-06", "2028-01-26", "2029-02-13",
                      "2030-02-03"])
TRUNG_THU = pd.to_datetime(["2018-09-24", "2019-09-13", "2020-10-01", "2021-09-21", "2022-09-10", "2023-09-29",
                            "2024-09-17", "2025-10-06", "2026-09-25", "2027-09-15", "2028-10-03", "2029-09-22",
                            "2030-09-12"])
NGAY_DAU, NGAY_CUOI = pd.Timestamp("2018-01-01"), pd.Timestamp("2030-12-31")

COT_THAM_SO = ["mat_hang", "gia_von", "gia_ban", "han_dung_ngay", "chi_phi_dat_hang",
               "ty_le_giu_hang_nam", "lead_time_ngay", "do_lech_lead_time", "muc_phuc_vu"]

# Tham số mặc định cho 6 nhóm hàng của bản mô phỏng (GIẢ ĐỊNH minh hoạ)
_MAC_DINH = {
    "Kẹo dừa Bến Tre (gói 200g)": (12000, 18000, 180),
    "Bánh pía (hộp)": (28000, 40000, 30),
    "Mứt Tết (hộp)": (45000, 70000, 120),
    "Bánh trung thu (cái)": (60000, 95000, 60),
    "Bánh quy / bánh gạo (gói)": (8000, 12000, 240),
    "Kẹo lạc / kẹo mè xửng": (10000, 15000, 90),
}


# ----------------------------------------------------------------------------
# 1. NHẬP DỮ LIỆU
# ----------------------------------------------------------------------------
def _bo_dau(s):
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")
    return s.lower().strip().replace("-", "_").replace(" ", "_")


def doc_file(f):
    """Đọc file CSV hoặc Excel người dùng tải lên (đối tượng của st.file_uploader hoặc đường dẫn)."""
    ten = str(getattr(f, "name", f)).lower()
    if ten.endswith((".xlsx", ".xls")):
        return pd.read_excel(f)
    data = f.getvalue() if hasattr(f, "getvalue") else (f.read() if hasattr(f, "read") else open(f, "rb").read())
    for enc in ("utf-8-sig", "cp1258", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(data), sep=None, engine="python", encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception as e:                                   # noqa: BLE001
            raise ValueError(f"Không đọc được file: {e}") from e
    raise ValueError("Không đọc được file (sai bảng mã). Hãy lưu lại dạng CSV UTF-8.")


def _nfc(s):
    """Chuẩn hoá Unicode (NFC) + bỏ khoảng trắng để tên mặt hàng gõ kiểu tổ hợp vẫn khớp nhau."""
    return unicodedata.normalize("NFC", str(s)).strip()


def _doc_ngay(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s)
    t = s.astype(str).str.strip()
    return pd.to_datetime(t, dayfirst=t.str.contains("/").any(), errors="coerce")


def chuan_hoa_ban_hang(df):
    """Đưa file bán hàng về dạng rộng: mỗi dòng một ngày liên tục, mỗi cột một mặt hàng.
    Chấp nhận 2 dạng:  (a) dài: ngay | mat_hang | so_luong_ban   (b) rộng: ngay | Mặt hàng 1 | Mặt hàng 2 ...
    Trả về (bảng_rộng, danh_sách_cảnh_báo). Gặp lỗi nặng thì ném ValueError với câu giải thích."""
    canh_bao = []
    d = df.dropna(how="all").copy()
    if d.empty:
        raise ValueError("File trống.")
    ten = {c: _bo_dau(c) for c in d.columns}
    tim = lambda ds: next((c for c, k in ten.items() if k in ds), None)      # noqa: E731
    c_ngay = tim({"ngay", "date", "ngay_ban", "thoi_gian"})
    if c_ngay is None:
        raise ValueError("Không tìm thấy cột ngày. Hãy đặt tên cột đầu là 'ngay' (ví dụ 2025-01-15 hoặc 15/01/2025).")
    ngay = _doc_ngay(d[c_ngay])
    xau = ngay.isna()
    if xau.any():
        vd = (d.index[xau][:3] + 2).tolist()
        raise ValueError(f"{int(xau.sum())} dòng có ngày không hợp lệ (ví dụ dòng {vd} trong file). "
                         "Dùng dạng 2025-01-15 hoặc 15/01/2025.")
    c_mh = tim({"mat_hang", "san_pham", "sku", "product", "item", "ten_hang"})
    c_sl = tim({"so_luong_ban", "so_luong", "sl", "quantity", "qty", "sales", "ban"})
    c_hh = tim({"het_hang", "stockout", "out_of_stock"})
    co_ngay = pd.DatetimeIndex(ngay.dt.normalize().unique())     # những ngày có ít nhất một dòng trong file
    het_hang = None
    if c_mh and c_sl:                                            # dạng dài
        sl = pd.to_numeric(d[c_sl], errors="coerce")
        if (sl.isna() & d[c_sl].notna()).any():
            raise ValueError(f"Cột '{c_sl}' có giá trị không phải số.")
        sl = sl.fillna(0)
        if (sl < 0).any():
            raise ValueError("Số lượng bán có giá trị âm. Hãy kiểm tra lại file.")
        tmp = pd.DataFrame({"ngay": ngay.dt.normalize(), "mh": d[c_mh].astype(str).map(_nfc), "sl": sl})
        rong = tmp.pivot_table(index="ngay", columns="mh", values="sl", aggfunc="sum").fillna(0.0)
        if c_hh:                                                 # cột tuỳ chọn: 1 / x / có = hôm đó hết hàng
            co = d[c_hh].astype(str).str.strip().str.lower()
            co = co.isin({"1", "1.0", "x", "co", "có", "yes", "true", "y", "het"}) | (pd.to_numeric(d[c_hh], errors="coerce") > 0)
            het_hang = tmp.loc[co.values, ["ngay", "mh"]].drop_duplicates()
    else:                                                        # dạng rộng
        cot = [c for c in d.columns if c != c_ngay]
        if not cot:
            raise ValueError("Chỉ có cột ngày. Cần thêm cột số lượng bán (dạng dài: mat_hang + so_luong_ban; "
                             "dạng rộng: mỗi mặt hàng một cột).")
        ten_moi = [_nfc(c) for c in cot]
        if len(set(ten_moi)) < len(ten_moi):
            raise ValueError("Có hai cột mặt hàng trùng tên. Hãy đổi tên hoặc gộp lại.")
        loi = [_nfc(c) for c in cot if (pd.to_numeric(d[c], errors="coerce").isna() & d[c].notna()).any()]
        so = pd.DataFrame({_nfc(c): pd.to_numeric(d[c], errors="coerce") for c in cot})
        if loi:
            raise ValueError(f"Cột {loi} có giá trị không phải số.")
        so = so.fillna(0)
        if (so < 0).any().any():
            raise ValueError("Số lượng bán có giá trị âm. Hãy kiểm tra lại file.")
        so["ngay"] = ngay.dt.normalize().values
        rong = so.groupby("ngay").sum()
    rong = rong.sort_index()
    day_du = pd.date_range(rong.index.min(), rong.index.max(), freq="D")
    thieu = len(day_du) - len(co_ngay)
    # P3 (D2): ngày không có dòng nào = THIẾU DỮ LIỆU (NaN), không phải bán 0; dự báo sẽ bỏ qua những ngày này
    rong = rong.reindex(day_du).astype(float)
    rong.index.name = "ngay"
    if het_hang is not None and len(het_hang):
        for _, r in het_hang.iterrows():
            if r["mh"] in rong.columns:
                rong.loc[r["ngay"], r["mh"]] = np.nan
        canh_bao.append(f"Có {len(het_hang)} ngày–mặt hàng được đánh dấu hết hàng: coi là thiếu dữ liệu, vì lượng bán "
                        "những hôm đó thấp hơn nhu cầu thật.")
    if thieu > 0:
        canh_bao.append(f"Có {thieu} ngày không có dòng nào trong file (nghỉ bán hoặc thiếu sổ): coi là THIẾU DỮ LIỆU, "
                        "không phải bán 0, nên dự báo bỏ qua những ngày này. Nếu ngày nghỉ lặp lại hằng năm (ví dụ mùng 1–3 Tết) "
                        "và bạn muốn dự báo những ngày đó bằng 0, hãy ghi dòng với số lượng 0.")
    if len(rong) < 60:
        raise ValueError(f"Chỉ có {len(rong)} ngày dữ liệu; cần ít nhất 60 ngày (khuyến nghị từ 365 ngày trở lên).")
    if len(rong) < 365:
        canh_bao.append(f"Dữ liệu chỉ có {len(rong)} ngày (< 1 năm), mô hình chưa thấy trọn một mùa Tết/Trung thu "
                        "nên dự báo mùa vụ kém tin cậy.")
    trong = [c for c in rong.columns if rong[c].sum() <= 0]
    if trong:
        canh_bao.append(f"Bỏ các mặt hàng không có lượng bán nào: {trong}.")
        rong = rong.drop(columns=trong)
    if rong.shape[1] == 0:
        raise ValueError("Không còn mặt hàng nào có số liệu bán.")
    if rong.index.min() < NGAY_DAU or rong.index.max() > NGAY_CUOI:
        canh_bao.append("Có ngày nằm ngoài 2018–2030; bảng ngày Tết/Trung thu của ứng dụng chỉ có trong khoảng này.")
    return rong, canh_bao


def tham_so_mac_dinh(ds_mat_hang):
    rows = []
    for m in ds_mat_hang:
        gv, gb, hd = _MAC_DINH.get(m, (10000, 15000, 90))
        rows.append([m, gv, gb, hd, 70000, 0.30, 2.0, 0.7, 0.95])
    return pd.DataFrame(rows, columns=COT_THAM_SO)


def chuan_hoa_tham_so(df, ds_mat_hang):
    """Ghép file tham số người dùng tải lên với mặc định; mặt hàng thiếu dùng giá trị mặc định."""
    mac_dinh = tham_so_mac_dinh(ds_mat_hang)
    canh_bao = []
    d = df.copy()
    d.columns = [_bo_dau(c) for c in d.columns]
    if "mat_hang" not in d.columns:
        raise ValueError("File tham số cần có cột 'mat_hang'.")
    d["mat_hang"] = d["mat_hang"].astype(str).map(_nfc)
    ket_qua = mac_dinh.set_index("mat_hang")
    for _, r in d.iterrows():
        if r["mat_hang"] not in ket_qua.index:
            canh_bao.append(f"Mặt hàng '{r['mat_hang']}' trong file tham số không có trong dữ liệu bán hàng, bỏ qua.")
            continue
        for c in COT_THAM_SO[1:]:
            if c in d.columns and pd.notna(r[c]):
                ket_qua.loc[r["mat_hang"], c] = float(r[c])
    thieu = [m for m in ds_mat_hang if m not in set(d["mat_hang"])]
    if thieu:
        canh_bao.append(f"Thiếu tham số cho {thieu}: dùng giá trị mặc định, hãy kiểm tra trong bảng.")
    return ket_qua.reset_index(), canh_bao


def kiem_tra_tham_so(tp):
    loi = []
    for _, r in tp.iterrows():
        m = r["mat_hang"]
        if not all(pd.notna(r[c]) for c in COT_THAM_SO[1:]):
            loi.append(f"{m}: còn ô trống trong bảng tham số.")
            continue
        if r["gia_von"] <= 0 or r["gia_ban"] <= 0:
            loi.append(f"{m}: giá vốn và giá bán phải lớn hơn 0.")
        if r["han_dung_ngay"] < 3:
            loi.append(f"{m}: hạn dùng phải từ 3 ngày trở lên.")
        if r["chi_phi_dat_hang"] <= 0 or r["ty_le_giu_hang_nam"] <= 0:
            loi.append(f"{m}: chi phí đặt hàng và tỷ lệ giữ hàng phải lớn hơn 0.")
        if r["lead_time_ngay"] < 1:
            loi.append(f"{m}: thời gian giao hàng phải từ 1 ngày trở lên.")
        if r["do_lech_lead_time"] < 0:
            loi.append(f"{m}: độ lệch lead time không được âm.")
        if not 0.5 <= r["muc_phuc_vu"] < 1:
            loi.append(f"{m}: mức phục vụ phải trong khoảng 0,5 đến dưới 1 (ví dụ 0,95).")
    return loi


def mau_ban_hang_csv():
    d = pd.DataFrame({"ngay": ["2025-01-01"] * 2 + ["2025-01-02"] * 2 + ["2025-01-03"] * 2,
                      "mat_hang": ["Kẹo dừa Bến Tre (gói 200g)", "Bánh pía (hộp)"] * 3,
                      "so_luong_ban": [18, 10, 20, 9, 25, 14]})
    return d.to_csv(index=False).encode("utf-8-sig")


def mau_tham_so_csv(ds_mat_hang=None):
    return tham_so_mac_dinh(ds_mat_hang or list(_MAC_DINH)).to_csv(index=False).encode("utf-8-sig")


# ----------------------------------------------------------------------------
# 2. DỰ BÁO NHU CẦU (thống kê mùa vụ, không dùng học máy)
# ----------------------------------------------------------------------------
CUA_SO_TET = (-60, 30)        # mùa Tết: từ 60 ngày trước đến 30 ngày sau mùng 1
CUA_SO_TRUNG_THU = (-45, 10)  # mùa Trung thu: từ 45 ngày trước đến 10 ngày sau Rằm tháng Tám
SO_NGAY_NEN = 56              # mức nền lấy từ 56 ngày ngoài mùa vụ gần nhất
PHI_XU_HUONG = 0.98           # hệ số hãm xu hướng mỗi ngày (xu hướng tác động tối đa khoảng 50 ngày)


def _ngay_gan_nhat(ngay, moc):
    """Số ngày (có dấu) từ mỗi ngày tới mốc gần nhất: âm = trước mốc, dương = sau mốc."""
    d = ngay.values.astype("datetime64[D]")[:, None] - moc.values.astype("datetime64[D]")[None, :]
    d = d.astype(int)
    i = np.abs(d).argmin(axis=1)
    return d[np.arange(len(d)), i]


def _trong(lech, cua):
    return (lech >= cua[0]) & (lech <= cua[1])


def _tb(x):
    """Trung bình bỏ qua NaN; NaN nếu không có giá trị nào."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(x.mean()) if len(x) else np.nan


def hoc_mua_vu(y, xu_huong=False):
    """Phân rã nhân tính chuỗi bán hàng y (index = ngày liên tục) thành mức nền, hệ số thứ và hệ số mùa vụ.
    Giá trị NaN (ngày nghỉ bán, ngày hết hàng = thiếu dữ liệu) được bỏ qua khi ước lượng.
    xu_huong=True: thêm xu hướng tuyến tính có hãm cho mức nền, ước lượng từ 180 ngày gần nhất (P3, D3)."""
    v = y.values.astype(float)
    co = np.isfinite(v)
    ngay = pd.DatetimeIndex(y.index)
    dow = ngay.dayofweek.values
    dt, dtt = _ngay_gan_nhat(ngay, TET), _ngay_gan_nhat(ngay, TRUNG_THU)
    thuong = ~(_trong(dt, CUA_SO_TET) | _trong(dtt, CUA_SO_TRUNG_THU))          # ngày ngoài mùa vụ

    # Mức nền theo thời gian: trung bình trượt 91 ngày của các ngày ngoài mùa vụ (bỏ NaN)
    s = pd.Series(np.where(thuong & co, v, np.nan), index=ngay)
    nen = s.rolling(91, center=True, min_periods=14).mean().interpolate(limit_direction="both")
    tb_chung = _tb(v)
    nen = nen.fillna(max(tb_chung if np.isfinite(tb_chung) else 0.05, 0.05)).clip(lower=0.05).values
    ty_le = v / nen

    # Hệ số thứ trong tuần (chỉ tính trên ngày ngoài mùa vụ), chuẩn hoá trung bình = 1
    thu = np.ones(7)
    for k in range(7):
        g = _tb(ty_le[thuong & (dow == k)])
        if np.isfinite(g) and g > 0:
            thu[k] = g
    thu = thu / thu.mean()
    ty_le_khong_thu = ty_le / thu[dow]

    def he_so(lech, cua):
        k = np.arange(cua[0], cua[1] + 1)
        tb = pd.Series([_tb(ty_le_khong_thu[lech == i]) for i in k], index=k)
        return tb.rolling(5, center=True, min_periods=1).mean().fillna(1.0).clip(lower=0.0)

    # Mức nền dùng để dự báo: trung bình (đã bỏ hệ số thứ) của các ngày ngoài mùa vụ gần nhất
    idx = np.where(thuong & co)[0][-SO_NGAY_NEN:]
    muc_nen = float(np.mean(v[idx] / thu[dow[idx]])) if len(idx) else float(nen[-1])

    # Xu hướng tuyến tính có hãm: hồi quy (bán / hệ số thứ) theo thời gian trên ngày thường của 180 ngày cuối
    do_doc, muc_cuoi = 0.0, muc_nen
    if xu_huong:
        cua = thuong & co & (ngay >= ngay[-1] - pd.Timedelta(days=179))
        if cua.sum() >= 60:
            t = (ngay[cua] - ngay[-1]).days.values.astype(float)
            z = v[cua] / thu[dow[cua]]
            b, a = np.polyfit(t, z, 1)
            tran = 0.5 * max(a, 0.05) / (1 / (1 - PHI_XU_HUONG))       # tối đa ±50 % mức nền sau khi hãm
            do_doc, muc_cuoi = float(np.clip(b, -tran, tran)), float(max(a, 0.05))

    co_mua = lambda moc, lech, cua: int(sum(_trong(lech, cua)[co & (ngay >= m + pd.Timedelta(days=cua[0])) &  # noqa: E731
                                                              (ngay <= m + pd.Timedelta(days=cua[1]))].any()
                                            for m in moc))
    return {"muc_nen": max(muc_nen, 0.05), "he_so_thu": thu,
            "he_so_tet": he_so(dt, CUA_SO_TET), "he_so_trung_thu": he_so(dtt, CUA_SO_TRUNG_THU),
            "so_mua_tet": co_mua(TET, dt, CUA_SO_TET), "so_mua_trung_thu": co_mua(TRUNG_THU, dtt, CUA_SO_TRUNG_THU),
            "xu_huong": bool(xu_huong and do_doc != 0.0), "do_doc": do_doc, "muc_cuoi": muc_cuoi,
            "ngay_cuoi": ngay[-1], "ty_le_thieu_du_lieu": float(1 - co.mean())}


def du_bao_tu_mo_hinh(mh, ngay):
    """Áp mô hình mùa vụ `mh` (kết quả hoc_mua_vu) cho các ngày `ngay`."""
    ngay = pd.DatetimeIndex(ngay)
    dt, dtt = _ngay_gan_nhat(ngay, TET), _ngay_gan_nhat(ngay, TRUNG_THU)
    ft = np.where(_trong(dt, CUA_SO_TET), mh["he_so_tet"].reindex(dt).fillna(1.0).values, 1.0)
    ftt = np.where(_trong(dtt, CUA_SO_TRUNG_THU), mh["he_so_trung_thu"].reindex(dtt).fillna(1.0).values, 1.0)
    if mh.get("xu_huong"):
        h = np.clip((ngay - mh["ngay_cuoi"]).days.values.astype(float), 0, None)
        nen = mh["muc_cuoi"] + mh["do_doc"] * PHI_XU_HUONG * (1 - PHI_XU_HUONG ** h) / (1 - PHI_XU_HUONG)
        nen = np.clip(nen, 0.05, None)
    else:
        nen = mh["muc_nen"]
    return np.clip(nen * mh["he_so_thu"][ngay.dayofweek.values] * ft * ftt, 0.05, None)


def _wape(thuc, du_bao):
    thuc, du_bao = np.asarray(thuc, float), np.asarray(du_bao, float)
    m = np.isfinite(thuc) & np.isfinite(du_bao)
    if not m.any() or thuc[m].sum() <= 0:
        return np.nan
    return float(np.abs(thuc[m] - du_bao[m]).sum() / thuc[m].sum())


def du_bao_nhu_cau(y, so_ngay, xu_huong=False):
    """Dự báo `so_ngay` ngày kế tiếp từ chuỗi bán hàng y (NaN = thiếu dữ liệu, được bỏ qua).
    Nếu có >= 240 ngày: giữ lại 30% cuối để đo sai số ngoài mẫu và ước lượng phương sai Var = a·d + b·d²."""
    v, n = y.values.astype(float), len(y)
    meta = {"so_ngay_du_lieu": n}
    if n >= 240:
        cut = int(n * 0.7)
        p = du_bao_tu_mo_hinh(hoc_mua_vu(y.iloc[:cut], xu_huong), y.index[cut:])
        thuc = v[cut:]
        meta.update(ngoai_mau=True, wape_du_bao=_wape(thuc, p),
                    wape_trung_binh=_wape(thuc, np.full(len(thuc), _tb(v[:cut]))))
    else:
        p = du_bao_tu_mo_hinh(hoc_mua_vu(y, xu_huong), y.index)
        thuc = v
        meta.update(ngoai_mau=False)
    m = np.isfinite(thuc)
    coef = np.clip(np.linalg.lstsq(np.c_[p[m], p[m] ** 2], (thuc[m] - p[m]) ** 2, rcond=None)[0], 0, None) \
        if m.sum() >= 10 else np.array([1.0, 0.0])
    mh = hoc_mua_vu(y, xu_huong)
    ngay = pd.date_range(y.index[-1] + pd.Timedelta(days=1), periods=so_ngay)
    d_hat = du_bao_tu_mo_hinh(mh, ngay)
    var = np.maximum(coef[0] * d_hat + coef[1] * d_hat ** 2, d_hat)      # tối thiểu bằng phương sai Poisson
    meta.update(he_so_phuong_sai=coef.tolist(), so_mua_tet=mh["so_mua_tet"], so_mua_trung_thu=mh["so_mua_trung_thu"])
    return {"ngay": ngay, "d_hat": d_hat, "var": var, "meta": meta, "mo_hinh": mh}


def kiem_dinh_theo_mua(y, so_ngay=90, xu_huong=False, lich_su_toi_thieu=180):
    """P3 (D1): kiểm định dự báo theo kiểu dịch dần mốc thời gian, riêng cho từng mùa.
    Với mỗi Tết (Trung thu) có trong dữ liệu: mốc = 60 (45) ngày trước ngày lễ; chỉ học từ dữ liệu TRƯỚC mốc,
    dự báo `so_ngay` ngày sau mốc, rồi so với thực tế. So sánh với 2 cách đơn giản: (1) trung bình 56 ngày gần nhất;
    (2) "năm ngoái ngày này bán bao nhiêu" theo lịch dương (cách tiểu thương hay làm, lệch theo âm lịch).
    WAPE được tính trên cả khung dự báo và riêng phần đỉnh mùa (Tết: −30..+7 ngày; Trung thu: −30..+2 ngày)."""
    rows = []
    dau, cuoi = y.index[0], y.index[-1]
    for mua, ds_moc, truoc, dinh in [("Tết", TET, 60, (-30, 7)), ("Trung thu", TRUNG_THU, 45, (-30, 2))]:
        for m in ds_moc:
            goc = m - pd.Timedelta(days=truoc)
            if m + pd.Timedelta(days=dinh[1]) > cuoi or goc <= dau:
                continue
            hoc = y[y.index < goc]
            if np.isfinite(hoc.values).sum() < lich_su_toi_thieu:
                continue
            thu = y[(y.index >= goc) & (y.index < goc + pd.Timedelta(days=so_ngay))]
            p = du_bao_tu_mo_hinh(hoc_mua_vu(hoc, xu_huong), thu.index)
            tb56 = np.full(len(thu), _tb(hoc.values[-56:]))
            nam_truoc = y.reindex(thu.index - pd.Timedelta(days=365)).values
            lech = (thu.index - m).days.values
            o_dinh = (lech >= dinh[0]) & (lech <= dinh[1])
            a = thu.values.astype(float)
            rows.append({"mua": mua, "nam": m.year, "moc_du_bao": goc.date(), "so_ngay_hoc": int(np.isfinite(hoc.values).sum()),
                         "wape_mo_hinh": _wape(a, p), "wape_trung_binh_56": _wape(a, tb56),
                         "wape_nam_ngoai_cung_ngay": _wape(a, nam_truoc),
                         "wape_dinh_mo_hinh": _wape(a[o_dinh], p[o_dinh]),
                         "wape_dinh_trung_binh_56": _wape(a[o_dinh], tb56[o_dinh]),
                         "wape_dinh_nam_ngoai": _wape(a[o_dinh], nam_truoc[o_dinh]),
                         "lech_tong_dinh": float((np.nansum(p[o_dinh]) - np.nansum(a[o_dinh])) / max(np.nansum(a[o_dinh]), 1e-9))})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# 3. QUY TẮC: EOQ động, tồn kho an toàn, ROP
# ----------------------------------------------------------------------------
def can_them_ngay(tp):
    """Số ngày dự báo cần thêm sau khung kế hoạch để tính được ROP và trần hạn dùng."""
    L = max(1, int(round(tp["lead_time_ngay"])))
    return max(L + 1, 31, int(0.6 * tp["han_dung_ngay"]) + 1) + 1


def chinh_sach(d_hat, var, tp, so_ngay):
    """Với mỗi ngày j trong [0, so_ngay): tồn kho an toàn, ROP và lượng nhập Q*."""
    L = max(1, int(round(tp["lead_time_ngay"])))
    z, var_L = NormalDist().inv_cdf(float(tp["muc_phuc_vu"])), float(tp["do_lech_lead_time"]) ** 2
    H = float(tp["ty_le_giu_hang_nam"]) * float(tp["gia_von"])
    S = float(tp["chi_phi_dat_hang"])
    ngay_tran = max(3, int(0.6 * tp["han_dung_ngay"]))
    cs, cv = np.r_[0.0, np.cumsum(d_hat)], np.r_[0.0, np.cumsum(var)]
    ss, rop, q = np.zeros(so_ngay), np.zeros(so_ngay), np.zeros(so_ngay)
    for j in range(so_ngay):
        mu = cs[j + L + 1] - cs[j + 1]                              # nhu cầu dự báo trong lead time
        ss[j] = z * math.sqrt(cv[j + L + 1] - cv[j + 1] + (mu / L) ** 2 * var_L)
        rop[j] = mu + ss[j]
        D = 365.0 * (cs[j + 31] - cs[j + 1]) / 30.0                 # nhu cầu năm quy đổi
        q_eoq = math.sqrt(2.0 * D * S / H)
        tran = cs[j + ngay_tran + 1] - cs[j + 1]                    # không nhập quá 60% hạn dùng
        q[j] = max(1, math.ceil(min(q_eoq, tran)))
    return {"ss": ss, "rop": rop, "q": q, "L": L}


def chinh_sach_eoq_tinh(y, tp):
    """Đối chứng 'EOQ cổ điển': Q*, tồn kho an toàn và ROP CỐ ĐỊNH tính từ trung bình và độ lệch chuẩn lịch sử."""
    L = max(1, int(round(tp["lead_time_ngay"])))
    z = NormalDist().inv_cdf(float(tp["muc_phuc_vu"]))
    d, sd = float(np.nanmean(y)), float(np.nanstd(y))
    ss = z * math.sqrt(L * sd ** 2 + d ** 2 * float(tp["do_lech_lead_time"]) ** 2)
    q = max(1.0, math.ceil(math.sqrt(2.0 * d * 365 * float(tp["chi_phi_dat_hang"]) /
                                     (float(tp["ty_le_giu_hang_nam"]) * float(tp["gia_von"])))))
    return {"ss": ss, "rop": d * L + ss, "q": q, "L": L}


def chinh_sach_kinh_nghiem(muc_ban_dau):
    """Đối chứng 'kinh nghiệm': khi tồn kho tổng <= 7 ngày bán gần đây thì nhập lượng bằng 14 ngày bán gần đây.
    Trả về hai hàm (rop, q) theo lịch sử nhu cầu đã thấy, dùng được với mo_phong."""
    def tb14(da_qua):
        return float(np.mean(da_qua[-14:])) if len(da_qua) else float(muc_ban_dau)
    return (lambda t, da_qua: 7 * tb14(da_qua)), (lambda t, da_qua: max(1.0, round(14 * tb14(da_qua))))


def tinh_tat_ca(ban_hang, tham_so, so_ngay):
    """Dự báo + chính sách cho mọi mặt hàng."""
    tp_idx = tham_so.set_index("mat_hang")
    kq = {}
    for m in ban_hang.columns:
        tp = tp_idx.loc[m]
        dubao = du_bao_nhu_cau(ban_hang[m], so_ngay + can_them_ngay(tp))
        cs = chinh_sach(dubao["d_hat"], dubao["var"], tp, so_ngay)
        kq[m] = {**dubao, **cs, "so_ngay": so_ngay}
    return kq


# ----------------------------------------------------------------------------
# 4. TRẠNG THÁI VÀ MÔ PHỎNG THEO NGÀY
# ----------------------------------------------------------------------------
def trang_thai(vi_tri, ton_kho, rop, ss):
    """Trả về (mã, mức, nhãn, giải thích) theo các quy tắc của sơ đồ."""
    if ton_kho <= 0:
        return "HET_HANG", "error", "🔴 Hết hàng", "Tồn kho thực tế bằng 0: đang mất doanh thu."
    if ton_kho < ss:
        if vi_tri > rop:
            return "DUOI_AN_TOAN_HANG_VE", "warning", "🟡 Dưới mức an toàn, hàng đang về", \
                "Tồn kho thực tế thấp hơn mức an toàn nhưng lượng hàng đang về đủ bù. Theo dõi sát."
        return "DUOI_AN_TOAN", "error", "🔴 Dưới mức an toàn, đặt ngay", \
            "Tồn kho thực tế đã thấp hơn mức an toàn và mức tồn kho tổng chạm điểm đặt hàng: cần đặt ngay."
    if vi_tri <= rop:
        return "DAT_HANG", "warning", "🟠 Đến điểm đặt hàng", \
            "Mức tồn kho tổng (tồn kho + hàng đang về) đã chạm điểm đặt hàng lại: nên đặt hôm nay."
    return "AN_TOAN", "success", "🟢 An toàn", "Mức tồn kho tổng còn cao hơn điểm đặt hàng lại, chưa cần đặt."


def mo_phong(d_hat, rop, ss, q, L, ton_kho0, hang_ve0, han_dung, ngay0, so_ngay=None,
             ngau_nhien=False, seed=0, cho_phep_dat=True, han_con_lai0=None, nhu_cau=None, lead_times=None):
    """Mô phỏng chuỗi ĐẶT HÀNG -> GIAO HÀNG -> BÁN từng ngày theo đúng các quy tắc của sơ đồ.
    Đầu ngày: nhận hàng về, loại hàng hết hạn. Trong ngày: bán theo FIFO. Cuối ngày: nếu mức tồn kho TỔNG <= ROP
    thì đặt n·Q, hàng về sau lead time.
      - rop, q: mảng theo ngày, hoặc hàm f(t, nhu_cau_da_qua) (dùng cho chính sách kinh nghiệm).
      - nhu_cau: nhu cầu thực tế từng ngày; nếu không có thì dùng d_hat (hoặc Poisson quanh d_hat nếu ngau_nhien).
      - lead_times: lead time của đơn đặt vào ngày t; nếu không có thì luôn bằng L.
    Các mảng bắt đầu từ ngày `ngay0`."""
    T = so_ngay or len(nhu_cau if nhu_cau is not None else d_hat)
    rng = np.random.default_rng(seed)
    lay_rop = rop if callable(rop) else (lambda t, _: rop[t])
    lay_q = q if callable(q) else (lambda t, _: q[t])
    kho = [[float(ton_kho0), float(han_con_lai0 if han_con_lai0 is not None else han_dung / 2)]] if ton_kho0 > 0 else []
    duong = [(L, float(hang_ve0))] if hang_ve0 > 0 else []          # hàng đang về giả định về sau L ngày
    da_qua = np.zeros(T)
    rows = []
    for t in range(T):
        ve = sum(x for d, x in duong if d <= t)
        duong = [(d, x) for d, x in duong if d > t]
        if ve > 0:
            kho.append([ve, t + han_dung])
        het_han = sum(b[0] for b in kho if b[1] <= t)
        kho = [b for b in kho if b[1] > t]
        if nhu_cau is not None:
            nc = float(nhu_cau[t])
        else:
            nc = float(rng.poisson(d_hat[t])) if ngau_nhien else float(d_hat[t])
        da_qua[t] = nc
        can = nc
        for b in kho:                                               # FIFO
            lay = min(b[0], can)
            b[0] -= lay
            can -= lay
            if can <= 1e-12:
                break
        kho = [b for b in kho if b[0] > 1e-9]
        ton = sum(b[0] for b in kho)
        dang_ve = sum(x for _, x in duong)
        dat = 0.0
        r_t = float(lay_rop(t, da_qua[:t + 1]))
        if cho_phep_dat and ton + dang_ve <= r_t:
            q_t = float(lay_q(t, da_qua[:t + 1]))
            dat = max(1, math.ceil((r_t - (ton + dang_ve)) / q_t)) * q_t
            lt = int(lead_times[t]) if lead_times is not None else L
            duong.append((t + max(1, lt), dat))
        rows.append({"ngay": pd.Timestamp(ngay0) + pd.Timedelta(days=t), "nhu_cau": nc, "ban": nc - max(can, 0.0),
                     "hang_ve": ve, "het_han": het_han, "thieu_hang": max(can, 0.0), "ton_kho": ton,
                     "hang_dang_ve": dang_ve + dat, "muc_ton_kho_tong": ton + dang_ve + dat,
                     "rop": r_t, "ton_kho_an_toan": float(ss[t]) if ss is not None else np.nan, "dat_hang": dat})
    return pd.DataFrame(rows)


def ngay_dat_muon_nhat(d_hat, ss, L, ton_kho0, hang_ve0, han_dung, ngay0, ngay_xet=60):
    """Nếu không đặt thêm, ngày nào tồn kho thực tế chạm mức an toàn? Từ đó suy ra ngày đặt muộn nhất."""
    T = min(ngay_xet, len(ss))
    z = np.zeros(T)
    s = mo_phong(d_hat, z, ss, np.ones(T), L, ton_kho0, hang_ve0, han_dung, ngay0, so_ngay=T, cho_phep_dat=False)
    cham = s.index[s["ton_kho"] <= s["ton_kho_an_toan"] + 1e-9]
    if len(cham) == 0:
        return None
    t_cham = int(cham[0])
    return {"ngay_cham_an_toan": s.loc[t_cham, "ngay"], "dat_muon_nhat": t_cham - L,
            "ngay_dat_muon_nhat": pd.Timestamp(ngay0) + pd.Timedelta(days=t_cham - L)}


def danh_gia_hom_nay(kq, k, ton_kho, hang_ve, tp, ngay_bat_dau):
    """Khuyến nghị tại ngày thứ k của khung dự báo."""
    rop, ss, q, L = kq["rop"][k], kq["ss"][k], kq["q"][k], kq["L"]
    vi_tri = ton_kho + hang_ve
    ma, muc, nhan, giai_thich = trang_thai(vi_tri, ton_kho, rop, ss)
    nhap = 0
    if vi_tri <= rop:
        nhap = int(max(1, math.ceil((rop - vi_tri) / q)) * q)
    ngay0 = pd.Timestamp(ngay_bat_dau) + pd.Timedelta(days=k)
    gioi_han = max(1, min(60, kq["so_ngay"] - k))
    muon = ngay_dat_muon_nhat(kq["d_hat"][k:k + gioi_han], kq["ss"][k:k + gioi_han], L, ton_kho, hang_ve,
                              tp["han_dung_ngay"], ngay0, ngay_xet=gioi_han)
    return {"du_bao_ngay": float(kq["d_hat"][k]), "rop": float(rop), "ton_kho_an_toan": float(ss), "q": float(q),
            "vi_tri": vi_tri, "ma": ma, "muc": muc, "nhan": nhan, "giai_thich": giai_thich,
            "nhap": nhap, "von_can": nhap * float(tp["gia_von"]), "muon": muon, "L": L}


def chi_phi(sim, tp):
    """Ước tính chi phí của một lần mô phỏng (VND)."""
    dat = int((sim["dat_hang"] > 0).sum())
    giu = float((sim["ton_kho"] * tp["gia_von"] * tp["ty_le_giu_hang_nam"] / 365).sum())
    het = float(sim["het_han"].sum() * tp["gia_von"])
    thieu = float(sim["thieu_hang"].sum() * (tp["gia_ban"] - tp["gia_von"]))
    c = {"so_lan_dat": dat, "chi_phi_dat_hang": dat * tp["chi_phi_dat_hang"], "chi_phi_giu_hang": giu,
         "hang_het_han": het, "loi_nhuan_mat": thieu,
         "ty_le_dap_ung": float(sim["ban"].sum() / max(sim["nhu_cau"].sum(), 1e-9)),
         "sl_het_han": float(sim["het_han"].sum()), "sl_thieu": float(sim["thieu_hang"].sum())}
    c["tong"] = c["chi_phi_dat_hang"] + giu + het + thieu
    return c
