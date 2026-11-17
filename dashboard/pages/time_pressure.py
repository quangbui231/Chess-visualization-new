import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

import helpers as h

h.page_header(
    "Thời gian và bối cảnh ván cờ",
    "Hai câu hỏi về đồng hồ thi đấu và sự khác nhau giữa ván trong và ngoài giải đấu",
)
f = h.sidebar_filters()
MIN_N = 300
TERM_ORDER = ["Normal", "Time forfeit", "Abandoned", "Insufficient material", "Rules infraction"]
TERM_NAMES = {
    "Normal": "Bình thường (chiếu hết, bỏ cuộc, hòa...)",
    "Time forfeit": "Hết giờ",
    "Abandoned": "Bỏ ván (rời đi)",
    "Insufficient material": "Không đủ quân",
    "Rules infraction": "Vi phạm luật",
}

# =====================================================================
# Câu hỏi 4. Đồng hồ và hết giờ
# =====================================================================
st.subheader("Câu hỏi 4 — Thời gian ban đầu và số giây cộng thêm mỗi nước liên quan thế nào đến tỷ lệ hết giờ?")
st.caption(
    "Mỗi điểm là một kiểu đồng hồ có ít nhất 300 ván. Trục ngang là thời gian ban đầu (phút), "
    "trục dọc là số giây được cộng sau mỗi nước đi. Màu thể hiện tỷ lệ hết giờ, hình dạng là thể thức "
    "và kích thước điểm cho biết số ván."
)

q4 = h.query(f"""
    SELECT speed, base_seconds, increment_seconds, count(*) AS n,
           avg(is_time_forfeit::INT) AS rate
    FROM staging.games {f.where}
    GROUP BY speed, base_seconds, increment_seconds
    HAVING count(*) >= {MIN_N}
    ORDER BY base_seconds, increment_seconds
""", f.params)

if q4.empty:
    st.info("Không đủ cấu hình đồng hồ có từ 300 ván trong bộ lọc hiện tại.")
else:
    q4["base_minutes"] = q4["base_seconds"] / 60
    q4["clock"] = q4.apply(
        lambda row: f"{row.base_seconds // 60}+{int(row.increment_seconds)}", axis=1
    )
    fig = px.scatter(
        q4, x="base_minutes", y="increment_seconds", color="rate",
        symbol="speed", size="n", color_continuous_scale="YlOrRd",
        hover_name="clock", hover_data={
            "base_minutes": ":.1f", "increment_seconds": True,
            "rate": ":.1%", "n": ":,",
        },
        category_orders={"speed": h.SPEED_ORDER},
        labels={
            "base_minutes": "Thời gian ban đầu (phút)",
            "increment_seconds": "Increment (giây)",
            "rate": "Tỷ lệ hết giờ",
            "speed": "Thể thức",
            "n": "Số ván",
        },
        title="Tỷ lệ hết giờ theo thời gian ban đầu và increment",
    )
    st.plotly_chart(h.style_fig(fig, height=430), width="stretch")

# =====================================================================
# Câu hỏi 5. Giải đấu và ngoài giải đấu
# =====================================================================
st.subheader("Câu hỏi 5 — Kết quả và diễn biến ván có khác giữa trong và ngoài giải đấu không?")
st.caption(
    "So sánh điểm của Trắng, tỷ lệ hết giờ hoặc số nước đi giữa các ván cùng thể thức và nhóm rating. "
    "Chỉ hiện nhóm có ít nhất 300 ván. Đây là so sánh mô tả, không chứng minh việc thi đấu trong giải "
    "là nguyên nhân tạo ra khác biệt. Dữ liệu nhận diện giải đấu qua tên sự kiện."
)

q5 = h.query(f"""
    SELECT CASE WHEN is_tournament THEN 'Trong giải đấu' ELSE 'Ngoài giải đấu' END AS context,
           speed,
           rating_band,
           count(*) AS n,
           avg(white_score) AS white_score,
           avg(is_time_forfeit::INT) AS forfeit_rate,
           median(total_moves) AS median_moves
    FROM staging.games {f.where}
    GROUP BY is_tournament, speed, rating_band
    HAVING count(*) >= {MIN_N}
    ORDER BY rating_band, speed, is_tournament DESC
""", f.params)

if not q5.empty:
    measure = st.selectbox(
        "Chỉ số so sánh",
        options=["white_score", "forfeit_rate", "median_moves"],
        format_func={
            "white_score": "Điểm trung bình của quân Trắng",
            "forfeit_rate": "Tỷ lệ hết giờ",
            "median_moves": "Trung vị số nước đi",
        }.get,
        key="tournament_comparison_measure",
    )
    metric_labels = {
        "white_score": ("Điểm trung bình của Trắng", ".3f"),
        "forfeit_rate": ("Tỷ lệ hết giờ", ".1%"),
        "median_moves": ("Trung vị số nước đi", ".0f"),
    }
    metric_label, _ = metric_labels[measure]
    fig = px.scatter(
        q5, x="speed", y=measure, color="context", symbol="context",
        facet_col="rating_band", facet_col_wrap=3,
        category_orders={
            "speed": h.SPEED_ORDER,
            "rating_band": h.BAND_ORDER,
            "context": ["Ngoài giải đấu", "Trong giải đấu"],
        },
        hover_data={"n": ":,", "rating_band": False},
        labels={
            "speed": "Thể thức",
            measure: metric_label,
            "context": "Bối cảnh",
            "n": "Số ván",
            "rating_band": "Nhóm rating trung bình",
        },
        title=f"{metric_label}: giải đấu và ngoài giải đấu trong cùng nhóm",
    )
    if measure == "forfeit_rate":
        fig.update_yaxes(tickformat=".0%")
    elif measure == "white_score":
        fig.update_yaxes(range=[0, 1])
    fig.for_each_annotation(lambda annotation: annotation.update(
        text=annotation.text.replace("rating_band=", "Rating ")
    ))
    st.plotly_chart(h.style_fig(fig, height=520), width="stretch")
    st.caption(
        "Rê chuột để xem cỡ mẫu từng nhóm. Ô không xuất hiện nghĩa là nhóm có dưới "
        f"{MIN_N} ván trong bộ lọc hiện tại."
    )
else:
    st.info("Không có nhóm đủ cỡ mẫu để so sánh với bộ lọc hiện tại.")

# ---------------------------------------------------------------------
# Phân tích bổ trợ: cách kết thúc ván
# ---------------------------------------------------------------------
with st.expander("Phân tích bổ trợ — Cơ cấu cách kết thúc ván"):
    b = h.query(f"""
        SELECT speed, termination, count(*) AS n
        FROM staging.games {f.where}
        GROUP BY speed, termination
    """, f.params)
    b["share"] = b["n"] / b.groupby("speed")["n"].transform("sum")
    b["Cách kết thúc"] = b["termination"].map(TERM_NAMES).fillna(b["termination"])
    fig = px.bar(
        b, y="speed", x="share", color="Cách kết thúc", orientation="h", barmode="stack",
        category_orders={"speed": h.SPEED_ORDER,
                         "Cách kết thúc": [TERM_NAMES[t] for t in TERM_ORDER]},
        text=b["share"].map(lambda value: f"{value:.1%}" if value >= 0.03 else ""),
        labels={"speed": "Thể thức", "share": "Tỷ lệ ván"},
        title="Cơ cấu cách kết thúc theo thể thức",
    )
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(h.style_fig(fig, height=360), width="stretch")

h.data_note()
