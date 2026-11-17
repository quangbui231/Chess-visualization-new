
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

import helpers as h

h.page_header(
    "Tổng quan",
    "Tổng quan về mẫu dữ liệu các ván cờ trên Lichess.",
)

f = h.sidebar_filters()

# ---------------------------------------------------------------------
# Các chỉ số tổng quan
# ---------------------------------------------------------------------
kpi = h.query(f"""
    SELECT count(*) AS n,
           avg((winner = 'white')::INT) AS white_win,
           avg((winner = 'black')::INT) AS black_win,
           avg((winner = 'draw')::INT) AS draw,
           median(total_moves) AS med_moves
    FROM staging.games {f.where}
""", f.params).iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Tổng số ván đấu", f"{int(kpi.n):,}")
c2.metric("Trắng thắng", f"{kpi.white_win:.1%}")
c3.metric("Đen thắng", f"{kpi.black_win:.1%}")
c4.metric("Hòa", f"{kpi.draw:.1%}")


st.divider()

# =====================================================================
# RQ1 — Mức độ phổ biến của các thể thức thời gian
# =====================================================================
st.subheader(
    "RQ1 — Những thể thức thời gian được chơi phổ biến nhất?"
)

st.caption(
    "Phân tích số lượng và tỷ trọng ván đấu thuộc từng thể thức thời gian "
    "trong mẫu dữ liệu."
)

rq1 = h.query(f"""
    SELECT speed, count(*) AS n
    FROM staging.games {f.where}
    GROUP BY speed
    ORDER BY n DESC
""", f.params)

if rq1.empty:
    st.info("Không có dữ liệu phù hợp với các bộ lọc hiện tại.")
else:
    rq1["share"] = rq1["n"] / rq1["n"].sum()
    rq1["share_label"] = rq1["share"].map(lambda x: f"{x:.1%}")

    fig = px.bar(
        rq1,
        x="speed",
        y="n",
        text="share_label",
        category_orders={"speed": h.SPEED_ORDER},
        labels={
            "speed": "Thể thức thời gian",
            "n": "Số lượng ván đấu",
        },
        title="Số lượng ván đấu theo thể thức thời gian",
        color_discrete_sequence=[h.COLORS["accent"]],
        hover_data={"share": ":.1%", "n": ":,"},
    )

    fig.update_traces(textposition="outside")
    st.plotly_chart(h.style_fig(fig, height=380), width="stretch")

st.divider()

# =====================================================================
# RQ2 — Phân bố Elo của người chơi
# =====================================================================
st.subheader(
    "RQ2 — Mức Elo của người chơi trong mẫu dữ liệu được phân bố như thế nào?"
)

st.caption(
    "Sử dụng Elo trung bình của hai người chơi trong mỗi ván để phân tích "
    "phân bố trình độ người chơi trong mẫu dữ liệu. "
    "Mỗi khoảng trên biểu đồ đại diện cho một nhóm Elo rộng 50 điểm."
)

rq2 = h.query(f"""
    SELECT floor(avg_rating / 50) * 50 AS rating_bin,
           count(*) AS n
    FROM staging.games {f.where}
    GROUP BY 1
    ORDER BY 1
""", f.params)

if rq2.empty:
    st.info("Không có dữ liệu phù hợp với các bộ lọc hiện tại.")
else:
    fig = px.bar(
        rq2,
        x="rating_bin",
        y="n",
        labels={
            "rating_bin": "Elo trung bình của hai người chơi",
            "n": "Số lượng ván đấu",
        },
        title="Phân bố Elo trung bình của các ván đấu",
        color_discrete_sequence=[h.COLORS["accent"]],
        hover_data={"n": ":,"},
    )

    fig.update_xaxes(dtick=100)
    st.plotly_chart(h.style_fig(fig, height=400), width="stretch")

h.data_note()
