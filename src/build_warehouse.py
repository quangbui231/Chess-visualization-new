
"""Nạp dữ liệu Lichess vào DuckDB, làm sạch và tạo các chỉ số phân tích.

Các tầng dữ liệu:
  raw.lichess_games        Dữ liệu nguồn
  work                     Bảng tạm phục vụ làm sạch
  staging.games            Dữ liệu đã xử lý
  staging.cleaning_report  Báo cáo làm sạch
"""

import duckdb
import config


# Đếm số nửa nước đi sau khi loại chú thích, số thứ tự và kết quả cuối ván.
PLY_EXPR = r"""
CASE
    WHEN movetext IS NULL
         OR trim(regexp_replace(
             regexp_replace(
                 regexp_replace(
                     regexp_replace(movetext, '[{][^}]*[}]', ' ', 'g'),
                     '[$][0-9]+', ' ', 'g'
                 ),
                 '[0-9]+[.]+', ' ', 'g'
             ),
             '(1-0|0-1|1/2-1/2|[*])\s*$', ''
         )) = ''
    THEN 0
    ELSE len(string_split_regex(
        trim(regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(movetext, '[{][^}]*[}]', ' ', 'g'),
                    '[$][0-9]+', ' ', 'g'
                ),
                '[0-9]+[.]+', ' ', 'g'
            ),
            '(1-0|0-1|1/2-1/2|[*])\s*$', ''
        )),
        '\s+'
    ))
END
"""

# Phân loại thể thức.
SPEED_EXPR = """
CASE
    WHEN Event ILIKE '%UltraBullet%' THEN 'UltraBullet'
    WHEN Event ILIKE '%Bullet%' THEN 'Bullet'
    WHEN Event ILIKE '%Blitz%' THEN 'Blitz'
    WHEN Event ILIKE '%Rapid%' THEN 'Rapid'
    WHEN Event ILIKE '%Classical%' THEN 'Classical'
    WHEN Event ILIKE '%Correspondence%' THEN 'Correspondence'
    ELSE 'Other'
END
"""

# Các điều kiện loại dữ liệu, áp dụng lần lượt.
CLEANING_RULES = [
    ("Không có kết quả hợp lệ",
     "Result IS NULL OR Result NOT IN ('1-0', '0-1', '1/2-1/2')"),

    ("Có bot ở một trong hai bên",
     "COALESCE(WhiteTitle, '') = 'BOT' OR COALESCE(BlackTitle, '') = 'BOT'"),

    ("Thiếu hoặc sai Elo",
     "WhiteElo IS NULL OR BlackElo IS NULL OR WhiteElo <= 0 OR BlackElo <= 0"),

    ("Thiếu ngày giờ",
     "UTCDate IS NULL OR UTCTime IS NULL"),

    ("Thiếu game_id",
     "game_id IS NULL OR trim(game_id) = ''"),

    ("Thể thức hoặc đồng hồ không xác định",
     "speed IN ('Other', 'Correspondence') OR base_seconds IS NULL"),

    ("Ván không có nước đi nào",
     "total_plies = 0"),

    ("Trùng game_id (giữ một dòng)",
     """rowid IN (
         SELECT rowid FROM (
             SELECT rowid,
                    row_number() OVER (
                        PARTITION BY game_id ORDER BY rowid
                    ) AS rn
             FROM work
         )
         WHERE rn > 1
     )"""),
]


def load_raw(con):
    """Nạp dữ liệu Parquet vào tầng raw."""

    if not config.SAMPLE_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy dữ liệu: {config.SAMPLE_FILE}. "
            "Hãy chạy python src/ingest.py trước."
        )

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE SCHEMA IF NOT EXISTS staging")

    sample = config.SAMPLE_FILE.as_posix()

    con.execute(f"""
        CREATE OR REPLACE TABLE raw.lichess_games AS
        SELECT *, 'lichess_hf' AS source, now() AS loaded_at
        FROM read_parquet('{sample}')
    """)

    n = con.execute(
        "SELECT count(*) FROM raw.lichess_games"
    ).fetchone()[0]

    print(f"[raw] Đã nạp {n:,} ván vào raw.lichess_games")
    return n


