# -*- coding: utf-8 -*-
"""Biểu đồ dùng chung (Altair): chữ trục và chú thích lớn, màu đậm dễ đọc, màu gán đúng theo tên đường.

st.line_chart / st.bar_chart không chỉnh được cỡ chữ và gán màu theo tên cột đã xếp chữ cái, nên các trang dùng
các hàm ở đây thay thế. Hàm ton_kho_rop vẽ sơ đồ tồn kho kinh điển: tồn kho răng cưa, Reorder Point, tồn an toàn,
điểm đặt hàng và hàng về.
"""
import altair as alt
import streamlit as st

from giao_dien.kieu import CAO_BIEU_DO

CHU, CHU_PHU, LUOI = "#1f2937", "#374151", "#e5e7eb"
CO_CHU = 15


def _cau_hinh(c, cao):
    return (c.properties(height=cao)
            .configure(font="Be Vietnam Pro, Segoe UI, sans-serif")
            .configure_axis(labelFontSize=CO_CHU, titleFontSize=CO_CHU, labelColor=CHU_PHU, titleColor=CHU, gridColor=LUOI,
                            domainColor="#9ca3af", tickColor="#9ca3af", titleFontWeight=600, labelPadding=6, labelLimit=320)
            .configure_legend(orient="top", labelFontSize=CO_CHU, titleFontSize=CO_CHU, labelColor=CHU, title=None,
                              symbolSize=220, symbolStrokeWidth=4, columnPadding=24, labelLimit=400)
            .configure_view(strokeWidth=0))


def _ve(c, cao):
    st.altair_chart(_cau_hinh(c, cao), use_container_width=True)


def _dai(df, ten_x):
    d = df.copy()
    d.index.name = ten_x
    return d.reset_index().melt(ten_x, var_name="Đường", value_name="Giá trị").dropna(subset=["Giá trị"])


def duong(df, mau, cao=CAO_BIEU_DO, truc_y="Số lượng", truc_x="Ngày", net_dut=(), kieu_x="T"):
    """Biểu đồ đường: df index = trục x, mỗi cột một đường; mau = {tên cột: màu}; net_dut = các cột vẽ nét đứt."""
    d = _dai(df[list(mau)], truc_x)
    chon = alt.selection_point(fields=["Đường"], bind="legend")
    c = alt.Chart(d).mark_line(strokeWidth=2.6).encode(
        x=alt.X(f"{truc_x}:{kieu_x}", title=truc_x),
        y=alt.Y("Giá trị:Q", title=truc_y),
        color=alt.Color("Đường:N", scale=alt.Scale(domain=list(mau), range=list(mau.values())), sort=list(mau)),
        strokeDash=alt.condition(alt.FieldOneOfPredicate("Đường", list(net_dut)), alt.value([7, 5]), alt.value([1, 0])),
        opacity=alt.condition(chon, alt.value(1), alt.value(0.2)),
        tooltip=[alt.Tooltip(f"{truc_x}:{kieu_x}", title=truc_x), "Đường:N", alt.Tooltip("Giá trị:Q", format=",.1f")],
    ).add_params(chon)
    _ve(c, cao)


def cot(df, mau, cao=CAO_BIEU_DO, truc_y="Số lượng", truc_x="", ngang=False, chong=True, kieu_x="O"):
    """Biểu đồ cột (chồng nếu nhiều cột). df index = nhóm; mau = {tên cột: màu}."""
    d = _dai(df[list(mau)], truc_x or "Nhóm")
    tx = truc_x or "Nhóm"
    mau_enc = alt.Color("Đường:N", scale=alt.Scale(domain=list(mau), range=list(mau.values())), sort=list(mau),
                        legend=None if len(mau) == 1 else alt.Legend())
    gia_tri = alt.X("Giá trị:Q", title=truc_y, stack=chong) if ngang else alt.Y("Giá trị:Q", title=truc_y, stack=chong)
    nhom = alt.Y(f"{tx}:{kieu_x}", title=truc_x or None, sort=list(df.index)) if ngang else \
        alt.X(f"{tx}:{kieu_x}", title=truc_x or None, sort=list(df.index), axis=alt.Axis(labelAngle=0))
    c = alt.Chart(d).mark_bar().encode(
        x=gia_tri if ngang else nhom, y=nhom if ngang else gia_tri, color=mau_enc,
        tooltip=[alt.Tooltip(f"{tx}:{kieu_x}", title=truc_x or "Nhóm"), "Đường:N", alt.Tooltip("Giá trị:Q", format=",.1f")])
    _ve(c, cao)


