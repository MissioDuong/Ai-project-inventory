# -*- coding: utf-8 -*-
"""Trang Phân tích › Dự đoán: mỗi mặt hàng bán bao nhiêu mỗi ngày, tồn an toàn, điểm đặt hàng (ROP), còn mấy ngày thì chạm;
giải thích cách ra con số; kiểm định dự báo theo mùa; AI phân tích. Biểu đồ nằm ở trang Biểu đồ."""
import pandas as pd
import streamlit as st

from tinh_toan import loi
from giao_dien.kieu import DONG_BANG, cao_bang, kpi_hang, tieu_de
from giao_dien.tien_ich import kiem_dinh
from giao_dien.khung_ai import du_lieu_ai_mat_hang, hop_phan_tich, ngay_dang_xem, vi_the_hien_tai

NHAN_NGUON = {"uoc_luong": "🎯 Ước lượng của bạn", "dang_hoc": "📏 Ước lượng + số đo", "day_du": "📈 Mô hình mùa vụ"}


def _cham(t, ngay0, n):
    if t is None:
        return f"🟢 Chưa chạm trong {n} ngày"
    if t == 0:
        return "🔴 Đặt hôm nay"
    return f"{'🟡' if t <= 3 else '🟢'} Sau {t} ngày ({ngay0 + pd.Timedelta(days=t):%d/%m})"


