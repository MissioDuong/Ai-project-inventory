# -*- coding: utf-8 -*-
"""
Trợ lý AI (LLM của OpenAI) cho tiểu thương: hỏi đáp bằng tiếng Việt về việc nhập hàng.

Nguyên tắc thiết kế:
  - LLM KHÔNG tự tính số. Mọi con số (nhập bao nhiêu, ROP, tồn an toàn, dự báo, chi phí) đến từ các hàm tính toán
    minh bạch trong loi.py / nhieu_mat_hang.py, được LLM gọi qua cơ chế function calling (tool use).
  - LLM làm phần mà công thức không làm được: hiểu câu hỏi tự nhiên, chọn đúng công cụ, giải thích kết quả
    bằng lời dễ hiểu, gợi ý hành động (bán đẩy hàng sắp hết hạn, mua kèm...).
  - API key đọc từ biến môi trường OPENAI_API_KEY, hoặc .streamlit/secrets.toml (không đưa lên GitHub).
"""
import json
import math
import os

import numpy as np
import pandas as pd

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # thư mục gốc dự án
MO_HINH_MAC_DINH = "gpt-4o-mini"
MO_HINH_GOI_Y = ["gpt-4o-mini", "gpt-4.1-mini", "gpt-5-mini", "gpt-4o", "gpt-4.1"]
SO_VONG_CONG_CU = 6

HUONG_DAN = """Bạn là "Trợ lý nhập hàng" của ứng dụng EOQ Bánh Kẹo Chợ, giúp tiểu thương bánh kẹo ở chợ truyền thống
Việt Nam quyết định nhập hàng cho NHIỀU mặt hàng thực phẩm (có hạn dùng, hư hỏng, bảo quản, vốn và sức chứa kho).

Quy tắc bắt buộc:
- MỌI con số (số lượng nên nhập, tiền, điểm đặt hàng, tồn an toàn, dự báo, chi phí, phần trăm) PHẢI lấy từ công cụ.
  Không tự tính nhẩm, không đoán. Nếu công cụ không có thông tin, nói rõ là không có.
- Trả lời bằng tiếng Việt, ngắn gọn, thân thiện, dễ hiểu với người bán hàng (tránh thuật ngữ; nếu dùng thì giải thích).
  Dùng gạch đầu dòng và in đậm con số quan trọng. Tiền viết dạng 1.250.000 đ.
- Khi khuyên nhập hàng: nêu nguồn hàng, mặt hàng, số lượng, tiền, và lý do (phải đặt vì sắp hết / mua kèm vì đằng nào
  cũng đi chuyến này). Khi có hàng có thể hết hạn: gợi ý bày phía trước, bán giảm giá, bán kèm.
- Nếu dữ liệu là dữ liệu mô phỏng, nhắc một lần rằng con số chỉ để minh hoạ.
- Lịch sự từ chối câu hỏi không liên quan tới bán hàng, nhập hàng, tồn kho của sạp.
- SỬA DỮ LIỆU (chỉ khi có công cụ sua_...): chỉ sửa khi người dùng yêu cầu rõ ràng. Nếu yêu cầu mơ hồ (không rõ mặt hàng,
  không rõ giá trị) thì hỏi lại, không đoán. Với yêu cầu tương đối ("tăng 10 %", "thêm 20 gói") hãy đọc giá trị hiện tại
  bằng công cụ trước rồi mới sửa. Sau khi sửa, báo lại từng thay đổi "giá trị cũ → giá trị mới"; nếu công cụ báo lỗi
  (giá trị không hợp lệ) thì giải thích cho người dùng. Sau khi sửa, gọi lại công cụ đọc để lấy số liệu kế hoạch MỚI.
Bối cảnh hiện tại (từ ứng dụng): {boi_canh}"""


# ----------------------------------------------------------------------------
# API KEY VÀ CLIENT
# ----------------------------------------------------------------------------
def doc_cau_hinh():
    """Trả về (api_key, mô hình) từ biến môi trường hoặc .streamlit/secrets.toml (cạnh file này hoặc thư mục chạy)."""
    key, mo_hinh = os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_MODEL")
    for duong in (os.path.join(THU_MUC, ".streamlit", "secrets.toml"), os.path.join(os.getcwd(), ".streamlit", "secrets.toml")):
        if (key and mo_hinh) or not os.path.exists(duong):
            continue
        try:
            import tomllib
            with open(duong, "rb") as f:
                cfg = tomllib.load(f)
            key = key or cfg.get("OPENAI_API_KEY")
            mo_hinh = mo_hinh or cfg.get("OPENAI_MODEL")
        except Exception:                                     # noqa: BLE001
            pass
    return key, mo_hinh or MO_HINH_MAC_DINH


