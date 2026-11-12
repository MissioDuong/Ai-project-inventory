# -*- coding: utf-8 -*-
"""Cấu hình chung cho bộ kiểm thử: thêm thư mục dự án vào sys.path, dựng sẵn dữ liệu dùng chung."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, THU_MUC)

from tinh_toan import loi  # noqa: E402
from tinh_toan import nhieu_mat_hang as nm  # noqa: E402

DU_LIEU_THU = os.path.join(THU_MUC, "du_lieu_thu")


@pytest.fixture(scope="session")
def ban_hang_mo_phong(tmp_path_factory):
    import pipeline
    return pipeline.du_lieu_mo_phong(str(tmp_path_factory.mktemp("mp")))


@pytest.fixture(scope="session")
def bo_thu():
    """Bộ dữ liệu thử trong du_lieu_thu/: (doanh số, mặt hàng, nguồn, khu)."""
    import pipeline
    bh, _ = loi.chuan_hoa_ban_hang(loi.doc_file(os.path.join(DU_LIEU_THU, "doanh_so_thu.csv")))
    mh = pipeline._doc_bang(os.path.join(DU_LIEU_THU, "mat_hang_thu.csv"), None, nm.COT_MAT_HANG)
    ng = pipeline._doc_bang(os.path.join(DU_LIEU_THU, "nguon_hang_thu.csv"), None, nm.COT_NGUON)
    kz = pipeline._doc_bang(os.path.join(DU_LIEU_THU, "khu_bao_quan_thu.csv"), None, nm.COT_KHU)
    return bh, mh, ng, kz


@pytest.fixture(scope="session")
def ke_hoach_mo_phong(ban_hang_mo_phong):
    bh = ban_hang_mo_phong
    mh = nm.mat_hang_mac_dinh(list(bh.columns))
    return nm.ke_hoach(bh, mh, nm.nguon_mac_dinh(mh["nguon_hang"]), nm.khu_mac_dinh(), 120)


def kich_ban(kh, T, seed=7):
    """Nhu cầu và lead time ngẫu nhiên dùng chung cho các test mô phỏng."""
    rng = np.random.default_rng(seed)
    nc = {m: rng.poisson(kh["mat_hang"][m]["d_hat"][:T]).astype(float) for m in kh["mat_hang"]}
    return nc, nm.sinh_lead_times(kh["info"], T, rng)


def chuoi_co_tet(so_ngay=730, bat_dau="2023-01-01", co_so=10.0, bien_do=4.0, seed=0):
    """Chuỗi bán hàng giả có đỉnh trước Tết, dùng để kiểm tra dự báo."""
    ngay = pd.date_range(bat_dau, periods=so_ngay)
    dt = loi._ngay_gan_nhat(ngay, loi.TET)
    mu = co_so * (1 + bien_do * np.exp(-0.5 * ((dt + 6) / 7.0) ** 2) * (dt <= 3))
    return pd.Series(np.random.default_rng(seed).poisson(mu).astype(float), index=ngay)
