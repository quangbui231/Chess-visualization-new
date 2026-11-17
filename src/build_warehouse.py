"""Nạp mẫu Lichess vào DuckDB, làm sạch có báo cáo, tạo cột và chỉ số mới.

Các tầng trong kho (data/chess.duckdb):
  raw.lichess_games     dữ liệu đúng như file mẫu, thêm cột nguồn và thời điểm nạp
  staging.games         dữ liệu đã làm sạch, mỗi dòng là một ván, kèm cột dẫn xuất
  staging.cleaning_report  số dòng bị loại theo từng quy tắc
"""
import duckdb

import config

# ---------------------------------------------------------------------------
# Các biểu thức SQL dùng chung (viết thường, không dùng f-string để khỏi lẫn dấu {})
# ---------------------------------------------------------------------------

# Số nửa nước đi (ply) trong movetext: bỏ chú thích {...}, số nước đi, ký hiệu $n
# và kết quả cuối ván, rồi đếm số token còn lại.
PLY_EXPR = r"""
CASE WHEN movetext IS NULL THEN 0 ELSE
  CASE WHEN trim(regexp_replace(regexp_replace(regexp_replace(regexp_replace(
         movetext, '[{][^}]*[}]', ' ', 'g'),
         '[$][0-9]+', ' ', 'g'),
         '[0-9]+[.]+', ' ', 'g'),
         '(1-0|0-1|1/2-1/2|[*])\s*$', '')) = ''
       THEN 0
  ELSE len(string_split_regex(trim(regexp_replace(regexp_replace(regexp_replace(regexp_replace(
         movetext, '[{][^}]*[}]', ' ', 'g'),
         '[$][0-9]+', ' ', 'g'),
         '[0-9]+[.]+', ' ', 'g'),
         '(1-0|0-1|1/2-1/2|[*])\s*$', '')), '\s+'))
  END
END
"""

SPEED_EXPR = """
CASE WHEN Event ILIKE '%UltraBullet%' THEN 'UltraBullet'
     WHEN Event ILIKE '%Bullet%'      THEN 'Bullet'
     WHEN Event ILIKE '%Blitz%'       THEN 'Blitz'
     WHEN Event ILIKE '%Rapid%'       THEN 'Rapid'
     WHEN Event ILIKE '%Classical%'   THEN 'Classical'
     WHEN Event ILIKE '%Correspondence%' THEN 'Correspondence'
     ELSE 'Other' END
"""

# Quy tắc làm sạch: (tên quy tắc, điều kiện để LOẠI dòng). Áp dụng lần lượt.
CLEANING_RULES = [
    ("Không có kết quả hợp lệ (Result không phải 1-0, 0-1, 1/2-1/2)",
     "Result IS NULL OR Result NOT IN ('1-0', '0-1', '1/2-1/2')"),
    ("Có bot ở một trong hai bên",
     "COALESCE(WhiteTitle, '') = 'BOT' OR COALESCE(BlackTitle, '') = 'BOT'"),
    ("Thiếu hoặc sai Elo",
     "WhiteElo IS NULL OR BlackElo IS NULL OR WhiteElo <= 0 OR BlackElo <= 0"),
    ("Thiếu ngày giờ",
     "UTCDate IS NULL OR UTCTime IS NULL"),
    ("Thể thức hoặc đồng hồ không xác định",
     "speed = 'Other' OR speed = 'Correspondence' OR base_seconds IS NULL"),
    ("Ván không có nước đi nào",
     "total_plies = 0"),
    ("Trùng game_id (giữ một dòng)",
     "rowid IN (SELECT rowid FROM (SELECT rowid, row_number() OVER "
     "(PARTITION BY game_id ORDER BY rowid) AS rn FROM work) WHERE rn > 1)"),
]


