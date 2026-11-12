# AGENTS.md: đọc file này TRƯỚC mỗi lần chỉnh sửa hoặc chạy test

Dự án **EOQ Bánh Kẹo Chợ**: giúp tiểu thương quyết định *hôm nay nhập ở đâu, mua gì, bao nhiêu* cho nhiều mặt hàng thực
phẩm (hạn dùng, hư hỏng, nhiệt độ, vốn, sức chứa). Python + Streamlit, trợ lý AI dùng OpenAI.
Thuật toán, tham số, kết quả: [tai_lieu/DU_AN.md](tai_lieu/DU_AN.md). Cơ sở tài liệu: [tai_lieu/NGHIEN_CUU_HANG_THUC_PHAM.md](tai_lieu/NGHIEN_CUU_HANG_THUC_PHAM.md).

---

## 1. Bản đồ code

```
aie_project/
├── AGENTS.md              ← file này (workflow + ràng buộc)
├── README.md              ← giới thiệu ngắn + cách chạy (cho người)
├── app.py                 ← ĐIỂM VÀO Streamlit: chỉ điều phối thứ tự dựng dữ liệu, chọn trang
├── pipeline.py            ← ĐIỂM VÀO dòng lệnh: sinh dữ liệu mô phỏng, mô phỏng lặp, xuất CSV/JSON/biểu đồ vào output/
├── tinh_toan/             ← TẦNG TÍNH TOÁN (numpy/pandas thuần)
│   ├── loi.py             │  đọc/chuẩn hoá dữ liệu, dự báo mùa vụ Tết/Trung thu, kiểm định, SS/ROP/EOQ một mặt hàng
│   └── nhieu_mat_hang.py  │  hàng dễ hỏng, nhập gộp can-order, ràng buộc vốn/sức chứa, kế hoạch hôm nay, mô phỏng cửa hàng, chi phí
├── tro_ly_ai/             ← TẦNG AI
│   └── tro_ly.py          │  cấu hình key, CongCu (công cụ đọc), BoSua (công cụ sửa có kiểm tra), tra_loi, phan_tich
├── giao_dien/             ← TẦNG GIAO DIỆN (nơi duy nhất import streamlit)
│   ├── cau_hinh.py        │  đường dẫn, tên trang TRANG, lựa chọn nguồn dữ liệu
│   ├── kieu.py            │  CSS, kpi_hang, tieu_de
│   ├── tien_ich.py        │  hàm tính có cache (du_bao, kiem_dinh, mo_phong), tien, ghep_bang, dat_bang/bang_sua
│   ├── thanh_ben.py       │  thanh bên: menu, ⚙️ kế hoạch & vốn, cấu hình AI → tạo ctx ban đầu
│   ├── du_lieu.py         │  nạp doanh số (mô phỏng / file người dùng), khởi tạo bảng thiết lập khi đổi dữ liệu
│   ├── khung_ai.py        │  cầu nối UI ↔ AI: bối cảnh, áp dụng/hoàn tác AI sửa, khung "AI phân tích", client_ai
│   ├── trang_hom_nay.py   │  🛒 Hôm nay
│   ├── trang_mat_hang.py  │  📦 Mặt hàng & kho (3 hàm: ve_thiet_lap, ve_han_dung, ve_ai_sua)
│   ├── trang_du_bao.py    │  📈 Dự báo
│   ├── trang_mo_phong.py  │  🧪 Mô phỏng & so sánh
│   ├── trang_huong_dan.py │  📖 Hướng dẫn (nội dung tĩnh, câu hỏi thường gặp)
│   └── trang_tro_ly.py    │  🤖 Trợ lý AI (chat)
├── tests/                 ← pytest: test_loi, test_nhieu_mat_hang, test_giai_doan_*, test_tro_ly, test_giao_dien
├── du_lieu_thu/           ← dữ liệu mẫu 8 mặt hàng cho người dùng tải lên VÀ cho test (đừng sửa tuỳ tiện)
├── output/                ← kết quả pipeline.py mới nhất; app đọc output/du_lieu_lich_su_mo_phong_2023_2024.csv làm dữ liệu demo
├── tai_lieu/              ← DU_AN.md (hồ sơ thuật toán + kết quả + lịch sử), NGHIEN_CUU_HANG_THUC_PHAM.md (tài liệu khoa học)
└── .streamlit/            ← config.toml (theme) · secrets.toml (API KEY, BÍ MẬT)
```

