# -*- coding: utf-8 -*-
"""
LUỒNG END-TO-END CHO CẢ CỬA HÀNG (nhiều mặt hàng thực phẩm, không dùng AI / học máy).

  Bước 1. Dữ liệu        : doanh số theo ngày (file của bạn hoặc dữ liệu mô phỏng 2023–2024)
                           + danh mục mặt hàng, nguồn hàng, khu bảo quản (file của bạn hoặc mặc định)
  Bước 2. Dự báo         : mức nền × hệ số thứ × hệ số Tết × hệ số Trung thu
  Bước 3. Chính sách     : hạn dùng thực theo nhiệt độ (Q10), hư hỏng/ngày, SS, ROP, EOQ có hư hỏng
  Bước 4. Kế hoạch       : bảng SS/ROP/Q theo ngày cho từng mặt hàng
  Bước 5. Đặt->giao->bán : mô phỏng cả cửa hàng, N lần lặp, 4 chính sách, cùng nhu cầu và lead time
  Bước 6. Chi phí        : chuyến hàng, dòng hàng, lãi vốn, bảo quản, hư hỏng, hết hạn, lợi nhuận mất,
                           số ngày vượt vốn / vượt sức chứa

Chạy:
  python pipeline.py
  python pipeline.py --du-lieu ban_hang.csv --mat-hang mat_hang.csv --nguon nguon.csv --khu khu.csv --von 10000000
"""
import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tinh_toan import loi
from tinh_toan import nhieu_mat_hang as nm

if hasattr(sys.stdout, "reconfigure"):          # console Windows (cp1252) không in được tiếng Việt
    sys.stdout.reconfigure(encoding="utf-8")
plt.rcParams["font.family"] = "DejaVu Sans"
THU_MUC = os.path.dirname(os.path.abspath(__file__))
MAU = {"A": "#9aa5b1", "B": "#e0a030", "C": "#7aa6e0", "D": "#1f6feb"}

# ----------------------------------------------------------------------------
# BỘ SINH DỮ LIỆU MÔ PHỎNG (chỉ dùng khi không có dữ liệu thật)
# ----------------------------------------------------------------------------
HE_SO_THU = np.array([0.85, 0.90, 0.95, 1.00, 1.10, 1.25, 1.35])     # T2..CN
MAT_HANG_MO_PHONG = {                                               # (bán/ngày cơ sở, biên độ Tết, biên độ Trung thu)
    "Kẹo dừa Bến Tre (gói 200g)": (18, 1.5, 0.0),
    "Bánh pía (hộp)": (10, 0.6, 0.3),
    "Mứt Tết (hộp)": (6, 5.0, 0.0),
    "Bánh trung thu (cái)": (1.5, 0.0, 12.0),
    "Bánh quy / bánh gạo (gói)": (25, 1.0, 0.0),
    "Kẹo lạc / kẹo mè xửng": (14, 1.2, 0.0),
}


def nhu_cau_ky_vong(mat_hang, ngay):
    co_so, a_tet, a_tt = MAT_HANG_MO_PHONG[mat_hang]
    dt, dtt = loi._ngay_gan_nhat(ngay, loi.TET), loi._ngay_gan_nhat(ngay, loi.TRUNG_THU)
    m = np.ones(len(ngay))
    m += a_tet * np.exp(-0.5 * ((dt + 5) / 8.0) ** 2) * (dt <= 7)
    m *= np.where((dt >= 8) & (dt <= 25) & (a_tet > 0), 0.75, 1.0)          # trũng sau Tết
    m += a_tt * np.exp(-0.5 * ((dtt + 8) / 5.0) ** 2) * (dtt <= 2)
    return co_so * HE_SO_THU[ngay.dayofweek.values] * m


def sinh_nhu_cau(mat_hang, ngay, rng, s=0.15):
    mu = nhu_cau_ky_vong(mat_hang, ngay)
    return rng.poisson(mu * rng.lognormal(-0.5 * s * s, s, size=len(mu))).astype(float)


def du_lieu_mo_phong(out):
    ngay = pd.date_range("2023-01-01", "2024-12-31")
    rng = np.random.default_rng(42)
    ban_hang = pd.DataFrame({m: sinh_nhu_cau(m, ngay, rng) for m in MAT_HANG_MO_PHONG}, index=ngay)
    ban_hang.index.name = "ngay"
    ban_hang.reset_index().to_csv(os.path.join(out, "du_lieu_lich_su_mo_phong_2023_2024.csv"),
                                  index=False, encoding="utf-8-sig")
    return ban_hang


