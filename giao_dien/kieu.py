# -*- coding: utf-8 -*-
"""Giao diện chung: CSS (màu, font, thẻ, menu) và các khối HTML nhỏ dùng ở nhiều trang."""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');
html, body, p, li, label, input, textarea, button, td, th, h1, h2, h3, h4, h5, h6, .stMarkdown {
  font-family: 'Be Vietnam Pro', 'Segoe UI', sans-serif; }
[data-testid="stIconMaterial"], .material-symbols-rounded { font-family: 'Material Symbols Rounded' !important; }
:root { --ac1: #ff8a3d; --ac2: #f2542d; --chu: #2b2a33; --phu: #6b6873; --vien: #f0e2d6; --the: #ffffff;
  --nen-nhat: #fff6ef; --bong: 0 4px 18px rgba(242, 84, 45, .07); }
.stApp { background: linear-gradient(180deg, #fffaf5 0%, #fff6ee 100%); }
.block-container { padding-top: 1.8rem; max-width: 1280px; }

/* ---- thanh bên ---- */
section[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--vien); }
section[data-testid="stSidebar"] .block-container, section[data-testid="stSidebarUserContent"] { padding-top: 1rem; }
.thuong-hieu { background: linear-gradient(135deg, var(--ac1), var(--ac2)); border-radius: 18px; padding: 16px 18px;
  color: #fff; box-shadow: 0 10px 24px rgba(242, 84, 45, .25); margin-bottom: 14px; }
.thuong-hieu .t1 { font-size: 1.35rem; font-weight: 700; line-height: 1.25; color: #fff; }
.thuong-hieu .t2 { font-size: .82rem; opacity: .95; margin-top: 4px; color: #fff; }
.nhan-muc { font-size: .72rem; letter-spacing: .12em; font-weight: 700; color: var(--phu); margin: 6px 4px 6px; }

/* menu điều hướng: radio -> nút dọc */
.st-key-menu div[role="radiogroup"] { gap: 6px; }
.st-key-menu label[data-baseweb="radio"] { width: 100%; margin: 0; padding: 11px 14px; border-radius: 13px;
  border: 1px solid transparent; transition: all .15s ease; cursor: pointer; }
.st-key-menu label[data-baseweb="radio"] > div:first-child { display: none; }
.st-key-menu label[data-baseweb="radio"] p { font-size: 1.1rem; font-weight: 500; color: var(--chu); }
.st-key-menu label[data-baseweb="radio"]:hover { background: var(--nen-nhat); border-color: var(--vien); transform: translateX(2px); }
.st-key-menu label[data-baseweb="radio"]:has(input:checked) { background: linear-gradient(135deg, var(--ac1), var(--ac2));
  box-shadow: 0 6px 16px rgba(242, 84, 45, .28); }
.st-key-menu label[data-baseweb="radio"]:has(input:checked) p { color: #fff; font-weight: 700; }

/* ô cài đặt nhỏ */
.chip-hang { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 2px 8px; }
.chip { font-size: .78rem; padding: 4px 10px; border-radius: 999px; background: var(--nen-nhat); border: 1px solid var(--vien);
  color: var(--chu); }
section[data-testid="stSidebar"] [data-testid="stExpander"] details { border-radius: 14px; border: 1px solid var(--vien);
  background: #fffdfb; }
section[data-testid="stSidebar"] [data-testid="stExpander"] summary p { font-weight: 600; }

/* tiêu đề trang */
.tieu-de { display: flex; align-items: center; gap: 16px; margin: 0 0 18px; padding: 18px 22px; border-radius: 20px;
  background: linear-gradient(120deg, #ffffff 0%, #fff1e6 60%, #ffe5d6 100%); border: 1px solid var(--vien);
  box-shadow: var(--bong); }
.tieu-de .bt { font-size: 2.2rem; width: 58px; height: 58px; display: flex; align-items: center; justify-content: center;
  background: #fff; border-radius: 16px; box-shadow: 0 4px 12px rgba(242, 84, 45, .12); }
.tieu-de .t1 { font-size: 1.55rem; font-weight: 700; line-height: 1.2; color: var(--chu); }
.tieu-de .t2 { font-size: .93rem; color: var(--phu); margin-top: 3px; }

/* thẻ tóm tắt (KPI) */
.kpi-hang { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin: 4px 0 16px; }
.kpi { background: var(--the); border: 1px solid var(--vien); border-radius: 18px; padding: 16px 18px; box-shadow: var(--bong);
  border-top: 4px solid var(--mau, var(--ac2)); }
.kpi .nhan { font-size: .85rem; color: var(--phu); font-weight: 500; }
.kpi .so { font-size: 1.7rem; font-weight: 700; color: var(--chu); margin-top: 4px; line-height: 1.15; }
.kpi .phu { font-size: .78rem; color: var(--phu); margin-top: 4px; }
.the-trang { background: #ecfdf3; border: 1px solid #b7ebcb; color: #11643a; border-radius: 16px; padding: 14px 18px;
  font-weight: 500; margin-bottom: 12px; }

/* thẻ số liệu, khung */
[data-testid="stMetric"] { background: var(--the); border: 1px solid var(--vien); border-radius: 16px; padding: 14px 16px;
  box-shadow: var(--bong); }
[data-testid="stMetricLabel"] p { font-size: .88rem; color: var(--phu); }
[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; color: var(--chu); }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 18px; }
[data-testid="stExpander"] details { border-radius: 16px; background: var(--the); border-color: var(--vien); box-shadow: var(--bong); }
[data-testid="stDataFrame"] { border-radius: 12px; }
.stButton button, .stDownloadButton button { border-radius: 12px; font-weight: 600; border-color: var(--vien); }
.stButton button[kind="primary"] { background: linear-gradient(135deg, var(--ac1), var(--ac2)); border: none; }
h4, h5 { color: var(--chu); }
h5 { margin-top: .3rem; }
[data-testid="stChatMessage"] { background: var(--the); border: 1px solid var(--vien); border-radius: 16px; box-shadow: var(--bong); }
</style>
"""


def ap_dung_css():
    st.markdown(CSS, unsafe_allow_html=True)


def kpi_hang(the):
    """Hàng thẻ tóm tắt: [(nhãn, số, dòng phụ, màu viền trên)]."""
    html = "".join(f'<div class="kpi" style="--mau:{m}"><div class="nhan">{n}</div><div class="so">{s}</div>'
                   f'<div class="phu">{p}</div></div>' for n, s, p, m in the)
    st.markdown(f'<div class="kpi-hang">{html}</div>', unsafe_allow_html=True)


def tieu_de(bieu_tuong, ten, mo_ta):
    st.markdown(f'<div class="tieu-de"><div class="bt">{bieu_tuong}</div><div><div class="t1">{ten}</div>'
                f'<div class="t2">{mo_ta}</div></div></div>', unsafe_allow_html=True)
