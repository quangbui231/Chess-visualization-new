
"""Kết nối DuckDB, bộ lọc chung và hàm dựng biểu đồ cho các trang dashboard."""

import sys
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config  # noqa: E402

SPEED_ORDER = ["UltraBullet", "Bullet", "Blitz", "Rapid", "Classical"]
BAND_ORDER = ["<1200", "1200-1499", "1500-1799", "1800-2099", "2100+"]
GAP_ORDER = ["0-49", "50-99", "100-199", "200-399", "400+"]

COLORS = {
    "white": "#E8E8E8",
    "black": "#2B2B2B",
    "draw": "#9AA5B1",
    "accent": "#1F77B4",
}


# ---------------------------------------------------------------------------
# Kết nối và truy vấn
# ---------------------------------------------------------------------------
@st.cache_resource
def get_connection():
    if not config.DB_PATH.exists():
        st.error("Chưa có kho dữ liệu. Hãy chạy: python src\\build_warehouse.py")
        st.stop()

    return duckdb.connect(str(config.DB_PATH), read_only=True)


@st.cache_data(ttl=600, show_spinner=False)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Chạy SQL trên DuckDB, kết quả được lưu đệm 10 phút."""
    cur = get_connection().cursor()
    return cur.execute(sql, list(params)).df()


# ---------------------------------------------------------------------------
# Bộ lọc dùng chung cho các trang
# ---------------------------------------------------------------------------
@dataclass
class Filters:
    where: str
    params: tuple
    n_games: int


def sidebar_filters(complete_toggle: bool = False) -> Filters:
    st.sidebar.header("Bộ lọc")

    speeds = st.sidebar.multiselect(
        "Thể thức thời gian",
        SPEED_ORDER,
        default=SPEED_ORDER,
    )

    bands = st.sidebar.multiselect(
        "Nhóm Elo trung bình",
        BAND_ORDER,
        default=BAND_ORDER,
    )

    kind = st.sidebar.radio(
        "Loại ván đấu",
        ["Tất cả", "Chỉ giải đấu", "Không giải đấu"],
    )

    clauses = [
        "list_contains(?, speed)",
        "list_contains(?, rating_band)",
    ]
    params = [speeds, bands]

    if kind == "Chỉ giải đấu":
        clauses.append("is_tournament")
    elif kind == "Không giải đấu":
        clauses.append("NOT is_tournament")

    if complete_toggle and st.sidebar.checkbox(
        "Chỉ ván chơi trọn",
        value=True,
        help="Bỏ các ván Abandoned và Rules infraction, vì ván không được chơi đến cùng.",
    ):
        clauses.append("is_complete_game")

    where = "WHERE " + " AND ".join(clauses)

    n = int(
        query(
            f"SELECT count(*) AS n FROM staging.games {where}",
            tuple(params),
        ).iloc[0]["n"]
    )

    if n == 0:
        st.warning(
            "Không có ván nào thỏa mãn bộ lọc. "
            "Hãy điều chỉnh lại các lựa chọn ở thanh bên."
        )
        st.stop()

    st.sidebar.metric("Số ván đang xem", f"{n:,}")

    return Filters(
        where=where,
        params=tuple(params),
        n_games=n,
    )


# ---------------------------------------------------------------------------
# Giao diện chung
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str):
    st.title(title)
    st.caption(subtitle)


def style_fig(fig, height: int = 380):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        font=dict(size=13),
        legend_title_text="",
    )
    return fig


def data_note():
    st.caption(
        "Nguồn: mẫu phân tầng theo thời gian gồm các ván Lichess tháng 09/2025, "
        "mỗi ván một dòng. Số ván theo ngày hoặc theo giờ trong mẫu không phản ánh "
        "lượng ván thật (mỗi lát thời gian lấy số ván bằng nhau), chỉ nên so sánh tỷ lệ."
    )


def heatmap(
    df, value_col, n_col, fmt, title, colorbar_title, colorscale,
    zmin=None, zmax=None, zmid=None, min_n=300, height=360,
    x_order=None, y_order=None, x_title="Nhóm Elo trung bình",
):
    """Bản đồ nhiệt thể thức x nhóm Elo."""
    import plotly.graph_objects as go

    x_order = x_order or BAND_ORDER
    y_order = y_order or SPEED_ORDER

    val = (
        df.pivot(index="speed", columns="rating_band", values=value_col)
        .reindex(index=y_order, columns=x_order)
    )
    cnt = (
        df.pivot(index="speed", columns="rating_band", values=n_col)
        .reindex(index=y_order, columns=x_order)
    )

    val = val.where(cnt >= min_n)
    text = [
        ["" if pd.isna(v) else format(v, fmt) for v in row]
        for row in val.values
    ]

    fig = go.Figure(
        go.Heatmap(
            z=val.values,
            x=x_order,
            y=y_order,
            text=text,
            texttemplate="%{text}",
            customdata=cnt.values,
            hovertemplate=(
                "Thể thức: %{y}<br>"
                "Nhóm Elo: %{x}<br>"
                "Giá trị: %{text}<br>"
                "%{customdata:,.0f} ván<extra></extra>"
            ),
            colorscale=colorscale,
            zmin=zmin,
            zmax=zmax,
            zmid=zmid,
            colorbar=dict(title=colorbar_title),
            xgap=2,
            ygap=2,
        )
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title="Thể thức thời gian",
    )

    return style_fig(fig, height)
