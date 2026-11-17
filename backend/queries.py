"""Read-only SQL for KPIs and the seven existing research questions."""

from __future__ import annotations

from typing import Any

import duckdb

from .database import fetch_rows
from .filters import BAND_ORDER, GAP_ORDER, MIN_GROUP_SIZE, SPEED_ORDER, FilterSpec


def get_filter_options(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    speeds = fetch_rows(connection, "SELECT DISTINCT speed FROM staging.games")
    bands = fetch_rows(connection, "SELECT DISTINCT rating_band FROM staging.games")
    actual_speeds = {row["speed"] for row in speeds}
    actual_bands = {row["rating_band"] for row in bands}
    return {
        "speed": [value for value in SPEED_ORDER if value in actual_speeds],
        "rating_band": [value for value in BAND_ORDER if value in actual_bands],
        "game_type": [
            {"value": "all", "label": "Tất cả"},
            {"value": "tournament", "label": "Chỉ giải đấu"},
            {"value": "non_tournament", "label": "Không giải đấu"},
        ],
    }


def get_overview_kpis(connection: duckdb.DuckDBPyConnection, filters: FilterSpec) -> dict[str, Any]:
    rows = fetch_rows(
        connection,
        f"""
        SELECT count(*) AS n,
               avg((winner = 'white')::INT) AS white_win,
               avg((winner = 'black')::INT) AS black_win,
               avg((winner = 'draw')::INT) AS draw,
               median(total_moves) AS med_moves
        FROM staging.games {filters.where_sql}
        """,
        filters.params,
    )
    return rows[0]


def get_rq1(connection: duckdb.DuckDBPyConnection, filters: FilterSpec) -> list[dict[str, Any]]:
    rows = fetch_rows(
        connection,
        f"""
        SELECT speed, count(*) AS n
        FROM staging.games {filters.where_sql}
        GROUP BY speed
        ORDER BY n DESC
        """,
        filters.params,
    )
    total = sum(row["n"] for row in rows)
    for row in rows:
        row["share"] = row["n"] / total if total else 0.0
    return rows


def get_rq2(connection: duckdb.DuckDBPyConnection, filters: FilterSpec) -> list[dict[str, Any]]:
    return fetch_rows(
        connection,
        f"""
        SELECT floor(avg_rating / 50) * 50 AS rating_bin,
               count(*) AS n
        FROM staging.games {filters.where_sql}
        GROUP BY 1
        ORDER BY 1
        """,
        filters.params,
    )


def get_rq3(
    connection: duckdb.DuckDBPyConnection,
    filters: FilterSpec,
    *,
    complete_only: bool = True,
) -> list[dict[str, Any]]:
    effective = _with_complete_filter(filters, complete_only)
    rows = fetch_rows(
        connection,
        f"""
        SELECT rating_gap_group,
               count(*) AS n,
               avg(higher_rated_score) AS score,
               coalesce(stddev_samp(higher_rated_score), 0) AS sd
        FROM staging.games {effective.where_sql}
          AND higher_rated_side <> 'equal'
        GROUP BY rating_gap_group
        HAVING count(*) >= {MIN_GROUP_SIZE}
        """,
        effective.params,
    )
    for row in rows:
        row["ci"] = 1.96 * row["sd"] / row["n"] ** 0.5
    return sorted(rows, key=lambda row: GAP_ORDER.index(row["rating_gap_group"]))


def get_rq4(
    connection: duckdb.DuckDBPyConnection,
    filters: FilterSpec,
    *,
    complete_only: bool = True,
) -> list[dict[str, Any]]:
    effective = _with_complete_filter(filters, complete_only)
    rows = fetch_rows(
        connection,
        f"""
        SELECT speed,
               count(*) AS n,
               avg(white_score) AS score,
               coalesce(stddev_samp(white_score), 0) AS sd
        FROM staging.games {effective.where_sql}
          AND abs_rating_diff < 100
        GROUP BY speed
        HAVING count(*) >= {MIN_GROUP_SIZE}
        """,
        effective.params,
    )
    for row in rows:
        row["ci"] = 1.96 * row["sd"] / row["n"] ** 0.5
    return sorted(rows, key=lambda row: SPEED_ORDER.index(row["speed"]))


def get_rq5(
    connection: duckdb.DuckDBPyConnection,
    filters: FilterSpec,
    *,
    complete_only: bool = True,
) -> list[dict[str, Any]]:
    effective = _with_complete_filter(filters, complete_only)
    rows = fetch_rows(
        connection,
        f"""
        SELECT speed, winner, count(*) AS n
        FROM staging.games {effective.where_sql}
        GROUP BY speed, winner
        """,
        effective.params,
    )
    totals: dict[str, int] = {}
    for row in rows:
        totals[row["speed"]] = totals.get(row["speed"], 0) + row["n"]
    outcome_order = {"white": 0, "black": 1, "draw": 2}
    for row in rows:
        row["share"] = row["n"] / totals[row["speed"]]
    return sorted(
        rows,
        key=lambda row: (SPEED_ORDER.index(row["speed"]), outcome_order[row["winner"]]),
    )


def get_rq6(connection: duckdb.DuckDBPyConnection, filters: FilterSpec) -> list[dict[str, Any]]:
    return fetch_rows(
        connection,
        f"""
        SELECT speed,
               count(*) AS n,
               avg(is_time_forfeit::INT) AS forfeit_rate
        FROM staging.games {filters.where_sql}
        GROUP BY speed
        HAVING count(*) >= {MIN_GROUP_SIZE}
        ORDER BY forfeit_rate DESC
        """,
        filters.params,
    )


def get_rq7(connection: duckdb.DuckDBPyConnection, filters: FilterSpec) -> list[dict[str, Any]]:
    return fetch_rows(
        connection,
        f"""
        SELECT speed, total_moves
        FROM (
            SELECT speed,
                   total_moves,
                   row_number() OVER (
                       PARTITION BY speed
                       ORDER BY hash(game_id)
                   ) AS rn
            FROM staging.games {filters.where_sql}
              AND total_moves IS NOT NULL
        ) sampled
        WHERE rn <= 5000
        ORDER BY speed, total_moves
        """,
        filters.params,
    )


def _with_complete_filter(filters: FilterSpec, complete_only: bool) -> FilterSpec:
    if not complete_only:
        return filters
    return FilterSpec(
        where_sql=f"{filters.where_sql} AND is_complete_game",
        params=filters.params,
        game_type=filters.game_type,
    )
