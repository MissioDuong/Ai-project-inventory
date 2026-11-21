# -*- coding: utf-8 -*-
"""Trang 🧪 Mô phỏng & so sánh: so sánh chính sách A/B/C/C+G/C+G+E/D, ablation, AI phân tích."""
import pandas as pd
import streamlit as st
from tinh_toan import nhieu_mat_hang as nm
from giao_dien.kieu import tieu_de
from giao_dien.tien_ich import mo_phong, tien
from giao_dien.khung_ai import hop_phan_tich

ss = st.session_state


def ve(ctx):
    """Vẽ trang Mô phỏng."""
    so_ngay, von, xu_huong, ban_hang, skus, mh, nguon, khu, kh = ctx.so_ngay, ctx.von, ctx.xu_huong, ctx.ban_hang, ctx.skus, ctx.mh, ctx.nguon, ctx.khu, ctx.kh
    tieu_de("🧪", "Mô phỏng & so sánh", "Cùng nhu cầu, cùng thời gian giao hàng, chỉ khác cách nhập: cách nào rẻ nhất?")
    n_kd = sum(bool(v["meta"].get("khoi_dong")) for v in kh["mat_hang"].values())
    if n_kd:
        st.info(f"{n_kd}/{len(skus)} mặt hàng chưa đủ ngày đo nên nhu cầu mô phỏng dựa trên ước lượng: kết quả chỉ để tham khảo.")
    with st.expander("Các cách nhập được so sánh", expanded=False):
        st.markdown("- **A. Kinh nghiệm**: còn ít hơn 7 ngày bán thì nhập bằng 14 ngày bán gần nhất.\n"
                    "- **B. EOQ cổ điển**: điểm đặt hàng và lượng nhập cố định, tính từ mức bán trung bình.\n"
                    "- **C. EOQ động từng mặt hàng**: theo dự báo mùa vụ, có hư hỏng và hạn dùng, mỗi mặt hàng tự đặt riêng.\n"
                    "- **C + gộp chuyến**: bước trung gian để đo riêng tác dụng của việc gộp chuyến theo nguồn hàng.\n"
                    "- **C + gộp chuyến + tồn khả dụng**: thêm việc bỏ phần hàng sắp hết hạn khỏi tồn kho khi quyết định.\n"
                    "- **D. Nhập gộp** *(dùng ở trang Hôm nay)*: gộp chuyến theo nguồn hàng, nhập đủ bán một số ngày (đặt-tới-mức), "
                    "giữ trong giới hạn vốn và sức chứa. Mặc định **không** dùng tồn khả dụng (bật ở ô ⚙️ nếu muốn thử).")
    c1, c2 = st.columns(2)
    ss.setdefault("mp_n_ngay", min(so_ngay, 180))
    ss.setdefault("mp_n_lan", 3)
    n_ngay = c1.slider("Số ngày mô phỏng", 30, so_ngay, step=10, key="mp_n_ngay")
    n_lan = c2.slider("Số lần lặp (nhiều hơn = tin cậy hơn, chậm hơn)", 1, 10, step=1, key="mp_n_lan")
    ap_rb = st.toggle("⚖️ So sánh công bằng: áp giới hạn vốn và sức chứa cho MỌI cách nhập", value=True, key="mp_ap_rb",
                      help="Tắt đi để xem A, B, C khi được phép vượt vốn / sức chứa (chỉ để tham khảo, không khả thi)")
    lifo = st.slider("🧺 Khách chọn hàng mới (% nhu cầu lấy lô mới nhất)", 0, 100, 0, step=10, key="mp_lifo",
                     help="Ở chợ, khách hay lựa hàng mới hơn. 0 % = luôn bán hàng cũ trước (FIFO).")
    kq_mp, mau = mo_phong(ban_hang, mh, nguon, khu, so_ngay, float(von), n_ngay, n_lan, ap_rb, xu_huong, lifo / 100,
                          nm.DUNG_TON_KHA_DUNG, uoc_luong=ctx.uoc_luong)
    tb_all = kq_mp.groupby("chinh_sach").mean(numeric_only=True)
    tb = tb_all.loc[["A", "B", "C", "C+G", "C+G+E", "D"]]
    c_rb = tb_all.loc["C_rb" if "C_rb" in tb_all.index else "C", "tong"]
    giam = (1 - tb.loc["D", "tong"] / tb.loc["C", "tong"]) * 100
    a, b, c, d = st.columns(4)
    a.metric("💸 Tổng chi phí với D", tien(tb.loc["D", "tong"]))
    b.metric("📉 D so với C", f"−{giam:.1f}%" if giam > 0 else f"+{-giam:.1f}%", help="Âm là D rẻ hơn")
    if ap_rb:
        c.metric("🔗 Nhờ gộp chuyến", tien(tb.loc["C+G", "tong"] - c_rb), help="Chênh lệch C+G so với C, cùng ràng buộc")
        d.metric("⏳ Nhờ tồn khả dụng", tien(tb.loc["C+G+E", "tong"] - tb.loc["C+G", "tong"]),
                 help="Chênh lệch C+G+E so với C+G. Dương là tồn khả dụng làm tăng chi phí")
    else:
        c.metric("📦 Ngày C vượt sức chứa", int(round(tb.loc["C", "ngay_vuot_suc_chua"])), help="D luôn giữ trong sức chứa")
        d.metric("💰 Ngày C vượt vốn", int(round(tb.loc["C", "ngay_vuot_von"])), help="D luôn giữ trong vốn mỗi ngày")
    bang_cp = pd.DataFrame({
        "Cách nhập": [nm.TEN_CS[p] for p in tb.index],
        "Chuyến hàng": tb["chi_phi_chuyen"], "Dòng hàng": tb["chi_phi_dong_hang"], "Lãi vốn": tb["lai_von"],
        "Bảo quản": tb["bao_quan"], "Hư hỏng": tb["hu_hong"], "Hết hạn": tb["het_han"], "Lợi nhuận mất": tb["loi_nhuan_mat"],
        "TỔNG": tb["tong"], "Số chuyến": tb["so_chuyen"], "Ngày vượt vốn": tb["ngay_vuot_von"],
        "Ngày vượt sức chứa": tb["ngay_vuot_suc_chua"], "Tỷ lệ đáp ứng": tb["ty_le_dap_ung"] * 100,
        "CSL đạt được": tb["csl"] * 100}).round(1)
    with st.container(border=True):
        st.markdown("##### Chi phí theo cách nhập")
        st.dataframe(bang_cp, hide_index=True, use_container_width=True,
                     column_config={**{c_: st.column_config.NumberColumn(format="%d") for c_ in
                                       ["Chuyến hàng", "Dòng hàng", "Lãi vốn", "Bảo quản", "Hư hỏng", "Hết hạn", "Lợi nhuận mất", "TỔNG"]},
                                    "Tỷ lệ đáp ứng": st.column_config.NumberColumn(format="%.1f%%",
                                                                                 help="Lượng bán được / nhu cầu"),
                                    "CSL đạt được": st.column_config.NumberColumn(format="%.1f%%",
                                                                                help="Tỷ lệ chu kỳ bổ sung không có ngày nào hết hàng; "
                                                                                     "so với tham số 'Mức phục vụ' ở trang 📦")})
        st.caption(f"Không tính {min(30, n_ngay // 4)} ngày đầu (giai đoạn khởi động). Tồn đầu = điểm đặt hàng + nửa lượng nhập. "
                   f"Tiền điện cố định của kho ({tien(tb['chi_phi_co_dinh_kho'].iloc[0])}) như nhau với mọi cách nhập nên không cộng vào tổng.")
        st.bar_chart(bang_cp.set_index("Cách nhập")[["Chuyến hàng", "Dòng hàng", "Lãi vốn", "Bảo quản", "Hư hỏng", "Hết hạn",
                                                     "Lợi nhuận mất"]], horizontal=True)
    with st.container(border=True):
        st.markdown("##### 🧩 Mỗi thành phần của D đóng góp bao nhiêu? (cùng giới hạn vốn và sức chứa)")
        buoc = pd.DataFrame({"Bước": ["1. C (có ràng buộc)", "2. + Gộp chuyến theo nguồn", "3. + Tồn khả dụng (C+G+E)"],
                             "Tổng chi phí": [c_rb, tb.loc["C+G", "tong"], tb.loc["C+G+E", "tong"]]})
        buoc["Thay đổi so với bước trước"] = buoc["Tổng chi phí"].diff().fillna(0)
        st.dataframe(buoc, hide_index=True, use_container_width=True,
                     column_config={k: st.column_config.NumberColumn(format="%d") for k in ["Tổng chi phí", "Thay đổi so với bước trước"]})
        st.caption("Âm là giảm chi phí. Trên dữ liệu mô phỏng 20 lần × 365 ngày (pipeline.py), gộp chuyến đóng góp gần như toàn bộ "
                   "phần tiết kiệm; tồn khả dụng không có lợi ích đo được và làm tăng chi phí khi khách hay chọn hàng mới, "
                   "nên D mặc định không dùng.")
    hop_phan_tich(ctx, "mp", "kết quả so sánh các cách nhập hàng", {
        "dieu_kien": {"so_ngay": n_ngay, "so_lan_lap": n_lan, "von_moi_ngay": float(von), "cung_rang_buoc": bool(ap_rb),
                      "ty_le_khach_chon_hang_moi": lifo / 100},
        "bang_chi_phi": bang_cp.drop(columns=["Ngày vượt vốn", "Ngày vượt sức chứa"]).round(0).to_dict("records"),
        "dong_gop_tung_buoc": buoc.round(0).to_dict("records"),
        "chu_thich": "A kinh nghiệm, B EOQ cổ điển, C EOQ động từng mặt hàng, C+G thêm gộp chuyến, C+G+E thêm tồn khả dụng, "
                     "D nhập gộp (khuyến nghị). Chi phí tính bằng đồng."})
    c1, c2 = st.columns(2)
    ngay_mp = pd.DatetimeIndex(kh["ngay"][:n_ngay])
    with c1.container(border=True):
        st.markdown("##### 🧊 Sức chứa đang dùng (lít)")
        z = st.selectbox("Khu", list(kh["khu"].index), key="mp_khu")
        dd = pd.DataFrame({"C": mau["C"][1][z].values, "D": mau["D"][1][z].values}, index=ngay_mp)
        cap = float(kh["khu"].loc[z, "suc_chua_lit"])
        if cap > 0:
            dd["Sức chứa"] = cap
        st.line_chart(dd)
    with c2.container(border=True):
        st.markdown("##### 📦 Tồn kho một mặt hàng")
        m4 = st.selectbox("Mặt hàng", skus, key="mp_mh")
        st.line_chart(pd.DataFrame({p: mau[p][0].query("mat_hang == @m4")["ton_kho"].values for p in "ABCD"}, index=ngay_mp))
    st.caption(("Mọi cách nhập cùng bị giới hạn vốn và sức chứa; đơn vượt giới hạn bị cắt bớt, ưu tiên mặt hàng sắp hết. "
                if ap_rb else "Chỉ C+G và D bị giới hạn; A, B, C được phép vượt (đếm ở các cột 'Ngày vượt'). ") +
               "Mọi cách nhập đều gộp các đơn cùng nguồn, cùng ngày thành một chuyến. Nhu cầu mô phỏng là ngẫu nhiên quanh dự báo. "
               "Để chạy nhiều lần trên cả năm: python pipeline.py")
