# -*- coding: utf-8 -*-
"""Giao diện chung kiểu phần mềm quản lý (ERP): thanh nhóm xanh đậm, menu theo nhóm, khung vuông gọn, chữ và bảng lớn.
Gồm CSS và các khối HTML nhỏ dùng ở nhiều trang."""
import streamlit as st

from giao_dien.cau_hinh import NHOM_CUA

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');
html, body, p, li, label, input, textarea, button, td, th, h1, h2, h3, h4, h5, h6, .stMarkdown {
  font-family: 'Be Vietnam Pro', 'Segoe UI', sans-serif; }
[data-testid="stIconMaterial"], .material-symbols-rounded { font-family: 'Material Symbols Rounded' !important; }
/* Màu dịu mắt: nền xám ấm rất nhạt thay cho trắng tinh, chữ xám đậm thay cho đen tuyền, tương phản vẫn ≥ 10:1 */
:root { --xanh: #1d5c9c; --xanh-dam: #154a80; --xanh-nhat: #e6eef7; --chu: #27313d; --phu: #4f5a68; --vien: #d3d9e1;
  --nen: #f6f7f9; --the: #fbfbfc; --do: #c5372c; --vang: #c98a12; --la: #1f7a3f; }
.stApp { background: var(--nen); color: var(--chu); }
.block-container { padding: 1.1rem 2.2rem 3rem; max-width: 100%; }
.stMarkdown p, .stMarkdown li { font-size: 1.08rem; line-height: 1.65; color: var(--chu); }
.stMarkdown strong { color: #1b2531; }
label[data-testid="stWidgetLabel"] p { font-size: 1.02rem; font-weight: 600; color: var(--chu); }

/* ---- thanh bên: thương hiệu + danh sách trang theo nhóm ---- */
section[data-testid="stSidebar"] { background: var(--the); border-right: 1px solid var(--vien); }
section[data-testid="stSidebarUserContent"] { padding-top: .6rem; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 2px; }
.thuong-hieu { display: flex; align-items: baseline; gap: 8px; padding: 4px 4px 14px; border-bottom: 1px solid var(--vien);
  margin-bottom: 8px; }
.thuong-hieu .t1 { font-size: 1.9rem; font-weight: 800; letter-spacing: -.02em; color: var(--xanh); }
.thuong-hieu .t2 { font-size: 1rem; font-weight: 600; color: var(--phu); }
.nhom-menu { font-size: .95rem; font-weight: 700; color: var(--chu); padding: 12px 10px 4px; margin-top: 4px;
  border-top: 1px solid #edf0f4; }
section[data-testid="stSidebar"] div:has(> .nhom-menu), section[data-testid="stSidebar"] div:has(> .thuong-hieu) {
  margin-bottom: 0 !important; }
section[data-testid="stSidebar"] .stButton button { justify-content: flex-start; text-align: left; border: none;
  background: transparent; border-radius: 6px; padding: 7px 12px 7px 24px; min-height: 0; box-shadow: none; }
section[data-testid="stSidebar"] .stButton button > div { justify-content: flex-start; }
section[data-testid="stSidebar"] .stButton button p { font-size: 1.02rem; font-weight: 500; color: #2f3b4c; }
section[data-testid="stSidebar"] .stButton button p::before { content: "·"; margin-right: 10px; color: #9aa5b4; font-weight: 700; }
section[data-testid="stSidebar"] .stButton button:hover { background: var(--xanh-nhat); }
section[data-testid="stSidebar"] .stButton button:focus-visible { outline: 2px solid var(--xanh); outline-offset: 1px; }

/* ---- thanh nhóm ngang ở đầu trang ---- */
.st-key-thanh_tren { background: var(--xanh); border-radius: 4px; padding: 6px 10px; margin-bottom: 14px; }
.st-key-thanh_tren [data-testid="stHorizontalBlock"] { gap: 6px; }
.st-key-thanh_tren [data-testid="stColumn"] { min-width: 0; }
.st-key-thanh_tren .stButton button { background: transparent !important; border: 1px solid transparent !important;
  border-radius: 3px; min-height: 38px; padding: 4px 8px; box-shadow: none; }
.st-key-thanh_tren .stButton button p { color: #ffffff; font-size: 1.05rem; font-weight: 600; white-space: nowrap; }
.st-key-thanh_tren .stButton button:hover { background: var(--xanh-dam) !important; border-color: rgba(255, 255, 255, .25) !important; }
.st-key-thanh_tren .thong-tin { color: rgba(255, 255, 255, .85); font-size: .9rem; text-align: right; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.st-key-thanh_tren div:has(> .thong-tin) { margin-bottom: 0 !important; }
@media (max-width: 1100px) { .st-key-thanh_tren [data-testid="stColumn"]:last-child { display: none; }
  .st-key-thanh_tren .stButton button p { font-size: .95rem; } }

/* ---- tiêu đề trang ---- */
.tieu-de { background: var(--the); border: 1px solid var(--vien); border-left: 4px solid var(--xanh); border-radius: 4px;
  padding: 14px 20px; margin: 0 0 16px; }
.tieu-de .duong-dan { font-size: .85rem; color: var(--phu); margin-bottom: 2px; }
.tieu-de .t1 { font-size: 1.7rem; font-weight: 700; line-height: 1.25; color: var(--chu); }
.tieu-de .t2 { font-size: 1.05rem; color: var(--phu); margin-top: 4px; }

/* ---- thẻ tóm tắt (KPI) ---- */
.kpi-hang { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 4px 0 16px; }
.kpi { background: var(--the); border: 1px solid var(--vien); border-radius: 4px; padding: 14px 18px;
  border-top: 3px solid var(--mau, var(--xanh)); }
.kpi .nhan { font-size: 1rem; color: var(--phu); font-weight: 500; }
.kpi .so { font-size: 2rem; font-weight: 700; color: var(--chu); margin-top: 4px; line-height: 1.15;
  font-variant-numeric: tabular-nums; }
.kpi .phu { font-size: .95rem; color: var(--phu); margin-top: 4px; }
.the-trang { background: #e9f6ee; border: 1px solid #b9e0c6; color: #17663a; border-radius: 4px; padding: 14px 18px;
  font-weight: 500; margin-bottom: 12px; }

/* ---- khung, bảng, nút ---- */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) { border-color: var(--vien); }
[data-testid="stAlert"] p { font-size: 1.04rem; }
.stTextInput input, .stNumberInput input, .stDateInput input, [data-baseweb="select"] { font-size: 1.04rem; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 4px; }
[data-testid="stMetric"] { background: var(--the); border: 1px solid var(--vien); border-radius: 4px; padding: 14px 16px; }
[data-testid="stMetricLabel"] p { font-size: .95rem; color: var(--phu); }
[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: var(--chu); }
[data-testid="stExpander"] details { border-radius: 4px; background: var(--the); border-color: var(--vien); }
[data-testid="stExpander"] summary p { font-size: 1.02rem; font-weight: 600; }
[data-testid="stDataFrame"] { border-radius: 2px; }
h4 { font-size: 1.4rem; color: var(--chu); }
h5 { font-size: 1.25rem; color: var(--chu); margin-top: .2rem; padding-bottom: 6px; border-bottom: 1px solid #edf0f4; }
.stButton button, .stDownloadButton button { border-radius: 4px; font-weight: 600; border-color: var(--vien); }
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] { background: var(--xanh); border-color: var(--xanh); }
.stButton button[kind="primary"]:hover { background: var(--xanh-dam); border-color: var(--xanh-dam); }
.stTabs [data-baseweb="tab-list"] { gap: 2px; border-bottom: 1px solid var(--vien); }
.stTabs [data-baseweb="tab"] { padding: 8px 18px; background: #eef2f7; border: 1px solid var(--vien); border-bottom: none;
  border-radius: 4px 4px 0 0; }
.stTabs [data-baseweb="tab"] p { font-size: 1.02rem; font-weight: 600; }
.stTabs [aria-selected="true"] { background: var(--xanh); }
.stTabs [aria-selected="true"] p { color: #ffffff; }
[data-testid="stChatMessage"] { background: var(--the); border: 1px solid var(--vien); border-radius: 4px; }

/* chú giải biểu đồ tồn kho (bieu_do.ton_kho_rop) và chữ ghi chú dưới biểu đồ */
.chu-giai { display: flex; flex-wrap: wrap; gap: 8px 22px; font-size: 1rem; color: var(--chu); margin: 2px 0 6px; }
.chu-giai span { display: inline-flex; align-items: center; gap: 8px; }
.chu-giai i { display: inline-block; width: 26px; height: 4px; border-radius: 2px; }
.chu-giai i.dut { height: 0; border-top: 3px dashed; background: none; }
[data-testid="stCaptionContainer"] { opacity: 1 !important; }               /* Streamlit làm mờ 60%: khó đọc */
[data-testid="stCaptionContainer"] p { font-size: 1rem; color: var(--phu); line-height: 1.55; }
.so-rop { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin: 2px 0 10px; }
.so-rop > div { border: 1px solid var(--vien); border-radius: 4px; padding: 10px 14px; }
.so-rop .n { font-size: .9rem; color: var(--phu); }
.so-rop .s { font-size: 1.55rem; font-weight: 700; color: var(--chu); font-variant-numeric: tabular-nums; }
.so-rop > .rop { border-color: #c5372c; border-width: 2px; }
.so-rop .rop .s { color: #c5372c; }

/* ô AI phân tích bên cạnh biểu đồ */
.ai-ben { font-size: 1.08rem; font-weight: 700; color: var(--xanh); margin-bottom: 2px; }
[class*="st-key-ai_"] { background: var(--xanh-nhat); }
[class*="st-key-ai_"] .stMarkdown p, [class*="st-key-ai_"] .stMarkdown li { font-size: 1rem; line-height: 1.55; }
@media (max-width: 1100px) {                                  /* màn hình hẹp: ô AI xuống dưới biểu đồ */
  [class*="st-key-khung_"] [data-testid="stHorizontalBlock"] { flex-direction: column; }
  [class*="st-key-khung_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { width: 100% !important;
    flex: 1 1 100% !important; } }

/* ô chọn nguồn dữ liệu (trang Nhập dữ liệu): 3 thẻ ngang */
.st-key-w_dl_nguon div[role="radiogroup"] { gap: 10px; flex-wrap: wrap; }
.st-key-w_dl_nguon label[data-baseweb="radio"] { flex: 1 1 220px; margin: 0; padding: 12px 14px; border-radius: 4px;
  border: 1px solid var(--vien); background: var(--the); }
.st-key-w_dl_nguon label[data-baseweb="radio"]:has(input:checked) { border-color: var(--xanh); background: var(--xanh-nhat);
  box-shadow: inset 0 0 0 1px var(--xanh); }
.st-key-w_dl_nguon label[data-baseweb="radio"] p { font-weight: 600; }
</style>
"""

# Màu thẻ KPI theo ý nghĩa (dùng chung để các trang giống nhau)
MAU = {"xanh": "#1d5c9c", "do": "#c5372c", "vang": "#c98a12", "la": "#1f7a3f", "xam": "#9aa5b4"}
CAO_BIEU_DO = 400                                              # chiều cao biểu đồ chính (px)
DONG_BANG = 40                                                # chiều cao mỗi dòng bảng (px), chữ bảng theo baseFontSize


def cao_bang(so_dong, toi_da=12):
    """Chiều cao vừa khít cho bảng chỉ đọc (tiêu đề + tối đa toi_da dòng, nhiều hơn thì cuộn): không cắt dòng, không thừa chỗ."""
    return (min(int(so_dong), toi_da) + 1) * DONG_BANG + 18       # +18: chỗ cho thanh cuộn ngang khi bảng rộng


def ap_dung_css():
    st.markdown(CSS, unsafe_allow_html=True)


def kpi_hang(the):
    """Hàng thẻ tóm tắt: [(nhãn, số, dòng phụ, màu viền trên)]."""
    html = "".join(f'<div class="kpi" style="--mau:{m}"><div class="nhan">{n}</div><div class="so">{s}</div>'
                   f'<div class="phu">{p}</div></div>' for n, s, p, m in the)
    st.markdown(f'<div class="kpi-hang">{html}</div>', unsafe_allow_html=True)


def tieu_de(bieu_tuong, ten, mo_ta):
    """Thanh tiêu đề trang: đường dẫn (nhóm › trang), tên, mô tả. bieu_tuong giữ cho tương thích, không hiển thị."""
    trang = st.session_state.get("trang", "")
    duong_dan = f"{NHOM_CUA[trang]} › {trang}" if trang in NHOM_CUA else ""
    st.markdown(f'<div class="tieu-de"><div class="duong-dan">{duong_dan}</div><div class="t1">{ten}</div>'
                f'<div class="t2">{mo_ta}</div></div>', unsafe_allow_html=True)