### Muốn sửa X thì vào đâu

| Cần sửa | File / vị trí |
|---|---|
| Công thức dự báo, hệ số mùa vụ, bảng ngày Tết/Trung thu | `tinh_toan/loi.py` (`TET`, `TRUNG_THU`, `hoc_mua_vu`, `du_bao_nhu_cau`, `kiem_dinh_theo_mua`) |
| SS / ROP / EOQ một mặt hàng | `tinh_toan/loi.py` (`chinh_sach`, `chinh_sach_eoq_tinh`, `chinh_sach_kinh_nghiem`) |
| Hạn dùng theo nhiệt độ (Q10), hư hỏng θ, chi phí giữ | `tinh_toan/nhieu_mat_hang.py` (`han_dung_hieu_dung`, `chuan_bi`, `_tp`) |
| Tham số mặc định mặt hàng / nguồn / khu | `tinh_toan/nhieu_mat_hang.py` (`_MH`, `_NGUON`, `_KHU`, `COT_*`) |
| Quy tắc nhập gộp, can-order, cắt theo vốn/sức chứa | `tinh_toan/nhieu_mat_hang.py` (`chu_ky_chung`, `dat_hang_gop`, `cat_theo_rang_buoc`, `HE_SO_CAN_ORDER`) |
| Danh sách đi chợ hôm nay (nhiều lô) | `tinh_toan/nhieu_mat_hang.py` (`ke_hoach_hom_nay`, `gom_lo`) |
| Mô phỏng cửa hàng, chi phí, CSL, chính sách A/B/C/D | `tinh_toan/nhieu_mat_hang.py` (`mo_phong_cua_hang`, `chi_phi_cua_hang`, `TEN_CS`, `CAU_HINH`) |
| Dữ liệu mô phỏng, mô phỏng lặp, độ nhạy, biểu đồ PNG, tham số dòng lệnh | `pipeline.py` |
| Lời dặn hệ thống cho LLM, danh sách mô hình | `tro_ly_ai/tro_ly.py` (`HUONG_DAN`, `MO_HINH_GOI_Y`) |
| Thêm/sửa công cụ AI đọc số liệu | `tro_ly_ai/tro_ly.py` (`CongCu` + định nghĩa công cụ) |
| Trường AI được phép sửa và giới hạn hợp lệ | `tro_ly_ai/tro_ly.py` (`TRUONG_*`, `DINH_NGHIA_SUA`, `BoSua`) |
| Màu sắc, font, thẻ KPI | `giao_dien/kieu.py`, `.streamlit/config.toml` |
| Thêm/đổi tên/đổi thứ tự trang | `giao_dien/cau_hinh.py` (`TRANG`) + bảng định tuyến cuối `app.py` + file `giao_dien/trang_*.py` |
| Nội dung một trang | `giao_dien/trang_<tên>.py` |
| Thanh bên, vốn, số ngày kế hoạch | `giao_dien/thanh_ben.py` |
| Tải file doanh số, đọc file người dùng | `giao_dien/du_lieu.py` (UI) · `tinh_toan/loi.py` (`doc_file`, `chuan_hoa_ban_hang`) |
| Nút "✨ Phân tích", hoàn tác AI sửa | `giao_dien/khung_ai.py` |

## 2. Kiến trúc và quy tắc phụ thuộc (bắt buộc)

```
app.py ──► giao_dien/ ──► tro_ly_ai/ ──► tinh_toan/
pipeline.py ─────────────────────────► tinh_toan/
```

