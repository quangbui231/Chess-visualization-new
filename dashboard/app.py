import streamlit as st

st.set_page_config(page_title="Phân tích ván cờ Lichess", page_icon="♟️", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --chess-blue: #1f5f8b;
        --chess-blue-soft: #eaf3f8;
        --chess-ink: #17324d;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f8fbfd 0%, #eef5f8 100%);
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #eaf3f8 0%, #f7fafb 100%);
        border-right: 1px solid #d6e4eb;
    }
    h1, h2, h3 { color: var(--chess-ink); letter-spacing: -0.02em; }
    h2 { margin-top: 1.4rem; }
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid #d6e4eb;
        border-radius: 14px;
        padding: 0.8rem 1rem;
        box-shadow: 0 4px 16px rgba(23, 50, 77, 0.06);
    }
    [data-testid="stMetricLabel"] { color: var(--chess-blue); }
    [data-testid="stMetricValue"] { color: var(--chess-ink); }
    [data-testid="stExpander"] {
        border: 1px solid #d6e4eb;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.55);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

pages = [
    st.Page("pages/overview.py", title="Tổng quan", icon="📊", default=True),
    st.Page("pages/rating_result.py", title="Rating và kết quả", icon="⚖️"),
    st.Page("pages/time_pressure.py", title="Thời gian và kết thúc ván", icon="⏱️"),
]

st.navigation(pages).run()  