def tao_client(api_key):
    from openai import OpenAI
    return OpenAI(api_key=api_key, timeout=60)


def loi_than_thien(e):
    """Đổi lỗi API thành câu tiếng Việt dễ hiểu."""
    ten, s = type(e).__name__, str(e)
    if "insufficient_quota" in s or "no credits" in s.lower() or "quota" in s.lower():
        return ("Tài khoản OpenAI đã **hết tín dụng**. Vào https://platform.openai.com/settings/organization/billing "
                "để nạp thêm, rồi thử lại. Các chức năng tính toán của ứng dụng vẫn dùng bình thường.")
    if ten == "AuthenticationError" or "invalid_api_key" in s:
        return "API key không hợp lệ hoặc đã bị thu hồi. Kiểm tra lại OPENAI_API_KEY."
    if ten == "NotFoundError" or "model_not_found" in s:
        return "Tài khoản không dùng được mô hình đã chọn. Hãy chọn mô hình khác ở ô cài đặt."
    if ten == "RateLimitError":
        return "OpenAI đang giới hạn tốc độ (gọi quá nhanh). Đợi vài giây rồi thử lại."
    if ten in ("APIConnectionError", "APITimeoutError"):
        return "Không kết nối được tới OpenAI. Kiểm tra mạng internet."
    return f"Lỗi khi gọi AI: {ten}: {s[:200]}"


# ----------------------------------------------------------------------------
# CÔNG CỤ (mọi con số do code tính)
# ----------------------------------------------------------------------------
def _so(x, nd=0):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return None
    return round(float(x), nd) if nd else int(round(float(x)))


def _tim(ds, ten):
    ten = str(ten).strip().lower()
    dung = [m for m in ds if m.lower() == ten]
    return dung or [m for m in ds if ten in m.lower()]