def _doc_bang(duong_dan, mac_dinh, cot):
    if not duong_dan:
        return mac_dinh
    d = loi.doc_file(duong_dan)
    chuan = {c.lower(): c for c in cot}                          # khớp tên cột không phân biệt hoa/thường
    d.columns = [chuan.get(loi._bo_dau(c), loi._bo_dau(c)) for c in d.columns]
    if "tuoi_khi_nhan_ngay" in cot and "tuoi_khi_nhan_ngay" not in d.columns:   # file cũ (trước P4)
        print(f"  ! {os.path.basename(duong_dan)} chưa có cột tuoi_khi_nhan_ngay: coi như hàng nhận về còn nguyên hạn (0 ngày)")
        d["tuoi_khi_nhan_ngay"] = 0
    if "chi_phi_co_dinh_ngay" in cot and "chi_phi_co_dinh_ngay" not in d.columns:   # file khu cũ (trước P5)
        d["chi_phi_co_dinh_ngay"] = 0.0
    thieu = [c for c in cot if c not in d.columns]
    if thieu:
        sys.exit(f"File {duong_dan} thiếu cột {thieu}. Cần các cột: {cot}")
    return d[cot]


# ----------------------------------------------------------------------------
# MÔ PHỎNG LẶP VÀ TỔNG HỢP
# ----------------------------------------------------------------------------
# (chính sách, có ràng buộc vốn & sức chứa hay không)
CONG_BANG = [("A", True), ("B", True), ("C", True), ("C+G", True), ("C+G+E", True), ("D", True)]  # công bằng + ablation
THAM_KHAO = [("A", False), ("B", False), ("C", False), ("C+G", False), ("C+G+E", False)]  # không ràng buộc (tham khảo)


def mo_phong_lap(kh, nguon_dl, so_lan, von, cau_hinh=CONG_BANG + THAM_KHAO, bo_ngay_dau=30, tao_ke_hoach=None,
                 he_so_mat_khach=1.0, ty_le_lifo=0.0):
    """Lặp mô phỏng. tao_ke_hoach(r): nếu có, dựng lại kế hoạch (dự báo) cho lần lặp r từ một lịch sử mới (P2, A5).
    Dữ liệu người dùng: nhu cầu tương lai có cả sai số dự báo (nhị thức âm, phương sai a·d + b·d²) (P2, A4)."""
    rows, mau, theo_mh, mpv = [], {}, [], []
    for r in range(so_lan):
        kh_r = tao_ke_hoach(r) if tao_ke_hoach else kh
        T, ds = kh_r["so_ngay"], list(kh_r["mat_hang"])
        rng = np.random.default_rng(1000 + r)
        if nguon_dl == "mo_phong":
            nc = {m: sinh_nhu_cau(m, kh_r["ngay"], rng) for m in ds}
        else:
            nc = {m: nm.sinh_nhu_cau(kh_r["mat_hang"][m]["d_hat"][:T], kh_r["mat_hang"][m]["var"][:T], rng) for m in ds}
        lts = nm.sinh_lead_times(kh_r["info"], T, rng)
        for p, rb in cau_hinh:
            sim, sk, ch = nm.mo_phong_cua_hang(kh_r, p, nc, lts, von_moi_ngay=von, seed=2000 + r, rang_buoc=rb,
                                              ty_le_lifo=ty_le_lifo)
            c = nm.chi_phi_cua_hang(kh_r, sim, sk, ch, von, bo_ngay_dau=bo_ngay_dau, he_so_mat_khach=he_so_mat_khach)
            c.update(lan=r, chinh_sach=p, rang_buoc=rb)
            rows.append(c)
            if rb and p in ("C", "D"):
                s_w = sim[sim["ngay"] >= bo_ngay_dau]
                theo_mh.append(nm.chi_phi_theo_mat_hang(kh_r, s_w).assign(chinh_sach=p, lan=r))
                mpv.append(nm.muc_phuc_vu_dat_duoc(s_w).assign(chinh_sach=p, lan=r))
            if r == 0:
                mau[(p, rb)] = (sim, sk)
    return pd.DataFrame(rows), mau, pd.concat(theo_mh), pd.concat(mpv)


def do_nhay_muc_phuc_vu(tao_kh, nguon_dl, so_lan, von, bo_ngay_dau, muc=(0.80, 0.90, 0.95, 0.98), he_so=(1, 2, 3)):
    """P2: chi phí và mức phục vụ đạt được khi đổi mức phục vụ mục tiêu và hệ số mất khách."""
    rows = []
    for z in muc:
        kh = tao_kh(z)
        for r in range(so_lan):
            T, ds = kh["so_ngay"], list(kh["mat_hang"])
            rng = np.random.default_rng(1000 + r)
            nc = ({m: sinh_nhu_cau(m, kh["ngay"], rng) for m in ds} if nguon_dl == "mo_phong" else
                  {m: nm.sinh_nhu_cau(kh["mat_hang"][m]["d_hat"][:T], kh["mat_hang"][m]["var"][:T], rng) for m in ds})
            lts = nm.sinh_lead_times(kh["info"], T, rng)
            for p in ("C", "D"):
                sim, sk, ch = nm.mo_phong_cua_hang(kh, p, nc, lts, von_moi_ngay=von, seed=2000 + r, rang_buoc=True)
                for k in he_so:
                    c = nm.chi_phi_cua_hang(kh, sim, sk, ch, von, bo_ngay_dau=bo_ngay_dau, he_so_mat_khach=k)
                    rows.append({"muc_phuc_vu": z, "he_so_mat_khach": k, "chinh_sach": p, "lan": r, "tong": c["tong"],
                                 "ty_le_dap_ung": c["ty_le_dap_ung"], "csl": c["csl"], "ngay_het_hang": c["ngay_het_hang"]})
    return pd.DataFrame(rows).groupby(["chinh_sach", "he_so_mat_khach", "muc_phuc_vu"]).mean(numeric_only=True).drop(columns="lan")


