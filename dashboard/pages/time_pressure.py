
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

import helpers as h

h.page_header(
    "Thời gian và diễn biến ván đấu",
    "Phân tích tỷ lệ hết giờ và độ dài ván đấu theo từng thể thức thời gian.",
)

f = h.sidebar_filters()
MIN_N = 300

# =====================================================================
# RQ6 — Tỷ lệ kết thúc ván do hết giờ
# =====================================================================
st.subheader(
    "RQ6 — Thể thức thời gian nào có tỷ lệ kết thúc ván do hết giờ cao nhất?"
)

st.caption(
    "Tính tỷ lệ các ván kết thúc do hết giờ trên tổng số ván thuộc từng thể thức. "
    "Biểu đồ đồng thời thể hiện số lượng ván để hỗ trợ đánh giá cỡ mẫu."
)

rq6 = h.query(f"""
    SELECT speed,
           count(*) AS n,
           avg(is_time_forfeit::INT) AS forfeit_rate
    FROM staging.games {f.where}
    GROUP BY speed
    HAVING count(*) >= {MIN_N}
    ORDER BY forfeit_rate DESC
""", f.params)

if rq6.empty:
    st.info("Không đủ dữ liệu để phân tích câu hỏi này với bộ lọc hiện tại.")
else:
    fig = px.bar(
        rq6,
        x="forfeit_rate",
        y="speed",
        orientation="h",
        text=rq6["forfeit_rate"].map(lambda x: f"{x:.1%}"),
        category_orders={
            "speed": rq6.sort_values("forfeit_rate")["speed"].tolist()
        },
        labels={
            "speed": "Thể thức thời gian",
            "forfeit_rate": "Tỷ lệ kết thúc do hết giờ",
        },
        title="Tỷ lệ kết thúc ván do hết giờ theo thể thức",
        color_discrete_sequence=[h.COLORS["accent"]],
        hover_data={"n": ":,", "forfeit_rate": ":.1%"},
    )

    fig.update_xaxes(tickformat=".0%")
    fig.update_traces(textposition="outside")
    st.plotly_chart(h.style_fig(fig, height=380), width="stretch")

    st.caption(
        f"Chỉ hiển thị các thể thức có ít nhất {MIN_N} ván."
    )

st.divider()

# =====================================================================
# RQ7 — Độ dài ván đấu theo thể thức
# =====================================================================
st.subheader(
    "RQ7 — Độ dài các ván đấu có sự khác biệt như thế nào giữa các thể thức thời gian?"
)

st.caption(
    "Sử dụng số nước đi của mỗi ván để so sánh độ dài ván đấu giữa các thể thức. "
    "Biểu đồ hộp thể hiện trung vị, khoảng tứ phân vị và các giá trị ngoại lệ."
)

rq7 = h.query(f"""
    SELECT speed, total_moves
    FROM (
        SELECT speed,
               total_moves,
               row_number() OVER (
                   PARTITION BY speed
                   ORDER BY hash(game_id)
               ) AS rn
        FROM staging.games {f.where}
        AND total_moves IS NOT NULL
    ) sampled
    WHERE rn <= 5000
""", f.params)

if rq7.empty:
    st.info("Không có dữ liệu phù hợp để phân tích câu hỏi này.")
else:
    fig = px.box(
        rq7,
        x="speed",
        y="total_moves",
        category_orders={"speed": h.SPEED_ORDER},
        labels={
            "speed": "Thể thức thời gian",
            "total_moves": "Số nước đi trong ván",
        },
        title="Phân bố số nước đi theo thể thức thời gian",
        color_discrete_sequence=[h.COLORS["accent"]],
        points=False,
    )

    fig.update_traces(
        hovertemplate="Thể thức: %{x}<br>Số nước đi: %{y}<extra></extra>"
    )

    st.plotly_chart(h.style_fig(fig, height=430), width="stretch")

    st.caption(
        "Biểu đồ sử dụng tối đa 5.000 ván cho mỗi thể thức để hiển thị. "
        "Việc lấy mẫu được thực hiện bằng mã băm của mã ván đấu."
    )


