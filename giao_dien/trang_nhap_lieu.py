# -*- coding: utf-8 -*-
"""Trang 📝 Nhập dữ liệu: chọn nguồn số liệu bán hàng, kiểm kho cuối ngày, mặt hàng + ước lượng ban đầu, sổ đã ghi, tải file.

Trang này không cần dự báo / kế hoạch (app.py vẽ nó ngay sau thanh bên rồi dừng), nên dùng được cả khi chưa có dữ liệu.
Sổ kiểm kho và ước lượng được lưu ngay vào cau_hinh.noi_luu_so() (MongoDB hoặc thư mục CSV) khi bấm nút lưu.
"""
import numpy as np
import pandas as pd
import streamlit as st

from tinh_toan import loi, so_ghi
from giao_dien.cau_hinh import DL_CUA_TOI, DL_MO_PHONG, DL_SO_GHI, noi_luu_so
from giao_dien.du_lieu import chon_nguon_du_lieu, khung_tai_doanh_so
from giao_dien.kieu import kpi_hang, tieu_de
from giao_dien.tien_ich import csv_bytes

ss = st.session_state
NHAN_CHE_DO = {"uoc_luong": "🎯 Chỉ có ước lượng", "dang_hoc": "📏 Đang học", "day_du": "✅ Đủ dữ liệu"}


def _ver(ten):
    return ss.get(f"{ten}_ver", 0)


def _luu(kk=None, uoc=None, thong_bao=""):
    try:
        so_ghi.ghi_so(noi_luu_so(), kk=kk, uoc=uoc)
    except ValueError as e:
        st.error(f"❌ {e}")
        return
    for ten in ("kk", "uoc", "so"):                             # bảng sửa được dựng lại từ dữ liệu vừa lưu
        ss[f"{ten}_ver"] = _ver(ten) + 1
    ss.pop("ton_cur", None)                                     # tồn kho trang Hôm nay lấy lại từ lần đếm mới
    ss["nl_thong_bao"] = thong_bao
    st.rerun()


def _bao_loi(loi_):
    st.error("Chưa lưu được:\n\n- " + "\n- ".join(loi_))


def ve(ctx):
    """Vẽ trang Nhập dữ liệu."""
    tieu_de("📝", "Nhập dữ liệu", "Chọn nơi lấy số liệu bán hàng · chưa có sổ sách thì kiểm kho mỗi tối, app tự đo lượng bán")
    if ss.get("nl_thong_bao"):
        st.success(ss.pop("nl_thong_bao"))
    with st.container(border=True):
        st.markdown("##### ① App lấy số liệu bán hàng từ đâu?")
        chon_nguon_du_lieu()
        nguon = ss["nguon_du_lieu"]
        if nguon == DL_MO_PHONG:
            st.caption("Đang dùng số liệu giả lập để xem thử. Khi bán thật, chọn **Sổ kiểm kho của tôi**.")
        elif nguon == DL_CUA_TOI and not ss.get("file_du_lieu"):
            st.warning("Chưa có file doanh số. Tải lên ở tab **📂 File doanh số** bên dưới.")
        noi_luu = noi_luu_so()
        st.caption(f"Sổ kiểm kho, ước lượng và thiết lập lưu tại: **{so_ghi.mo_ta_noi_luu(noi_luu)}**" +
                   ("" if so_ghi.la_mongo(noi_luu) else " (MongoDB không chạy hoặc đang chạy thử)"))

    loi_doc = None
    try:
        kk, uoc = so_ghi.doc_so(noi_luu_so())
    except ValueError as e:
        loi_doc = str(e)
        kk, uoc = so_ghi.kiem_kho_trong(), so_ghi.uoc_luong_trong()
    if loi_doc:
        st.error(f"❌ {loi_doc} Sửa ở tab 📒 Sổ đã ghi.")
    hom_nay = pd.Timestamp.today().normalize()
    rong, canh_bao = so_ghi.bang_ban_hang(kk, uoc, hom_nay)
    ds_mh = list(dict.fromkeys(list(uoc["mat_hang"]) + list(kk["mat_hang"])))

    if ds_mh:
        _tinh_trang(kk, uoc, rong, nguon)
    for c in canh_bao:
        st.warning(c)

    t_kk, t_uoc, t_so, t_file = st.tabs(["🧮 Kiểm kho cuối ngày", "🎯 Mặt hàng & ước lượng ban đầu", "📒 Sổ đã ghi",
                                         "📂 File doanh số"])
    with t_kk:
        _kiem_kho(kk, ds_mh, hom_nay)
    with t_uoc:
        _uoc_luong(uoc, kk)
    with t_so:
        _so_da_ghi(kk)
    with t_file:
        if nguon != DL_CUA_TOI:
            st.caption("Tải file lên thì app chuyển sang dùng file đó.")
        khung_tai_doanh_so()


