
import streamlit as st

st.set_page_config(
    page_title="Phân tích ván cờ Lichess",
    page_icon="♟️",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --chess-navy: #17324D;
        --chess-blue: #2878A8;
        --chess-blue-light: #EAF3F8;
        --chess-teal: #2A9D8F;
        --chess-orange: #E69F00;
        --chess-text: #263746;
        --chess-muted: #718096;
        --chess-border: #E2EAF0;
        --chess-surface: #FFFFFF;
        --chess-background: #F4F7FA;
    }

    /* Nền tổng thể */
    [data-testid="stAppViewContainer"] {
        background: var(--chess-background);
    }

    [data-testid="stHeader"] {
        background: rgba(244, 247, 250, 0.9);
    }

    /* Thu gọn khoảng trống đầu trang */
    [data-testid="stMainBlockContainer"] {
        padding-top: 2rem;
        padding-bottom: 3rem;
        padding-left: 3rem;
        padding-right: 3rem;
        max-width: 1500px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #EDF3F7;
        border-right: 1px solid var(--chess-border);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem;
    }

    [data-testid="stSidebar"] h2 {
        color: var(--chess-navy);
        font-size: 1.15rem;
        font-weight: 700;
    }

    [data-testid="stSidebar"] label {
        color: var(--chess-text);
        font-weight: 500;
    }

    /* Tiêu đề */
    h1, h2, h3 {
        color: var(--chess-navy) !important;
        letter-spacing: -0.025em;
    }

    h1 {
        font-size: 2.25rem !important;
        font-weight: 750 !important;
        margin-bottom: 0.4rem !important;
    }

    h2 {
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        margin-top: 1.8rem !important;
        margin-bottom: 0.7rem !important;
    }

    h3 {
        font-size: 1.15rem !important;
        font-weight: 650 !important;
    }

    /* Mô tả và caption */
    [data-testid="stCaptionContainer"] {
        color: var(--chess-muted);
        font-size: 0.9rem;
        line-height: 1.6;
    }

    /* Thẻ KPI */
    [data-testid="stMetric"] {
        background: var(--chess-surface);
        border: 1px solid var(--chess-border);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 2px 8px rgba(23, 50, 77, 0.04);
        transition: box-shadow 0.2s ease, transform 0.2s ease;
    }

    [data-testid="stMetric"]:hover {
        box-shadow: 0 5px 16px rgba(23, 50, 77, 0.08);
        transform: translateY(-2px);
    }

    [data-testid="stMetricLabel"] {
        color: var(--chess-muted);
        font-size: 0.85rem;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: var(--chess-navy);
        font-weight: 750;
    }

    /* Khu vực biểu đồ */
    [data-testid="stPlotlyChart"] {
        background: var(--chess-surface);
        border: 1px solid var(--chess-border);
        border-radius: 14px;
        padding: 0.6rem 0.6rem 0.2rem 0.6rem;
        box-shadow: 0 2px 8px rgba(23, 50, 77, 0.035);
    }

    /* Bộ lọc multiselect */
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background: var(--chess-navy) !important;
        border: 0 !important;
        border-radius: 6px !important;
    }

    [data-testid="stSidebar"] [data-baseweb="tag"] span {
        color: #FFFFFF !important;
    }

    [data-testid="stSidebar"] [data-baseweb="tag"] svg {
        fill: #FFFFFF !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        border-radius: 9px;
        border-color: #D5E0E8;
        background: #FFFFFF;
    }

    /* Radio và checkbox */
    [data-testid="stSidebar"] input[type="radio"],
    [data-testid="stSidebar"] input[type="checkbox"] {
        accent-color: var(--chess-blue);
    }

    /* Expander */
    [data-testid="stExpander"] {
        background: #FFFFFF;
        border: 1px solid var(--chess-border);
        border-radius: 12px;
    }

    /* Nút bấm */
    [data-testid="stButton"] button {
        border-radius: 8px;
        font-weight: 600;
    }

    /* Đường phân cách */
    hr {
        border-color: var(--chess-border);
    }

    /* Chữ nhỏ */
    small {
        color: var(--chess-muted);
    }

    /* Responsive cho màn hình nhỏ */
    @media (max-width: 900px) {
        [data-testid="stMainBlockContainer"] {
            padding-left: 1.2rem;
            padding-right: 1.2rem;
            padding-top: 1.2rem;
        }

        h1 {
            font-size: 1.8rem !important;
        }

        h2 {
            font-size: 1.3rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

pages = [
    st.Page(
        "pages/overview.py",
        title="Tổng quan",
        icon="📊",
        default=True,
    ),
    st.Page(
        "pages/rating_result.py",
        title="Elo và kết quả ván đấu",
        icon="⚖️",
    ),
    st.Page(
        "pages/time_pressure.py",
        title="Thời gian và diễn biến",
        icon="⏱️",
    ),
]

st.navigation(pages).run()
