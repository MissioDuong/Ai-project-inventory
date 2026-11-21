# -*- coding: utf-8 -*-
"""Trang Thiết lập › Mặt hàng & kho: bảng nguồn hàng / khu bảo quản / mặt hàng, hạn dùng thực tế, ô 'Nhờ AI sửa thông số'.
(Số liệu bán hàng nhập ở trang Nhập dữ liệu.)

Trang này vẽ làm 3 phần vì app.py phải tính thiết lập (mh, nguon, khu) và kế hoạch (kh) xen giữa:
  ve_thiet_lap  → trước khi kiểm tra thiết lập (trả về khung trống để đặt ô AI lên đầu trang)
  ve_han_dung   → sau khi kiểm tra thiết lập
  ve_ai_sua     → sau khi đã có kế hoạch kh (AI cần kh để trả lời)
"""
import numpy as np
import pandas as pd
import streamlit as st
from tinh_toan import loi, so_ghi
from tinh_toan import nhieu_mat_hang as nm
from tro_ly_ai import tro_ly as tl
from giao_dien.cau_hinh import noi_luu_so
from giao_dien.du_lieu import TEN_SO_GHI
from giao_dien.kieu import DONG_BANG, cao_bang, tieu_de
from giao_dien.tien_ich import csv_bytes, ghep_bang, mh_hien, mh_mo_hinh, dat_bang, bang_sua
from giao_dien.khung_ai import chay_ai_sua, nut_hoan_tac, mo_ta_thay_doi

ss = st.session_state


def _luu_thiet_lap():
    try:
        so_ghi.ghi_thiet_lap(noi_luu_so(), mh_mo_hinh(ss["mh_cur"]).dropna(how="all"), ss["nguon_cur"].dropna(how="all"),
                             ss["khu_cur"].dropna(how="all"))
        ss["tl_da_luu"] = "Đã lưu thiết lập vào " + so_ghi.mo_ta_noi_luu(noi_luu_so()) + "."
    except ValueError as e:
        ss["tl_da_luu"] = e