class CongCu:
    """Bọc trạng thái hiện tại của ứng dụng thành các công cụ cho LLM.
    bc: dict gồm kh (kế hoạch), bang/don/suc_chua (kết quả ke_hoach_hom_nay), ngay (Timestamp), von, nguon_du_lieu,
        ket_qua_mo_phong (dict, tuỳ chọn)."""

    def __init__(self, bc):
        self.bc = bc
        self.kh = bc["kh"]
        self.info = self.kh["info"]
        self.ds = list(self.kh["mat_hang"])

    # --- định nghĩa công cụ theo chuẩn OpenAI ---
    DINH_NGHIA = [
        {"type": "function", "function": {
            "name": "danh_sach_di_cho",
            "description": "Danh sách đi chợ HÔM NAY theo từng nguồn hàng: mặt hàng, số lượng, tiền, lý do (phải đặt / mua kèm), "
                           "chu kỳ gộp, ràng buộc vốn/sức chứa nếu có.",
            "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {
            "name": "tinh_trang_mat_hang",
            "description": "Tình trạng HÔM NAY của một mặt hàng: tồn, điểm đặt hàng, tồn an toàn, có cần nhập không, phần có thể hết "
                           "hạn, hạn dùng thực tế, nguồn hàng, chỗ cất, giá.",
            "parameters": {"type": "object", "properties": {
                "mat_hang": {"type": "string", "description": "Tên mặt hàng, có thể gõ một phần, ví dụ 'mứt'"}},
                "required": ["mat_hang"]}}},
        {"type": "function", "function": {
            "name": "du_bao_nhu_cau",
            "description": "Dự báo lượng bán của một mặt hàng trong N ngày tới (từ ngày đang xem): tổng, trung bình/ngày, ngày bán "
                           "cao nhất, và hệ số mùa Tết / Trung thu.",
            "parameters": {"type": "object", "properties": {
                "mat_hang": {"type": "string"},
                "so_ngay": {"type": "integer", "description": "Số ngày tới, 1–120, mặc định 30"}},
                "required": ["mat_hang"]}}},
        {"type": "function", "function": {
            "name": "hang_sap_het_han_va_canh_bao",
            "description": "Các mặt hàng đang hết hàng / dưới mức an toàn, và các mặt hàng có phần có thể hết hạn trước khi bán kịp "
                           "(số lượng và tiền vốn).",
            "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {
            "name": "so_sanh_cach_nhap_hang",
            "description": "Kết quả mô phỏng so sánh các cách nhập hàng (kinh nghiệm, EOQ cổ điển, EOQ từng mặt hàng, nhập gộp) cùng "
                           "điều kiện: tổng chi phí, mức tiết kiệm, đóng góp của từng thành phần.",
            "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {
            "name": "tinh_eoq",
            "description": "Tính EOQ cổ điển Q* = sqrt(2DS/H) cho bài toán tổng quát người dùng đưa ra.",
            "parameters": {"type": "object", "properties": {
                "nhu_cau_nam": {"type": "number"}, "chi_phi_moi_lan_dat": {"type": "number"},
                "chi_phi_giu_1_don_vi_nam": {"type": "number"}},
                "required": ["nhu_cau_nam", "chi_phi_moi_lan_dat", "chi_phi_giu_1_don_vi_nam"]}}},
    ]

    def goi(self, ten, tham_so):
        ham = getattr(self, ten, None)
        if ham is None or ten.startswith("_"):
            return {"loi": f"Không có công cụ '{ten}'."}
        try:
            return ham(**(tham_so or {}))
        except TypeError as e:
            return {"loi": f"Thiếu hoặc sai tham số: {e}"}
        except Exception as e:                                 # noqa: BLE001
            return {"loi": f"Lỗi khi tính: {e}"}

    def _mh(self, ten):
        kq = _tim(self.ds, ten)
        if len(kq) != 1:
            return None, {"loi": f"Không xác định được mặt hàng '{ten}'.", "cac_mat_hang": self.ds}
        return kq[0], None

    # --- các công cụ ---
    def danh_sach_di_cho(self):
        info, don = self.info, self.bc["don"]
        chuyen = []
        for ng, (qs, tt) in don.items():
            if not qs:
                continue
            chuyen.append({
                "nguon_hang": ng, "hang_ve_sau_ngay": int(info[info["nguon_hang"] == ng]["L"].iloc[0]),
                "tong_tien": _so(sum(q * info.loc[i, "gia_von"] for i, q in qs.items())),
                "so_ngay_du_ban": tt["so_ngay_du_ban"], "chu_ky_gop_toi_uu_ngay": tt["chu_ky"],
                "bi_gioi_han_boi": tt["rang_buoc"],
                "mat_hang": [{"ten": i, "so_luong": int(q), "quy_cach": int(info.loc[i, "quy_cach"]),
                              "tien": _so(q * info.loc[i, "gia_von"]),
                              "ly_do": "phải đặt (đã chạm điểm đặt hàng)" if i in tt["phai_dat"] else
                                       "mua kèm (sắp chạm, đi chung chuyến)"} for i, q in qs.items()]})
        return {"ngay": str(self.bc["ngay"].date()), "von_toi_da_ngay": _so(self.bc["von"]),
                "can_di_cho": bool(chuyen), "so_chuyen": len(chuyen),
                "tong_tien_can": _so(sum(c["tong_tien"] for c in chuyen)), "cac_chuyen": chuyen,
                "ghi_chu": "Số lượng tính theo dự báo mùa vụ, điểm đặt hàng, nhập gộp theo nguồn và giới hạn vốn / sức chứa."}

    def tinh_trang_mat_hang(self, mat_hang):
        m, loi = self._mh(mat_hang)
        if loi:
            return loi
        r = self.bc["bang"].set_index("mat_hang").loc[m]
        i = self.info.loc[m]
        return {"mat_hang": m, "tinh_trang": r["trang_thai"], "giai_thich": r["giai_thich"],
                "du_bao_ban_hom_nay": _so(r["du_bao_ngay"], 1), "dang_co": _so(r["ton_kho"]),
                "vi_the_tinh_ca_hang_dang_ve": _so(r["vi_the_kha_dung"]), "diem_dat_hang": _so(r["rop"]),
                "ton_an_toan": _so(r["ss"]), "nen_nhap_hom_nay": int(r["nhap"]), "tien_nhap": _so(r["von"]),
                "co_the_het_han_truoc_khi_ban_kip": _so(r["sap_het_han"]), "so_lo": int(r.get("so_lo", 1)),
                "han_in_bao_bi_ngay": int(i["han_dung_ngay"]), "da_cu_khi_nhan_ngay": int(i["tuoi_khi_nhan_ngay"]),
                "han_con_khi_nhan_theo_cho_cat_ngay": int(i["han_con_khi_nhan"]),
                "nguon_hang": i["nguon_hang"], "cat_o": i["khu_bao_quan"], "gia_von": _so(i["gia_von"]),
                "gia_ban": _so(i["gia_ban"]), "quy_cach": int(i["quy_cach"])}

    def du_bao_nhu_cau(self, mat_hang, so_ngay=30):
        m, loi = self._mh(mat_hang)
        if loi:
            return loi
        so_ngay = int(min(max(int(so_ngay or 30), 1), 120))
        v = self.kh["mat_hang"][m]
        k = max(0, int((self.bc["ngay"] - pd.Timestamp(v["ngay"][0])).days))
        d = np.asarray(v["d_hat"][k:k + so_ngay], float)
        ngay = pd.DatetimeIndex(v["ngay"][k:k + so_ngay])
        j = int(np.argmax(d))
        mh = v["mo_hinh"]
        theo_tuan = [{"tu_ngay": str(ngay[a].date()), "tong": _so(d[a:a + 7].sum())} for a in range(0, len(d), 7)]
        return {"mat_hang": m, "tu_ngay": str(ngay[0].date()), "so_ngay": len(d), "tong_du_bao": _so(d.sum()),
                "trung_binh_ngay": _so(d.mean(), 1), "ngay_ban_nhieu_nhat": str(ngay[j].date()),
                "luong_ngay_nhieu_nhat": _so(d[j], 1), "theo_tuan": theo_tuan[:18],
                "muc_nen_ngay_thuong": _so(mh["muc_nen"], 1),
                "he_so_tet_cao_nhat": _so(float(mh["he_so_tet"].max()), 2),
                "he_so_trung_thu_cao_nhat": _so(float(mh["he_so_trung_thu"].max()), 2),
                "sai_so_du_bao_wape": _so(v["meta"].get("wape_du_bao"), 3)}

    def hang_sap_het_han_va_canh_bao(self):
        b, info = self.bc["bang"], self.info
        thieu = [{"mat_hang": r["mat_hang"], "tinh_trang": r["trang_thai"], "dang_co": _so(r["ton_kho"]),
                  "diem_dat_hang": _so(r["rop"])} for _, r in b[b["muc"] == "error"].iterrows()]
        het = [{"mat_hang": r["mat_hang"], "so_luong_co_the_het_han": _so(r["sap_het_han"]),
                "tien_von": _so(r["sap_het_han"] * info.loc[r["mat_hang"], "gia_von"]),
                "lo_sap_het_han_nhat_con_ngay": _so(r.get("han_ngan_nhat"))} for _, r in b[b["sap_het_han"] >= 1].iterrows()]
        return {"het_hang_hoac_duoi_muc_an_toan": thieu, "co_the_het_han": het,
                "tong_tien_co_the_het_han": _so(sum(x["tien_von"] for x in het))}

    def so_sanh_cach_nhap_hang(self):
        kq = self.bc.get("ket_qua_mo_phong")
        if not kq:
            duong = os.path.join(THU_MUC, "output", "ket_qua_tong_hop.json")
            if not os.path.exists(duong):
                return {"loi": "Chưa có kết quả mô phỏng. Chạy: python pipeline.py"}
            with open(duong, encoding="utf-8") as f:
                kq = json.load(f)
        cb = kq.get("so_sanh_cong_bang", {})
        return {"dieu_kien": f"Mọi cách nhập cùng giới hạn vốn {_so(kq.get('von_moi_ngay'))} đ/ngày và sức chứa; "
                              f"{kq.get('so_lan_lap')} lần lặp × {kq.get('so_ngay')} ngày; dữ liệu {kq.get('nguon_du_lieu')}",
                "tong_chi_phi": {k: _so(v.get("tong")) for k, v in cb.items()},
                "so_chuyen": {k: _so(v.get("so_chuyen")) for k, v in cb.items()},
                "muc_giam_cua_nhap_gop_D_phan_tram": {k: _so(v["tb_phan_tram"], 1) for k, v in
                                                      kq.get("muc_giam_tong_chi_phi_cua_D", {}).items()},
                "dong_gop_tung_thanh_phan": [{"buoc": b["buoc"], "thay_doi_chi_phi": _so(b["thay_doi_tb"])}
                                             for b in kq.get("ablation", {}).get("cac_buoc", [])],
                "chu_thich": "A kinh nghiệm, B EOQ cổ điển, C EOQ động từng mặt hàng, C+G thêm gộp chuyến, "
                             "C+G+E thêm tồn khả dụng, D nhập gộp (đang khuyến nghị)."}

    def tinh_eoq(self, nhu_cau_nam, chi_phi_moi_lan_dat, chi_phi_giu_1_don_vi_nam):
        D, S, H = float(nhu_cau_nam), float(chi_phi_moi_lan_dat), float(chi_phi_giu_1_don_vi_nam)
        if D <= 0 or S <= 0 or H <= 0:
            return {"loi": "Nhu cầu, chi phí đặt và chi phí giữ phải lớn hơn 0."}
        q = math.sqrt(2 * D * S / H)
        return {"Q_toi_uu": _so(q, 1), "so_lan_dat_moi_nam": _so(D / q, 1), "chu_ky_ngay": _so(365 * q / D, 1),
                "tong_chi_phi_nam": _so(D / q * S + q / 2 * H)}


