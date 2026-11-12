# -*- coding: utf-8 -*-
"""Trang 🛒 Hôm nay: tồn kho hôm nay → danh sách đi chợ theo nguồn, vốn cần, cảnh báo, sức chứa, AI tóm tắt."""
import pandas as pd
import streamlit as st
from tinh_toan import nhieu_mat_hang as nm
from tro_ly_ai import tro_ly as tl
from giao_dien.kieu import kpi_hang, tieu_de
from giao_dien.tien_ich import csv_bytes, tien, dat_bang, bang_sua
from giao_dien.khung_ai import client_ai, boi_canh_ai, ton_mac_dinh

ss = st.session_state


def ve(ctx):
    """Vẽ trang Hôm nay."""
    so_ngay, von, ai_mo_hinh, skus, sig, kh, info, bat_dau = ctx.so_ngay, ctx.von, ctx.ai_mo_hinh, ctx.skus, ctx.sig, ctx.kh, ctx.info, ctx.bat_dau
    tieu_de("🛒", "Hôm nay cần nhập gì?", "Danh sách đi chợ theo từng nguồn hàng · sửa tồn kho ở bên dưới để cập nhật")
    lo, hi = bat_dau.date(), (bat_dau + pd.Timedelta(days=so_ngay - 1)).date()
    v_ngay = min(max(ss.get("ngay_hn_v", lo), lo), hi)
    c1, c2 = st.columns([1, 2])
    ngay_hn = c1.date_input("📅 Hôm nay là ngày", value=v_ngay, min_value=lo, max_value=hi, format="DD/MM/YYYY")
    ss["ngay_hn_v"] = ngay_hn
    ds_nguon = sorted(info["nguon_hang"].unique())
    if "di_cho" in ss:
        ss["di_cho"] = [x for x in ss["di_cho"] if x in ds_nguon]
    di_cho = c2.multiselect("🚚 Hôm nay tôi chắc chắn đi tới (mua kèm những gì sắp cần)", ds_nguon,
                            key="di_cho", help="Đã phải đi thì tranh thủ mua luôn các mặt hàng cùng nguồn sắp chạm điểm đặt hàng")
    k = (pd.Timestamp(ngay_hn) - bat_dau).days

    if "ton_cur" not in ss or list(ss["ton_cur"]["mat_hang"]) != skus:
        dat_bang("ton", ton_mac_dinh(ctx))
    if "lo_cur" not in ss or ss.get("lo_sig") != sig:
        dat_bang("lo", pd.DataFrame({"mat_hang": pd.Series(dtype=str), "so_luong": pd.Series(dtype=float),
                                     "han_con_lai": pd.Series(dtype=float)}))
        ss["lo_sig"] = sig

    khung_kq = st.container()                                  # kết quả hiển thị TRÊN cùng, tính xong mới điền

    c_trai, c_phai = st.columns([3, 2], gap="medium")
    with c_trai:
        with st.container(border=True):
            st.markdown("##### ✏️ Tồn kho hôm nay")
            st.caption("Số mặc định là ước tính, hãy sửa cho đúng. **Hạn còn lại**: lô hàng đang có còn bao nhiêu ngày tới hạn dùng.")
            ton = bang_sua("ton", hide_index=True, disabled=["mat_hang"], use_container_width=True,
                           column_config={"mat_hang": "Mặt hàng",
                                          "ton_kho": st.column_config.NumberColumn("Đang có", min_value=0, step=1, format="%d"),
                                          "han_con_lai": st.column_config.NumberColumn("Hạn còn lại (ngày)", min_value=0, step=1, format="%d"),
                                          "hang_dang_ve": st.column_config.NumberColumn("Đã đặt, đang về", min_value=0, step=1, format="%d")})
            ton = ton.fillna(0)
            with st.popover("➕ Có nhiều lô với hạn khác nhau? Thêm lô", use_container_width=False):
                st.caption("Dòng ở bảng trên là **lô chính**. Thêm ở đây các lô khác của cùng mặt hàng (ví dụ 20 gói còn 10 ngày, "
                           "50 gói còn 90 ngày). App cộng dồn vào tồn kho và tính phần có thể hết hạn theo từng lô.")
                lo_them = bang_sua("lo", num_rows="dynamic", hide_index=True, use_container_width=True,
                                   column_config={"mat_hang": st.column_config.SelectboxColumn("Mặt hàng", options=skus, required=True),
                                                  "so_luong": st.column_config.NumberColumn("Số lượng", min_value=0, step=1, format="%d"),
                                                  "han_con_lai": st.column_config.NumberColumn("Hạn còn lại (ngày)", min_value=0, step=1,
                                                                                               format="%d")})
            n_lo = int(lo_them.dropna(subset=["mat_hang"]).shape[0]) if len(lo_them) else 0
            if n_lo:
                st.caption(f"Đã thêm {n_lo} lô phụ, cộng vào tồn kho của mặt hàng tương ứng.")

    bang, don, suc_chua = nm.ke_hoach_hom_nay(kh, k, ton, von, di_cho=set(di_cho), lo_them=lo_them)
    co_don = {ng: d for ng, d in don.items() if d[0]}
    tong_von = sum(sum(q * info.loc[i, "gia_von"] for i, q in d[0].items()) for d in co_don.values())
    tien_het_han = float((bang["sap_het_han"] * bang["mat_hang"].map(info["gia_von"])).sum())
    nguy = bang[bang["muc"] == "error"]

    with c_phai:
        with st.container(border=True):
            st.markdown("##### ⚠️ Cần chú ý")
            co_chu_y = False
            for _, r in nguy.iterrows():
                st.error(f"**{r['mat_hang']}** — {r['trang_thai']}.")
                co_chu_y = True
            for _, r in bang[bang["sap_het_han"] >= 1].iterrows():
                st.warning(f"**{r['mat_hang']}**: khoảng **{r['sap_het_han']:.0f} đv** có thể hết hạn trước khi bán hết "
                           f"(≈ {tien(r['sap_het_han'] * info.loc[r['mat_hang'], 'gia_von'])}). "
                           "Nên bày phía trước, bán giảm giá hoặc bán kèm.")
                co_chu_y = True
            if not co_chu_y:
                st.success("Không có mặt hàng nào hết hàng, dưới mức an toàn hay sắp hết hạn.")
        with st.container(border=True):
            st.markdown("##### 🧊 Sức chứa kho")
            for _, r in suc_chua.iterrows():
                if r["suc_chua"] > 0:
                    ty = r["sau_khi_nhap"] / r["suc_chua"]
                    st.progress(min(ty, 1.0), text=f"{r['khu']}: {r['dang_dung']:.0f} → ~{r['sau_khi_nhap']:.0f} / "
                                                    f"{r['suc_chua']:.0f} lít ({ty:.0%})")
                else:
                    st.caption(f"{r['khu']}: {r['sau_khi_nhap']:.0f} lít (không giới hạn)")
            st.caption("Số đầu: đang chiếm; số sau: dự kiến lúc hàng mới về.")

    with khung_kq:
        n_nhap = int((bang["nhap"] > 0).sum())
        kpi_hang([("🚚 Chuyến cần đi", str(len(co_don)), ", ".join(co_don) if co_don else "Chưa cần đi", "#f2542d"),
                  ("📦 Mặt hàng cần nhập", str(n_nhap), f"trên {len(skus)} mặt hàng", "#ff8a3d"),
                  ("💰 Tổng vốn cần", tien(tong_von), f"còn {tien(max(von - tong_von, 0))} trong hạn mức", "#16a34a"),
                  ("⏳ Có thể hết hạn", tien(tien_het_han), "giá vốn phần bán không kịp", "#e11d48" if tien_het_han else "#94a3b8")])
        if not co_don:
            st.markdown('<div class="the-trang">✅ <b>Hôm nay chưa cần đi nhập hàng.</b> Tồn kho cộng hàng đang về vẫn trên '
                        'điểm đặt hàng của mọi mặt hàng.</div>', unsafe_allow_html=True)
        else:
            st.markdown("#### 🧾 Danh sách đi chợ")
            ds_ng = list(co_don.items())
            for a in range(0, len(ds_ng), 2):
                cot = st.columns(2, gap="medium")
                for c_, (ng, (qs, tt)) in zip(cot, ds_ng[a:a + 2]):
                    with c_.container(border=True):
                        L = int(info[info["nguon_hang"] == ng]["L"].iloc[0])
                        v_ng = sum(q * info.loc[i, "gia_von"] for i, q in qs.items())
                        st.markdown(f"##### 📍 {ng}")
                        st.caption(f"{len(qs)} mặt hàng · **{tien(v_ng)}** · hàng về sau ~{L} ngày")
                        ds_ = pd.DataFrame([{
                            "Mặt hàng": i, "Số lượng": int(q),
                            "Quy cách": f"{int(q // info.loc[i, 'quy_cach'])}×{int(info.loc[i, 'quy_cach'])}" if info.loc[i, "quy_cach"] > 1 else "",
                            "Tiền hàng": q * info.loc[i, "gia_von"],
                            "Vì sao": "🔴 Phải đặt" if i in tt["phai_dat"] else "🟡 Mua kèm"} for i, q in qs.items()])
                        st.dataframe(ds_, hide_index=True, use_container_width=True,
                                     column_config={"Tiền hàng": st.column_config.NumberColumn(format="%d")})
                        ghi = f"Nhập đủ bán khoảng **{tt['so_ngay_du_ban']} ngày** (chu kỳ gộp {tt['chu_ky']} ngày)."
                        if tt["rang_buoc"]:
                            ghi += f" ⚠️ Giới hạn bởi **{tt['rang_buoc']}**."
                        st.caption(ghi)
            ds_all = pd.DataFrame([{"nguon_hang": ng, "mat_hang": i, "so_luong": int(q), "tien_hang": q * info.loc[i, "gia_von"]}
                                   for ng, (qs, _) in co_don.items() for i, q in qs.items()])
            st.download_button("⬇️ Tải danh sách đi chợ (CSV)", csv_bytes(ds_all), f"di_cho_{ngay_hn}.csv", "text/csv")

        with st.container(border=True):
            c_ai1, c_ai2 = st.columns([3, 1])
            c_ai1.markdown("##### 🤖 Trợ lý AI tóm tắt việc hôm nay")
            bam_ai = c_ai2.button("✨ Giải thích bằng AI", use_container_width=True, key="ai_giai_thich", type="primary")
            dau_vet = (str(ngay_hn), str(sorted((ng, tuple(sorted(d[0].items()))) for ng, d in don.items())),
                       float(bang["sap_het_han"].sum()), ai_mo_hinh)
            if bam_ai:
                client, thong_bao = client_ai(ctx)
                if client is None:
                    st.warning(thong_bao)
                else:
                    with st.spinner("AI đang đọc kết quả tính toán và viết tóm tắt..."):
                        try:
                            ss["ai_tom_tat"] = (dau_vet, tl.giai_thich_hom_nay(client, ai_mo_hinh,
                                                                              boi_canh_ai(ctx, ngay_hn, bang, don, suc_chua)))
                        except Exception as e:                 # noqa: BLE001
                            st.error(tl.loi_than_thien(e))
            if ss.get("ai_tom_tat") and ss["ai_tom_tat"][0] == dau_vet:
                st.markdown(ss["ai_tom_tat"][1])
                st.caption("AI chỉ diễn giải các con số do thuật toán tính, không tự tính thêm.")
            elif not bam_ai:
                st.caption("AI viết lại danh sách đi chợ và các cảnh báo thành lời dễ hiểu. Mọi con số vẫn do thuật toán tính.")

    with st.expander("🔍 Chi tiết từng mặt hàng (vì sao nhập / không nhập)"):
        ct = bang.rename(columns={"mat_hang": "Mặt hàng", "trang_thai": "Tình trạng", "du_bao_ngay": "Dự báo bán hôm nay",
                                  "ton_kho": "Đang có", "vi_the_kha_dung": "Vị thế dùng để quyết định", "rop": "Điểm đặt hàng",
                                  "ss": "Tồn an toàn", "sap_het_han": "Có thể hết hạn", "nhap": "Nhập",
                                  "han_con_khi_nhan": "Hạn khi nhận lô mới", "so_lo": "Số lô",
                                  "han_ngan_nhat": "Lô sắp hết hạn nhất (ngày)"})
        st.dataframe(ct[["Mặt hàng", "Tình trạng", "Dự báo bán hôm nay", "Đang có", "Số lô", "Lô sắp hết hạn nhất (ngày)",
                         "Vị thế dùng để quyết định", "Điểm đặt hàng", "Tồn an toàn", "Có thể hết hạn", "Nhập",
                         "Hạn khi nhận lô mới"]].round(1), hide_index=True, use_container_width=True)
        st.caption("**Vị thế dùng để quyết định** = đang có + đang về (mặc định). Nếu bật 'Trừ hàng sắp hết hạn' ở ô ⚙️ thì chỉ tính "
                   "phần hàng bán kịp trước hạn, đã trừ hao hụt trong thời gian chờ. Khi vị thế ≤ điểm đặt hàng thì phải đặt; "
                   "mặt hàng cùng nguồn sắp chạm thì được mua kèm. Cột 'Có thể hết hạn' luôn được tính để cảnh báo.")