def ve_thiet_lap(ctx):
    """Các bảng thiết lập. Trả về khung để ve_ai_sua điền sau."""
    ban_hang, canh_bao = ctx.ban_hang, ctx.canh_bao
    khung_ai_dm = st.container()
    tieu_de("⚙️", "Mặt hàng & kho", "Khai báo một lần: nơi nhập hàng, nơi cất hàng và thông số từng mặt hàng")
    for c in canh_bao:
        st.warning(c)
    if ctx.ten_nguon == TEN_SO_GHI:
        c_l1, c_l2 = st.columns([3, 1])
        c_l1.info("Đang dùng **Sổ kiểm kho**: bấm lưu để lần sau mở app vẫn còn các thông số bên dưới.")
        c_l2.button("💾 Lưu thiết lập", key="tl_luu", on_click=_luu_thiet_lap, type="primary",
                    use_container_width=True)
        kq = ss.pop("tl_da_luu", None)
        if isinstance(kq, str):
            st.success(kq)
        elif kq is not None:
            st.error(f"❌ {kq}")
    with st.expander("📂 Thiết lập từ file (tuỳ chọn): nguồn hàng, khu bảo quản, mặt hàng"):
        st.caption(f"Tải file thay cho việc sửa bảng bên dưới. Dữ liệu bán hàng hiện có {len(ban_hang)} ngày × "
                   f"{ban_hang.shape[1]} mặt hàng ({ban_hang.index.min():%d/%m/%Y} → {ban_hang.index.max():%d/%m/%Y}); "
                   "đổi ở trang Nhập dữ liệu.")
        c1, c2, c3 = st.columns(3)
        try:
            for cot, nhan, ten, khoa, k_id in [(c1, "Nguồn hàng", "nguon", "nguon_hang", "f_ng_id"),
                                               (c2, "Khu bảo quản", "khu", "khu_bao_quan", "f_kz_id"),
                                               (c3, "Mặt hàng", "mh", "mat_hang", "f_mh_id")]:
                f = cot.file_uploader(nhan, type=["csv", "xlsx", "xls"], key=f"up_{ten}")
                if f is not None and ss.get(k_id) != (f.name, f.size):
                    if ten == "mh":
                        dat_bang("mh", mh_hien(ghep_bang(loi.doc_file(f), mh_mo_hinh(ss["mh_cur"]), khoa)))
                    else:
                        dat_bang(ten, ghep_bang(loi.doc_file(f), ss[f"{ten}_cur"], khoa))
                    ss[k_id] = (f.name, f.size)
                cur = mh_mo_hinh(ss["mh_cur"]) if ten == "mh" else ss[f"{ten}_cur"]
                cot.download_button(f"⬇️ Tải {nhan.lower()} (CSV)", csv_bytes(cur), f"{khoa}.csv", "text/csv", key=f"dl_{ten}")
        except ValueError as e:
            st.error(f"❌ {e}")

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("##### 🚚 ① Nơi nhập hàng")
            st.caption("Mỗi nguồn là một chuyến đi / một lần gọi hàng. Thêm dòng nếu có nguồn mới.")
            bang_sua("nguon", num_rows="dynamic", hide_index=True, row_height=DONG_BANG, use_container_width=True, column_config={
                "nguon_hang": "Nguồn hàng",
                "chi_phi_chuyen": st.column_config.NumberColumn("Chi phí/chuyến (đ)", min_value=0, step=5000, format="%d",
                                                                help="Xăng xe, công đi, phí ship... cho MỘT chuyến"),
                "lead_time_ngay": st.column_config.NumberColumn("Giao sau (ngày)", min_value=1, step=0.5, format="%.1f"),
                "do_lech_lead_time": st.column_config.NumberColumn("Hay lệch (ngày)", min_value=0, step=0.1, format="%.1f")})
    with c2:
        with st.container(border=True):
            st.markdown("##### 🧊 ② Nơi cất hàng")
            st.caption("Nhiệt độ quyết định hạn dùng thực tế. Sức chứa 0 = không giới hạn.")
            bang_sua("khu", num_rows="dynamic", hide_index=True, row_height=DONG_BANG, use_container_width=True, column_config={
                "khu_bao_quan": "Khu bảo quản",
                "nhiet_do_C": st.column_config.NumberColumn("Nhiệt độ (°C)", step=1.0, format="%.0f"),
                "suc_chua_lit": st.column_config.NumberColumn("Sức chứa (lít)", min_value=0, step=10.0, format="%.0f"),
                "chi_phi_bao_quan_lit_ngay": st.column_config.NumberColumn("Chi phí thêm (đ/lít/ngày)", min_value=0, step=1.0, format="%.0f",
                                                                             help="Phần chi phí TĂNG THEO lượng hàng cất (thường rất nhỏ)"),
                "chi_phi_co_dinh_ngay": st.column_config.NumberColumn("Tiền điện cố định (đ/ngày)", min_value=0, step=1000.0, format="%.0f",
                                                                        help="Tiền điện chạy tủ dù đầy hay vơi. Như nhau với mọi cách nhập nên "
                                                                             "không ảnh hưởng so sánh, chỉ báo riêng")})

    with st.container(border=True):
        st.markdown("##### 🍬 ③ Mặt hàng")
        ds_ng = sorted(set(ss["nguon_cur"]["nguon_hang"].dropna().astype(str)) | set(ss["mh_cur"]["nguon_hang"]))
        ds_kz = sorted(set(ss["khu_cur"]["khu_bao_quan"].dropna().astype(str)) | set(ss["mh_cur"]["khu_bao_quan"]))
        bang_sua("mh", hide_index=True, row_height=DONG_BANG, disabled=["mat_hang"], use_container_width=True, column_config={
            "mat_hang": st.column_config.TextColumn("Mặt hàng", width="medium"),
            "gia_von": st.column_config.NumberColumn("Giá vốn (đ)", min_value=1, step=500, format="%d"),
            "gia_ban": st.column_config.NumberColumn("Giá bán (đ)", min_value=1, step=500, format="%d"),
            "han_dung_ngay": st.column_config.NumberColumn("Hạn in bao bì (ngày)", min_value=3, step=1, format="%d"),
            "tuoi_khi_nhan_ngay": st.column_config.NumberColumn("Đã cũ khi nhận (ngày)", min_value=0, step=1, format="%d",
                                                                help="Lúc nhận hàng, hạn dùng đã trôi qua bao nhiêu ngày. Hàng lấy ở "
                                                                     "chợ đầu mối thường đã cũ vài tuần"),
            "ty_le_hu_hong_ngay": st.column_config.NumberColumn("Hư hỏng (%/ngày)", min_value=0.0, max_value=19.9, step=0.005, format="%.3f",
                                                                help="Phần hàng hỏng mỗi ngày do ẩm, mốc, móp, chuột... 0,03%/ngày ≈ 11%/năm"),
            "q10": st.column_config.NumberColumn("Q10", min_value=1.0, max_value=10.0, step=0.1, format="%.1f",
                                                 help="Nóng thêm 10°C thì hạn dùng ngắn đi bao nhiêu lần (thường 2–3)"),
            "nhiet_do_chuan_C": st.column_config.NumberColumn("Hạn áp dụng ở (°C)", step=1.0, format="%.0f",
                                                              help="Nhiệt độ bảo quản mà hạn in trên bao bì áp dụng"),
            "khu_bao_quan": st.column_config.SelectboxColumn("Cất ở", options=ds_kz, required=True),
            "the_tich_lit": st.column_config.NumberColumn("Thể tích (lít/đv)", min_value=0.01, step=0.05, format="%.2f"),
            "nguon_hang": st.column_config.SelectboxColumn("Nhập từ", options=ds_ng, required=True),
            "quy_cach": st.column_config.NumberColumn("Quy cách", min_value=1, step=1, format="%d",
                                                      help="Mua theo bội số này, ví dụ 1 bịch 10 gói"),
            "ty_le_giu_hang_nam": st.column_config.NumberColumn("Lãi vốn (%/năm)", min_value=0.0, step=1.0, format="%.0f"),
            "muc_phuc_vu": st.column_config.NumberColumn("Mức phục vụ", min_value=0.5, max_value=0.999, step=0.01, format="%.2f",
                                                         help="0,95 = chấp nhận hết hàng khoảng 5% số chu kỳ"),
            "chi_phi_dong": st.column_config.NumberColumn("Chi phí/dòng hàng (đ)", min_value=0, step=1000, format="%d",
                                                          help="Công đếm, kiểm, xếp kệ cho mỗi mặt hàng trong một chuyến")})
    return khung_ai_dm


