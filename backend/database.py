"""Read-only DuckDB access for API requests."""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_configured_path = Path(os.environ.get("CHESS_DB_PATH", "data/chess.duckdb")).expanduser()
DB_PATH = (_configured_path if _configured_path.is_absolute() else PROJECT_ROOT / _configured_path).resolve()


def get_connection() -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield one read-only connection per request and always close it."""
    if not DB_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"DuckDB database was not found at {DB_PATH}.",
        )

    try:
        connection = duckdb.connect(str(DB_PATH), read_only=True)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not open the DuckDB database in read-only mode.",
        ) from exc

    try:
        yield connection
    finally:
        connection.close()


def fetch_rows(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    params: Sequence[Any] = (),
) -> list[dict[str, Any]]:
    """Execute a fixed query and normalize DuckDB scalar values for JSON."""
    cursor = connection.execute(sql, list(params))
    columns = [description[0] for description in cursor.description or ()]
    return [
        {column: _json_value(value) for column, value in zip(columns, row)}
        for row in cursor.fetchall()
    ]


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).decode("utf-8")
    return value