- `tinh_toan/` **không** import `streamlit`, `openai`, `giao_dien`, `tro_ly_ai`. Import nội bộ dùng tương đối (`from . import loi`).
- `tro_ly_ai/` **không** import `streamlit`. LLM **không tự tính số**: mọi con số phải đến từ hàm trong `tinh_toan/`
  qua công cụ (function calling). Công cụ sửa phải kiểm tra hợp lệ và không đổi dữ liệu gốc (`BoSua` làm trên bản sao).
- `giao_dien/` là nơi duy nhất import `streamlit`. Mỗi trang là hàm `ve(ctx)`; dữ liệu dùng chung truyền qua `ctx`
  (`SimpleNamespace` do `app.py` dựng: `trang, so_ngay, von, xu_huong, ai_key, ai_mo_hinh, ds_mo_hinh, ban_hang, canh_bao,
  ten_nguon, skus, sig, mh, nguon, khu, loi_tl, db, kh, info, bat_dau`). Không dùng biến toàn cục giữa các file trang.
- `app.py` chỉ điều phối; không viết nội dung trang vào đây.
- Import từ thư mục gốc dự án theo dạng `from tinh_toan import loi`, `from tinh_toan import nhieu_mat_hang as nm`,
  `from tro_ly_ai import tro_ly as tl` (chạy lệnh từ thư mục gốc; `tests/conftest.py` đã thêm gốc vào `sys.path`).

## 3. Workflow mỗi lần chỉnh sửa

1. **Đọc AGENTS.md** (file này). Tra bảng "Muốn sửa X thì vào đâu" để mở đúng file; chỉ đọc phần liên quan.
2. **Chạy test làm mốc** trước khi sửa: `python -m pytest tests -q`. Ghi nhận số test đang qua.
3. **Sửa** theo quy tắc phụ thuộc ở mục 2 và ràng buộc ở mục 5. Thay đổi nhỏ, đúng chỗ; không đổi tên hàm công khai
   nếu không cần (test và trợ lý AI gọi theo tên).
4. **Thêm/cập nhật test** cho hành vi mới (thuật toán → `tests/test_*.py` tương ứng; giao diện → `tests/test_giao_dien.py`).
5. **Chạy lại toàn bộ test**: phải qua hết, số test không giảm.
6. Nếu sửa giao diện: chạy thêm `streamlit run app.py` và xem trang đã sửa (test khói chỉ bắt lỗi, không bắt bố cục xấu).
7. Nếu thay đổi làm **đổi kết quả số** (thuật toán, tham số mặc định, hằng số như `HE_SO_CAN_ORDER`, `DUNG_TON_KHA_DUNG`):
   chạy `python pipeline.py` (ghi vào `output/`) rồi cập nhật bảng kết quả trong `tai_lieu/DU_AN.md`.
8. **Cập nhật tài liệu**: thêm một dòng vào mục "Lịch sử chỉnh sửa" của `tai_lieu/DU_AN.md`; nếu thêm/đổi file hoặc
   thư mục thì cập nhật bản đồ code ở mục 1 của file này; README chỉ sửa khi cách chạy thay đổi.

## 4. Lệnh

```bash
pip install -r requirements.txt
python -m pytest tests -q                       # toàn bộ test (~15 giây), gồm test khói mọi trang giao diện
python -m pytest tests -q -k "not giao_dien"    # chỉ tầng tính toán + AI (~4 giây)
streamlit run app.py                            # http://localhost:8501
python pipeline.py --so-lan 1 --out <thư_mục_tạm>   # chạy thử nhanh, KHÔNG ghi đè output/
python pipeline.py                              # chạy đầy đủ, ghi kết quả chính thức vào output/
```
Trên Windows, nếu in tiếng Việt bị lỗi mã hoá: đặt `PYTHONIOENCODING=utf-8` trước lệnh.

## 5. Ràng buộc

**Bảo mật**
- `.streamlit/secrets.toml` chứa OpenAI API key thật: **không đọc ra, không in, không chép** vào code, log, tài liệu,
  câu trả lời hay commit. Code chỉ lấy key qua `tro_ly.doc_cau_hinh()`.
