import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import helpers as h

h.page_header(
    "Rating và kết quả ván cờ",
    "Ba câu hỏi về lợi thế quân Trắng và mối liên hệ giữa rating với kết quả",
)
f = h.sidebar_filters(complete_toggle=True)
MIN_N = 300

# =====================================================================
# Câu hỏi 1. Lợi thế quân Trắng sau khi kiểm soát rating gap
# =====================================================================
st.subheader("Câu hỏi 1 — Khi hai bên có rating gần nhau, quân Trắng có ghi điểm tốt hơn không?")
st.caption(
    "Mỗi ván được tính 1 điểm nếu Trắng thắng, 0,5 nếu hòa và 0 nếu Trắng thua. "
    "Mốc 0,50 là cân bằng; thanh sai số thể hiện khoảng tin cậy 95%."
)

q1 = h.query(f"""
    SELECT speed, rating_gap_group AS rating_band, count(*) AS n,
           avg(white_score) AS score,
           coalesce(stddev_samp(white_score), 0) AS sd
    FROM staging.games {f.where}
    AND abs_rating_diff < 100
    GROUP BY speed, rating_gap_group
    HAVING count(*) >= {MIN_N}
""", f.params)

if q1.empty:
    st.info("Không đủ dữ liệu để trả lời câu hỏi này với bộ lọc hiện tại.")
else:
    q1["ci"] = 1.96 * q1["sd"] / np.sqrt(q1["n"])
    fig = px.scatter(
        q1, x="rating_band", y="score", color="speed", error_y="ci",
        category_orders={"rating_band": h.GAP_ORDER, "speed": h.SPEED_ORDER},
        hover_data={"n": ":,", "score": ":.4f", "ci": ":.4f"},
        labels={
            "rating_band": "Chênh lệch rating tuyệt đối",
            "score": "Điểm trung bình của Trắng",
            "speed": "Thể thức",
        },
        title="Lợi thế của Trắng trong các nhóm chênh lệch rating nhỏ",
    )
    fig.add_hline(y=0.5, line_dash="dash", line_color="gray")
    fig.update_traces(marker=dict(size=10))
    st.plotly_chart(h.style_fig(fig, height=420), width="stretch")
    st.caption(f"Chỉ hiển thị nhóm có từ {MIN_N} ván trở lên khi diễn giải; rê chuột để xem cỡ mẫu.")

# =====================================================================
# Câu hỏi 2. Rating gap và kết quả
# =====================================================================
st.subheader("Câu hỏi 2 — Khi rating chênh lệch nhiều hơn, người có rating cao hơn có thường đạt điểm cao hơn không?")
st.caption(
    "Mỗi điểm biểu thị điểm trung bình thực tế của người có rating cao hơn trong một nhóm ván. "
    "Đường nét đứt là mức tham khảo theo công thức Elo. So sánh này tổng hợp nhiều ván, "
    "không dự đoán người thắng của từng ván; các ván hai bên bằng rating không được tính."
)

q2 = h.query(f"""
    SELECT floor(abs_rating_diff / 25) * 25 AS bin_lo, count(*) AS n,
           avg(higher_rated_score) AS score,
           coalesce(stddev_samp(higher_rated_score), 0) AS sd,
           avg(abs_rating_diff) AS mean_gap
    FROM staging.games {f.where}
    AND higher_rated_side <> 'equal' AND abs_rating_diff < 600
    GROUP BY 1 HAVING count(*) >= 100 ORDER BY 1
""", f.params)

if q2.empty:
    st.info("Không đủ ván trong bộ lọc hiện tại để vẽ biểu đồ này.")
else:
    q2["ci"] = 1.96 * q2["sd"] / np.sqrt(q2["n"])
    q2["expected"] = 1 / (1 + 10 ** (-q2["mean_gap"] / 400))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=q2["mean_gap"], y=q2["score"], mode="lines+markers", name="Dữ liệu thực tế",
        error_y=dict(type="data", array=q2["ci"], visible=True),
        customdata=q2[["n"]],
        hovertemplate="Chênh lệch %{x:.0f}<br>Điểm %{y:.3f}<br>%{customdata[0]:,} ván<extra></extra>",
        line=dict(color=h.COLORS["accent"]),
    ))
    fig.add_trace(go.Scatter(
        x=q2["mean_gap"], y=q2["expected"], mode="lines",
        name="Kỳ vọng theo công thức Elo", line=dict(color="gray", dash="dash"),
    ))
    fig.update_layout(
        title="Điểm thực tế và kỳ vọng Elo theo chênh lệch rating",
        xaxis_title="Chênh lệch rating (điểm)",
        yaxis_title="Điểm trung bình của bên rating cao hơn",
    )
    st.plotly_chart(h.style_fig(fig, height=420), width="stretch")
    st.caption(
        "Đường Elo chỉ để tham khảo; Lichess dùng hệ thống rating Glicko-2 nên hai đường không nhất thiết trùng nhau. "
        "Các nhóm có dưới 100 ván không được hiển thị."
    )

# =====================================================================
# Câu hỏi 3. Rating gap thay đổi theo thể thức
# =====================================================================
st.subheader("Câu hỏi 3 — Rating chênh lệch liên quan đến kết quả ra sao ở từng thể thức?")
st.caption(
    "Màu và số trong mỗi ô cho biết điểm trung bình của người có rating cao hơn. "
    "Ô trống là nhóm có ít ván, chưa đủ để so sánh."
)

q3 = h.query(f"""
    SELECT speed, rating_gap_group AS rating_band, count(*) AS n,
           avg(higher_rated_score) AS score
    FROM staging.games {f.where}
    AND higher_rated_side <> 'equal' AND abs_rating_diff < 600
    GROUP BY speed, rating_gap_group
""", f.params)
fig = h.heatmap(
    q3, "score", "n", ".3f",
    "Điểm của bên rating cao hơn theo thể thức và rating gap",
    "Điểm bên mạnh hơn", "RdBu", zmin=0.50, zmax=0.80, zmid=0.65,
    min_n=MIN_N, x_order=h.GAP_ORDER, x_title="Chênh lệch rating tuyệt đối",
)
st.plotly_chart(fig, width="stretch")

h.data_note()
