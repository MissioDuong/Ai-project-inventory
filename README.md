# EOQ Bánh Kẹo Chợ

Công cụ giúp tiểu thương bánh kẹo ở chợ quyết định **hôm nay đi nhập ở đâu, mua gì, bao nhiêu** cho nhiều mặt hàng
thực phẩm cùng lúc: tính hạn dùng, hư hỏng, nhiệt độ bảo quản, vốn và sức chứa kho. Có **trợ lý AI** (LLM của OpenAI)
trả lời câu hỏi tiếng Việt bằng cách gọi các hàm tính toán của ứng dụng, **sửa thông số / tồn kho / vốn theo yêu cầu**
(kiểm tra hợp lệ, có hoàn tác) và **phân tích ngay dưới các biểu đồ**.

> Dữ liệu mẫu là mô phỏng, tham số mang tính minh hoạ. Chi tiết thuật toán và kết quả: **[tai_lieu/DU_AN.md](tai_lieu/DU_AN.md)**.

## Chạy
```bash
pip install -r requirements.txt
python -m pytest tests -q   # 76 bài kiểm thử
streamlit run app.py        # giao diện, http://localhost:8501
python pipeline.py          # mô phỏng so sánh chính sách, kết quả vào output/
```

**Trợ lý AI:** tạo file `.streamlit/secrets.toml` (đã có trong `.gitignore`, không chia sẻ):
```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```
Hoặc đặt biến môi trường `OPENAI_API_KEY`, hoặc nhập trong ô 🤖 ở thanh bên. Tài khoản OpenAI cần còn tín dụng.

**Dữ liệu của bạn:** xem mẫu trong `du_lieu_thu/`, rồi tải lên trong app, hoặc chạy:
```bash
python pipeline.py --du-lieu du_lieu_thu/doanh_so_thu.csv --mat-hang du_lieu_thu/mat_hang_thu.csv --nguon du_lieu_thu/nguon_hang_thu.csv --khu du_lieu_thu/khu_bao_quan_thu.csv
```
Tuỳ chọn khác của `pipeline.py`: `--von`, `--so-ngay`, `--so-lan`, `--do-nhay`, `--do-nhay-han-dung`, `--chinh-can-order`,
`--hoc-lai`, `--xu-huong`, `--ty-le-lifo`, `--ton-kha-dung` (xem `python pipeline.py -h`).

## Giao diện
| Trang | Nội dung |
|---|---|
| 🛒 Hôm nay | Nhập tồn kho (nhiều lô) → danh sách đi chợ theo nguồn, vốn cần, cảnh báo, sức chứa; nút "✨ Giải thích bằng AI" |
| 🤖 Trợ lý AI | Hỏi đáp tiếng Việt; AI gọi hàm tính toán, **sửa dữ liệu khi được yêu cầu** (“kẹo dừa còn 120 gói”, “vốn 8 triệu”), có nút ↩️ hoàn tác |
| 📦 Mặt hàng & kho | Nguồn hàng, khu bảo quản, mặt hàng (thiết lập một lần); ô **“Nhờ AI sửa thông số”** bằng lời |
| 📈 Dự báo | Dự báo, hệ số mùa vụ, kiểm định theo mùa; **AI phân tích dưới biểu đồ** |
| 🧪 Mô phỏng | So sánh các cách nhập hàng cùng điều kiện, phân tích từng thành phần; **AI phân tích kết quả** |
| 📖 Hướng dẫn | Cách dùng, thuật toán, tài liệu, câu hỏi thường gặp |

## Cấu trúc
| Thư mục / tệp | Nội dung |
|---|---|
| `app.py` | Điểm vào giao diện Streamlit (chỉ điều phối) |
| `pipeline.py` | Điểm vào dòng lệnh: mô phỏng, so sánh chính sách, xuất kết quả vào `output/` |
| `tinh_toan/` | Thuật toán: dữ liệu, dự báo, SS / ROP / EOQ, nhập gộp, mô phỏng |
| `tro_ly_ai/` | Trợ lý AI (OpenAI, function calling) |
| `giao_dien/` | Các trang giao diện, mỗi trang một file `trang_*.py` |
| `tests/` · `du_lieu_thu/` · `output/` | Kiểm thử · dữ liệu mẫu · kết quả mới nhất |
| `tai_lieu/` | `DU_AN.md` (hồ sơ thuật toán, kết quả) · `NGHIEN_CUU_HANG_THUC_PHAM.md` (tài liệu khoa học) |
| `AGENTS.md` | Workflow và ràng buộc khi chỉnh sửa (AI Agent đọc đầu tiên) |

Tài liệu ngoài phạm vi code (bản Vòng 1, PDF thuyết minh, prompt nộp ban tổ chức, kết quả từng giai đoạn) nằm trong
`../aie_project_tai_lieu_ngoai_du_an.zip`.
