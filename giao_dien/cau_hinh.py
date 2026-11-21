# -*- coding: utf-8 -*-
"""Hằng số giao diện: đường dẫn, tên các trang, lựa chọn nguồn dữ liệu."""
import os

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # thư mục gốc dự án
DEMO = os.path.join(THU_MUC, "output", "du_lieu_lich_su_mo_phong_2023_2024.csv")  # do pipeline.py sinh ra


def thu_muc_so():
    """Nơi lưu sổ kiểm kho, ước lượng và thiết lập của người dùng (không đưa lên git). Test đặt EOQ_THU_MUC_SO."""
    return os.environ.get("EOQ_THU_MUC_SO") or os.path.join(THU_MUC, "du_lieu_cua_toi")


# Các nút menu, theo thứ tự hiển thị. Code dùng tên hằng (HOM_NAY, NHAP_LIEU, ...), không dùng chỉ số
TRANG = ["🛒  Hôm nay", "📝  Nhập dữ liệu", "🔮  Dự đoán", "📊  Biểu đồ", "⚙️  Thiết lập", "🧪  Mô phỏng", "🤖  Trợ lý AI",
         "📖  Hướng dẫn"]
HOM_NAY, NHAP_LIEU, DU_DOAN, BIEU_DO, THIET_LAP, MO_PHONG, TRO_LY, HUONG_DAN = TRANG
MO_TA_TRANG = ["Danh sách đi chợ", "Kiểm kho, ước lượng, file", "Khi nào cần đặt hàng", "Đã bán, tồn kho, mùa vụ",
               "Mặt hàng, nguồn, kho", "So sánh các cách nhập", "Hỏi đáp, sửa bằng lời", "Cách dùng, hỏi đáp"]

DL_MO_PHONG, DL_SO_GHI, DL_CUA_TOI = "Dữ liệu mô phỏng (dùng thử)", "Sổ kiểm kho của tôi", "File doanh số của tôi"
NGUON_DL = [DL_MO_PHONG, DL_SO_GHI, DL_CUA_TOI]
MO_TA_NGUON_DL = ["6 mặt hàng mẫu, 2 năm bán hàng giả lập", "Đếm hàng mỗi tối, app tự suy ra lượng bán",
                  "File CSV/Excel có sẵn, ít nhất 60 ngày"]