def ve_han_dung(ctx):
    """Bảng hạn dùng thực tế và chi phí giữ hàng (hoặc lỗi thiết lập)."""
    mh, nguon, khu, loi_tl = ctx.mh, ctx.nguon, ctx.khu, ctx.loi_tl
    if loi_tl:
        for e in loi_tl:
            st.error(e)
    else:
        info = nm.chuan_bi(mh, nguon, khu)
        with st.container(border=True):
            st.markdown("##### 🔎 Hạn dùng thực tế và chi phí giữ hàng (tự tính)")
            dx = pd.DataFrame({
                "Mặt hàng": info.index, "Cất ở": info["khu_bao_quan"].values,
                "Hạn in (ngày)": info["han_dung_ngay"].values, "Đã cũ khi nhận": info["tuoi_khi_nhan_ngay"].values,
                "Còn hạn khi nhận, theo chỗ cất (ngày)": info["han_con_khi_nhan"].values,
                "Hư hỏng (%/năm)": (1 - (1 - info["ty_le_hu_hong_ngay"]) ** 365).values * 100,
                "Giữ 1 đv / ngày (đ)": (info["giu_ngay"] + info["hu_hong_ngay"]).values,
                "Giao sau (ngày)": info["L"].values})
            hs = info["he_so_nhiet"].values
            dx["Ghi chú"] = np.where(hs < 0.999, "⚠️ Cất nóng hơn khuyến nghị: hạn bị rút ngắn, hư hỏng nhanh hơn",
                                     np.where(hs > 1.001, "❄️ Cất mát hơn: hạn kéo dài, hư hỏng chậm hơn", "✓"))
            st.dataframe(dx.round(2), hide_index=True, row_height=DONG_BANG, height=cao_bang(len(dx)), use_container_width=True,
                         column_config={"Giữ 1 đv / ngày (đ)": st.column_config.NumberColumn(format="%.0f"),
                                        "Hư hỏng (%/năm)": st.column_config.NumberColumn(format="%.1f")})


def ve_ai_sua(ctx, khung_ai_dm):
    """Ô 'Nhờ AI sửa thông số' đặt vào khung_ai_dm ở đầu trang."""
    with khung_ai_dm.container(border=True):
        st.markdown("##### 🤖 Nhờ AI sửa thông số")
        st.caption("Gõ yêu cầu bằng lời, ví dụ: “giá vốn mứt Tết lên 50.000”, “chuyển bánh pía sang kho khô”, "
                   "“tủ mát chỉ còn 100 lít”, “đi chợ đầu mối tốn 70 nghìn một chuyến”. AI kiểm tra hợp lệ rồi sửa các bảng bên dưới.")
        c1_, c2_ = st.columns([5, 1])
        yc = c1_.text_input("Yêu cầu", key="ai_dm_yc", label_visibility="collapsed",
                            placeholder="Ví dụ: hư hỏng của bánh pía là 0,2 %/ngày")
        if c2_.button("✍️ Sửa bằng AI", key="ai_dm_bam", type="primary", use_container_width=True) and yc.strip():
            with st.spinner("AI đang đọc thiết lập và sửa..."):
                try:
                    tra_loi_, _, td_ = chay_ai_sua(ctx, yc, [])
                    ss["ai_dm_kq"] = (tra_loi_, td_)
                    if td_:
                        st.rerun()
                except Exception as e:                         # noqa: BLE001
                    st.warning(str(e) if isinstance(e, RuntimeError) else tl.loi_than_thien(e))
        if ss.get("ai_dm_kq"):
            tra_loi_, td_ = ss["ai_dm_kq"]
            if td_:
                st.success("✍️ AI đã sửa:\n" + mo_ta_thay_doi(td_))
            st.markdown(tra_loi_)
        nut_hoan_tac("ht_dm")
