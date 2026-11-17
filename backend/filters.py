"""Validated, parameterized dashboard filters shared by API routes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from fastapi import HTTPException, Query

SPEED_ORDER = ("UltraBullet", "Bullet", "Blitz", "Rapid", "Classical")
BAND_ORDER = ("<1200", "1200-1499", "1500-1799", "1800-2099", "2100+")
GAP_ORDER = ("0-49", "50-99", "100-199", "200-399", "400+")
MIN_GROUP_SIZE = 300


class GameType(str, Enum):
    all = "all"
    tournament = "tournament"
    non_tournament = "non_tournament"


@dataclass(frozen=True)
class FilterSpec:
    """Static SQL predicate plus values to bind, never raw user SQL."""

    where_sql: str
    params: tuple[list[str], list[str]]
    game_type: GameType


def build_filter_spec(
    speed: list[str] | None,
    rating_band: list[str] | None,
    game_type: GameType,
    *,
    complete_only: bool = False,
) -> FilterSpec:
    # An omitted filter means "all". An explicitly empty selection (encoded
    # by the client as an empty query value) must match no rows, as in Streamlit.
    speeds = list(SPEED_ORDER) if speed is None else [value for value in speed if value]
    bands = list(BAND_ORDER) if rating_band is None else [value for value in rating_band if value]

    invalid_speeds = sorted(set(speeds).difference(SPEED_ORDER))
    invalid_bands = sorted(set(bands).difference(BAND_ORDER))
    if invalid_speeds or invalid_bands:
        raise HTTPException(
            status_code=422,
            detail={
                "invalid_speed": invalid_speeds,
                "invalid_rating_band": invalid_bands,
            },
        )

    clauses = ["list_contains(?, speed)", "list_contains(?, rating_band)"]
    if game_type is GameType.tournament:
        clauses.append("is_tournament")
    elif game_type is GameType.non_tournament:
        clauses.append("NOT is_tournament")
    if complete_only:
        clauses.append("is_complete_game")

    return FilterSpec(
        where_sql="WHERE " + " AND ".join(clauses),
        params=(speeds, bands),
        game_type=game_type,
    )


def filter_query_parameters(
    speed: Annotated[list[str] | None, Query(description="Repeat for multiple time controls.")] = None,
    rating_band: Annotated[list[str] | None, Query(description="Repeat for multiple Elo bands.")] = None,
    game_type: GameType = GameType.all,
) -> FilterSpec:
    """FastAPI dependency for the three common dashboard filters."""
    return build_filter_spec(speed, rating_band, game_type)