def load_raw(con):
    if not config.SAMPLE_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy mẫu dữ liệu: {config.SAMPLE_FILE}. "
            "Hãy chạy `python src/ingest.py` trước."
        )
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE SCHEMA IF NOT EXISTS staging")
    sample = config.SAMPLE_FILE.as_posix()
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.lichess_games AS
        SELECT *, 'lichess_hf' AS source, now() AS loaded_at
        FROM read_parquet('{sample}')
    """)
    n = con.execute("SELECT count(*) FROM raw.lichess_games").fetchall()[0][0]
    print(f"[raw] Đã nạp {n:,} ván vào raw.lichess_games")
    return n


def clean(con, n_input):
    if n_input <= 0:
        raise ValueError("Dữ liệu đầu vào không có bản ghi.")
    # Bảng làm việc: thêm các cột cần để đánh giá quy tắc
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE work AS
        SELECT *,
               regexp_extract(Site, '([A-Za-z0-9]+)$', 1)        AS game_id,
               {SPEED_EXPR}                                       AS speed,
               TRY_CAST(split_part(TimeControl, '+', 1) AS INTEGER) AS base_seconds,
               TRY_CAST(split_part(TimeControl, '+', 2) AS INTEGER) AS increment_seconds,
               {PLY_EXPR}                                          AS total_plies
        FROM raw.lichess_games
    """)

    report = [(0, "Đầu vào (raw.lichess_games)", 0, n_input, 0.0)]
    remaining = n_input
    for step, (name, cond) in enumerate(CLEANING_RULES, 1):
        removed = con.execute(
            f"SELECT count(*) FROM work WHERE COALESCE(({cond}), false)"
        ).fetchall()[0][0]
        if removed:
            con.execute(f"DELETE FROM work WHERE COALESCE(({cond}), false)")
        remaining -= removed
        report.append((step, name, removed, remaining, 100.0 * removed / n_input))

    con.execute("""
        CREATE OR REPLACE TABLE staging.cleaning_report (
            step INTEGER, rule VARCHAR, rows_removed BIGINT,
            rows_remaining BIGINT, pct_of_input DOUBLE)
    """)
    con.executemany("INSERT INTO staging.cleaning_report VALUES (?, ?, ?, ?, ?)", report)
    return remaining


def build_features(con):
    con.execute("""
        CREATE OR REPLACE TABLE staging.games AS
        SELECT
            game_id,
            UTCDate + UTCTime                                  AS played_at,
            UTCDate                                            AS date_utc,
            hour(UTCTime)                                      AS hour_utc,
            speed,
            Event ILIKE '%tournament%'                         AS is_tournament,
            TimeControl                                        AS time_control,
            base_seconds,
            increment_seconds,
            White                                              AS white,
            Black                                              AS black,
            WhiteElo                                           AS white_elo,
            BlackElo                                           AS black_elo,
            (WhiteElo + BlackElo) / 2.0                        AS avg_rating,
            WhiteElo - BlackElo                                AS rating_diff,
            abs(WhiteElo - BlackElo)                           AS abs_rating_diff,
            CASE WHEN abs(WhiteElo - BlackElo) < 50  THEN '0-49'
                 WHEN abs(WhiteElo - BlackElo) < 100 THEN '50-99'
                 WHEN abs(WhiteElo - BlackElo) < 200 THEN '100-199'
                 WHEN abs(WhiteElo - BlackElo) < 400 THEN '200-399'
                 ELSE '400+' END                               AS rating_gap_group,
            CASE WHEN (WhiteElo + BlackElo) / 2.0 < 1200 THEN '<1200'
                 WHEN (WhiteElo + BlackElo) / 2.0 < 1500 THEN '1200-1499'
                 WHEN (WhiteElo + BlackElo) / 2.0 < 1800 THEN '1500-1799'
                 WHEN (WhiteElo + BlackElo) / 2.0 < 2100 THEN '1800-2099'
                 ELSE '2100+' END                              AS rating_band,
            CASE WHEN WhiteElo > BlackElo THEN 'white'
                 WHEN WhiteElo < BlackElo THEN 'black'
                 ELSE 'equal' END                              AS higher_rated_side,
            Result                                             AS result,
            CASE Result WHEN '1-0' THEN 'white'
                        WHEN '0-1' THEN 'black'
                        ELSE 'draw' END                        AS winner,
            CASE Result WHEN '1-0' THEN 1.0
                        WHEN '0-1' THEN 0.0
                        ELSE 0.5 END                           AS white_score,
            Termination                                        AS termination,
            Termination = 'Time forfeit'                       AS is_time_forfeit,
            Termination IN ('Normal', 'Time forfeit',
                            'Insufficient material')           AS is_complete_game,
            total_plies,
            (total_plies + 1) // 2                             AS total_moves,
            source
        FROM work
    """)
    # Điểm số của bên có rating cao hơn (NULL nếu hai bên bằng Elo)
    con.execute("""
        ALTER TABLE staging.games ADD COLUMN higher_rated_score DOUBLE;
        UPDATE staging.games SET higher_rated_score =
            CASE higher_rated_side WHEN 'white' THEN white_score
                                   WHEN 'black' THEN 1.0 - white_score
                                   ELSE NULL END;
    """)