def ton_kho_rop(sim, rop, ss, q, L, don_vi="đv", cao=CAO_BIEU_DO + 60):
    """Sơ đồ tồn kho có Reorder Point.
    sim: kết quả loi.mo_phong (cột ngay, ton_kho, muc_ton_kho_tong, rop, ton_kho_an_toan, dat_hang, hang_ve)."""
    d = sim.copy()
    nen = alt.Chart(d)
    x = alt.X("ngay:T", title="Ngày")
    ton = nen.mark_area(line={"color": "#1d5c9c", "strokeWidth": 2.6}, color="#1d5c9c", opacity=0.12,
                        interpolate="step-after").encode(
        x=x, y=alt.Y("ton_kho:Q", title=f"Tồn kho ({don_vi})"),
        tooltip=[alt.Tooltip("ngay:T", title="Ngày"), alt.Tooltip("ton_kho:Q", title="Tồn kho thực tế", format=",.0f"),
                 alt.Tooltip("muc_ton_kho_tong:Q", title="Gồm hàng đang về", format=",.0f"),
                 alt.Tooltip("rop:Q", title="Điểm đặt hàng (ROP)", format=",.1f")])
    tong = nen.mark_line(color="#7aa6d6", strokeWidth=1.8, strokeDash=[3, 3], interpolate="step-after").encode(
        x=x, y="muc_ton_kho_tong:Q")
    duong_rop = nen.mark_line(color="#c5372c", strokeWidth=2.6, strokeDash=[9, 5]).encode(x=x, y="rop:Q")
    duong_ss = nen.mark_line(color="#1f7a3f", strokeWidth=2.4, strokeDash=[4, 4]).encode(x=x, y="ton_kho_an_toan:Q")
    cuoi = d.iloc[[-1]]                                        # nhãn ở cuối biểu đồ, xếp chồng phía trên hai đường (hai đường thường sát nhau)
    chu_rop = alt.Chart(cuoi.assign(nhan=f"Reorder Point ≈ {rop:.0f}")).mark_text(
        align="right", dx=-4, dy=-32, fontSize=CO_CHU + 1, fontWeight="bold", color="#c5372c").encode(
        x="ngay:T", y="rop:Q", text="nhan:N")
    chu_ss = alt.Chart(cuoi.assign(nhan=f"Tồn an toàn ≈ {ss:.0f}")).mark_text(
        align="right", dx=-4, dy=-12, fontSize=CO_CHU, fontWeight="bold", color="#1f7a3f").encode(
        x="ngay:T", y="ton_kho_an_toan:Q", text="nhan:N")
    chu = chu_rop + chu_ss
    dat = d[d["dat_hang"] > 0]
    diem_dat = alt.Chart(dat).mark_point(shape="triangle-down", size=220, filled=True, color="#c5372c").encode(
        x="ngay:T", y="muc_ton_kho_tong:Q",
        tooltip=[alt.Tooltip("ngay:T", title="Đặt hàng ngày"), alt.Tooltip("dat_hang:Q", title="Lượng đặt", format=",.0f")])
    ve = d[d["hang_ve"] > 0]
    diem_ve = alt.Chart(ve).mark_point(shape="triangle-up", size=200, filled=True, color="#1d5c9c").encode(
        x="ngay:T", y="ton_kho:Q",
        tooltip=[alt.Tooltip("ngay:T", title="Hàng về ngày"), alt.Tooltip("hang_ve:Q", title="Lượng về", format=",.0f")])
    _ve(alt.layer(ton, tong, duong_ss, duong_rop, diem_dat, diem_ve, chu), cao)
    st.markdown(
        '<div class="chu-giai">'
        '<span><i style="background:#1d5c9c"></i>Tồn kho thực tế</span>'
        '<span><i class="dut" style="border-color:#7aa6d6"></i>Gồm hàng đang về</span>'
        '<span><i class="dut" style="border-color:#c5372c"></i>Điểm đặt hàng (Reorder Point)</span>'
        '<span><i class="dut" style="border-color:#1f7a3f"></i>Tồn an toàn</span>'
        '<span><b style="color:#c5372c">▼</b> Ngày đặt hàng</span><span><b style="color:#1d5c9c">▲</b> Ngày hàng về</span>'
        '</div>', unsafe_allow_html=True)