def _tinh_trang(kk, uoc, rong, nguon):
    """Mỗi mặt hàng đã đo được bao nhiêu ngày và app đang dùng mức bán nào."""
    tt = so_ghi.tom_tat_do_luong(kk, uoc, rong)
    with st.container(border=True):
        st.markdown("##### 📏 Tình trạng đo lượng bán (sổ kiểm kho)")
        if nguon != DL_SO_GHI:
            st.caption("App đang dùng nguồn khác; bảng này cho biết sổ kiểm kho đã đo được tới đâu.")
        n_du = int((tt["che_do"] == "day_du").sum())
        lan_cuoi = kk["ngay"].max() if len(kk) else None
        kpi_hang([("🍬 Mặt hàng trong sổ", str(len(tt)), f"{len(uoc)} có ước lượng ban đầu", "#f2542d"),
                  ("📅 Lần đếm gần nhất", f"{lan_cuoi:%d/%m}" if lan_cuoi is not None else "Chưa đếm",
                   "Mỗi tối đếm một lần là tốt nhất", "#ff8a3d"),
                  ("✅ Đủ dữ liệu", f"{n_du}/{len(tt)}", f"cần {loi.NGAY_DAY_DU} ngày đo để dự báo theo mùa", "#16a34a")])
        hien = pd.DataFrame({
            "Mặt hàng": tt["mat_hang"], "Trạng thái": tt["che_do"].map(NHAN_CHE_DO),
            "Đã đo (ngày)": tt["so_ngay_do"], "Tiến độ": np.minimum(tt["so_ngay_do"] / loi.NGAY_DAY_DU, 1.0),
            "Bán TB đo được": tt["ban_tb_do"], "Ước lượng của bạn": tt["ban_thuong_uoc"],
            "App đang dùng (đv/ngày)": tt["muc_dang_dung"],
            "Lần đếm cuối": pd.to_datetime(tt["lan_dem_cuoi"]).dt.strftime("%d/%m/%Y").fillna("—"),
            "Còn lúc đếm": tt["ton_cuoi"]})
        st.dataframe(hien, hide_index=True, use_container_width=True, column_config={
            "Tiến độ": st.column_config.ProgressColumn(f"Tới {loi.NGAY_DAY_DU} ngày", min_value=0.0, max_value=1.0, format="percent"),
            "Bán TB đo được": st.column_config.NumberColumn(format="%.1f"),
            "Ước lượng của bạn": st.column_config.NumberColumn(format="%.1f"),
            "App đang dùng (đv/ngày)": st.column_config.NumberColumn(format="%.1f"),
            "Còn lúc đếm": st.column_config.NumberColumn(format="%.0f")})
        st.caption(f"Lúc đầu app dùng ước lượng của bạn (nặng bằng {loi.TRONG_SO_UOC_LUONG} ngày đo) trộn với số đo được; đo càng "
                   f"nhiều ngày thì số đo càng quyết định. Đủ {loi.NGAY_DAY_DU} ngày thì app học thêm thứ trong tuần, mùa Tết, "
                   "Trung thu. Khi còn ít số liệu, tồn an toàn được để cao hơn cho chắc.")