def tom_tat_boi_canh(bc):
    kh = bc["kh"]
    von = f"{bc['von']:,.0f}".replace(",", ".")
    return (f"ngày đang xem {bc['ngay']:%d/%m/%Y}; {len(kh['mat_hang'])} mặt hàng ({', '.join(kh['mat_hang'])}); "
            f"{kh['info']['nguon_hang'].nunique()} nguồn hàng; vốn tối đa {von} đ/ngày; "
            f"dữ liệu: {bc.get('nguon_du_lieu', 'không rõ')}.")


# ----------------------------------------------------------------------------
# AI SỬA DỮ LIỆU (có kiểm tra hợp lệ; ứng dụng áp dụng thay đổi và cho hoàn tác)
# ----------------------------------------------------------------------------
# tên trường: (mô tả, kiểu, nhỏ nhất, lớn nhất). Bảng mặt hàng lưu % cho hư hỏng và lãi vốn (giống bảng trong app).
TRUONG_MAT_HANG = {
    "gia_von": ("giá vốn (đ)", float, 1, 1e8), "gia_ban": ("giá bán (đ)", float, 1, 1e8),
    "han_dung_ngay": ("hạn in trên bao bì (ngày)", int, 3, 3650),
    "tuoi_khi_nhan_ngay": ("đã cũ khi nhận (ngày)", int, 0, 3650),
    "ty_le_hu_hong_ngay": ("hư hỏng (%/ngày)", float, 0, 19.9), "q10": ("Q10", float, 1, 10),
    "nhiet_do_chuan_C": ("nhiệt độ áp dụng hạn dùng (°C)", float, -30, 60),
    "khu_bao_quan": ("cất ở khu", str, None, None), "the_tich_lit": ("thể tích (lít/đv)", float, 0.01, 1000),
    "nguon_hang": ("nhập từ nguồn", str, None, None), "quy_cach": ("quy cách (đv/lần mua)", int, 1, 100000),
    "ty_le_giu_hang_nam": ("lãi vốn (%/năm)", float, 0, 200), "muc_phuc_vu": ("mức phục vụ", float, 0.5, 0.999),
    "chi_phi_dong": ("chi phí mỗi dòng hàng (đ)", float, 0, 1e7)}