- Test **không gọi OpenAI thật** (tốn tiền, tài khoản có thể hết tín dụng): dùng client giả như `tests/test_tro_ly.py`,
  hoặc thay `tl.doc_cau_hinh` như `tests/test_giao_dien.py`.

**Dữ liệu**
- Không sửa `du_lieu_thu/` trừ khi được yêu cầu: test phụ thuộc vào nó.
- Không xoá `output/du_lieu_lich_su_mo_phong_2023_2024.csv`: app cần file này cho chế độ "Dữ liệu mô phỏng có sẵn".
- Chạy thử pipeline thì dùng `--out` tới thư mục tạm; chỉ ghi `output/` khi cố ý cập nhật kết quả chính thức.
- Dữ liệu mẫu và tham số mặc định là **giả định minh hoạ**; không trình bày như số liệu thật.

**Streamlit**
- `st.set_page_config` phải là lệnh Streamlit đầu tiên trong `app.py`.
- Không để chuỗi hoặc biểu thức đứng một mình trong code giao diện: Streamlit "magic" sẽ in nó ra màn hình
  (docstring phải là dòng đầu tiên của hàm).
- `key` của widget phải duy nhất. Bảng sửa được dùng `dat_bang` / `bang_sua` (giữ chỉnh sửa khi chuyển trang).
  Đổi giá trị widget từ code (AI sửa, hoàn tác) thì đặt cờ trong `st.session_state` rồi `st.rerun()`, như `_cho_von`.
- Thứ tự `TRANG` được dùng theo chỉ số (`TRANG[1]`, `TRANG[5]`): đổi thứ tự thì sửa mọi chỗ dùng.

**Quy ước code**
- Tên biến/hàm/file: tiếng Việt không dấu, `snake_case`. Chuỗi hiển thị cho người dùng: tiếng Việt có dấu. File UTF-8.
- Chỉ dùng thư viện trong `requirements.txt`; thêm thư viện thì cập nhật file này.
- Giữ phong cách code xung quanh (dòng dài kiểu bảng cấu hình là bình thường ở đây); chú thích ngắn, giải thích *vì sao*.

**Giữ dự án gọn**
- Không tạo thêm file `.md` kế hoạch, báo cáo tạm hay ghi chú trong dự án. Tiến độ và quyết định ghi vào mục lịch sử
  của `tai_lieu/DU_AN.md`. Script thử nghiệm tạm để ngoài thư mục dự án.
- Tài liệu không thuộc code / thuật toán / app (bản Vòng 1, PDF thuyết minh, prompt nộp ban tổ chức, kịch bản video,
  kết quả từng giai đoạn P0–P5) đã đóng vào `../aie_project_tai_lieu_ngoai_du_an.zip`. Đừng giải nén lại vào dự án.
- Không commit `__pycache__/`, `.pytest_cache/`, `secrets.toml`.

**Git**
- Dự án có repo git riêng (nhánh `main`, chưa có remote). Chỉ commit khi người dùng yêu cầu; trước khi commit chạy test
  và kiểm tra `git status` không có `secrets.toml` hay key (`git grep --cached -nE "sk-[A-Za-z0-9_-]{20,}"` phải rỗng).
- Không `push`, không `reset --hard` / `push --force` khi chưa hỏi người dùng.

## 6. Checklist trước khi báo xong

- [ ] `python -m pytest tests -q` qua hết, số test không giảm
- [ ] Không vi phạm quy tắc phụ thuộc (mục 2); không có key/bí mật trong thay đổi
- [ ] Đã chạy app xem trang đã sửa (nếu sửa giao diện)
- [ ] Kết quả số trong `tai_lieu/DU_AN.md` còn đúng (nếu đổi thuật toán/tham số)
- [ ] Đã cập nhật lịch sử trong `tai_lieu/DU_AN.md` và bản đồ code ở đây (nếu đổi cấu trúc)