def _kiem_kho(kk, ds_mh, hom_nay):
    if not ds_mh:
        st.info("Sổ chưa có mặt hàng nào. Vào tab **🎯 Mặt hàng & ước lượng ban đầu** để thêm danh sách mặt hàng trước.")
        return
    st.markdown("**Mỗi tối, đếm hàng còn lại và ghi hàng mới nhập.** App tự tính: "
                "*đã bán = còn lần trước + nhập thêm − hỏng/bỏ − còn hôm nay*. Không cần ghi từng lần bán.")
    c1, c2 = st.columns([1, 3])
    ngay = pd.Timestamp(c1.date_input("📅 Ngày đếm", value=hom_nay.date(), max_value=hom_nay.date(), format="DD/MM/YYYY",
                                      key="kk_ngay"))
    truoc = so_ghi.lan_dem_cuoi(kk, truoc_ngay=ngay)
    da_co = kk[kk["ngay"] == ngay].set_index("mat_hang")
    if len(da_co):
        c2.info(f"Ngày {ngay:%d/%m/%Y} đã có {len(da_co)} dòng trong sổ: bảng dưới hiện số đã ghi, lưu lại sẽ thay số cũ.")

    def lay(m, c, mac_dinh):
        return da_co.loc[m, c] if m in da_co.index else mac_dinh

    base = pd.DataFrame({
        "mat_hang": ds_mh,
        "lan_truoc": [f"{truoc.loc[m, 'ngay']:%d/%m}: còn {truoc.loc[m, 'ton_cuoi_ngay']:.0f}" if m in truoc.index
                      else "Lần đầu" for m in ds_mh],
        "ton_cuoi_ngay": [lay(m, "ton_cuoi_ngay", np.nan) for m in ds_mh],
        "nhap_them": [lay(m, "nhap_them", 0.0) for m in ds_mh],
        "hu_hong": [lay(m, "hu_hong", 0.0) for m in ds_mh],
        "het_hang": [bool(lay(m, "het_hang", False)) for m in ds_mh]})
    ed = st.data_editor(base, key=f"kk_ed_{ngay:%Y%m%d}_{_ver('kk')}", hide_index=True, use_container_width=True,
                        disabled=["mat_hang", "lan_truoc"], column_config={
                            "mat_hang": "Mặt hàng",
                            "lan_truoc": st.column_config.TextColumn("Lần đếm trước"),
                            "ton_cuoi_ngay": st.column_config.NumberColumn("Đếm được còn", min_value=0, step=1, format="%d",
                                                                           help="Bỏ trống nếu hôm nay không đếm mặt hàng này"),
                            "nhap_them": st.column_config.NumberColumn("Nhập thêm", min_value=0, step=1, format="%d",
                                                                       help="Hàng mới về kể từ lần đếm trước"),
                            "hu_hong": st.column_config.NumberColumn("Hỏng / bỏ đi", min_value=0, step=1, format="%d",
                                                                     help="Hàng hỏng, hết hạn, đem cho... kể từ lần đếm trước"),
                            "het_hang": st.column_config.CheckboxColumn("Có lúc hết hàng",
                                                                        help="Đánh dấu nếu có lúc hết sạch mặt hàng này: "
                                                                             "số bán những ngày đó sẽ không dùng để đo")})
    da_dem = ed[ed["ton_cuoi_ngay"].notna()]
    if len(da_dem):
        xem = []
        for _, r in da_dem.iterrows():
            m = r["mat_hang"]
            if m not in truoc.index:
                xem.append({"Mặt hàng": m, "Suy ra đã bán": None, "Trong (ngày)": None, "Ghi chú": "Lần đầu: làm mốc, lần sau mới tính được"})
                continue
            k = int((ngay - truoc.loc[m, "ngay"]).days)
            ban = truoc.loc[m, "ton_cuoi_ngay"] + np.nan_to_num(r["nhap_them"]) - np.nan_to_num(r["hu_hong"]) - r["ton_cuoi_ngay"]
            ghi = "⚠️ Âm: có thể quên ghi hàng nhập" if ban < 0 else \
                ("Hết hàng: không dùng để đo" if r["het_hang"] else (f"≈ {ban / k:.1f} đv/ngày" if k > 1 else ""))
            xem.append({"Mặt hàng": m, "Suy ra đã bán": ban, "Trong (ngày)": k, "Ghi chú": ghi})
        st.dataframe(pd.DataFrame(xem), hide_index=True, use_container_width=True,
                     column_config={"Suy ra đã bán": st.column_config.NumberColumn(format="%.0f")})
    if st.button(f"💾 Lưu kiểm kho ngày {ngay:%d/%m/%Y}", type="primary", key="kk_luu", disabled=not len(da_dem)):
        moi = da_dem.drop(columns=["lan_truoc"]).assign(ngay=ngay)
        kk2, loi_ = so_ghi.cap_nhat_kiem_kho(kk, moi)
        if loi_:
            _bao_loi(loi_)
        else:
            _luu(kk=kk2, thong_bao=f"Đã lưu kiểm kho ngày {ngay:%d/%m/%Y} ({len(moi)} mặt hàng).")
    if not len(da_dem):
        st.caption("Nhập số **Đếm được còn** cho ít nhất một mặt hàng để lưu.")