TRUONG_NGUON = {"chi_phi_chuyen": ("chi phí mỗi chuyến (đ)", float, 0, 1e8),
                "lead_time_ngay": ("giao sau (ngày)", float, 1, 60), "do_lech_lead_time": ("hay lệch (ngày)", float, 0, 30)}
TRUONG_KHU = {"nhiet_do_C": ("nhiệt độ (°C)", float, -30, 60), "suc_chua_lit": ("sức chứa (lít, 0 = không giới hạn)", float, 0, 1e6),
              "chi_phi_bao_quan_lit_ngay": ("chi phí thêm (đ/lít/ngày)", float, 0, 1e5),
              "chi_phi_co_dinh_ngay": ("tiền điện cố định (đ/ngày)", float, 0, 1e7)}
TRUONG_TON = {"ton_kho": ("đang có", float, 0, 1e7), "han_con_lai": ("hạn còn lại (ngày)", float, 0, 3650),
              "hang_dang_ve": ("đã đặt, đang về", float, 0, 1e7)}


def _mo_ta_truong(bang):
    return "; ".join(f"{k} = {v[0]}" for k, v in bang.items())


DINH_NGHIA_SUA = [
    {"type": "function", "function": {
        "name": "sua_mat_hang",
        "description": "SỬA một thông số của một mặt hàng trong danh mục. Các trường: " + _mo_ta_truong(TRUONG_MAT_HANG) +
                       ". Hư hỏng và lãi vốn nhập theo %, ví dụ 0.03 nghĩa là 0,03 %/ngày.",
        "parameters": {"type": "object", "properties": {
            "mat_hang": {"type": "string"}, "truong": {"type": "string", "enum": list(TRUONG_MAT_HANG)},
            "gia_tri": {"type": ["number", "string"]}}, "required": ["mat_hang", "truong", "gia_tri"]}}},
    {"type": "function", "function": {
        "name": "sua_nguon_hang",
        "description": "SỬA thông số một nguồn hàng: " + _mo_ta_truong(TRUONG_NGUON),
        "parameters": {"type": "object", "properties": {
            "nguon_hang": {"type": "string"}, "truong": {"type": "string", "enum": list(TRUONG_NGUON)},
            "gia_tri": {"type": "number"}}, "required": ["nguon_hang", "truong", "gia_tri"]}}},
    {"type": "function", "function": {
        "name": "sua_khu_bao_quan",
        "description": "SỬA thông số một khu bảo quản: " + _mo_ta_truong(TRUONG_KHU),
        "parameters": {"type": "object", "properties": {
            "khu": {"type": "string"}, "truong": {"type": "string", "enum": list(TRUONG_KHU)},
            "gia_tri": {"type": "number"}}, "required": ["khu", "truong", "gia_tri"]}}},
    {"type": "function", "function": {
        "name": "sua_ton_kho",
        "description": "SỬA tồn kho hôm nay của một mặt hàng (lô chính): " + _mo_ta_truong(TRUONG_TON),
        "parameters": {"type": "object", "properties": {
            "mat_hang": {"type": "string"}, "truong": {"type": "string", "enum": list(TRUONG_TON)},
            "gia_tri": {"type": "number"}}, "required": ["mat_hang", "truong", "gia_tri"]}}},
    {"type": "function", "function": {
        "name": "dat_von_moi_ngay",
        "description": "SỬA vốn tối đa dành cho nhập hàng mỗi ngày (đ).",
        "parameters": {"type": "object", "properties": {"so_tien": {"type": "number"}}, "required": ["so_tien"]}}},
    {"type": "function", "function": {
        "name": "xem_thiet_lap",
        "description": "Xem toàn bộ thông số hiện tại (mặt hàng, nguồn hàng, khu bảo quản, tồn kho, vốn) trước khi sửa.",
        "parameters": {"type": "object", "properties": {}}}},
]


