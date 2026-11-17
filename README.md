# Chess Visualization

Dự án phân tích và trực quan hóa dữ liệu các ván cờ Lichess. Pipeline Python, dashboard Streamlit và DuckDB hiện có được giữ nguyên. Phiên bản dashboard mới gồm API FastAPI ở `backend/` và giao diện Next.js ở `frontend/`; API mở DuckDB ở chế độ chỉ đọc.

## Yêu cầu

- Python 3.10 trở lên
- Node.js 20.9 trở lên và npm
- Dataset DuckDB đã có tại `data/chess.duckdb`

## Chạy backend

Mở terminal tại thư mục gốc dự án:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API mặc định tìm database ở `data/chess.duckdb`. Có thể đặt `CHESS_DB_PATH` nếu database nằm chỗ khác (đường dẫn tương đối được tính từ thư mục gốc dự án). API docs: <http://127.0.0.1:8000/docs>.

## Chạy frontend

Mở terminal thứ hai tại thư mục frontend:

```powershell
cd frontend
npm ci
npm run dev
```

Mở <http://localhost:3000>. Mặc định frontend gọi backend tại `http://127.0.0.1:8000`. Nếu backend chạy ở địa chỉ khác, tạo `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Các trang và câu hỏi nghiên cứu

- **Tổng quan:** KPI, RQ1 về độ phổ biến của thể thức thời gian, RQ2 về phân bố Elo trung bình mỗi ván (bin 50 Elo).
- **Elo & kết quả:** RQ3 về kết quả của người có Elo cao hơn; RQ4 về điểm quân Trắng khi Elo tương đương; RQ5 về tỷ lệ thắng Trắng/Đen/hòa theo thể thức.
- **Thời gian & ván đấu:** RQ6 về tỷ lệ hết giờ; RQ7 về phân bố tổng số nước đi.

Ba bộ lọc (thể thức thời gian, nhóm Elo và loại ván đấu) được chia sẻ giữa các trang. RQ3–RQ5 mặc định chỉ tính ván hoàn tất; RQ7 lấy mẫu xác định tối đa 5.000 ván cho mỗi thể thức, khớp cách tính trong dashboard Streamlit.

## Kiểm tra frontend

```powershell
cd frontend
npm run lint
npm run build
```

## Bảo vệ dữ liệu

Backend chỉ mở DuckDB ở chế độ đọc. Không tạo lại hoặc sửa dataset. Không đưa dữ liệu thật, database hoặc thông tin bí mật lên dịch vụ công khai nếu chưa kiểm tra chính sách chia sẻ dữ liệu.