def _uoc_luong(uoc, kk):
    st.markdown("**Danh sách mặt hàng và bạn đoán mỗi ngày bán khoảng bao nhiêu.** Nhờ số đoán này, app có điểm đặt hàng "
                "ngay từ hôm nay; sau đó số đo từ kiểm kho sẽ dần thay thế.")
    base = uoc if len(uoc) else so_ghi.uoc_luong_trong()
    ed = st.data_editor(base, num_rows="dynamic", key=f"uoc_ed_{_ver('uoc')}", hide_index=True, use_container_width=True,
                        column_config={
                            "mat_hang": st.column_config.TextColumn("Mặt hàng", required=True, width="medium"),
                            "ban_it_nhat": st.column_config.NumberColumn("Ngày ế bán (ít nhất)", min_value=0.0, step=1.0, format="%.1f",
                                                                         help="Bỏ trống thì lấy bằng nửa mức thường"),
                            "ban_thuong": st.column_config.NumberColumn("Ngày thường bán", min_value=0.0, step=1.0, format="%.1f"),
                            "ban_nhieu_nhat": st.column_config.NumberColumn("Ngày đắt hàng (nhiều nhất)", min_value=0.0, step=1.0,
                                                                            format="%.1f",
                                                                            help="Bỏ trống thì lấy bằng 1,5 lần mức thường")})
    st.caption("Ví dụ: kẹo dừa, ngày ế 4 gói, ngày thường 8, ngày đắt hàng 15. Khoảng ít–nhiều càng rộng (càng không chắc) "
               "thì tồn an toàn càng cao. Tên mặt hàng nên giống tên ở trang Mặt hàng & kho.")
    with st.expander("🧮 Không chắc mỗi ngày bán bao nhiêu? Tính từ thời gian bán hết một lô"):
        c1, c2, c3 = st.columns(3)
        lo = c1.number_input("Một lô / thùng có (đv)", min_value=1, value=50, step=1, key="uoc_lo")
        ngay_het = c2.number_input("Thường bán hết trong (ngày)", min_value=1, value=7, step=1, key="uoc_ngay_het")
        c3.metric("≈ Bán mỗi ngày", f"{lo / ngay_het:.1f}".replace(".", ","))
    if st.button("💾 Lưu danh sách & ước lượng", type="primary", key="uoc_luu"):
        uoc2, loi_ = so_ghi.chuan_hoa_uoc_luong(ed)
        if loi_:
            _bao_loi(loi_)
        else:
            bo = [m for m in dict.fromkeys(kk["mat_hang"]) if m not in set(uoc2["mat_hang"])]
            _luu(uoc=uoc2, thong_bao=f"Đã lưu {len(uoc2)} mặt hàng." +
                 (f" Lưu ý: {', '.join(bo)} vẫn còn trong sổ kiểm kho nên vẫn được dự báo từ số đo." if bo else ""))