def clean(con, n_input):
    """Làm sạch dữ liệu và tạo báo cáo số dòng bị loại."""

    if n_input <= 0:
        raise ValueError("Dữ liệu đầu vào không có bản ghi.")

    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE work AS
        SELECT *,
               regexp_extract(Site, '([A-Za-z0-9]+)$', 1) AS game_id,
               {SPEED_EXPR} AS speed,
               TRY_CAST(split_part(TimeControl, '+', 1) AS INTEGER) AS base_seconds,
               TRY_CAST(split_part(TimeControl, '+', 2) AS INTEGER) AS increment_seconds,
               {PLY_EXPR} AS total_plies
        FROM raw.lichess_games
    """)

    report = [(0, "Đầu vào (raw.lichess_games)", 0, n_input, 0.0)]
    remaining = n_input

    for step, (name, condition) in enumerate(CLEANING_RULES, start=1):
        condition = f"COALESCE(({condition}), FALSE)"

        removed = con.execute(
            f"SELECT count(*) FROM work WHERE {condition}"
        ).fetchone()[0]

        if removed:
            con.execute(f"DELETE FROM work WHERE {condition}")

        remaining -= removed
        report.append((
            step, name, removed, remaining,
            100.0 * removed / n_input
        ))

    con.execute("""
        CREATE OR REPLACE TABLE staging.cleaning_report (
            step INTEGER,
            rule VARCHAR,
            rows_removed BIGINT,
            rows_remaining BIGINT,
            pct_of_input DOUBLE
        )
    """)

    con.executemany(
        "INSERT INTO staging.cleaning_report VALUES (?, ?, ?, ?, ?)",
        report
    )

    return remaining


def build_features(con):
    """Tạo bảng staging.games và các cột phục vụ phân tích."""

    con.execute("""
        CREATE OR REPLACE TABLE staging.games AS
        SELECT
            game_id,
            UTCDate + UTCTime AS played_at,
            UTCDate AS date_utc,
            hour(UTCTime) AS hour_utc,

            speed,
            Event ILIKE '%tournament%' AS is_tournament,
            TimeControl AS time_control,

            White AS white,
            Black AS black,
            WhiteElo AS white_elo,
            BlackElo AS black_elo,

            (WhiteElo + BlackElo) / 2.0 AS avg_rating,
            abs(WhiteElo - BlackElo) AS abs_rating_diff,

            CASE
                WHEN abs(WhiteElo - BlackElo) < 50 THEN '0-49'
                WHEN abs(WhiteElo - BlackElo) < 100 THEN '50-99'
                WHEN abs(WhiteElo - BlackElo) < 200 THEN '100-199'
                WHEN abs(WhiteElo - BlackElo) < 400 THEN '200-399'
                ELSE '400+'
            END AS rating_gap_group,

            CASE
                WHEN (WhiteElo + BlackElo) / 2.0 < 1200 THEN '<1200'
                WHEN (WhiteElo + BlackElo) / 2.0 < 1500 THEN '1200-1499'
                WHEN (WhiteElo + BlackElo) / 2.0 < 1800 THEN '1500-1799'
                WHEN (WhiteElo + BlackElo) / 2.0 < 2100 THEN '1800-2099'
                ELSE '2100+'
            END AS rating_band,

            CASE
                WHEN WhiteElo > BlackElo THEN 'white'
                WHEN WhiteElo < BlackElo THEN 'black'
                ELSE 'equal'
            END AS higher_rated_side,

            Result AS result,

            CASE Result
                WHEN '1-0' THEN 'white'
                WHEN '0-1' THEN 'black'
                ELSE 'draw'
            END AS winner,

            CASE Result
                WHEN '1-0' THEN 1.0
                WHEN '0-1' THEN 0.0
                ELSE 0.5
            END AS white_score,

            Termination AS termination,

            COALESCE(
                Termination = 'Time forfeit', FALSE
            ) AS is_time_forfeit,

            COALESCE(
                Termination IN (
                    'Normal', 'Time forfeit', 'Insufficient material'
                ),
                FALSE
            ) AS is_complete_game,

            (total_plies + 1) // 2 AS total_moves,
            source

        FROM work
    """)

    con.execute("""
        ALTER TABLE staging.games
        ADD COLUMN higher_rated_score DOUBLE
    """)

    con.execute("""
        UPDATE staging.games
        SET higher_rated_score =
            CASE higher_rated_side
                WHEN 'white' THEN white_score
                WHEN 'black' THEN 1.0 - white_score
                ELSE NULL
            END
    """)


def check_quality(con, n_input, n_clean):
    """Kiểm tra chất lượng dữ liệu sau khi xử lý."""

    def count(sql):
        return con.execute(sql).fetchone()[0]

    n = count("SELECT count(*) FROM staging.games")
    removed = count(
        "SELECT COALESCE(sum(rows_removed), 0) "
        "FROM staging.cleaning_report"
    )

    checks = [
        ("Đối chiếu số dòng đầu vào",
         n_input == n + removed),

        ("Số dòng staging khớp kết quả làm sạch",
         n == n_clean),

        ("game_id không trùng",
         count("SELECT count(DISTINCT game_id) FROM staging.games") == n),

        ("Không có game_id NULL hoặc rỗng",
         count("""SELECT count(*) FROM staging.games
                  WHERE game_id IS NULL OR trim(game_id) = ''""") == 0),

        ("Winner hợp lệ",
         count("""SELECT count(*) FROM staging.games
                  WHERE winner IS NULL
                     OR winner NOT IN ('white', 'black', 'draw')""") == 0),

        ("Elo hợp lệ",
         count("""SELECT count(*) FROM staging.games
                  WHERE white_elo IS NULL OR black_elo IS NULL
                     OR white_elo <= 0 OR black_elo <= 0""") == 0),

        ("Mọi ván có ít nhất một nước đi",
         count("""SELECT count(*) FROM staging.games
                  WHERE total_moves IS NULL OR total_moves < 1""") == 0),

        ("Hai cột Boolean không chứa NULL",
         count("""SELECT count(*) FROM staging.games
                  WHERE is_time_forfeit IS NULL
                     OR is_complete_game IS NULL""") == 0),

        ("Điểm số bên trắng nằm trong khoảng 0 đến 1",
         count("""SELECT count(*) FROM staging.games
                  WHERE white_score IS NULL
                     OR white_score < 0 OR white_score > 1""") == 0),

        ("Không còn ván của bot",
         count("""SELECT count(*) FROM work
                  WHERE COALESCE(WhiteTitle, '') = 'BOT'
                     OR COALESCE(BlackTitle, '') = 'BOT'""") == 0),
    ]

    print("\n[kiểm tra chất lượng dữ liệu]")
    all_passed = True

    for name, passed in checks:
        print(f"  [{'ĐẠT' if passed else 'LỖI'}] {name}")
        all_passed = all_passed and bool(passed)

    if not all_passed:
        raise SystemExit("Có kiểm tra không đạt. Hãy kiểm tra lại dữ liệu.")

    print("Tất cả kiểm tra chất lượng đều đạt.")


def main():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(config.DB_PATH))

    try:
        n_input = load_raw(con)
        n_clean = clean(con, n_input)
        build_features(con)

        # In và xuất báo cáo làm sạch.
        print("\n[báo cáo làm sạch]")
        report = con.execute("""
            SELECT step AS buoc,
                   rule AS quy_tac,
                   rows_removed AS so_dong_loai,
                   rows_remaining AS con_lai,
                   round(pct_of_input, 3) AS pct_dau_vao
            FROM staging.cleaning_report
            ORDER BY step
        """).fetchdf()

        print(report.to_string(index=False))

        report_csv = (config.DATA_DIR / "cleaning_report.csv").as_posix()
        con.execute(
            f"COPY staging.cleaning_report TO '{report_csv}' "
            "(HEADER, DELIMITER ',')"
        )
        print("Đã lưu báo cáo:", report_csv)

        check_quality(con, n_input, n_clean)

        # Thống kê theo thể thức.
        print("\n[tóm tắt staging.games]")
        summary = con.execute("""
            SELECT
                speed AS the_thuc,
                count(*) AS so_van,
                round(
                    100.0 * count(*) / sum(count(*)) OVER (), 2
                ) AS pct,
                round(avg(white_score), 4) AS diem_trung_binh_cua_trang
            FROM staging.games
            GROUP BY speed
            ORDER BY so_van DESC
        """).fetchdf()

        print(summary.to_string(index=False))

        print(
            f"\nHoàn tất: {n_input:,} ván đầu vào, "
            f"{n_clean:,} ván sau làm sạch."
        )

    finally:
        con.close()


if __name__ == "__main__":
    main()
