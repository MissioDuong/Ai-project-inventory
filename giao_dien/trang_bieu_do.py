# -*- coding: utf-8 -*-
"""Trang Phân tích › Biểu đồ: đã bán và dự báo, sơ đồ tồn kho có Reorder Point, Reorder Point theo mùa, tồn kho đếm được (sổ kiểm kho),
hệ số mùa vụ, lượng bán theo tuần. Mỗi biểu đồ có ô AI phân tích bên cạnh, nhận đúng số liệu của biểu đồ đó."""
import numpy as np
import pandas as pd
import streamlit as st

from tinh_toan import loi, so_ghi
from giao_dien import bieu_do as bd
from giao_dien.cau_hinh import noi_luu_so
from giao_dien.du_lieu import TEN_SO_GHI
from giao_dien.kieu import CAO_BIEU_DO, tieu_de
from giao_dien.khung_ai import bieu_do_co_ai, du_lieu_ai_mat_hang, ngay_dang_xem, ton_hien_tai

BANG_MAU = ["#1d5c9c", "#c5372c", "#c98a12", "#1f7a3f", "#7b4fb3", "#0f9fb0", "#c2185b", "#6b7280", "#8d6e63", "#3949ab"]


def _so(x, le=0):
    """Số kiểu Việt: 1.234 hoặc 12,5."""
    return f"{x:,.{le}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _o_so(ds):
    """Dải số: [(nhãn, giá trị, là ROP?)]."""
    html = "".join(f'<div class="{"rop" if r else ""}"><div class="n">{n}</div><div class="s">{s}</div></div>' for n, s, r in ds)
    st.markdown(f'<div class="so-rop">{html}</div>', unsafe_allow_html=True)


def _ngay(x):
    return str(pd.Timestamp(x).date())