def ve(ctx):
    """Vẽ trang Dự đoán."""
    kh, skus, info = ctx.kh, ctx.skus, ctx.info
    tieu_de("🔮", "Dự đoán", "Mỗi mặt hàng bán bao nhiêu mỗi ngày, còn bao nhiêu thì phải đặt, và bao giờ sẽ chạm mức đó")
    ngay_, k = ngay_dang_xem(ctx)
    ngay0 = pd.Timestamp(ngay_)
    vt = vi_the_hien_tai(ctx)
    rows = []
    for m in skus:
        v = kh["mat_hang"][m]
        n = ctx.so_ngay - k
        t = loi.ngay_cham_diem_dat(v["d_hat"][k:k + n], v["rop"][k:k + n], vt[m])
        rows.append({"Mặt hàng": m, "Bán dự đoán (đv/ngày)": float(v["d_hat"][k]), "Giao sau (ngày)": int(v["L"]),
                     "Tồn an toàn": float(v["ss"][k]), "Điểm đặt hàng": float(v["rop"][k]),
                     "Đang có + đang về": float(vt[m]), "Chạm điểm đặt": _cham(t, ngay0, n),
                     "Số liệu từ": NHAN_NGUON.get(v["meta"].get("che_do"), "📈 Mô hình mùa vụ"), "_t": t,
                     "_kd": bool(v["meta"].get("khoi_dong"))})
    bang = pd.DataFrame(rows)
    n_nay = int((bang["_t"] == 0).sum())
    n_sap = int(bang["_t"].apply(lambda t: t is not None and 0 < t <= 3).sum())
    n_kd = int(bang["_kd"].sum())
    kpi_hang([("🔴 Phải đặt hôm nay", str(n_nay), f"ngày {ngay0:%d/%m/%Y}", "#c5372c"),
              ("🟡 Sắp chạm (≤ 3 ngày)", str(n_sap), "chuẩn bị đi nhập", "#c98a12"),
              ("🎯 Còn dựa vào ước lượng", str(n_kd), f"chưa đủ {loi.NGAY_DAY_DU} ngày đo", "#c98a12" if n_kd else "#9aa5b4"),
              ("📈 Đủ dữ liệu theo mùa", str(len(skus) - n_kd), f"trên {len(skus)} mặt hàng", "#1f7a3f")])

    with st.container(border=True):
        st.markdown("##### 🎯 Khi nào cần đặt hàng")
        st.dataframe(bang.drop(columns=["_t", "_kd"]), hide_index=True, row_height=DONG_BANG, height=cao_bang(len(bang)), use_container_width=True, column_config={
            "Bán dự đoán (đv/ngày)": st.column_config.NumberColumn(format="%.1f"),
            "Tồn an toàn": st.column_config.NumberColumn(format="%.1f"),
            "Điểm đặt hàng": st.column_config.NumberColumn(format="%.0f", help="Đang có + đang về ≤ số này thì phải đặt"),
            "Đang có + đang về": st.column_config.NumberColumn(format="%.0f")})
        st.caption("**Đang có + đang về** lấy từ bảng tồn kho ở trang Hôm nay (dùng sổ kiểm kho thì là số đếm gần nhất). "
                   "**Chạm điểm đặt**: nếu không nhập thêm và bán đúng như dự đoán. Đổi ngày ở trang Hôm nay.")

    m = st.selectbox("Xem kỹ một mặt hàng", skus, key="db_mh")
    v = kh["mat_hang"][m]
    me, mh2 = v["meta"], v["mo_hinh"]
    d, L, ss_, rop, q = float(v["d_hat"][k]), int(v["L"]), float(v["ss"][k]), float(v["rop"][k]), float(v["q"][k])
    mpv = float(info.loc[m, "muc_phuc_vu"]) if "muc_phuc_vu" in info.columns else 0.95
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1.container(border=True):
        st.markdown(f"##### Vì sao điểm đặt hàng của {m} là {rop:.0f} đv?")
        st.markdown(f"1. Đặt hôm nay thì hàng về sau **{L} ngày**. Trong {L} ngày chờ đó (tính từ ngày mai) dự đoán bán "
                    f"khoảng **{rop - ss_:.1f} đv** (hôm nay dự đoán {d:.1f} đv).\n"
                    f"2. Cộng **tồn an toàn {ss_:.1f} đv** phòng khi bán nhiều hơn dự đoán hoặc hàng về trễ "
                    f"(chấp nhận hết hàng khoảng {1 - mpv:.0%} số lần nhập).\n"
                    f"3. Vậy khi **đang có + đang về ≤ {rop:.0f} đv** thì đặt, mỗi lần khoảng **{q:.0f} đv**.")
        st.caption("Ở trang Hôm nay, lượng nhập có thể khác vì app gộp các mặt hàng cùng nguồn vào một chuyến và giới hạn "
                   "theo vốn, sức chứa.")
    with c2.container(border=True):
        st.markdown("##### Số bán dự đoán lấy từ đâu?")
        che_do = me.get("che_do", "day_du")
        if che_do == "uoc_luong":
            st.markdown(f"🎯 **Chưa có số đo**: dùng đúng ước lượng của bạn, **{me['muc_uoc_luong']:.1f} đv/ngày**.")
            st.caption(f"Tồn an toàn đang nhân ×{me['he_so_than_trong']:.2f} vì còn chưa chắc. Kiểm kho mỗi tối ở trang "
                       "Nhập dữ liệu để app đo được lượng bán thật.")
        elif che_do == "dang_hoc":
            n_do = me["so_ngay_do"]
            if me.get("muc_uoc_luong") is not None:
                st.markdown(f"📏 Trộn **{loi.TRONG_SO_UOC_LUONG} ngày ước lượng** ({me['muc_uoc_luong']:.1f} đv/ngày) với "
                            f"**{n_do} ngày đo** ({me['muc_do_duoc']:.1f} đv/ngày) → **{d:.1f} đv/ngày**. "
                            f"Số đo đang chiếm {me['trong_so_do']:.0%}.")
            else:
                st.markdown(f"📏 Trung bình **{n_do} ngày đo**: **{d:.1f} đv/ngày** (chưa có ước lượng ban đầu).")
            st.progress(min(n_do / loi.NGAY_DAY_DU, 1.0), text=f"{n_do}/{loi.NGAY_DAY_DU} ngày đo")
            st.caption(f"Tồn an toàn đang nhân ×{me['he_so_than_trong']:.2f} cho chắc. Đo thêm {loi.NGAY_DAY_DU - n_do} ngày nữa "
                       "thì app học thêm thứ trong tuần và mùa Tết, Trung thu.")
        else:
            st.markdown(f"📈 **Mô hình mùa vụ** học từ {me.get('so_ngay_do', len(ctx.ban_hang))} ngày bán: mức nền "
                        f"**{mh2['muc_nen']:.1f} đv/ngày** × hệ số thứ × hệ số Tết × hệ số Trung thu.")
            st.markdown(f"🧧 Mùa Tết đã thấy: **{mh2['so_mua_tet']}** · 🥮 Mùa Trung thu đã thấy: **{mh2['so_mua_trung_thu']}**")
            if me.get("ngoai_mau"):
                st.metric("🎯 Sai số dự báo (WAPE)", f"{me['wape_du_bao']:.0%}",
                          delta=f"{me['wape_du_bao'] - me['wape_trung_binh']:+.0%} so với dùng trung bình", delta_color="inverse")
            if mh2["so_mua_tet"] == 0:
                st.warning("Dữ liệu chưa có mùa Tết nào nên dự báo sẽ không thấy đỉnh Tết.")

    hop_phan_tich(ctx, f"db_{m}", f"dự đoán của {m}", du_lieu_ai_mat_hang(ctx, m))

    with st.container(border=True):
        st.markdown("##### 🧪 Kiểm định theo mùa: nếu dùng mô hình này từ trước, nó sẽ đoán đúng tới đâu?")
        st.caption("Với mỗi mùa Tết / Trung thu có trong dữ liệu: chỉ học từ dữ liệu trước mốc (60 ngày trước Tết, 45 ngày trước "
                   "Trung thu), dự báo 90 ngày tiếp theo rồi so với thực tế. WAPE càng thấp càng tốt.")
        kd = kiem_dinh(ctx.ban_hang[m], ctx.xu_huong) if not me.get("khoi_dong") else pd.DataFrame()
        if len(kd):
            hien = pd.DataFrame({
                "Mùa": kd["mua"] + " " + kd["nam"].astype(str), "Mốc dự báo": kd["moc_du_bao"].astype(str),
                "Mô hình (đỉnh mùa)": kd["wape_dinh_mo_hinh"] * 100, "Trung bình 56 ngày (đỉnh)": kd["wape_dinh_trung_binh_56"] * 100,
                "Năm ngoái cùng ngày (đỉnh)": kd["wape_dinh_nam_ngoai"] * 100, "Mô hình (90 ngày)": kd["wape_mo_hinh"] * 100,
                "Dự báo lệch ở đỉnh": kd["lech_tong_dinh"] * 100})
            st.dataframe(hien.round(1), hide_index=True, row_height=DONG_BANG, height=cao_bang(len(hien)), use_container_width=True,
                         column_config={c: st.column_config.NumberColumn(format="%.1f%%") for c in hien.columns[2:]})
            st.caption("'Năm ngoái cùng ngày' là cách nhiều tiểu thương vẫn làm (xem sổ năm ngoái theo lịch dương). Vì Tết và "
                       "Trung thu đổi ngày dương lịch mỗi năm nên cách này lệch nhiều ở đỉnh mùa. 'Dự báo lệch ở đỉnh' dương là "
                       "dự báo dư, âm là dự báo thiếu.")
        else:
            st.info("Chưa đủ dữ liệu để kiểm định theo mùa (cần ít nhất 180 ngày trước một mùa Tết/Trung thu và có dữ liệu qua "
                    "đỉnh mùa đó).")
    with st.expander("Bảng sai số dự báo của tất cả mặt hàng"):
        st.dataframe(height=cao_bang(len(kh["mat_hang"])), data=pd.DataFrame([{"Mặt hàng": mm,
                                    "Sai số dự báo mùa vụ": f"{vv['meta']['wape_du_bao']:.0%}" if vv["meta"].get("ngoai_mau") else "—",
                                    "Sai số nếu dùng trung bình": f"{vv['meta']['wape_trung_binh']:.0%}" if vv["meta"].get("ngoai_mau") else "—"}
                                   for mm, vv in kh["mat_hang"].items()]), hide_index=True, row_height=DONG_BANG, use_container_width=True)
        st.caption("Đo trên 30% dữ liệu cuối (cần ≥ 240 ngày). Mặt hàng mà dự báo mùa vụ không hơn trung bình là hàng bán đều.")