class BoSua:
    """Giữ bản sao dữ liệu có thể sửa: dl = {"mh": DataFrame (% như bảng app), "nguon", "khu", "ton": DataFrame, "von": float}.
    Mỗi lần sửa được kiểm tra hợp lệ (khoảng giá trị + nhieu_mat_hang.kiem_tra); thay đổi ghi vào self.thay_doi."""

    def __init__(self, dl):
        self.dl = {k: (v.copy() if isinstance(v, pd.DataFrame) else v) for k, v in dl.items()}
        self.thay_doi = []

    def _hop_le(self):
        from tinh_toan import nhieu_mat_hang as nm
        mh = self.dl["mh"].copy()
        mh["ty_le_hu_hong_ngay"] = mh["ty_le_hu_hong_ngay"] / 100
        mh["ty_le_giu_hang_nam"] = mh["ty_le_giu_hang_nam"] / 100
        return nm.kiem_tra(mh, self.dl["nguon"], self.dl["khu"])

    @staticmethod
    def _ep_kieu(spec, gia_tri):
        mo_ta, kieu, lo, hi = spec
        if kieu is str:
            return str(gia_tri).strip(), None
        try:
            x = float(gia_tri)
        except (TypeError, ValueError):
            return None, f"{mo_ta} phải là số."
        if not math.isfinite(x) or x < lo or x > hi:
            return None, f"{mo_ta} phải trong khoảng {lo:g} đến {hi:g}."
        return (int(round(x)) if kieu is int else x), None

    def _sua(self, bang, cot_khoa, ten, truong, gia_tri, spec_bang, ten_bang):
        df = self.dl[bang]
        if truong not in spec_bang:
            return {"loi": f"Không sửa được trường '{truong}'. Các trường được sửa: {list(spec_bang)}"}
        khop = _tim(list(df[cot_khoa].astype(str)), ten)
        if len(khop) != 1:
            return {"loi": f"Không xác định được {ten_bang} '{ten}'.", "co_the_la": list(df[cot_khoa].astype(str))}
        moi, loi = self._ep_kieu(spec_bang[truong], gia_tri)
        if loi:
            return {"loi": loi}
        if truong == "khu_bao_quan" and moi not in set(self.dl["khu"]["khu_bao_quan"]):
            return {"loi": f"Khu '{moi}' chưa có.", "cac_khu": list(self.dl["khu"]["khu_bao_quan"])}
        if truong == "nguon_hang" and moi not in set(self.dl["nguon"]["nguon_hang"]):
            return {"loi": f"Nguồn '{moi}' chưa có.", "cac_nguon": list(self.dl["nguon"]["nguon_hang"])}
        i = df.index[df[cot_khoa].astype(str) == khop[0]][0]
        if spec_bang[truong][1] is float and df[truong].dtype.kind in "iu":
            df[truong] = df[truong].astype(float)
        cu = df.at[i, truong]
        df.at[i, truong] = moi
        if bang != "ton":
            loi_ = self._hop_le()
            if loi_:
                df.at[i, truong] = cu
                return {"loi": "Giá trị làm thiết lập không hợp lệ: " + "; ".join(loi_)}
        cu = cu.item() if hasattr(cu, "item") else cu
        self.thay_doi.append({"bang": bang, "doi_tuong": khop[0], "truong": truong, "mo_ta": spec_bang[truong][0],
                              "cu": cu, "moi": moi})
        return {"da_sua": True, ten_bang: khop[0], "truong": spec_bang[truong][0], "cu": cu, "moi": moi,
                "ghi_chu": "Đã áp dụng; kế hoạch được tính lại. Gọi lại công cụ đọc nếu cần số liệu mới."}

    def sua_mat_hang(self, mat_hang, truong, gia_tri):
        return self._sua("mh", "mat_hang", mat_hang, truong, gia_tri, TRUONG_MAT_HANG, "mat_hang")

    def sua_nguon_hang(self, nguon_hang, truong, gia_tri):
        return self._sua("nguon", "nguon_hang", nguon_hang, truong, gia_tri, TRUONG_NGUON, "nguon_hang")

    def sua_khu_bao_quan(self, khu, truong, gia_tri):
        return self._sua("khu", "khu_bao_quan", khu, truong, gia_tri, TRUONG_KHU, "khu")

    def sua_ton_kho(self, mat_hang, truong, gia_tri):
        return self._sua("ton", "mat_hang", mat_hang, truong, gia_tri, TRUONG_TON, "mat_hang")

    def dat_von_moi_ngay(self, so_tien):
        moi, loi = self._ep_kieu(("vốn mỗi ngày (đ)", float, 0, 1e10), so_tien)
        if loi:
            return {"loi": loi}
        cu = float(self.dl["von"])
        self.dl["von"] = moi
        self.thay_doi.append({"bang": "von", "doi_tuong": "vốn mỗi ngày", "truong": "von", "mo_ta": "vốn tối đa mỗi ngày (đ)",
                              "cu": cu, "moi": moi})
        return {"da_sua": True, "truong": "vốn tối đa mỗi ngày (đ)", "cu": _so(cu), "moi": _so(moi)}

    def xem_thiet_lap(self):
        def gon(df):
            return json.loads(df.to_json(orient="records", force_ascii=False))
        return {"mat_hang": gon(self.dl["mh"]), "nguon_hang": gon(self.dl["nguon"]), "khu_bao_quan": gon(self.dl["khu"]),
                "ton_kho": gon(self.dl["ton"]), "von_moi_ngay": _so(self.dl["von"]),
                "chu_thich": "ty_le_hu_hong_ngay và ty_le_giu_hang_nam tính theo %."}


