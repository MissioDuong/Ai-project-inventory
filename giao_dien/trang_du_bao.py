# -*- coding: utf-8 -*-
"""Trang 📈 Dự báo: dự báo mùa vụ từng mặt hàng, hệ số thứ/Tết/Trung thu, kiểm định theo mùa, AI phân tích."""
import numpy as np
import pandas as pd
import streamlit as st
from giao_dien.kieu import tieu_de
from giao_dien.tien_ich import kiem_dinh
from giao_dien.khung_ai import hop_phan_tich


def ve(ctx):
    """Vẽ trang Dự báo."""
    so_ngay, xu_huong, ban_hang, skus, kh = ctx.so_ngay, ctx.xu_huong, ctx.ban_hang, ctx.skus, ctx.kh
    tieu_de("📈", "Dự báo nhu cầu", "Nhu cầu ngày = mức nền × hệ số thứ × hệ số Tết × hệ số Trung thu, tính từ dữ liệu bán hàng")
    m2 = st.selectbox("Mặt hàng", skus, key="db_mh")
    v2 = kh["mat_hang"][m2]
    mh2 = v2["mo_hinh"]
    if mh2["so_mua_tet"] == 0:
        st.warning("Dữ liệu chưa có mùa Tết nào nên hệ số Tết đang bằng 1: dự báo sẽ không thấy đỉnh Tết.")
    if mh2["so_mua_trung_thu"] == 0:
        st.warning("Dữ liệu chưa có mùa Trung thu nào nên hệ số Trung thu đang bằng 1.")
    a, b, c, d = st.columns(4)
    a.metric("📏 Mức nền (đv/ngày)", f"{mh2['muc_nen']:.1f}")
    b.metric("🧧 Mùa Tết trong dữ liệu", mh2["so_mua_tet"])
    c.metric("🥮 Mùa Trung thu trong dữ liệu", mh2["so_mua_trung_thu"])
    me = v2["meta"]
    d.metric("🎯 Sai số dự báo (WAPE)", f"{me['wape_du_bao']:.0%}" if me.get("ngoai_mau") else "—",
             delta=f"{me['wape_du_bao'] - me['wape_trung_binh']:+.0%} so với dùng trung bình" if me.get("ngoai_mau") else None,
             delta_color="inverse")
    with st.container(border=True):
        st.markdown("##### Đã bán và dự báo")
        st.line_chart(pd.concat([ban_hang[m2].tail(365).rename("Đã bán"),
                                 pd.Series(v2["d_hat"][:so_ngay], index=v2["ngay"][:so_ngay], name="Dự báo")], axis=1),
                      color=["#9aa5b1", "#ff3d81"])
    _d = np.asarray(v2["d_hat"][:so_ngay], float)
    _ng = pd.DatetimeIndex(v2["ngay"][:so_ngay])
    _ls = ban_hang[m2].tail(365)
    _kd = kiem_dinh(ban_hang[m2], xu_huong)
    hop_phan_tich(ctx, f"db_{m2}", f"dự báo của {m2}", {
        "mat_hang": m2, "muc_nen_ngay_thuong": round(mh2["muc_nen"], 2),
        "he_so_thu_T2_den_CN": [round(x, 2) for x in mh2["he_so_thu"]],
        "he_so_tet_cao_nhat": round(float(mh2["he_so_tet"].max()), 2),
        "so_ngay_truoc_tet_ban_dinh": int(mh2["he_so_tet"].idxmax()),
        "he_so_trung_thu_cao_nhat": round(float(mh2["he_so_trung_thu"].max()), 2),
        "so_mua_tet_trong_du_lieu": mh2["so_mua_tet"], "so_mua_trung_thu_trong_du_lieu": mh2["so_mua_trung_thu"],
        "da_ban_365_ngay_gan_nhat": {"tong": float(np.nansum(_ls)), "tb_ngay": round(float(np.nanmean(_ls)), 2),
                                     "cao_nhat": float(np.nanmax(_ls))},
        "du_bao": {"tu_ngay": str(_ng[0].date()), "so_ngay": len(_d), "tong": round(float(_d.sum())),
                   "tb_ngay": round(float(_d.mean()), 2), "ngay_dinh": str(_ng[int(_d.argmax())].date()),
                   "luong_ngay_dinh": round(float(_d.max()), 1),
                   "theo_tuan": [round(float(_d[i:i + 7].sum())) for i in range(0, min(len(_d), 84), 7)]},
        "sai_so_wape_ngoai_mau": me.get("wape_du_bao"), "sai_so_neu_dung_trung_binh": me.get("wape_trung_binh"),
        "kiem_dinh_theo_mua": [] if not len(_kd) else
        _kd[["mua", "nam", "wape_dinh_mo_hinh", "wape_dinh_nam_ngoai", "lech_tong_dinh"]].round(3).to_dict("records")})
    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.markdown("**Hệ số thứ trong tuần**")
        st.bar_chart(pd.Series(mh2["he_so_thu"], index=["1.T2", "2.T3", "3.T4", "4.T5", "5.T6", "6.T7", "7.CN"]), color="#ff7a45")
    with c2.container(border=True):
        st.markdown("**Hệ số Tết** (số ngày tới mùng 1)")
        st.line_chart(mh2["he_so_tet"], color="#e45756")
    with c3.container(border=True):
        st.markdown("**Hệ số Trung thu** (số ngày tới Rằm)")
        st.line_chart(mh2["he_so_trung_thu"], color="#f2a541")
    with st.container(border=True):
        st.markdown("##### 🧪 Kiểm định theo mùa: nếu dùng mô hình này từ trước, nó sẽ đoán đúng tới đâu?")
        st.caption("Với mỗi mùa Tết / Trung thu có trong dữ liệu: chỉ học từ dữ liệu trước mốc (60 ngày trước Tết, 45 ngày trước "
                   "Trung thu), dự báo 90 ngày tiếp theo rồi so với thực tế. WAPE càng thấp càng tốt.")
        kd = kiem_dinh(ban_hang[m2], xu_huong)
        if len(kd):
            hien = pd.DataFrame({
                "Mùa": kd["mua"] + " " + kd["nam"].astype(str), "Mốc dự báo": kd["moc_du_bao"].astype(str),
                "Mô hình (đỉnh mùa)": kd["wape_dinh_mo_hinh"] * 100, "Trung bình 56 ngày (đỉnh)": kd["wape_dinh_trung_binh_56"] * 100,
                "Năm ngoái cùng ngày (đỉnh)": kd["wape_dinh_nam_ngoai"] * 100, "Mô hình (90 ngày)": kd["wape_mo_hinh"] * 100,
                "Dự báo lệch ở đỉnh": kd["lech_tong_dinh"] * 100})
            st.dataframe(hien.round(1), hide_index=True, use_container_width=True,
                         column_config={c: st.column_config.NumberColumn(format="%.1f%%") for c in hien.columns[2:]})
            st.caption("'Năm ngoái cùng ngày' là cách nhiều tiểu thương vẫn làm (xem sổ năm ngoái theo lịch dương). Vì Tết và "
                       "Trung thu đổi ngày dương lịch mỗi năm nên cách này lệch nhiều ở đỉnh mùa. 'Dự báo lệch ở đỉnh' dương là "
                       "dự báo dư, âm là dự báo thiếu.")
        else:
            st.info("Chưa đủ dữ liệu để kiểm định theo mùa (cần ít nhất 180 ngày trước một mùa Tết/Trung thu và có dữ liệu qua "
                    "đỉnh mùa đó).")
    with st.expander("Bảng sai số dự báo của tất cả mặt hàng"):
        st.dataframe(pd.DataFrame([{"Mặt hàng": m,
                                    "Sai số dự báo mùa vụ": f"{v['meta']['wape_du_bao']:.0%}" if v["meta"].get("ngoai_mau") else "—",
                                    "Sai số nếu dùng trung bình": f"{v['meta']['wape_trung_binh']:.0%}" if v["meta"].get("ngoai_mau") else "—"}
                                   for m, v in kh["mat_hang"].items()]), hide_index=True, use_container_width=True)
        st.caption("Đo trên 30% dữ liệu cuối (cần ≥ 240 ngày). Mặt hàng mà dự báo mùa vụ không hơn trung bình là hàng bán đều.")
