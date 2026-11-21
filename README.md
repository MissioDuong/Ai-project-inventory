# EOQ Bánh Kẹo Chợ

Công cụ giúp tiểu thương bánh kẹo ở chợ quyết định **hôm nay đi nhập ở đâu, mua gì, bao nhiêu** cho nhiều mặt hàng
thực phẩm cùng lúc: tính hạn dùng, hư hỏng, nhiệt độ bảo quản, vốn và sức chứa kho. Có **trợ lý AI** (LLM của OpenAI)
trả lời câu hỏi tiếng Việt bằng cách gọi các hàm tính toán của ứng dụng, **sửa thông số / tồn kho / vốn theo yêu cầu**
(kiểm tra hợp lệ, có hoàn tác) và **phân tích bên cạnh từng biểu đồ**.

> Dữ liệu mẫu là mô phỏng, tham số mang tính minh hoạ. Chi tiết thuật toán và kết quả: **[tai_lieu/DU_AN.md](tai_lieu/DU_AN.md)**.

## Chạy
```bash
pip install -r requirements.txt
python -m pytest tests -q   # 109 bài kiểm thử
streamlit run app.py        # giao diện, http://localhost:8501
python pipeline.py          # mô phỏng so sánh chính sách, kết quả vào output/
```

**Trợ lý AI:** tạo file `.streamlit/secrets.toml` (đã có trong `.gitignore`, không chia sẻ):
```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```
Hoặc đặt biến môi trường `OPENAI_API_KEY`. Tài khoản OpenAI cần còn tín dụng.

**Chưa có sổ sách bán hàng?** Trong app vào **📝 Nhập dữ liệu**, chọn **Sổ kiểm kho của tôi**, thêm mặt hàng kèm số đoán
bán mỗi ngày, rồi mỗi tối đếm hàng còn lại: app tự suy ra lượng bán và tính điểm đặt hàng. Sổ lưu trong MongoDB
`mongodb://127.0.0.1:27017/eoq_banh_keo` (đổi bằng biến môi trường `EOQ_MONGO_URI`); MongoDB không chạy thì lưu file CSV
trong `du_lieu_cua_toi/` (đã có trong `.gitignore`).

**Có file doanh số (≥ 60 ngày):** xem mẫu trong `du_lieu_thu/`, rồi tải lên ở trang 📝 Nhập dữ liệu, hoặc chạy:
```bash
python pipeline.py --du-lieu du_lieu_thu/doanh_so_thu.csv --mat-hang du_lieu_thu/mat_hang_thu.csv --nguon du_lieu_thu/nguon_hang_thu.csv --khu du_lieu_thu/khu_bao_quan_thu.csv
```
Tuỳ chọn khác của `pipeline.py`: `--von`, `--so-ngay`, `--so-lan`, `--do-nhay`, `--do-nhay-han-dung`, `--chinh-can-order`,
`--hoc-lai`, `--xu-huong`, `--ty-le-lifo`, `--ton-kha-dung` (xem `python pipeline.py -h`).

## Giao diện
Thanh nhóm ngang ở đầu trang (Hằng ngày · Phân tích · Thiết lập · Trợ giúp) và danh sách trang theo nhóm ở thanh bên.

| Nhóm › Trang | Nội dung |
|---|---|
| Hằng ngày › Hôm nay | Nhập tồn kho (nhiều lô) → danh sách đi chợ theo nguồn, vốn cần, cảnh báo, sức chứa; nút "✨ Giải thích bằng AI" |
| Hằng ngày › Nhập dữ liệu | Chọn nguồn số liệu (mô phỏng / sổ kiểm kho / file); **kiểm kho cuối ngày**, mặt hàng + **ước lượng ban đầu**, sổ đã ghi, tải file doanh số |
| Phân tích › Dự đoán | Bán bao nhiêu/ngày, tồn an toàn, **điểm đặt hàng**, còn mấy ngày thì chạm, giải thích con số, kiểm định theo mùa; **AI phân tích** |
| Phân tích › Biểu đồ | Đã bán và dự báo, **tồn kho dự kiến với Reorder Point**, Reorder Point theo mùa, tồn kho đếm được, hệ số mùa vụ, lượng bán theo tuần; **ô AI phân tích bên cạnh mỗi biểu đồ** |
| Phân tích › Mô phỏng | So sánh các cách nhập hàng cùng điều kiện, phân tích từng thành phần; **ô AI phân tích bên cạnh mỗi biểu đồ** |
| Thiết lập › Mặt hàng & kho | Nguồn hàng, khu bảo quản, mặt hàng; ô **“Nhờ AI sửa thông số”** bằng lời; lưu thiết lập khi dùng sổ kiểm kho |
| Thiết lập › Kế hoạch & vốn | Số ngày lập kế hoạch, vốn nhập hàng mỗi ngày, tuỳ chọn dự báo |
| Trợ giúp › Trợ lý AI | Hỏi đáp tiếng Việt; AI gọi hàm tính toán, **sửa dữ liệu khi được yêu cầu**, có nút ↩️ hoàn tác |
| Trợ giúp › Hướng dẫn | Cách dùng, cách app đo lượng bán khi chưa có số liệu, thuật toán, câu hỏi thường gặp |

## Cấu trúc
| Thư mục / tệp | Nội dung |
|---|---|
| `app.py` | Điểm vào giao diện Streamlit (chỉ điều phối) |
| `pipeline.py` | Điểm vào dòng lệnh: mô phỏng, so sánh chính sách, xuất kết quả vào `output/` |
| `tinh_toan/` | Thuật toán: dữ liệu, dự báo, SS / ROP / EOQ, nhập gộp, mô phỏng, sổ kiểm kho (MongoDB / CSV) |
| `tro_ly_ai/` | Trợ lý AI (OpenAI, function calling) |
| `giao_dien/` | Giao diện: mỗi trang một file `trang_*.py`; điều hướng, kiểu chữ/màu, biểu đồ, cầu nối AI dùng chung |
| `tests/` · `du_lieu_thu/` · `output/` | Kiểm thử · dữ liệu mẫu · kết quả mới nhất |
| `du_lieu_cua_toi/` | Nơi lưu dự phòng (CSV) khi MongoDB không chạy; không đưa lên git |
| `tai_lieu/` | `DU_AN.md` (hồ sơ thuật toán, kết quả) · `NGHIEN_CUU_HANG_THUC_PHAM.md` (tài liệu khoa học) |
| `AGENTS.md` | Workflow và ràng buộc khi chỉnh sửa (AI Agent đọc đầu tiên) |

Tài liệu ngoài phạm vi code (bản Vòng 1, PDF thuyết minh, prompt nộp ban tổ chức, kết quả từng giai đoạn) nằm trong
`../aie_project_tai_lieu_ngoai_du_an.zip`.