def tong_hop(df, so_lan):
    """Bảng trung bình (có / không ràng buộc), mức giảm của D, chuỗi ablation C → C+G → D (cùng ràng buộc)."""
    cb = df[df.rang_buoc].groupby("chinh_sach").mean(numeric_only=True).drop(columns="lan").loc[[p for p, _ in CONG_BANG]]
    tk = df[~df.rang_buoc].groupby("chinh_sach").mean(numeric_only=True).drop(columns="lan").loc[[p for p, _ in THAM_KHAO]]
    tong = df[df.rang_buoc].pivot(index="lan", columns="chinh_sach", values="tong")
    giam = {}
    for goc in "ABC":
        red = (1 - tong["D"] / tong[goc]) * 100
        giam[goc] = {"tb_phan_tram": float(red.mean()), "do_lech": float(red.std()),
                     "so_lan_D_thang": int((tong["D"] < tong[goc]).sum())}
    buoc = [("C", "C+G", "Gộp chuyến theo nguồn hàng"), ("C+G", "C+G+E", "Tồn khả dụng (bỏ hàng sắp hết hạn)")]
    ablation = {"diem_dau": float(tong["C"].mean()), "diem_cuoi": float(tong["C+G+E"].mean()), "D": float(tong["D"].mean()),
                "D_dung_ton_kha_dung": bool(nm.DUNG_TON_KHA_DUNG),
                "cac_buoc": [{"buoc": ten, "tu": a, "den": b, "thay_doi_tb": float((tong[b] - tong[a]).mean()),
                              "do_lech": float((tong[b] - tong[a]).std()),
                              "so_lan_giam": int((tong[b] < tong[a]).sum())} for a, b, ten in buoc]}
    return cb, tk, giam, ablation


