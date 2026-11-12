# -*- coding: utf-8 -*-
"""Hằng số giao diện: đường dẫn, tên các trang, lựa chọn nguồn dữ liệu."""
import os

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # thư mục gốc dự án
DEMO = os.path.join(THU_MUC, "output", "du_lieu_lich_su_mo_phong_2023_2024.csv")  # do pipeline.py sinh ra

# Thứ tự trong TRANG được dùng làm chỉ số ở nhiều nơi (TRANG[1] = Mặt hàng & kho, TRANG[5] = Trợ lý AI): đổi thứ tự phải sửa theo
TRANG = ["🛒  Hôm nay", "📦  Mặt hàng & kho", "📈  Dự báo", "🧪  Mô phỏng", "📖  Hướng dẫn", "🤖  Trợ lý AI"]
DL_MO_PHONG, DL_CUA_TOI = "Dữ liệu mô phỏng có sẵn", "Tải dữ liệu của tôi"