def _so_da_ghi(kk):
    if not len(kk):
        st.info("Sổ kiểm kho còn trống. Lưu lần kiểm kho đầu tiên ở tab **🧮 Kiểm kho cuối ngày**.")
    else:
        st.caption("Sửa số đã ghi nhầm hoặc xoá dòng (chọn dòng rồi bấm thùng rác), rồi bấm lưu.")
        hien = kk.sort_values(["ngay", "mat_hang"], ascending=[False, True]).reset_index(drop=True)
        ed = st.data_editor(hien, num_rows="dynamic", key=f"so_ed_{_ver('so')}", hide_index=True, use_container_width=True,
                            column_config={
                                "ngay": st.column_config.DateColumn("Ngày", format="DD/MM/YYYY"),
                                "mat_hang": "Mặt hàng",
                                "ton_cuoi_ngay": st.column_config.NumberColumn("Đếm được còn", min_value=0, format="%d"),
                                "nhap_them": st.column_config.NumberColumn("Nhập thêm", min_value=0, format="%d"),
                                "hu_hong": st.column_config.NumberColumn("Hỏng / bỏ đi", min_value=0, format="%d"),
                                "het_hang": st.column_config.CheckboxColumn("Có lúc hết hàng")})
        c1, c2 = st.columns(2)
        if c1.button("💾 Lưu thay đổi sổ", key="so_luu", type="primary"):
            kk2, loi_ = so_ghi.chuan_hoa_kiem_kho(ed)
            if loi_:
                _bao_loi(loi_)
            else:
                _luu(kk=kk2, thong_bao="Đã lưu thay đổi sổ kiểm kho.")
        c2.download_button("⬇️ Tải sổ kiểm kho (CSV)", csv_bytes(kk.assign(ngay=kk["ngay"].dt.strftime("%Y-%m-%d"))),
                           "kiem_kho.csv", "text/csv", key="so_tai")
        dai, _ = so_ghi.suy_ra_ban(kk)
        with st.expander("Lượng bán mỗi ngày app suy ra từ sổ"):
            if len(dai):
                st.dataframe(dai.rename(columns={"ngay": "Ngày", "mat_hang": "Mặt hàng", "so_luong_ban": "Đã bán (đv/ngày)",
                                                 "het_hang": "Hết hàng", "khoang_ngay": "Giữa hai lần đếm (ngày)"}),
                             hide_index=True, use_container_width=True,
                             column_config={"Ngày": st.column_config.DateColumn(format="DD/MM/YYYY"),
                                            "Đã bán (đv/ngày)": st.column_config.NumberColumn(format="%.1f")})
            else:
                st.caption("Cần ít nhất hai lần đếm của cùng một mặt hàng.")
    with st.expander("📥 Nhập sổ từ file CSV (ví dụ sổ chép từ máy khác)"):
        f = st.file_uploader("File sổ kiểm kho", type=["csv", "xlsx", "xls"], key=f"so_up_{_ver('so')}")
        st.caption("Cột: ngay, mat_hang, ton_cuoi_ngay, nhap_them, hu_hong, het_hang. Dòng trùng ngày và mặt hàng sẽ thay dòng cũ.")
        if f is not None and st.button("➕ Gộp vào sổ", key="so_gop"):
            try:
                kk2, loi_ = so_ghi.cap_nhat_kiem_kho(kk, loi.doc_file(f))
            except ValueError as e:
                kk2, loi_ = None, [str(e)]
            if loi_:
                _bao_loi(loi_)
            else:
                _luu(kk=kk2, thong_bao=f"Đã gộp {f.name} vào sổ kiểm kho.")
