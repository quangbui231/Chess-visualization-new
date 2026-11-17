from pathlib import Path

# ---------- Đường dẫn ----------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LANDING_DIR = DATA_DIR / "landing" / "lichess"
SAMPLE_FILE = LANDING_DIR / "lichess_sample.parquet"
TMP_DIR = DATA_DIR / "tmp"            # nơi tải tạm từng file, xóa ngay sau khi lấy mẫu
DB_PATH = DATA_DIR / "chess.duckdb"

# ---------- Nguồn 1: Lichess trên Hugging Face ----------
HF_REPO = "Lichess/standard-chess-games"
MONTH_FILTER = "year=2025/month=09"   # tên thư mục của tháng cần lấy
N_SHARDS = 10                         # số file Parquet lấy, rải đều từ đầu đến cuối tháng
SAMPLE_ROWS = 400_000                 # tổng số ván giữ lại (chia đều cho các file)
SAMPLE_SEED = 42                      # cố định để chạy lại ra cùng mẫu
MAX_DOWNLOAD_GB = 12                  # vượt ngưỡng này sẽ hỏi xác nhận trước khi tải

# Cố ý KHÔNG lấy ECO và Opening (ngoài phạm vi đề tài)
SAMPLE_COLUMNS = [
    "Event", "Site", "White", "Black", "Result", "WhiteTitle", "BlackTitle",
    "WhiteElo", "BlackElo", "WhiteRatingDiff", "BlackRatingDiff",
    "UTCDate", "UTCTime", "Termination", "TimeControl", "movetext",
]