def ve(ctx):
    """Vẽ trang Biểu đồ."""
    kh, ban_hang, so_ngay = ctx.kh, ctx.ban_hang, ctx.so_ngay
    tieu_de("📊", "Biểu đồ", "Đã bán, dự báo, tồn kho với điểm đặt hàng (Reorder Point) và mùa vụ · mỗi biểu đồ có AI phân tích bên cạnh")
    m = st.selectbox("Mặt hàng", ctx.skus, key="db_mh")
    v = kh["mat_hang"][m]
    me, mh2 = v["meta"], v["mo_hinh"]
    ngay = pd.DatetimeIndex(v["ngay"][:so_ngay])

    # 1. Đã bán và dự báo
    with bieu_do_co_ai(ctx, "📈 Đã bán và dự báo", f"bd_{m}", f"đã bán và dự báo của {m}", du_lieu_ai_mat_hang(ctx, m)):
        df = pd.concat([ban_hang[m].tail(365).rename("Đã bán"), pd.Series(v["d_hat"][:so_ngay], index=ngay, name="Dự báo")],
                       axis=1)
        bd.duong(df, {"Đã bán": "#9aa5b4", "Dự báo": "#1d5c9c"}, truc_y="Lượng bán mỗi ngày")
        if me.get("khoi_dong"):
            st.caption(f"Dự báo đang là đường phẳng vì mới có {me.get('so_ngay_do', 0)}/{loi.NGAY_DAY_DU} ngày đo. "
                       "Đủ ngày đo thì đường dự báo sẽ lên xuống theo thứ trong tuần và mùa vụ.")

    # 2. Tồn kho dự kiến với Reorder Point
    _, k = ngay_dang_xem(ctx)
    t = ton_hien_tai(ctx).loc[m]
    n = max(min(so_ngay - k, 120), 1)
    rop0, ss0, q0, L = float(v["rop"][k]), float(v["ss"][k]), float(v["q"][k]), int(v["L"])
    vt = float(t["ton_kho"] + t["hang_dang_ve"])
    sim = loi.mo_phong(v["d_hat"][k:k + n], v["rop"][k:k + n], v["ss"][k:k + n], v["q"][k:k + n], L, float(t["ton_kho"]),
                       float(t["hang_dang_ve"]), float(ctx.info.loc[m, "han_con_khi_nhan"]), ctx.bat_dau + pd.Timedelta(days=k),
                       so_ngay=n, han_con_lai0=float(t["han_con_lai"]) or None)
    dat = sim[sim["dat_hang"] > 0]
    ai_rop = {"mat_hang": m, "reorder_point_hom_nay": round(rop0, 1), "ton_an_toan": round(ss0, 1), "luong_moi_lan_dat_Q": q0,
              "giao_sau_ngay": L, "ban_trong_thoi_gian_cho": round(rop0 - ss0, 1), "dang_co_cong_dang_ve": vt,
              "so_ngay_mo_phong": n, "so_lan_dat_hang": int(len(dat)),
              "cac_lan_dat": [{"ngay": _ngay(r["ngay"]), "luong": float(r["dat_hang"])} for _, r in dat.head(8).iterrows()],
              "ton_kho_thap_nhat": float(sim["ton_kho"].min()), "ton_kho_trung_binh": round(float(sim["ton_kho"].mean()), 1),
              "so_ngay_duoi_ton_an_toan": int((sim["ton_kho"] < sim["ton_kho_an_toan"]).sum()),
              "so_ngay_thieu_hang": int((sim["thieu_hang"] > 0).sum()), "hang_het_han": float(sim["het_han"].sum()),
              "gia_dinh": "bán đúng dự báo, mỗi mặt hàng đặt riêng (chưa gộp chuyến theo nguồn)"}
    with bieu_do_co_ai(ctx, "📦 Tồn kho dự kiến và điểm đặt hàng (Reorder Point)", f"bd_rop_{m}",
                       f"tồn kho dự kiến và Reorder Point của {m}", ai_rop):
        _o_so([("Reorder Point hôm nay", _so(rop0), True), ("Tồn an toàn", _so(ss0), False),
               (f"Bán trong {L} ngày chờ hàng", _so(rop0 - ss0, 1), False), ("Mỗi lần đặt (Q)", _so(q0), False),
               ("Đang có + đang về", _so(vt), False)])
        bd.ton_kho_rop(sim, rop0, ss0, q0, L)
        st.caption(f"Reorder Point = lượng bán dự kiến trong {L} ngày chờ hàng + tồn an toàn. Mỗi cuối ngày, nếu **đang có + đang về** "
                   f"(đường xanh nhạt) chạm hoặc xuống dưới đường đỏ thì đặt hàng (▼); hàng về sau {L} ngày (▲) và tồn kho nhảy lên. "
                   "Tồn kho thực tế không nên xuống dưới đường xanh lá. Giả định bán đúng dự báo, mỗi mặt hàng đặt riêng; danh sách "
                   "đi chợ ở trang Hôm nay còn gộp chuyến theo nguồn hàng. Tồn kho ban đầu lấy từ bảng ở trang Hôm nay.")

    # 3. Reorder Point theo mùa
    rop_s, ss_s = pd.Series(v["rop"][:so_ngay], index=ngay), pd.Series(v["ss"][:so_ngay], index=ngay)
    ai_mua = {"mat_hang": m, "so_ngay": so_ngay, "reorder_point": {"thap_nhat": round(rop_s.min(), 1), "cao_nhat": round(rop_s.max(), 1),
                                                                   "ngay_cao_nhat": _ngay(rop_s.idxmax()),
                                                                   "trung_binh": round(rop_s.mean(), 1)},
              "ton_an_toan": {"thap_nhat": round(ss_s.min(), 1), "cao_nhat": round(ss_s.max(), 1)},
              "theo_tuan_reorder_point": [round(float(x), 1) for x in rop_s.resample("W").mean().head(20)]}
    with bieu_do_co_ai(ctx, "🎯 Reorder Point và tồn an toàn thay đổi theo mùa", f"bd_mua_{m}",
                       f"Reorder Point theo mùa của {m}", ai_mua):
        bd.duong(pd.DataFrame({"Điểm đặt hàng (Reorder Point)": rop_s, "Tồn an toàn": ss_s}),
                 {"Điểm đặt hàng (Reorder Point)": "#c5372c", "Tồn an toàn": "#1f7a3f"}, net_dut=("Tồn an toàn",))
        st.caption("Đường đỏ cao lên trước mùa đắt hàng (Tết, Trung thu) nghĩa là phải đặt sớm hơn, nhiều hơn.")

    # 4. Tồn kho đếm được (chỉ khi dùng sổ kiểm kho)
    if ctx.ten_nguon == TEN_SO_GHI:
        kk, _ = so_ghi.doc_so(noi_luu_so())
        dem = kk[kk["mat_hang"] == m].set_index("ngay")["ton_cuoi_ngay"]
        ai_dem = {"mat_hang": m, "so_lan_dem": int(len(dem)), "reorder_point_hom_nay": round(rop0, 1),
                  "14_lan_dem_gan_nhat": [{"ngay": _ngay(d), "con": float(x)} for d, x in dem.tail(14).items()],
                  "so_lan_duoi_reorder_point": int((dem <= rop0).sum()), "thap_nhat": float(dem.min()) if len(dem) else None}
        with bieu_do_co_ai(ctx, "🧮 Tồn kho đếm được (sổ kiểm kho)", f"bd_dem_{m}", f"tồn kho đếm được của {m}", ai_dem):
            if len(dem) >= 2:
                bd.duong(pd.DataFrame({"Đếm được còn": dem, "Reorder Point hôm nay": rop0}),
                         {"Đếm được còn": "#1d5c9c", "Reorder Point hôm nay": "#c5372c"}, net_dut=("Reorder Point hôm nay",))
            else:
                st.caption("Cần ít nhất hai lần đếm để vẽ.")

    # 5. Hệ số mùa vụ
    if not me.get("khoi_dong"):
        ai_hs = {"mat_hang": m, "he_so_thu_T2_den_CN": [round(float(x), 2) for x in mh2["he_so_thu"]],
                 "tet": {"cao_nhat": round(float(mh2["he_so_tet"].max()), 2), "so_ngay_tu_mung_1": int(mh2["he_so_tet"].idxmax()),
                         "so_mua_da_thay": mh2["so_mua_tet"]},
                 "trung_thu": {"cao_nhat": round(float(mh2["he_so_trung_thu"].max()), 2),
                               "so_ngay_tu_ram": int(mh2["he_so_trung_thu"].idxmax()), "so_mua_da_thay": mh2["so_mua_trung_thu"]},
                 "y_nghia": "1,0 = bán như ngày thường; số ngày âm = trước ngày lễ"}
        with bieu_do_co_ai(ctx, "🗓️ Hệ số mùa vụ", f"bd_hs_{m}", f"hệ số mùa vụ của {m}", ai_hs):
            t1, t2, t3 = st.tabs(["Thứ trong tuần", "Tết (số ngày tới mùng 1)", "Trung thu (số ngày tới Rằm)"])
            with t1:
                bd.cot(pd.DataFrame({"Hệ số": mh2["he_so_thu"]}, index=["T2", "T3", "T4", "T5", "T6", "T7", "CN"]),
                       {"Hệ số": "#1d5c9c"}, cao=CAO_BIEU_DO - 60, truc_y="Hệ số")
            with t2:
                bd.duong(mh2["he_so_tet"].to_frame("Hệ số Tết"), {"Hệ số Tết": "#c5372c"}, cao=CAO_BIEU_DO - 60, truc_y="Hệ số",
                         truc_x="Số ngày tới mùng 1 Tết", kieu_x="Q")
            with t3:
                bd.duong(mh2["he_so_trung_thu"].to_frame("Hệ số Trung thu"), {"Hệ số Trung thu": "#c98a12"},
                         cao=CAO_BIEU_DO - 60, truc_y="Hệ số", truc_x="Số ngày tới Rằm tháng Tám", kieu_x="Q")
            st.caption("1,0 = bán như ngày thường; 2,0 = gấp đôi ngày thường.")
    else:
        st.info(f"Hệ số thứ trong tuần, Tết, Trung thu sẽ hiện khi mặt hàng này có đủ {loi.NGAY_DAY_DU} ngày đo.")

    # 6. Lượng bán theo tuần, mọi mặt hàng
    tuan = ban_hang.resample("W").sum(min_count=1).dropna(how="all").tail(26)
    ai_tuan = {"so_tuan": int(len(tuan)),
               "theo_mat_hang": {c: {"tong_26_tuan": float(np.nansum(tuan[c])),
                                     "tb_4_tuan_gan_nhat": round(float(np.nanmean(tuan[c].tail(4))), 1) if tuan[c].tail(4).notna().any() else None,
                                     "tb_4_tuan_truoc_do": round(float(np.nanmean(tuan[c].iloc[-8:-4])), 1)
                                     if len(tuan) >= 8 and tuan[c].iloc[-8:-4].notna().any() else None}
                                 for c in tuan.columns}}
    with bieu_do_co_ai(ctx, "🗓️ Lượng bán theo tuần, mọi mặt hàng (26 tuần gần nhất)", "bd_tuan",
                       "lượng bán theo tuần của mọi mặt hàng", ai_tuan):
        if len(tuan):
            tuan.index = tuan.index.strftime("%d/%m/%y")
            bd.cot(tuan, {c: BANG_MAU[i % len(BANG_MAU)] for i, c in enumerate(tuan.columns)}, truc_y="Lượng bán / tuần",
                   truc_x="Tuần kết thúc ngày")
        else:
            st.caption("Chưa có tuần nào đo được lượng bán.")
