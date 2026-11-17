import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

import helpers as h

h.page_header("Tổng quan", "Bức tranh chung của mẫu ván cờ Lichess đang xem")
f = h.sidebar_filters()

# ---------- Chỉ số tổng quan ----------
kpi = h.query(f"""
    SELECT count(*) AS n,
           avg((winner = 'white')::INT) AS white_win,
           avg((winner = 'draw')::INT)  AS draw,
           avg(is_time_forfeit::INT)    AS forfeit,
           median(total_moves)          AS med_moves
    FROM staging.games {f.where}
""", f.params).iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Số ván", f"{int(kpi.n):,}")
c2.metric("Trắng thắng", f"{kpi.white_win:.1%}")
c3.metric("Hòa", f"{kpi.draw:.1%}")
c4.metric("Kết thúc do hết giờ", f"{kpi.forfeit:.1%}")
c5.metric("Số nước đi (trung vị)", f"{kpi.med_moves:.0f}")

# ---------- Biểu đồ ----------
left, right = st.columns(2)

with left:
    by_speed = h.query(f"""
        SELECT speed, count(*) AS n FROM staging.games {f.where}
        GROUP BY speed
    """, f.params)
    by_speed["pct"] = by_speed["n"] / by_speed["n"].sum()
    fig = px.bar(by_speed, x="speed", y="n", text=by_speed["pct"].map("{:.1%}".format),
                 category_orders={"speed": h.SPEED_ORDER},
                 labels={"speed": "Thể thức", "n": "Số ván"},
                 title="Số ván theo thể thức", color_discrete_sequence=[h.COLORS["accent"]])
    fig.update_traces(textposition="outside")
    st.plotly_chart(h.style_fig(fig), width="stretch")

with right:
    res = h.query(f"""
        SELECT winner, count(*) AS n FROM staging.games {f.where} GROUP BY winner
    """, f.params)
    names = {"white": "Trắng thắng", "black": "Đen thắng", "draw": "Hòa"}
    res["Kết quả"] = res["winner"].map(names)
    fig = px.pie(res, names="Kết quả", values="n", hole=0.5, title="Cơ cấu kết quả",
                 color="winner",
                 color_discrete_map={"white": "#D9D9D9", "black": "#444444", "draw": "#9AA5B1"})
    st.plotly_chart(h.style_fig(fig), width="stretch")

hist = h.query(f"""
    SELECT floor(avg_rating / 50) * 50 AS rating_bin, count(*) AS n
    FROM staging.games {f.where} GROUP BY 1 ORDER BY 1
""", f.params)
fig = px.bar(hist, x="rating_bin", y="n",
             labels={"rating_bin": "Rating trung bình của hai bên (nhóm 50 điểm)", "n": "Số ván"},
             title="Phân bố rating trung bình của ván cờ",
             color_discrete_sequence=[h.COLORS["accent"]])
st.plotly_chart(h.style_fig(fig, height=340), width="stretch")

h.data_note()