def ve_bieu_do(kh, mau, cb, ablation, out):
    ngay = pd.DatetimeIndex(kh["ngay"])
    ds_cs = list(cb.index)
    fig, ax = plt.subplots(figsize=(8.5, 4))
    phan = [("chi_phi_chuyen", "Chuyến hàng", "#4c78a8"), ("chi_phi_dong_hang", "Dòng hàng", "#9ecae9"),
            ("lai_von", "Lãi vốn", "#72b7b2"), ("bao_quan", "Bảo quản", "#54a24b"), ("hu_hong", "Hư hỏng", "#b279a2"),
            ("het_han", "Hết hạn", "#e45756"), ("loi_nhuan_mat", "Lợi nhuận mất", "#f2a541")]
    day = np.zeros(len(ds_cs))
    for key, nhan, mau_ in phan:
        gt = cb.loc[ds_cs, key].values / 1e6
        ax.bar(ds_cs, gt, bottom=day, label=nhan, color=mau_, width=0.55)
        day += gt
    for i in range(len(ds_cs)):
        ax.text(i, day[i] * 1.02, f"{day[i]:.1f} tr", ha="center", fontsize=9, fontweight="bold")
    ax.set_ylabel("Triệu đồng"); ax.set_ylim(0, day.max() * 1.25)
    ax.set_title("Tổng chi phí cả cửa hàng – mọi chính sách cùng giới hạn vốn và sức chứa", fontsize=10)
    ax.legend(fontsize=7, frameon=False, ncol=4, loc="upper right"); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(out, "hinh1_chi_phi.png"), dpi=160); plt.close(fig)

    khu = kh["khu"]
    fig, axes = plt.subplots(1, len(khu), figsize=(4 * len(khu), 3.2), squeeze=False)
    for ax, z in zip(axes[0], khu.index):
        for (p, rb), nhan, mau_ in [(("C", False), "C không ràng buộc", "#7aa6e0"), (("D", True), "D", "#1f6feb")]:
            sk = mau[(p, rb)][1]
            if z in sk:
                ax.plot(ngay[:len(sk)], sk[z], color=mau_, lw=1.4, label=nhan)
        cap = float(khu.loc[z, "suc_chua_lit"])
        if cap > 0:
            ax.axhline(cap, color="#d62728", ls="--", lw=1, label="Sức chứa")
        ax.set_title(z, fontsize=10); ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
        ax.spines[["top", "right"]].set_visible(False); ax.legend(fontsize=7, frameon=False)
    axes[0][0].set_ylabel("Lít đang dùng (tồn + đang về)")
    fig.tight_layout(); fig.savefig(os.path.join(out, "hinh2_suc_chua.png"), dpi=160); plt.close(fig)

    sim = mau[("D", True)][0]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for m, g in sim.groupby("mat_hang"):
        ax.plot(ngay[:len(g)], g["ton_kho"].values * kh["info"].loc[m, "gia_von"] / 1e6, lw=1.2, label=m)
    ax.set_ylabel("Triệu đồng"); ax.set_title("Giá trị tồn kho từng mặt hàng – chính sách D", fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    ax.legend(fontsize=7, frameon=False); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(out, "hinh3_ton_kho.png"), dpi=160); plt.close(fig)

    # Thác nước ablation: C → (+ gộp chuyến) → (+ tồn khả dụng) → D, cùng ràng buộc
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    nhan = ["C (có ràng buộc)"] + [b["buoc"] for b in ablation["cac_buoc"]] + ["C+G+E"]
    muc = ablation["diem_dau"] / 1e6
    ax.bar(0, muc, color="#7aa6e0", width=0.6)
    ax.text(0, muc * 1.02, f"{muc:.2f}", ha="center", fontsize=9)
    for k, b in enumerate(ablation["cac_buoc"], start=1):
        dt = b["thay_doi_tb"] / 1e6
        ax.bar(k, dt, bottom=muc, color="#54a24b" if dt < 0 else "#e45756", width=0.6)
        ax.text(k, max(muc, muc + dt) * 1.02, f"{dt:+.2f}", ha="center", fontsize=9)
        muc += dt
    ax.bar(len(nhan) - 1, muc, color="#1f6feb", width=0.6)
    ax.text(len(nhan) - 1, muc * 1.02, f"{muc:.2f}", ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(range(len(nhan)), [n.replace(" (", "\n(") for n in nhan], fontsize=8)
    ax.set_ylabel("Triệu đồng"); ax.set_ylim(0, ablation["diem_dau"] / 1e6 * 1.2)
    ax.set_title("Mỗi thành phần của D đóng góp bao nhiêu? (xanh = giảm, đỏ = tăng chi phí)", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(out, "hinh4_ablation.png"), dpi=160); plt.close(fig)


def do_nhay_han_dung(ban_hang, mh, nguon, khu, so_ngay, nguon_dl, so_lan, von, bo_ngay_dau, xu_huong=False):
    """P4: hàng nhập về đã cũ, khách chọn hàng mới, không kéo dài hạn khi cất lạnh. Đặc biệt kiểm tra tồn khả dụng (D − C+G)."""
    kich_ban = [("Cơ sở (tuổi khi nhận theo danh mục)", None, 0.0, None),
                ("Hàng mới nguyên (tuổi 0)", 0.0, 0.0, None),
                ("Tuổi khi nhận 50 % hạn", 0.5, 0.0, None),
                ("Khách chọn hàng mới 50 % (LIFO)", None, 0.5, None),
                ("Tuổi 50 % + khách chọn hàng mới 50 %", 0.5, 0.5, None),
                ("Không kéo dài hạn khi cất lạnh (×1,0)", None, 0.0, 1.0)]
    rows = []
    keo_goc = nm.KEO_DAI_TOI_DA
    try:
        for ten, tuoi, lifo, keo in kich_ban:
            mh_k = mh.copy()
            if tuoi is not None:
                mh_k["tuoi_khi_nhan_ngay"] = np.floor(tuoi * mh_k["han_dung_ngay"]).astype(int)
            nm.KEO_DAI_TOI_DA = keo if keo is not None else keo_goc
            kh = nm.ke_hoach(ban_hang, mh_k, nguon, khu, so_ngay, xu_huong=xu_huong)
            df, _, _, _ = mo_phong_lap(kh, nguon_dl, so_lan, von, cau_hinh=[("C", True), ("C+G", True), ("C+G+E", True),
                                                                          ("D", True)],
                                       bo_ngay_dau=bo_ngay_dau, ty_le_lifo=lifo)
            t = df.pivot(index="lan", columns="chinh_sach", values="tong")
            h = df.pivot(index="lan", columns="chinh_sach", values="het_han")
            rows.append({"kich_ban": ten, "C": t["C"].mean(), "C+G": t["C+G"].mean(), "C+G+E": t["C+G+E"].mean(),
                         "D": t["D"].mean(), "het_han_C": h["C"].mean(), "het_han_CG": h["C+G"].mean(),
                         "het_han_CGE": h["C+G+E"].mean(),
                         "ton_kha_dung": (t["C+G+E"] - t["C+G"]).mean(), "do_lech_ton_kha_dung": (t["C+G+E"] - t["C+G"]).std(),
                         "so_lan_ton_kha_dung_giam": int((t["C+G+E"] < t["C+G"]).sum()),
                         "D_so_voi_C_phan_tram": float(((1 - t["D"] / t["C"]) * 100).mean())})
    finally:
        nm.KEO_DAI_TOI_DA = keo_goc
    return pd.DataFrame(rows)


def chinh_can_order(kh, nguon_dl, so_lan, von, bo_ngay_dau, luoi=(0.0, 0.25, 0.5, 0.75, 1.0)):
    """P5 (B2): dò lưới hệ số can-order cho chính sách D; trả về (bảng, hệ số tốt nhất). Hoà thì chọn hệ số nhỏ hơn."""
    goc = nm.HE_SO_CAN_ORDER
    rows = []
    try:
        for hs in luoi:
            nm.HE_SO_CAN_ORDER = hs
            df, _, _, _ = mo_phong_lap(kh, nguon_dl, so_lan, von, cau_hinh=[("D", True)], bo_ngay_dau=bo_ngay_dau)
            rows.append({"he_so_can_order": hs, "tong": df["tong"].mean(), "so_chuyen": df["so_chuyen"].mean(),
                         "so_dong_dat": df["so_dong_dat"].mean(), "csl": df["csl"].mean()})
    finally:
        nm.HE_SO_CAN_ORDER = goc
    bang = pd.DataFrame(rows)
    tot = float(bang.loc[bang["tong"].round(-3).idxmin(), "he_so_can_order"])
    return bang, tot


def ve_do_nhay(do_nhay, out):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for k, mau_ in zip((1, 2, 3), ("#1f6feb", "#f2a541", "#e45756")):
        for p, ls in (("D", "-"), ("C", "--")):
            d = do_nhay.loc[(p, k)]
            axes[0].plot(d.index, d["tong"] / 1e6, ls=ls, marker="o", color=mau_, label=f"{p}, hệ số mất khách {k}")
    axes[0].set_xlabel("Mức phục vụ mục tiêu"); axes[0].set_ylabel("Tổng chi phí (triệu đ)")
    axes[0].legend(fontsize=7, frameon=False); axes[0].set_title("Chi phí theo mức phục vụ mục tiêu", fontsize=10)
    for p, mau_ in (("D", "#1f6feb"), ("C", "#7aa6e0")):
        d = do_nhay.loc[(p, 1)]
        axes[1].plot(d.index, d["csl"] * 100, marker="o", color=mau_, label=f"{p}: CSL đạt được")
        axes[1].plot(d.index, d["ty_le_dap_ung"] * 100, marker="s", ls=":", color=mau_, label=f"{p}: tỷ lệ đáp ứng")
    z = np.array(sorted(do_nhay.index.get_level_values("muc_phuc_vu").unique()))
    axes[1].plot(z, z * 100, color="#888", ls="--", lw=1, label="Mục tiêu")
    axes[1].set_xlabel("Mức phục vụ mục tiêu"); axes[1].set_ylabel("%"); axes[1].legend(fontsize=7, frameon=False)
    axes[1].set_title("Mục tiêu so với đạt được", fontsize=10)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(out, "hinh5_do_nhay.png"), dpi=160); plt.close(fig)


