# Phân tích ván cờ Lichess

## Mục tiêu

Dự án xây dựng pipeline và dashboard để phân tích các ván cờ tiêu chuẩn trên
Lichess. Câu hỏi tổng quát là: rating, màu quân, thể thức thời gian và bối
cảnh giải đấu ảnh hưởng thế nào đến kết quả và diễn biến của ván cờ?

Năm câu hỏi phân tích chính, được diễn đạt theo hướng dễ hiểu:

1. Khi hai bên có rating gần nhau, quân Trắng có ghi điểm tốt hơn không?
2. Khi rating chênh lệch nhiều hơn, người có rating cao hơn có thường đạt điểm cao hơn không?
3. Rating chênh lệch liên quan đến kết quả ra sao ở từng thể thức?
4. Thời gian ban đầu và số giây cộng thêm mỗi nước liên quan thế nào đến tỷ lệ hết giờ?
5. Kết quả và diễn biến ván có khác giữa trong và ngoài giải đấu không?

Các biểu đồ về cơ cấu cách kết thúc và độ dài ván được giữ ở vai trò phân
tích bổ trợ, không xem là câu hỏi nghiên cứu độc lập.

## Kiến trúc

```text
Hugging Face Parquet
        |
        v
src/ingest.py  ->  data/landing/lichess/lichess_sample.parquet
        |
        v
src/build_warehouse.py  ->  data/chess.duckdb
        |
        v
dashboard/app.py  ->  Streamlit dashboard
```

DuckDB có hai bảng chính và một bảng báo cáo:

- `raw.lichess_games`: dữ liệu mẫu sau khi nạp, giữ lại trường gốc.
- `staging.games`: dữ liệu đã làm sạch và các biến dẫn xuất phục vụ phân tích.
- `staging.cleaning_report`: số bản ghi bị loại ở từng quy tắc.

## Cài đặt và chạy

```powershell
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python run_pipeline.py
python -m streamlit run dashboard/app.py
```

`run_pipeline.py --refresh-sample` sẽ tải lại mẫu từ Hugging Face. Thao tác
này có thể tải nhiều dữ liệu và cần kết nối mạng.

## Phương pháp lấy mẫu

Pipeline chọn tối đa 10 shard trải đều trong thư mục tháng 09/2025, sau đó lấy
một số lượng gần bằng nhau từ mỗi shard. Đây là mẫu phân tầng theo thời gian,
không phải phân phối nguyên bản theo số ván của từng thời điểm. Vì vậy:

- Có thể so sánh tỷ lệ và mối quan hệ trong mẫu.
- Không nên dùng số ván theo ngày hoặc theo giờ để ước lượng hoạt động thật.
- Khi báo cáo kết quả, cần ghi rõ kích thước mẫu và tháng dữ liệu.

## Kiểm tra chất lượng

Chạy test trên bộ dữ liệu tổng hợp nhỏ, không cần tải lại mẫu 400.000 ván:

```powershell
python -m pytest -q
```

Test dựng kho DuckDB tạm từ Parquet tổng hợp, kiểm tra tính duy nhất của
`game_id`, đối soát số dòng trước/sau làm sạch, phân loại giải đấu/cấu hình
đồng hồ và đối chiếu số ply với `python-chess`.

## Giới hạn

- Dữ liệu chỉ là mẫu của một tháng, không đại diện cho mọi thời kỳ.
- Các kết luận quan sát không chứng minh quan hệ nhân quả.
- `total_plies` được tính từ PGN bằng biểu thức SQL và được đối chiếu bằng
  `python-chess` trên một mẫu kiểm tra.
