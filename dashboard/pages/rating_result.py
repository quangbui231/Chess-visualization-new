
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import plotly.express as px
import streamlit as st

import helpers as h

h.page_header(
    "Elo và kết quả ván đấu",
    "Phân tích mối liên hệ giữa trình độ người chơi, lợi thế quân Trắng và kết quả ván đấu.",
)

f = h.sidebar_filters(complete_toggle=True)
MIN_N = 300

# =====================================================================
# RQ3 — Kết quả của người có Elo cao hơn
# =====================================================================
st.subheader(
    "RQ3 — Người chơi có mức Elo cao hơn có thường đạt được kết quả tốt hơn không?"
)

st.caption(
    "Mỗi ván được tính 1 điểm nếu người có Elo cao hơn thắng, "
    "0,5 điểm nếu hòa và 0 điểm nếu người đó thua. "
    "Mốc 0,5 thể hiện mức điểm cân bằng."
)

rq3 = h.query(f"""
    SELECT rating_gap_group,
           count(*) AS n,
           avg(higher_rated_score) AS score,
           coalesce(stddev_samp(higher_rated_score), 0) AS sd
    FROM staging.games {f.where}
    AND higher_rated_side <> 'equal'
    GROUP BY rating_gap_group
    HAVING count(*) >= {MIN_N}
""", f.params)

if rq3.empty:
    st.info("Không đủ dữ liệu để phân tích câu hỏi này với bộ lọc hiện tại.")
else:
    rq3["ci"] = 1.96 * rq3["sd"] / np.sqrt(rq3["n"])

    fig = px.line(
        rq3,
        x="rating_gap_group",
        y="score",
        markers=True,
        error_y="ci",
        category_orders={"rating_gap_group": h.GAP_ORDER},
        labels={
            "rating_gap_group": "Mức chênh lệch Elo",
            "score": "Điểm trung bình của người Elo cao hơn",
        },
        title="Điểm trung bình theo mức chênh lệch Elo",
        hover_data={"n": ":,", "score": ":.3f", "ci": ":.3f"},
    )

    fig.add_hline(
        y=0.5,
        line_dash="dash",
        line_color="gray",
        annotation_text="Mốc cân bằng (0,5)",
    )

    fig.update_yaxes(range=[0, 1])
    fig.update_traces(line=dict(color=h.COLORS["accent"], width=3))
    st.plotly_chart(h.style_fig(fig, height=400), width="stretch")

    st.caption(
        f"Chỉ hiển thị các nhóm có ít nhất {MIN_N} ván. "
        "Các ván có Elo hai bên bằng nhau không được tính."
    )

st.divider()

# =====================================================================
# RQ4 — Lợi thế quân Trắng khi Elo tương đương
# =====================================================================
st.subheader(
    "RQ4 — Quân Trắng có lợi thế hơn quân Đen khi hai người chơi có mức Elo tương đương không?"
)

st.caption(
    "Chỉ xét các ván có chênh lệch Elo tuyệt đối dưới 100 điểm. "
    "Trắng thắng được tính 1 điểm, hòa 0,5 điểm và Trắng thua 0 điểm. "
    "Mốc 0,5 thể hiện mức cân bằng giữa hai bên."
)

rq4 = h.query(f"""
    SELECT speed,
           count(*) AS n,
           avg(white_score) AS score,
           coalesce(stddev_samp(white_score), 0) AS sd
    FROM staging.games {f.where}
    AND abs_rating_diff < 100
    GROUP BY speed
    HAVING count(*) >= {MIN_N}
""", f.params)

if rq4.empty:
    st.info("Không đủ dữ liệu để phân tích câu hỏi này với bộ lọc hiện tại.")
else:
    rq4["ci"] = 1.96 * rq4["sd"] / np.sqrt(rq4["n"])

    fig = px.bar(
        rq4,
        x="speed",
        y="score",
        error_y="ci",
        text=rq4["score"].map(lambda x: f"{x:.3f}"),
        category_orders={"speed": h.SPEED_ORDER},
        labels={
            "speed": "Thể thức thời gian",
            "score": "Điểm trung bình của quân Trắng",
        },
        title="Điểm trung bình của quân Trắng theo thể thức thời gian",
        color_discrete_sequence=[h.COLORS["accent"]],
        hover_data={"n": ":,", "score": ":.3f"},
    )

    fig.add_hline(
        y=0.5,
        line_dash="dash",
        line_color="gray",
        annotation_text="Mốc cân bằng (0,5)",
    )

    fig.update_yaxes(range=[0, 1])
    fig.update_traces(textposition="outside")
    st.plotly_chart(h.style_fig(fig, height=400), width="stretch")

    st.caption(
        f"Chỉ xét các nhóm thể thức có ít nhất {MIN_N} ván "
        "và chênh lệch Elo giữa hai bên dưới 100 điểm."
    )

st.divider()

# =====================================================================
# RQ5 — Phân bố kết quả theo thể thức thời gian
# =====================================================================
st.subheader(
    "RQ5 — Kết quả các ván đấu có sự khác biệt giữa các thể thức thời gian không?"
)

st.caption(
    "So sánh tỷ lệ Trắng thắng, Đen thắng và hòa giữa các thể thức thời gian. "
    "Mỗi cột thể hiện 100% tổng số ván thuộc một thể thức."
)

rq5 = h.query(f"""
    SELECT speed,
           winner,
           count(*) AS n
    FROM staging.games {f.where}
    GROUP BY speed, winner
""", f.params)

if rq5.empty:
    st.info("Không có dữ liệu phù hợp với các bộ lọc hiện tại.")
else:
    result_names = {
        "white": "Trắng thắng",
        "black": "Đen thắng",
        "draw": "Hòa",
    }

    rq5["Kết quả"] = rq5["winner"].map(result_names)
    rq5["share"] = rq5["n"] / rq5.groupby("speed")["n"].transform("sum")

    fig = px.bar(
        rq5,
        x="speed",
        y="share",
        color="Kết quả",
        barmode="stack",
        text=rq5["share"].map(
            lambda x: f"{x:.1%}" if x >= 0.05 else ""
        ),
        category_orders={
            "speed": h.SPEED_ORDER,
            "Kết quả": ["Trắng thắng", "Đen thắng", "Hòa"],
        },
        color_discrete_map={
            "Trắng thắng": "#D9D9D9",
            "Đen thắng": "#444444",
            "Hòa": "#9AA5B1",
        },
        labels={
            "speed": "Thể thức thời gian",
            "share": "Tỷ lệ ván đấu",
            "Kết quả": "Kết quả",
        },
        title="Cơ cấu kết quả ván đấu theo thể thức thời gian",
        hover_data={"n": ":,"},
    )

    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    st.plotly_chart(h.style_fig(fig, height=430), width="stretch")

h.data_note()
