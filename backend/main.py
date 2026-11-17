"""FastAPI application exposing the existing Streamlit analytics as JSON."""

from __future__ import annotations

import os
from typing import Annotated

import duckdb
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .database import get_connection
from .filters import FilterSpec, filter_query_parameters
from .queries import (
    get_filter_options,
    get_overview_kpis,
    get_rq1,
    get_rq2,
    get_rq3,
    get_rq4,
    get_rq5,
    get_rq6,
    get_rq7,
)

app = FastAPI(
    title="Chess Visualization API",
    description="Read-only API for the existing Lichess DuckDB analytics.",
    version="0.1.0",
)

origins = [
    origin.strip()
    for origin in os.environ.get(
        "CHESS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)

DB = Annotated[duckdb.DuckDBPyConnection, Depends(get_connection)]
CommonFilters = Annotated[FilterSpec, Depends(filter_query_parameters)]


@app.get("/api/health")
def health(connection: DB) -> dict[str, str]:
    connection.execute("SELECT count(*) FROM staging.games").fetchone()
    return {"status": "ok", "database": "read-only"}


@app.get("/api/filters")
def filter_options(connection: DB) -> dict:
    return get_filter_options(connection)


@app.get("/api/overview")
def overview(connection: DB, filters: CommonFilters) -> dict:
    return {"kpis": get_overview_kpis(connection, filters)}


@app.get("/api/rq/rq1")
def rq1(connection: DB, filters: CommonFilters) -> dict:
    return {"data": get_rq1(connection, filters)}


@app.get("/api/rq/rq2")
def rq2(connection: DB, filters: CommonFilters) -> dict:
    return {"data": get_rq2(connection, filters)}


@app.get("/api/rq/rq3")
def rq3(
    connection: DB,
    filters: CommonFilters,
    complete_only: bool = Query(
        default=True,
        description="Matches the existing Streamlit checkbox, which is enabled by default for RQ3.",
    ),
) -> dict:
    return {"data": get_rq3(connection, filters, complete_only=complete_only)}


@app.get("/api/rq/rq4")
def rq4(
    connection: DB,
    filters: CommonFilters,
    complete_only: bool = Query(
        default=True,
        description="Matches the existing Streamlit checkbox, which is enabled by default for RQ4.",
    ),
) -> dict:
    return {"data": get_rq4(connection, filters, complete_only=complete_only)}


@app.get("/api/rq/rq5")
def rq5(
    connection: DB,
    filters: CommonFilters,
    complete_only: bool = Query(
        default=True,
        description="Matches the existing Streamlit checkbox, which is enabled by default for RQ5.",
    ),
) -> dict:
    return {"data": get_rq5(connection, filters, complete_only=complete_only)}


@app.get("/api/rq/rq6")
def rq6(connection: DB, filters: CommonFilters) -> dict:
    return {"data": get_rq6(connection, filters)}


@app.get("/api/rq/rq7")
def rq7(connection: DB, filters: CommonFilters) -> dict:
    return {"data": get_rq7(connection, filters)}