def main():
    p = argparse.ArgumentParser(description="Luồng end-to-end cho cả cửa hàng nhiều mặt hàng thực phẩm")
    p.add_argument("--du-lieu", help="File doanh số CSV/Excel (bỏ trống = dữ liệu mô phỏng)")
    p.add_argument("--mat-hang", help=f"File danh mục mặt hàng, cột: {nm.COT_MAT_HANG}")
    p.add_argument("--nguon", help=f"File nguồn hàng, cột: {nm.COT_NGUON}")
    p.add_argument("--khu", help=f"File khu bảo quản, cột: {nm.COT_KHU}")
    p.add_argument("--von", type=float, default=10_000_000, help="Vốn tối đa dành cho nhập hàng mỗi ngày (đ)")
    p.add_argument("--so-ngay", type=int, default=None, help="Số ngày kế hoạch (mặc định 365 mô phỏng / 120 dữ liệu thật)")
    p.add_argument("--so-lan", type=int, default=20, help="Số lần mô phỏng lặp")
    p.add_argument("--out", default=os.path.join(THU_MUC, "output"), help="Thư mục kết quả")
    p.add_argument("--bo-ngay-dau", type=int, default=30, help="Bỏ W ngày đầu (khởi động) khỏi chỉ số, mặc định 30")
    p.add_argument("--hoc-lai", action="store_true", help="Dữ liệu mô phỏng: sinh lại lịch sử và học lại dự báo mỗi lần lặp")
    p.add_argument("--do-nhay", action="store_true", help="Chạy thêm phân tích độ nhạy mức phục vụ × hệ số mất khách")
    p.add_argument("--xu-huong", action="store_true", help="Thêm xu hướng tuyến tính có hãm vào dự báo (mặc định tắt)")
    p.add_argument("--chinh-can-order", action="store_true",
                   help="Dò lưới hệ số can-order {0; 0,25; 0,5; 0,75; 1} cho D rồi dùng hệ số tốt nhất (mặc định 0,5)")
    p.add_argument("--ton-kha-dung", action="store_true", help="D dùng tồn khả dụng (EWA) khi quyết định (mặc định tắt)")
    p.add_argument("--ty-le-lifo", type=float, default=0.0, help="Phần nhu cầu do khách chọn hàng mới nhất (0–1), mặc định 0")
    p.add_argument("--do-nhay-han-dung", action="store_true",
                   help="Chạy thêm độ nhạy hàng dễ hỏng: tuổi khi nhận, khách chọn hàng mới, mức kéo dài hạn khi cất lạnh")
    a = p.parse_args()
    nm.DUNG_TON_KHA_DUNG = bool(a.ton_kha_dung)
    os.makedirs(a.out, exist_ok=True)

    print("Bước 1/6  Đọc dữ liệu bán hàng và danh mục...")
    if a.du_lieu:
        ban_hang, cb_ = loi.chuan_hoa_ban_hang(loi.doc_file(a.du_lieu))
        for c in cb_:
            print("  ! " + c)
        nguon_dl = "nguoi_dung"
    else:
        ban_hang, nguon_dl = du_lieu_mo_phong(a.out), "mo_phong"
    ds = list(ban_hang.columns)
    mh = _doc_bang(a.mat_hang, nm.mat_hang_mac_dinh(ds), nm.COT_MAT_HANG)
    mh["mat_hang"] = mh["mat_hang"].map(loi._nfc)
    mh = mh[mh["mat_hang"].isin(ds)]
    thieu = [m for m in ds if m not in set(mh["mat_hang"])]
    if thieu:
        print(f"  ! Dùng tham số mặc định cho {thieu}")
        mh = pd.concat([mh, nm.mat_hang_mac_dinh(thieu)], ignore_index=True)
    nguon = _doc_bang(a.nguon, nm.nguon_mac_dinh(mh["nguon_hang"]), nm.COT_NGUON)
    khu = _doc_bang(a.khu, nm.khu_mac_dinh(), nm.COT_KHU)
    loi_ = nm.kiem_tra(mh, nguon, khu)
    if loi_:
        sys.exit("Tham số không hợp lệ:\n- " + "\n- ".join(loi_))
    so_ngay = a.so_ngay or (365 if nguon_dl == "mo_phong" else 120)
    print(f"          {len(ban_hang)} ngày × {len(ds)} mặt hàng, {nguon['nguon_hang'].nunique()} nguồn hàng, "
          f"{len(khu)} khu bảo quản")

    print(f"Bước 2-3/6  Dự báo {so_ngay} ngày, tính hạn dùng thực, SS, ROP, EOQ có hư hỏng...")
    kh = nm.ke_hoach(ban_hang, mh, nguon, khu, so_ngay, xu_huong=a.xu_huong)
    kd = []
    for m in ds:
        k = loi.kiem_dinh_theo_mua(ban_hang[m], xu_huong=a.xu_huong)
        if len(k):
            kd.append(k.assign(mat_hang=m))
    kiem_dinh = pd.concat(kd) if kd else pd.DataFrame()
    if len(kiem_dinh):
        kiem_dinh.to_csv(os.path.join(a.out, "kiem_dinh_du_bao_theo_mua.csv"), index=False, encoding="utf-8-sig")

    print("Bước 4/6  Xuất kế hoạch theo ngày...")
    pd.concat([pd.DataFrame({"ngay": kh["ngay"], "mat_hang": m, "du_bao_ngay": v["d_hat"][:so_ngay].round(2),
                             "ton_kho_an_toan": v["ss"].round(1), "diem_dat_hang_ROP": v["rop"].round(1),
                             "luong_nhap_Q_rieng_le": v["q"]}) for m, v in kh["mat_hang"].items()]) \
        .to_csv(os.path.join(a.out, "ke_hoach_ton_kho_theo_ngay.csv"), index=False, encoding="utf-8-sig")
    kh["info"].reset_index().to_csv(os.path.join(a.out, "tham_so_dan_xuat.csv"), index=False, encoding="utf-8-sig")

    print(f"Bước 5/6  Mô phỏng cả cửa hàng: {a.so_lan} lần lặp × {len(CONG_BANG + THAM_KHAO)} cấu hình "
          f"({len(CONG_BANG)} có ràng buộc, {len(THAM_KHAO)} không ràng buộc)...")
    bang_co = None
    if a.chinh_can_order:
        print("          Dò lưới hệ số can-order cho D...")
        bang_co, tot = chinh_can_order(kh, nguon_dl, min(a.so_lan, 10), a.von, a.bo_ngay_dau)
        bang_co.to_csv(os.path.join(a.out, "chinh_can_order.csv"), index=False, encoding="utf-8-sig")
        nm.HE_SO_CAN_ORDER = tot
        print(f"          → chọn hệ số can-order = {tot}")
    tao = None
    if a.hoc_lai and nguon_dl == "mo_phong":
        def tao(r):
            ngay = pd.date_range("2023-01-01", "2024-12-31")
            rng_h = np.random.default_rng(5000 + r)
            bh_r = pd.DataFrame({m: sinh_nhu_cau(m, ngay, rng_h) for m in MAT_HANG_MO_PHONG}, index=ngay)
            return nm.ke_hoach(bh_r, mh, nguon, khu, so_ngay, xu_huong=a.xu_huong)
        print("          (--hoc-lai: mỗi lần lặp dùng một lịch sử và một bộ dự báo mới)")
    df, mau, theo_mh, mpv = mo_phong_lap(kh, nguon_dl, a.so_lan, a.von, bo_ngay_dau=a.bo_ngay_dau, tao_ke_hoach=tao,
                                         ty_le_lifo=a.ty_le_lifo)

    print("Bước 6/6  Tổng hợp chi phí, ablation, vẽ biểu đồ...")
    df.to_csv(os.path.join(a.out, "ket_qua_mo_phong_chi_tiet.csv"), index=False, encoding="utf-8-sig")
    cb, tk, giam, ablation = tong_hop(df, a.so_lan)
    bang_mh = theo_mh.groupby(["mat_hang", "chinh_sach"]).mean(numeric_only=True).drop(columns="lan")
    bang_mh.reset_index().to_csv(os.path.join(a.out, "chi_phi_theo_mat_hang.csv"), index=False, encoding="utf-8-sig")
    bang_mpv = mpv.groupby([mpv.index, "chinh_sach"]).mean(numeric_only=True).drop(columns="lan")
    bang_mpv.index.names = ["mat_hang", "chinh_sach"]
    bang_mpv = bang_mpv.join(mh.set_index("mat_hang")["muc_phuc_vu"].rename("muc_tieu"), on="mat_hang")
    bang_mpv.reset_index().to_csv(os.path.join(a.out, "muc_phuc_vu_theo_mat_hang.csv"), index=False, encoding="utf-8-sig")
    dn_hd = None
    if a.do_nhay_han_dung:
        print("          Độ nhạy hàng dễ hỏng (tuổi khi nhận, khách chọn hàng mới, kéo dài hạn)...")
        dn_hd = do_nhay_han_dung(ban_hang, mh, nguon, khu, so_ngay, nguon_dl, min(a.so_lan, 10), a.von, a.bo_ngay_dau,
                                 a.xu_huong)
        dn_hd.to_csv(os.path.join(a.out, "do_nhay_han_dung.csv"), index=False, encoding="utf-8-sig")
    do_nhay = None
    if a.do_nhay:
        print("          Phân tích độ nhạy mức phục vụ × hệ số mất khách...")

        def tao_z(z):
            mh_z = mh.copy()
            mh_z["muc_phuc_vu"] = z
            return nm.ke_hoach(ban_hang, mh_z, nguon, khu, so_ngay, xu_huong=a.xu_huong)
        do_nhay = do_nhay_muc_phuc_vu(tao_z, nguon_dl, min(a.so_lan, 10), a.von, a.bo_ngay_dau)
        do_nhay.reset_index().to_csv(os.path.join(a.out, "do_nhay_muc_phuc_vu.csv"), index=False, encoding="utf-8-sig")
        ve_do_nhay(do_nhay, a.out)
    with open(os.path.join(a.out, "ket_qua_tong_hop.json"), "w", encoding="utf-8") as f:
        json.dump({"nguon_du_lieu": nguon_dl, "so_lan_lap": a.so_lan, "so_ngay": so_ngay, "von_moi_ngay": a.von,
                   "so_sanh_cong_bang": cb.round(2).to_dict("index"),
                   "khong_rang_buoc_tham_khao": tk.round(2).to_dict("index"),
                   "muc_giam_tong_chi_phi_cua_D": giam, "ablation": ablation, "bo_ngay_dau": a.bo_ngay_dau,
                   "hoc_lai": bool(a.hoc_lai), "xu_huong": bool(a.xu_huong), "ty_le_lifo": a.ty_le_lifo,
                   "he_so_can_order": nm.HE_SO_CAN_ORDER, "dung_he_so_boi": nm.DUNG_HE_SO_BOI,
                   "chinh_can_order": None if bang_co is None else bang_co.round(3).to_dict("records"),
                   "do_nhay_han_dung": None if dn_hd is None else dn_hd.round(2).to_dict("records"),
                   "kiem_dinh_theo_mua": {} if not len(kiem_dinh) else
                   kiem_dinh.groupby("mua")[[c for c in kiem_dinh.columns if c.startswith(("wape", "lech"))]]
                   .mean().round(4).to_dict("index"),
                   "muc_phuc_vu_theo_mat_hang": {f"{m}|{p}": v for (m, p), v in bang_mpv.round(4).to_dict("index").items()},
                   "do_nhay": None if do_nhay is None else
                   {f"{c}|k={k}|z={z}": v for (c, k, z), v in do_nhay.round(4).to_dict("index").items()},
                   "chi_phi_theo_mat_hang": {f"{m}|{p}": v for (m, p), v in bang_mh["tong"].round(0).items()},
                   "sai_so_du_bao": {m: {k: v["meta"].get(k) for k in ("wape_du_bao", "wape_trung_binh")}
                                     for m, v in kh["mat_hang"].items()}}, f, ensure_ascii=False, indent=2)
    ve_bieu_do(kh, mau, cb, ablation, a.out)

    pd.set_option("display.width", 250, "display.max_columns", None, "display.float_format", lambda x: f"{x:,.0f}")
    cot = ["chi_phi_chuyen", "chi_phi_dong_hang", "lai_von", "bao_quan", "hu_hong", "het_han", "loi_nhuan_mat", "tong",
           "so_chuyen", "so_dong_dat", "ngay_vuot_von", "ngay_vuot_suc_chua"]
    if bang_co is not None:
        print("\n== DÒ LƯỚI HỆ SỐ CAN-ORDER (chính sách D) ==")
        print(bang_co.to_string(index=False))
    print(f"\n(Chi phí cố định của kho (tiền điện chạy tủ): {cb['chi_phi_co_dinh_kho'].iloc[0]:,.0f} đ, như nhau mọi chính sách, "
          "không cộng vào tổng.)")
    print(f"\n(Bỏ {a.bo_ngay_dau} ngày đầu khỏi chỉ số; tồn đầu = ROP + Q/2.)")
    print(f"\n== SO SÁNH CÔNG BẰNG: mọi chính sách cùng giới hạn vốn {a.von:,.0f} đ/ngày và sức chứa ==")
    print(cb[cot].rename(index=nm.TEN_CS))
    print("\n== MỨC PHỤC VỤ ĐẠT ĐƯỢC (cùng ràng buộc; mục tiêu = tham số 'mức phục vụ', tính theo chu kỳ) ==")
    pd.set_option("display.float_format", lambda x: f"{x:,.4f}")
    print(cb[["ty_le_dap_ung", "csl", "ngay_het_hang"]].rename(index=nm.TEN_CS))
    pd.set_option("display.float_format", lambda x: f"{x:,.0f}")
    print("\n== THAM KHẢO: không giới hạn vốn / sức chứa ==")
    print(tk[cot].rename(index=nm.TEN_CS))
    print("\n== MỨC GIẢM TỔNG CHI PHÍ CỦA D (cùng ràng buộc) ==")
    for goc, g in giam.items():
        print(f"  so với {nm.TEN_CS[goc]}: {g['tb_phan_tram']:.1f}% (±{g['do_lech']:.1f}), D thắng {g['so_lan_D_thang']}/{a.so_lan} lần")
    print("\n== ABLATION (cùng ràng buộc): C → D ==")
    print(f"  C: {ablation['diem_dau']:,.0f} đ")
    for b in ablation["cac_buoc"]:
        print(f"  {b['buoc']:40s}: {b['thay_doi_tb']:+,.0f} đ (±{b['do_lech']:,.0f}), giảm ở {b['so_lan_giam']}/{a.so_lan} lần")
    print(f"  C+G+E: {ablation['diem_cuoi']:,.0f} đ   (D mặc định {'CÓ' if nm.DUNG_TON_KHA_DUNG else 'KHÔNG'} dùng tồn khả dụng: "
          f"{ablation['D']:,.0f} đ)")
    if dn_hd is not None:
        print("\n== ĐỘ NHẠY HÀNG DỄ HỎNG (cùng ràng buộc; 'tồn khả dụng' = (C+G+E) − (C+G), âm là có ích) ==")
        print(dn_hd.set_index("kich_ban"))
    if len(kiem_dinh):
        print("\n== KIỂM ĐỊNH DỰ BÁO THEO MÙA (học trước mốc, dự báo 90 ngày; WAPE, thấp hơn là tốt hơn) ==")
        pd.set_option("display.float_format", lambda x: f"{x:,.3f}")
        print(kiem_dinh.groupby("mua")[["wape_mo_hinh", "wape_trung_binh_56", "wape_nam_ngoai_cung_ngay", "wape_dinh_mo_hinh",
                                        "wape_dinh_trung_binh_56", "wape_dinh_nam_ngoai", "lech_tong_dinh"]].mean())
    print(f"\nĐã lưu kết quả vào: {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
