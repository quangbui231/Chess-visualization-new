"""Lấy mẫu ngẫu nhiên ván cờ Lichess từ Hugging Face và lưu vào data/landing/.

Mỗi file Parquet của Hugging Face chỉ chứa một lát thời gian ngắn (khoảng nửa ngày),
nên phải lấy nhiều file rải đều từ đầu đến cuối tháng thì mẫu mới đại diện cho cả tháng.
Để tiết kiệm ổ đĩa, từng file được tải, lấy mẫu rồi xóa ngay.
"""
import os
import shutil

import duckdb
from huggingface_hub import HfApi, hf_hub_download

import config


def pick_shards():
    api = HfApi()
    all_files = sorted(
        f for f in api.list_repo_files(config.HF_REPO, repo_type="dataset")
        if f.endswith(".parquet")
    )
    files = [f for f in all_files if config.MONTH_FILTER in f]
    if not files:
        print(f"Không có file nào khớp MONTH_FILTER = '{config.MONTH_FILTER}'.")
        print("Một vài đường dẫn thật trong repo, hãy chép đúng phần tên thư mục:")
        for f in all_files[:15]:
            print("  ", f)
        raise SystemExit(1)

    n = min(config.N_SHARDS, len(files))
    if n == 1:
        return files[:1]
    # chọn n file cách đều, có cả file đầu và file cuối của tháng
    idx = sorted({round(i * (len(files) - 1) / (n - 1)) for i in range(n)})
    return [files[i] for i in idx]


def confirm_size(chosen):
    """In dung lượng các file sắp tải; hỏi xác nhận nếu quá lớn."""
    try:
        infos = HfApi().get_paths_info(config.HF_REPO, chosen, repo_type="dataset")
        total_gb = sum((i.size or 0) for i in infos) / 1e9
    except Exception:
        print("Không lấy được dung lượng file, bỏ qua bước kiểm tra.")
        return
    print(f"Sẽ tải {len(chosen)} file, tổng khoảng {total_gb:.2f} GB (tải lần lượt, xóa sau mỗi file)")
    if total_gb > config.MAX_DOWNLOAD_GB:
        if input("Dung lượng lớn. Tiếp tục? (y/n): ").strip().lower() != "y":
            raise SystemExit("Đã hủy. Hãy giảm N_SHARDS trong config.py.")


def sample(chosen):
    if not chosen:
        raise ValueError("Không có shard nào được chọn để lấy mẫu.")

    config.LANDING_DIR.mkdir(parents=True, exist_ok=True)
    config.TMP_DIR.mkdir(parents=True, exist_ok=True)
    cols = ", ".join(config.SAMPLE_COLUMNS)
    if config.SAMPLE_ROWS <= 0:
        raise ValueError("SAMPLE_ROWS phải lớn hơn 0.")

    base_rows, remainder = divmod(config.SAMPLE_ROWS, len(chosen))
    shard_sizes = [base_rows + (i < remainder) for i in range(len(chosen))]
    parts = []

    try:
        for i, (f, shard_rows) in enumerate(zip(chosen, shard_sizes), 1):
            print(f"[{i}/{len(chosen)}] Tải {f}")
            local = hf_hub_download(
                config.HF_REPO, f, repo_type="dataset", local_dir=config.TMP_DIR
            )
            part = (config.TMP_DIR / f"part_{i:02d}.parquet").as_posix()
            src = str(local).replace("\\", "/")
            duckdb.sql(f"""
                COPY (
                    SELECT {cols} FROM read_parquet('{src}')
                    USING SAMPLE reservoir({shard_rows} ROWS)
                    REPEATABLE ({config.SAMPLE_SEED + i})
                ) TO '{part}' (FORMAT PARQUET)
            """)
            parts.append(part)
            try:
                os.remove(local)
            except OSError:
                pass

        part_list = "[" + ",".join(f"'{p}'" for p in parts) + "]"
        out = config.SAMPLE_FILE.as_posix()
        duckdb.sql(f"COPY (SELECT * FROM read_parquet({part_list})) TO '{out}' (FORMAT PARQUET)")
        print("Đã lưu:", out)
    finally:
        shutil.rmtree(config.TMP_DIR, ignore_errors=True)


def describe(path=None):
    """Kiểm tra nhanh mẫu vừa lấy."""
    p = (path or config.SAMPLE_FILE).as_posix()
    show = lambda title, sql: (print(f"\n--- {title} ---"), duckdb.sql(sql).show(max_rows=40))

    show("Số ván và khoảng ngày",
         f"SELECT count(*) AS so_van, count(DISTINCT UTCDate) AS so_ngay, "
         f"min(UTCDate) AS tu_ngay, max(UTCDate) AS den_ngay FROM '{p}'")
    show("Số ván theo ngày",
         f"SELECT UTCDate, count(*) n FROM '{p}' GROUP BY 1 ORDER BY 1")
    show("Số ván theo giờ trong ngày (UTC)",
         f"SELECT hour(UTCTime) AS gio, count(*) n FROM '{p}' GROUP BY 1 ORDER BY 1")
    show("Termination",
         f"SELECT Termination, count(*) n FROM '{p}' GROUP BY 1 ORDER BY n DESC")
    show("Result",
         f"SELECT Result, count(*) n FROM '{p}' GROUP BY 1 ORDER BY n DESC")
    show("TimeControl (top 10)",
         f"SELECT TimeControl, count(*) n FROM '{p}' GROUP BY 1 ORDER BY n DESC LIMIT 10")
    show("Elo: thiếu và khoảng giá trị",
         f"""SELECT count(*) FILTER (WHERE WhiteElo IS NULL) AS thieu_white_elo,
                    count(*) FILTER (WHERE BlackElo IS NULL) AS thieu_black_elo,
                    min(WhiteElo) AS min_elo, max(WhiteElo) AS max_elo FROM '{p}'""")


if __name__ == "__main__":
    chosen = pick_shards()
    print("Các file được chọn:", *chosen, sep="\n  ")
    confirm_size(chosen)
    sample(chosen)
    describe()
