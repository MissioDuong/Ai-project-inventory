# -*- coding: utf-8 -*-
"""Trang Trợ giúp › Trợ lý AI: hội thoại tiếng Việt, AI gọi hàm tính toán và (nếu bật) sửa dữ liệu, có hoàn tác."""
import pandas as pd
import streamlit as st
from tro_ly_ai import tro_ly as tl
from giao_dien.kieu import tieu_de
from giao_dien.khung_ai import chay_ai_sua, nut_hoan_tac, mo_ta_thay_doi

ss = st.session_state


def ve(ctx):
    """Vẽ trang Trợ lý AI."""
    so_ngay, ai_key, ai_mo_hinh, ds_mo_hinh, skus, bat_dau = ctx.so_ngay, ctx.ai_key, ctx.ai_mo_hinh, ctx.ds_mo_hinh, ctx.skus, ctx.bat_dau
    tieu_de("🤖", "Trợ lý AI", "Hỏi bằng tiếng Việt: AI gọi các hàm tính toán của ứng dụng rồi giải thích kết quả")
    lo, hi = bat_dau.date(), (bat_dau + pd.Timedelta(days=so_ngay - 1)).date()
    ngay_ai = min(max(ss.get("ngay_hn_v", lo), lo), hi)
    c_tt, c_mh = st.columns([3, 1])
    c_tt.caption(f"Trợ lý dùng tồn kho và ngày **{ngay_ai:%d/%m/%Y}** đã nhập ở trang Hôm nay, cùng kết quả mô phỏng mới nhất. "
                 + ("✅ Đã kết nối OpenAI." if ai_key else "⚠️ Chưa có API key: thêm OPENAI_API_KEY vào .streamlit/secrets.toml."))
    c_mh.selectbox("Mô hình", ds_mo_hinh, index=ds_mo_hinh.index(ai_mo_hinh) if ai_mo_hinh in ds_mo_hinh else 0,
                   key="w_ai_mo_hinh", on_change=lambda: ss.update(ai_mo_hinh_v=ss["w_ai_mo_hinh"]))
    cho_sua = st.toggle("✍️ Cho phép AI sửa dữ liệu (thông số mặt hàng, nguồn hàng, kho, tồn kho, vốn)", value=True,
                        key="ai_cho_sua", help="AI chỉ sửa khi bạn yêu cầu rõ; mọi giá trị được kiểm tra hợp lệ và có thể hoàn tác")
    with st.expander("ℹ️ Trợ lý AI làm gì và không làm gì?"):
        st.markdown("- **Làm:** hiểu câu hỏi, chọn đúng hàm tính (danh sách đi chợ, tình trạng mặt hàng, dự báo, cảnh báo hết hạn, "
                    "so sánh cách nhập, EOQ), rồi giải thích kết quả bằng lời dễ hiểu.\n"
                    "- **Không làm:** tự tính hay đoán con số. Mọi con số đến từ thuật toán minh bạch của ứng dụng; "
                    "bấm vào mục 🔧 dưới mỗi câu trả lời để xem AI đã gọi hàm nào và nhận số liệu gì.\n"
                    "- **Sửa dữ liệu** (khi bật công tắc): ví dụ “kẹo dừa còn 120 gói”, “vốn mỗi ngày 8 triệu”, “chuyển bánh pía "
                    "sang kho khô”. AI kiểm tra giá trị hợp lệ, sửa, tính lại kế hoạch và báo cũ → mới; bấm ↩️ để hoàn tác.\n"
                    "- **Dữ liệu gửi đi:** tên mặt hàng, thông số, tồn kho và kết quả tính, gửi tới OpenAI để tạo câu trả lời.")
    ss.setdefault("ai_hoi_thoai", [])
    goi_y = ["Hôm nay tôi cần đi chợ những đâu, mua gì?", "Hàng nào có nguy cơ hết hạn, nên xử lý sao?",
             f"{skus[0]} hôm nay còn 120, cập nhật giúp tôi",
             f"Dự báo {skus[-1]} 2 tuần tới thế nào?"]
    cols = st.columns(len(goi_y))
    chon = None
    for c, g in zip(cols, goi_y):
        if c.button(g, use_container_width=True, key=f"ai_goi_y_{g}"):
            chon = g
    for tin in ss["ai_hoi_thoai"]:
        with st.chat_message(tin["role"], avatar="🧑‍🌾" if tin["role"] == "user" else "🤖"):
            if tin.get("thay_doi"):
                st.success("✍️ AI đã sửa:\n" + mo_ta_thay_doi(tin["thay_doi"]))
            st.markdown(tin["content"])
            for ten, ts, kq in tin.get("cong_cu", []):
                with st.expander(f"🔧 Đã gọi hàm: {ten}"):
                    st.json({"tham_so": ts, "ket_qua": kq})
    cau = st.chat_input("Hỏi trợ lý về nhập hàng, tồn kho, hạn dùng...") or chon
    c_xoa, c_ht = st.columns([1, 3])
    if c_xoa.button("🗑️ Xoá hội thoại", key="ai_xoa"):
        ss["ai_hoi_thoai"] = []
        st.rerun()
    with c_ht:
        nut_hoan_tac("ht_chat")
    if cau:
        ss["ai_hoi_thoai"].append({"role": "user", "content": cau})
        with st.chat_message("user", avatar="🧑‍🌾"):
            st.markdown(cau)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Đang tính và soạn câu trả lời..."):
                try:
                    lich_su = [{"role": t["role"], "content": t["content"]} for t in ss["ai_hoi_thoai"][:-1]]
                    tra_loi, da_goi, td = chay_ai_sua(ctx, cau, lich_su, cho_sua=cho_sua)
                    ss["ai_hoi_thoai"].append({"role": "assistant", "content": tra_loi, "cong_cu": da_goi, "thay_doi": td})
                    if td:
                        st.rerun()                             # tính lại toàn bộ app với dữ liệu mới
                    st.markdown(tra_loi)
                    for ten, ts, kq in da_goi:
                        with st.expander(f"🔧 Đã gọi hàm: {ten}"):
                            st.json({"tham_so": ts, "ket_qua": kq})
                except Exception as e:                         # noqa: BLE001
                    st.warning(str(e)) if isinstance(e, RuntimeError) else st.error(tl.loi_than_thien(e))
                    ss["ai_hoi_thoai"].pop()
