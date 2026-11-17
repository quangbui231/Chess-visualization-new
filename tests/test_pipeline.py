"""Kiểm thử pipeline trên Parquet tổng hợp nhỏ, không cần kho dữ liệu cục bộ."""
import io
import sys
from datetime import date, time
from pathlib import Path

import chess.pgn
import duckdb
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import build_warehouse as warehouse  # noqa: E402
import config  # noqa: E402


def game_row(game_id, event, result, termination="Normal", white_title="",
             white_elo=1500, black_elo=1500, movetext=None):
    movetext = movetext or f"1. e4 e5 2. Nf3 Nc6 {result}"
    return {
        "Event": event,
        "Site": f"https://lichess.org/{game_id}",
        "White": "Player A",
        "Black": "Player B",
        "Result": result,
        "WhiteTitle": white_title,
        "BlackTitle": "",
        "WhiteElo": white_elo,
        "BlackElo": black_elo,
        "WhiteRatingDiff": 0,
        "BlackRatingDiff": 0,
        "UTCDate": date(2025, 9, 3),
        "UTCTime": time(12, 30, 0),
        "Termination": termination,
        "TimeControl": "180+2",
        "movetext": movetext,
    }


@pytest.fixture
def built_warehouse(tmp_path, monkeypatch):
    rows = [
        game_row("game001", "Rated Blitz tournament https://lichess.org/tournament/test",
                 "1-0", white_elo=1600, black_elo=1500),
        game_row("game002", "Rated Blitz game", "0-1", white_elo=1500, black_elo=1600),
        game_row("game003", "Rated Bullet game", "1/2-1/2", "Time forfeit"),
        game_row("game001", "Rated Blitz game", "1-0"),  # duplicate ID
        game_row("game004", "Rated Blitz game", "*"),  # invalid result
        game_row("game005", "Rated Blitz game", "1-0", white_title="BOT"),
    ]
    sample_path = tmp_path / "sample.parquet"
    pd.DataFrame(rows).to_parquet(sample_path, index=False)
    monkeypatch.setattr(config, "SAMPLE_FILE", sample_path)

    con = duckdb.connect(":memory:")
    n_input = warehouse.load_raw(con)
    n_clean = warehouse.clean(con, n_input)
    warehouse.build_features(con)
    warehouse.check_quality(con, n_input)
    yield con, n_input, n_clean
    con.close()


def test_cleaning_reconciles_input_and_output(built_warehouse):
    con, n_input, n_clean = built_warehouse
    n_output = con.execute("SELECT count(*) FROM staging.games").fetchone()[0]
    removed = con.execute(
        "SELECT sum(rows_removed) FROM staging.cleaning_report"
    ).fetchone()[0]

    assert n_input == 6
    assert n_clean == n_output == 3
    assert n_input == n_output + removed


def test_game_ids_are_unique_and_results_valid(built_warehouse):
    con, _, _ = built_warehouse
    n, distinct_ids = con.execute(
        "SELECT count(*), count(DISTINCT game_id) FROM staging.games"
    ).fetchone()
    bad = con.execute("""
        SELECT count(*) FROM staging.games
        WHERE winner NOT IN ('white', 'black', 'draw')
           OR white_elo <= 0 OR black_elo <= 0
    """).fetchone()[0]

    assert n == distinct_ids == 3
    assert bad == 0


def test_tournament_flag_and_time_features_are_built(built_warehouse):
    con, _, _ = built_warehouse
    tournament_n, clock_n = con.execute("""
        SELECT count(*) FILTER (WHERE is_tournament),
               count(*) FILTER (WHERE base_seconds = 180 AND increment_seconds = 2)
        FROM staging.games
    """).fetchone()

    assert tournament_n == 1
    assert clock_n == 3


def test_ply_count_matches_python_chess(built_warehouse):
    con, _, _ = built_warehouse
    rows = con.execute("""
        SELECT s.game_id, s.total_plies, r.movetext
        FROM staging.games s
        JOIN raw.lichess_games r
          ON regexp_extract(r.Site, '([A-Za-z0-9]+)$', 1) = s.game_id
        QUALIFY row_number() OVER (PARTITION BY s.game_id ORDER BY r.rowid) = 1
    """).fetchall()

    for _, plies, movetext in rows:
        game = chess.pgn.read_game(io.StringIO(movetext))
        assert sum(1 for _ in game.mainline_moves()) == plies