def check_quality(con, n_input):
    """Kiểm tra các điều kiện bắt buộc của dữ liệu sau làm sạch. Lỗi thì dừng."""
    q = lambda sql: con.execute(sql).fetchall()[0][0]
    n = q("SELECT count(*) FROM staging.games")
    removed = q("SELECT sum(rows_removed) FROM staging.cleaning_report")
    checks = [
        ("Số dòng đầu vào = số dòng còn lại + số dòng bị loại", n_input == n + removed),
        ("game_id không trùng", q("SELECT count(DISTINCT game_id) FROM staging.games") == n),
        ("Không có game_id rỗng", q("SELECT count(*) FROM staging.games WHERE game_id IS NULL OR game_id = ''") == 0),
        ("Kết quả chỉ gồm white/black/draw",
         q("SELECT count(*) FROM staging.games WHERE winner NOT IN ('white','black','draw')") == 0),
        ("Elo hợp lệ (> 0)", q("SELECT count(*) FROM staging.games WHERE white_elo <= 0 OR black_elo <= 0") == 0),
        ("Mọi ván có ít nhất 1 nước đi", q("SELECT count(*) FROM staging.games WHERE total_plies < 1") == 0),
        ("Không còn ván của bot",
         q("SELECT count(*) FROM raw.lichess_games r JOIN staging.games s "
           "ON regexp_extract(r.Site, '([A-Za-z0-9]+)$', 1) = s.game_id "
           "WHERE r.WhiteTitle = 'BOT' OR r.BlackTitle = 'BOT'") == 0),
    ]
    print("\n[kiểm tra chất lượng]")
    ok = True
    for name, passed in checks:
        print(f"  {'ĐẠT ' if passed else 'LỖI '} {name}")
        ok &= bool(passed)
    if not ok:
        raise SystemExit("Có kiểm tra không đạt, hãy xem lại dữ liệu hoặc quy tắc làm sạch.")


def main():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(config.DB_PATH))
    n_input = load_raw(con)
    n_clean = clean(con, n_input)
    build_features(con)

    print("\n[báo cáo làm sạch]")
    con.sql("""
        SELECT step AS buoc, rule AS quy_tac, rows_removed AS so_dong_loai,
               rows_remaining AS con_lai, round(pct_of_input, 3) AS pct_dau_vao
        FROM staging.cleaning_report ORDER BY step
    """).show(max_width=200)

    report_csv = (config.DATA_DIR / "cleaning_report.csv").as_posix()
    con.execute(f"COPY staging.cleaning_report TO '{report_csv}' (HEADER, DELIMITER ',')")
    print("Đã lưu báo cáo:", report_csv)

    check_quality(con, n_input)

    print("\n[tóm tắt staging.games]")
    con.sql("""
        SELECT speed AS the_thuc, count(*) AS so_van,
               round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct,
               round(avg(white_score), 4) AS diem_trung_binh_cua_trang
        FROM staging.games GROUP BY 1 ORDER BY so_van DESC
    """).show()
    print(f"Hoàn tất: {n_input:,} ván đầu vào, {n_clean:,} ván sau làm sạch.")
    con.close()


if __name__ == "__main__":
    main()
