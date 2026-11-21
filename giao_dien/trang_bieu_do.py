# -*- coding: utf-8 -*-
"""Trang 📊 Biểu đồ: đã bán và dự báo, điểm đặt hàng theo ngày, tồn kho đếm được (sổ kiểm kho), hệ số mùa vụ,
lượng bán theo tuần của mọi mặt hàng; AI phân tích biểu đồ."""
import pandas as pd
import streamlit as st

from tinh_toan import loi, so_ghi
from giao_dien.cau_hinh import noi_luu_so
from giao_dien.du_lieu import TEN_SO_GHI
from giao_dien.kieu import CAO_BIEU_DO, tieu_de
from giao_dien.khung_ai import du_lieu_ai_mat_hang, hop_phan_tich
from giao_dien.tien_ich import mau_cot


def ve(ctx):
    """Vẽ trang Biểu đồ."""
    kh, ban_hang, so_ngay = ctx.kh, ctx.ban_hang, ctx.so_ngay
    tieu_de("📊", "Biểu đồ", "Đã bán, dự báo, điểm đặt hàng và mùa vụ của từng mặt hàng")
    m = st.selectbox("Mặt hàng", ctx.skus, key="db_mh")
    v = kh["mat_hang"][m]
    me, mh2 = v["meta"], v["mo_hinh"]
    ngay = pd.DatetimeIndex(v["ngay"][:so_ngay])

    with st.container(border=True):
        st.markdown("##### 📈 Đã bán và dự báo")
        df = pd.concat([ban_hang[m].tail(365).rename("Đã bán"), pd.Series(v["d_hat"][:so_ngay], index=ngay, name="Dự báo")],
                       axis=1)
        st.line_chart(df, color=mau_cot(df, {"Đã bán": "#9aa5b4", "Dự báo": "#1d5c9c"}), height=CAO_BIEU_DO)
        if me.get("khoi_dong"):
            st.caption(f"Dự báo đang là đường phẳng vì mới có {me.get('so_ngay_do', 0)}/{loi.NGAY_DAY_DU} ngày đo. "
                       "Đủ ngày đo thì đường dự báo sẽ lên xuống theo thứ trong tuần và mùa vụ.")

    with st.container(border=True):
        st.markdown("##### 🎯 Điểm đặt hàng và tồn an toàn theo ngày")
        df = pd.DataFrame({"Điểm đặt hàng": v["rop"][:so_ngay], "Tồn an toàn": v["ss"][:so_ngay]}, index=ngay)
        st.line_chart(df, color=mau_cot(df, {"Điểm đặt hàng": "#d93025", "Tồn an toàn": "#1e8e3e"}), height=CAO_BIEU_DO)
        st.caption("Đang có + đang về chạm đường đỏ thì đặt hàng. Đường đỏ cao lên trước mùa đắt hàng (Tết, Trung thu) "
                   "nghĩa là phải đặt sớm hơn, nhiều hơn.")

    if ctx.ten_nguon == TEN_SO_GHI:
        kk, _ = so_ghi.doc_so(noi_luu_so())
        dem = kk[kk["mat_hang"] == m].set_index("ngay")["ton_cuoi_ngay"]
        with st.container(border=True):
            st.markdown("##### 🧮 Tồn kho đếm được (sổ kiểm kho)")
            if len(dem) >= 2:
                df = pd.DataFrame({"Đếm được còn": dem, "Điểm đặt hàng hiện tại": float(v["rop"][0])})
                st.line_chart(df, color=mau_cot(df, {"Đếm được còn": "#1d5c9c", "Điểm đặt hàng hiện tại": "#d93025"}), height=CAO_BIEU_DO)
            else:
                st.caption("Cần ít nhất hai lần đếm để vẽ.")

    if not me.get("khoi_dong"):
        with st.container(border=True):
            st.markdown("##### 🗓️ Hệ số mùa vụ")
            t1, t2, t3 = st.tabs(["Thứ trong tuần", "Tết (số ngày tới mùng 1)", "Trung thu (số ngày tới Rằm)"])
            t1.bar_chart(pd.Series(mh2["he_so_thu"], index=["1.T2", "2.T3", "3.T4", "4.T5", "5.T6", "6.T7", "7.CN"]),
                         color="#1d5c9c", height=CAO_BIEU_DO - 60)
            t2.line_chart(mh2["he_so_tet"], color="#d93025", height=CAO_BIEU_DO - 60)
            t3.line_chart(mh2["he_so_trung_thu"], color="#e8a317", height=CAO_BIEU_DO - 60)
            st.caption("1,0 = bán như ngày thường; 2,0 = gấp đôi ngày thường.")
    else:
        st.info(f"Hệ số thứ trong tuần, Tết, Trung thu sẽ hiện khi mặt hàng này có đủ {loi.NGAY_DAY_DU} ngày đo.")

    tuan = ban_hang.resample("W").sum(min_count=1).dropna(how="all").tail(26)
    with st.container(border=True):
        st.markdown("##### 🗓️ Lượng bán theo tuần, mọi mặt hàng (26 tuần gần nhất)")
        if len(tuan):
            st.bar_chart(tuan, height=CAO_BIEU_DO)
        else:
            st.caption("Chưa có tuần nào đo được lượng bán.")

    hop_phan_tich(ctx, f"bd_{m}", f"biểu đồ của {m}", du_lieu_ai_mat_hang(ctx, m))
