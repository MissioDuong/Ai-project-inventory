# -*- coding: utf-8 -*-
"""Hằng số giao diện: đường dẫn, tên các trang, lựa chọn nguồn dữ liệu."""
import os

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # thư mục gốc dự án
DEMO = os.path.join(THU_MUC, "output", "du_lieu_lich_su_mo_phong_2023_2024.csv")  # do pipeline.py sinh ra


MONGO_MAC_DINH = "mongodb://127.0.0.1:27017/eoq_banh_keo"       # MongoDB chạy trên máy; database riêng của app


def thu_muc_so():
    """Thư mục CSV dự phòng cho sổ kiểm kho / ước lượng / thiết lập (không đưa lên git). Test đặt EOQ_THU_MUC_SO."""
    return os.environ.get("EOQ_THU_MUC_SO") or os.path.join(THU_MUC, "du_lieu_cua_toi")


def noi_luu_so():
    """Nơi lưu sổ của người dùng: chuỗi mongodb://... hoặc đường dẫn thư mục CSV.
    - EOQ_THU_MUC_SO có đặt (test, chạy thử) → thư mục đó, không bao giờ đụng MongoDB.
    - Không thì MongoDB ở EOQ_MONGO_URI (mặc định MONGO_MAC_DINH) nếu đang chạy; MongoDB tắt thì dùng thư mục CSV."""
    from tinh_toan import so_ghi
    if os.environ.get("EOQ_THU_MUC_SO"):
        return os.environ["EOQ_THU_MUC_SO"]
    uri = os.environ.get("EOQ_MONGO_URI") or MONGO_MAC_DINH
    return uri if so_ghi.mongo_san_sang(uri) else thu_muc_so()


# Các trang. Code dùng tên hằng (HOM_NAY, NHAP_LIEU, ...), không dùng chỉ số
TRANG = ["Hôm nay", "Nhập dữ liệu", "Dự đoán", "Biểu đồ", "Mô phỏng", "Mặt hàng & kho", "Kế hoạch & vốn", "Trợ lý AI",
         "Hướng dẫn"]
HOM_NAY, NHAP_LIEU, DU_DOAN, BIEU_DO, MO_PHONG, THIET_LAP, KE_HOACH, TRO_LY, HUONG_DAN = TRANG
MO_TA_TRANG = dict(zip(TRANG, ["Danh sách đi chợ hôm nay", "Kiểm kho, ước lượng ban đầu, tải file", "Khi nào cần đặt hàng",
                               "Đã bán, tồn kho, mùa vụ", "So sánh các cách nhập", "Nguồn hàng, kho, thông số mặt hàng",
                               "Số ngày kế hoạch, vốn mỗi ngày", "Hỏi đáp, sửa bằng lời", "Cách dùng, câu hỏi thường gặp"]))
# Menu hai tầng: thanh nhóm ngang ở trên, các trang của mọi nhóm ở thanh bên
NHOM = [("Hằng ngày", [HOM_NAY, NHAP_LIEU]), ("Phân tích", [DU_DOAN, BIEU_DO, MO_PHONG]),
        ("Thiết lập", [THIET_LAP, KE_HOACH]), ("Trợ giúp", [TRO_LY, HUONG_DAN])]
NHOM_CUA = {t: ten for ten, ds in NHOM for t in ds}

DL_MO_PHONG, DL_SO_GHI, DL_CUA_TOI = "Dữ liệu mô phỏng (dùng thử)", "Sổ kiểm kho của tôi", "File doanh số của tôi"
NGUON_DL = [DL_MO_PHONG, DL_SO_GHI, DL_CUA_TOI]
MO_TA_NGUON_DL = ["6 mặt hàng mẫu, 2 năm bán hàng giả lập", "Đếm hàng mỗi tối, app tự suy ra lượng bán",
                  "File CSV/Excel có sẵn, ít nhất 60 ngày"]