# ----------------------------------------------------------------------------
# HỘI THOẠI CÓ GỌI CÔNG CỤ
# ----------------------------------------------------------------------------
def tra_loi(client, mo_hinh, lich_su, cau_hoi, bc, max_tokens=900, bo_sua=None, tinh_lai=None):
    """Một lượt hỏi đáp. lich_su: danh sách tin nhắn {role, content} của các lượt trước (chỉ phần chữ).
    bo_sua: BoSua (nếu cho phép AI sửa dữ liệu); tinh_lai(dl) -> bối cảnh mới sau khi sửa (để công cụ đọc trả số mới).
    Trả về (câu trả lời, danh sách công cụ đã gọi [(tên, tham số, kết quả)]). Thay đổi nằm trong bo_sua.thay_doi."""
    cc = CongCu(bc)
    cong_cu = CongCu.DINH_NGHIA + (DINH_NGHIA_SUA if bo_sua is not None else [])
    msgs = [{"role": "system", "content": HUONG_DAN.format(boi_canh=tom_tat_boi_canh(bc)) +
             ("\nBạn ĐƯỢC PHÉP sửa dữ liệu bằng các công cụ sua_... khi người dùng yêu cầu." if bo_sua is not None else
              "\nBạn KHÔNG có quyền sửa dữ liệu; nếu người dùng muốn sửa, hướng dẫn họ bật 'Cho phép AI sửa dữ liệu'.")}]
    msgs += lich_su[-12:] + [{"role": "user", "content": cau_hoi}]
    da_goi = []
    for _ in range(SO_VONG_CONG_CU):
        r = client.chat.completions.create(model=mo_hinh, messages=msgs, tools=cong_cu,
                                           max_completion_tokens=max_tokens)
        m = r.choices[0].message
        if not getattr(m, "tool_calls", None):
            return (m.content or "").strip(), da_goi
        msgs.append({"role": "assistant", "content": m.content or "",
                     "tool_calls": [{"id": tc.id, "type": "function",
                                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                                    for tc in m.tool_calls]})
        for tc in m.tool_calls:
            try:
                ts = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                ts = {}
            ten = tc.function.name
            if bo_sua is not None and ten in {d["function"]["name"] for d in DINH_NGHIA_SUA}:
                try:
                    kq = getattr(bo_sua, ten)(**ts)
                except TypeError as e:
                    kq = {"loi": f"Thiếu hoặc sai tham số: {e}"}
                if kq.get("da_sua") and tinh_lai is not None:
                    try:
                        cc = CongCu(tinh_lai(bo_sua.dl))                  # công cụ đọc dùng số liệu sau khi sửa
                    except Exception as e:                                 # noqa: BLE001
                        kq["canh_bao"] = f"Chưa tính lại được kế hoạch: {e}"
            else:
                kq = cc.goi(ten, ts)
            da_goi.append((ten, ts, kq))
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(kq, ensure_ascii=False, default=str)})
    return "Mình cần quá nhiều bước tính để trả lời câu này. Bạn hỏi cụ thể hơn được không?", da_goi


