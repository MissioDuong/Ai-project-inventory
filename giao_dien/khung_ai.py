# -*- coding: utf-8 -*-
"""Cầu nối giao diện ↔ trợ lý AI: dựng bối cảnh cho AI, áp dụng / hoàn tác thay đổi AI sửa, khung "AI phân tích" bên cạnh biểu đồ / dưới bảng.

Mọi hàm nhận `ctx` (ngữ cảnh do app.py dựng: kh, info, von, skus, ...). Logic gọi LLM nằm ở tro_ly_ai/tro_ly.py.
"""
import hashlib
import json
from contextlib import contextmanager

import numpy as np
import pandas as pd
import streamlit as st

from tinh_toan import nhieu_mat_hang as nm
from tro_ly_ai import tro_ly as tl
from giao_dien.tien_ich import dat_bang, kiem_dinh, mh_mo_hinh

ss = st.session_state


def ton_mac_dinh(ctx):
    """Tồn kho ban đầu: số đếm gần nhất trong sổ kiểm kho nếu có; không thì ước tính 5 ngày bán. Hạn còn = nửa hạn khi nhận."""
    dem = getattr(ctx, "ton_dem", None) or {}
    v = [dem[m] if m in dem else 5 * np.nan_to_num(ctx.ban_hang[m].tail(28).mean()) for m in ctx.skus]
    return pd.DataFrame({"mat_hang": ctx.skus,
                         "ton_kho": [int(round(x)) for x in v],
                         "han_con_lai": [int(ctx.info.loc[m, "han_con_khi_nhan"]) // 2 for m in ctx.skus],
                         "hang_dang_ve": [0] * len(ctx.skus)})


def ton_hien_tai(ctx):
    """Bảng tồn kho hiện tại (index = mặt hàng; cột ton_kho gồm cả lô phụ, hang_dang_ve, han_con_lai), theo bảng ở trang
    Hôm nay (chưa sửa thì lấy mặc định)."""
    ton = ss["ton_cur"].fillna(0) if "ton_cur" in ss and list(ss["ton_cur"]["mat_hang"]) == ctx.skus else ton_mac_dinh(ctx)
    ton = ton.set_index("mat_hang")[["ton_kho", "hang_dang_ve", "han_con_lai"]].astype(float)
    lo = ss.get("lo_cur") if ss.get("lo_sig") == ctx.sig else None
    if lo is not None and len(lo.dropna(subset=["mat_hang"])):
        ton["ton_kho"] = ton["ton_kho"].add(lo.dropna(subset=["mat_hang"]).groupby("mat_hang")["so_luong"].sum(), fill_value=0)
    return ton.reindex(ctx.skus).fillna(0.0)


def vi_the_hien_tai(ctx):
    """Đang có + đang về (+ lô phụ) của mỗi mặt hàng."""
    t = ton_hien_tai(ctx)
    return t["ton_kho"] + t["hang_dang_ve"]


def du_lieu_ai_mat_hang(ctx, m):
    """Số liệu dự báo + điểm đặt hàng của một mặt hàng, gửi cho AI phân tích (trang Dự đoán và 📊)."""
    v = ctx.kh["mat_hang"][m]
    mh2, me = v["mo_hinh"], v["meta"]
    _, k = ngay_dang_xem(ctx)
    _d = np.asarray(v["d_hat"][:ctx.so_ngay], float)
    _ng = pd.DatetimeIndex(v["ngay"][:ctx.so_ngay])
    _ls = ctx.ban_hang[m].tail(365)
    _kd = kiem_dinh(ctx.ban_hang[m], ctx.xu_huong) if not me.get("khoi_dong") else pd.DataFrame()
    return {
        "mat_hang": m, "nguon_so_lieu_du_bao": me.get("che_do"), "so_ngay_do_duoc": me.get("so_ngay_do"),
        "uoc_luong_cua_nguoi_ban_ngay": me.get("muc_uoc_luong"), "trung_binh_do_duoc_ngay": me.get("muc_do_duoc"),
        "muc_nen_ngay_thuong": round(mh2["muc_nen"], 2),
        "he_so_thu_T2_den_CN": [round(x, 2) for x in mh2["he_so_thu"]],
        "he_so_tet_cao_nhat": round(float(mh2["he_so_tet"].max()), 2),
        "so_ngay_truoc_tet_ban_dinh": int(mh2["he_so_tet"].idxmax()),
        "he_so_trung_thu_cao_nhat": round(float(mh2["he_so_trung_thu"].max()), 2),
        "so_mua_tet_trong_du_lieu": mh2["so_mua_tet"], "so_mua_trung_thu_trong_du_lieu": mh2["so_mua_trung_thu"],
        "da_ban_365_ngay_gan_nhat": {"tong": float(np.nansum(_ls)),
                                     "tb_ngay": round(float(np.nanmean(_ls)), 2) if np.isfinite(_ls).any() else None,
                                     "cao_nhat": float(np.nanmax(_ls)) if np.isfinite(_ls).any() else None},
        "hom_nay": {"ngay": str((ctx.bat_dau + pd.Timedelta(days=k)).date()), "du_bao_ban": round(float(v["d_hat"][k]), 2),
                    "ton_an_toan": round(float(v["ss"][k]), 1), "diem_dat_hang": round(float(v["rop"][k]), 1),
                    "giao_sau_ngay": int(v["L"])},
        "du_bao": {"tu_ngay": str(_ng[0].date()), "so_ngay": len(_d), "tong": round(float(_d.sum())),
                   "tb_ngay": round(float(_d.mean()), 2), "ngay_dinh": str(_ng[int(_d.argmax())].date()),
                   "luong_ngay_dinh": round(float(_d.max()), 1),
                   "theo_tuan": [round(float(_d[i:i + 7].sum())) for i in range(0, min(len(_d), 84), 7)]},
        "sai_so_wape_ngoai_mau": me.get("wape_du_bao"), "sai_so_neu_dung_trung_binh": me.get("wape_trung_binh"),
        "kiem_dinh_theo_mua": [] if not len(_kd) else
        _kd[["mua", "nam", "wape_dinh_mo_hinh", "wape_dinh_nam_ngoai", "lech_tong_dinh"]].round(3).to_dict("records")}


def boi_canh_ai(ctx, ngay, bang, don, suc_chua, kh_=None, von_=None):
    return {"kh": ctx.kh if kh_ is None else kh_, "bang": bang, "don": don, "suc_chua": suc_chua, "ngay": pd.Timestamp(ngay),
            "von": float(ctx.von if von_ is None else von_),
            "nguon_du_lieu": {"mo_phong": "mô phỏng (minh hoạ)", "so_kiem_kho": "sổ kiểm kho của người bán (lượng bán suy ra "
                              "từ số đếm; mặt hàng ít ngày đo dùng ước lượng ban đầu)"}.get(
                                  ctx.ten_nguon, f"file của người dùng {ctx.ten_nguon}")}


def ngay_dang_xem(ctx):
    lo_, hi_ = ctx.bat_dau.date(), (ctx.bat_dau + pd.Timedelta(days=ctx.so_ngay - 1)).date()
    ngay_ = min(max(ss.get("ngay_hn_v", lo_), lo_), hi_)
    return ngay_, (pd.Timestamp(ngay_) - ctx.bat_dau).days


def du_lieu_sua(ctx):
    """Bản sao dữ liệu AI được phép sửa (bảng mặt hàng giữ đơn vị % như trong app)."""
    ton_ = ss["ton_cur"].fillna(0) if "ton_cur" in ss and list(ss["ton_cur"]["mat_hang"]) == ctx.skus else ton_mac_dinh(ctx)
    return {"mh": ss["mh_cur"], "nguon": ss["nguon_cur"].dropna(how="all"),
            "khu": nm.bo_sung_cot_khu(ss["khu_cur"].dropna(how="all")), "ton": ton_, "von": float(ctx.von)}


def tinh_lai_ai(ctx, dl):
    """Dựng lại kế hoạch hôm nay từ dữ liệu AI vừa sửa, để công cụ đọc trả số liệu mới."""
    ngay_, k_ = ngay_dang_xem(ctx)
    kh2 = nm.ke_hoach(ctx.ban_hang, mh_mo_hinh(dl["mh"]), dl["nguon"], dl["khu"], ctx.so_ngay, du_bao=ctx.db,
                      xu_huong=ctx.xu_huong, uoc_luong=ctx.uoc_luong)
    lo_ = ss.get("lo_cur") if ss.get("lo_sig") == ctx.sig else None
    b_, d_, s_ = nm.ke_hoach_hom_nay(kh2, k_, dl["ton"], dl["von"], di_cho=set(ss.get("di_cho", [])), lo_them=lo_)
    return boi_canh_ai(ctx, ngay_, b_, d_, s_, kh2, dl["von"])


def bc_hien_tai(ctx):
    ngay_, k_ = ngay_dang_xem(ctx)
    dl = du_lieu_sua(ctx)
    lo_ = ss.get("lo_cur") if ss.get("lo_sig") == ctx.sig else None
    b_, d_, s_ = nm.ke_hoach_hom_nay(ctx.kh, k_, dl["ton"], ctx.von, di_cho=set(ss.get("di_cho", [])), lo_them=lo_)
    return boi_canh_ai(ctx, ngay_, b_, d_, s_)


def ap_dung_sua(ctx, bo_sua):
    """Áp các thay đổi AI vào app; lưu bản trước đó để hoàn tác. Trả về danh sách thay đổi."""
    if bo_sua is None or not bo_sua.thay_doi:
        return []
    ss.setdefault("ai_hoan_tac", []).append({"du_lieu": du_lieu_sua(ctx), "thay_doi": list(bo_sua.thay_doi)})
    doi = {t["bang"] for t in bo_sua.thay_doi}
    for b in ("mh", "nguon", "khu", "ton"):
        if b in doi:
            dat_bang(b, bo_sua.dl[b])
    if "von" in doi:
        ss["_cho_von"] = float(bo_sua.dl["von"])
    return list(bo_sua.thay_doi)


def mo_ta_thay_doi(td):
    def f(x):
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            return str(x)
        return f"{x:,.0f}".replace(",", ".") if abs(x) >= 100 or float(x).is_integer() else f"{x:g}".replace(".", ",")
    return "\n".join(f"- **{t['doi_tuong']}** · {t['mo_ta']}: {f(t['cu'])} → **{f(t['moi'])}**" for t in td)


def nut_hoan_tac(khoa):
    if ss.get("ai_hoan_tac"):
        lan = ss["ai_hoan_tac"][-1]
        if st.button(f"↩️ Hoàn tác lần AI sửa gần nhất ({len(lan['thay_doi'])} thay đổi)", key=khoa):
            snap = ss["ai_hoan_tac"].pop()
            for b in ("mh", "nguon", "khu", "ton"):
                dat_bang(b, snap["du_lieu"][b])
            ss["_cho_von"] = snap["du_lieu"]["von"]
            st.rerun()


def client_ai(ctx):
    """(client, None) nếu sẵn sàng; (None, thông báo) nếu chưa."""
    if not ctx.ai_key:
        return None, ("Chưa có OpenAI API key. Thêm dòng OPENAI_API_KEY = \"sk-...\" vào tệp .streamlit/secrets.toml "
                      "(hoặc đặt biến môi trường OPENAI_API_KEY) rồi khởi động lại ứng dụng.")
    try:
        return tl.tao_client(ctx.ai_key), None
    except Exception as e:                                     # noqa: BLE001
        return None, tl.loi_than_thien(e)


def _chay_phan_tich(ctx, khoa, chu_de, du_lieu, bam):
    """Gọi AI khi bấm, nhớ kết quả theo dấu vân tay số liệu; hiện kết quả hoặc lời nhắc. Trả về True nếu đã có kết quả."""
    dau = hashlib.md5(json.dumps(du_lieu, ensure_ascii=False, default=str, sort_keys=True).encode()).hexdigest() + ctx.ai_mo_hinh
    if bam:
        client, thong_bao = client_ai(ctx)
        if client is None:
            st.warning(thong_bao)
        else:
            with st.spinner("AI đang đọc số liệu..."):
                try:
                    ss[f"pt_kq_{khoa}"] = (dau, tl.phan_tich(client, ctx.ai_mo_hinh, chu_de, du_lieu))
                except Exception as e:                         # noqa: BLE001
                    st.error(tl.loi_than_thien(e))
    kq = ss.get(f"pt_kq_{khoa}")
    if kq and kq[0] == dau:
        st.markdown(kq[1])
        st.caption("AI chỉ diễn giải số liệu do thuật toán tính.")
        return True
    if kq:
        st.caption("Số liệu đã đổi so với lần phân tích trước. Bấm ✨ để cập nhật.")
    return False


def hop_phan_tich(ctx, khoa, chu_de, du_lieu,
                  mo_ta="AI đọc số liệu của bảng ở trên và nêu điều đáng chú ý, ý nghĩa, việc nên làm."):
    """Khung "AI phân tích" nằm ngang (dùng dưới bảng). Kết quả được nhớ theo số liệu (đổi số liệu thì phải phân tích lại)."""
    with st.container(border=True):
        c1_, c2_ = st.columns([4, 1])
        c1_.markdown(f"##### 🤖 AI phân tích · {chu_de}")
        bam = c2_.button("✨ Phân tích", key=f"pt_{khoa}", use_container_width=True, type="primary")
        if not _chay_phan_tich(ctx, khoa, chu_de, du_lieu, bam) and not bam and f"pt_kq_{khoa}" not in ss:
            st.caption(mo_ta)


@contextmanager
def bieu_do_co_ai(ctx, tieu, khoa, chu_de, du_lieu):
    """Khung một biểu đồ: tiêu đề, biểu đồ bên trái (vẽ trong khối with), ô AI phân tích bên phải.
    du_lieu: dict số liệu của CHÍNH biểu đồ này (AI không tự tính số). Nút AI có khoá pt_<khoa>."""
    with st.container(border=True, key=f"khung_{khoa}"):
        st.markdown(f"##### {tieu}")
        c_bd, c_ai = st.columns([3, 1.15], gap="medium")
        with c_bd:
            yield
        with c_ai.container(border=True, key=f"ai_{khoa}"):
            st.markdown('<div class="ai-ben">🤖 AI phân tích</div>', unsafe_allow_html=True)
            bam = st.button("✨ Phân tích", key=f"pt_{khoa}", use_container_width=True, type="primary")
            if not _chay_phan_tich(ctx, khoa, chu_de, du_lieu, bam) and not bam and f"pt_kq_{khoa}" not in ss:
                st.caption("AI đọc số liệu của biểu đồ này rồi nêu điều đáng chú ý và việc nên làm.")


def chay_ai_sua(ctx, cau, lich_su, cho_sua=True):
    """Gọi trợ lý với quyền sửa dữ liệu. Trả về (câu trả lời, công cụ đã gọi, thay đổi đã áp dụng) hoặc ném lỗi."""
    client, thong_bao = client_ai(ctx)
    if client is None:
        raise RuntimeError(thong_bao)
    bo = tl.BoSua(du_lieu_sua(ctx)) if cho_sua else None
    tra_loi_, da_goi_ = tl.tra_loi(client, ctx.ai_mo_hinh, lich_su, cau, bc_hien_tai(ctx), bo_sua=bo,
                                   tinh_lai=(lambda dl: tinh_lai_ai(ctx, dl)) if bo is not None else None)
    return tra_loi_, da_goi_, ap_dung_sua(ctx, bo)