def giai_thich_hom_nay(client, mo_hinh, bc, max_tokens=700):
    """Một đoạn giải thích ngắn danh sách đi chợ hôm nay (dùng sẵn kết quả công cụ, 1 lần gọi API)."""
    cc = CongCu(bc)
    du_lieu = {"danh_sach_di_cho": cc.danh_sach_di_cho(), "canh_bao": cc.hang_sap_het_han_va_canh_bao()}
    msgs = [{"role": "system", "content": HUONG_DAN.format(boi_canh=tom_tat_boi_canh(bc))},
            {"role": "user", "content": "Dựa CHỈ vào dữ liệu sau (do hệ thống tính), viết cho tôi một bản tóm tắt việc cần làm hôm nay, "
                                        "tối đa 8 gạch đầu dòng: đi những đâu, mua gì, bao nhiêu tiền, vì sao, và cần chú ý gì "
                                        "(hàng sắp hết, hàng có thể hết hạn).\n" + json.dumps(du_lieu, ensure_ascii=False, default=str)}]
    r = client.chat.completions.create(model=mo_hinh, messages=msgs, max_completion_tokens=max_tokens)
    return (r.choices[0].message.content or "").strip()


def phan_tich(client, mo_hinh, chu_de, du_lieu, bc=None, max_tokens=700):
    """AI phân tích một biểu đồ / bảng kết quả. du_lieu: dict số liệu do hệ thống tính (đưa nguyên cho AI)."""
    boi_canh = tom_tat_boi_canh(bc) if bc else "không có"
    msgs = [{"role": "system", "content": HUONG_DAN.format(boi_canh=boi_canh)},
            {"role": "user", "content": f"Hãy phân tích **{chu_de}** cho tiểu thương, dựa CHỈ vào số liệu sau (do hệ thống tính). "
                                        "Viết tối đa 6 gạch đầu dòng: (1) điều đáng chú ý nhất, (2) vì sao / ý nghĩa, "
                                        "(3) việc nên làm cụ thể. Nếu số liệu cho thấy điểm yếu hoặc rủi ro thì nói thẳng.\n"
                                        + json.dumps(du_lieu, ensure_ascii=False, default=str)}]
    r = client.chat.completions.create(model=mo_hinh, messages=msgs, max_completion_tokens=max_tokens)
    return (r.choices[0].message.content or "").strip()
