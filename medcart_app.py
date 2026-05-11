"""
MedCart — Complete Analytics Platform
======================================
Author : Aftab Dayer
Pages  : Dashboard | Inventory | Customers | Forecast | AI Chatbot | Rx Scanner
Run    : streamlit run medcart_app.py
Deploy : Streamlit Community Cloud (share.streamlit.io)

Secrets required (set in Streamlit Cloud dashboard):
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
"""

import os, sqlite3, base64, io, re, json, datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from groq import Groq

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG — reads from Streamlit Secrets (safe for public GitHub)
# ══════════════════════════════════════════════════════════════════════════════
try:
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
except Exception:
    GROQ_API_KEY = ""

# DB path — works both locally and on Streamlit Cloud
_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_HERE, "data", "medcart.db")
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join(_HERE, "medcart.db")  # fallback: root folder

# Forecast CSV path
FORECAST_CSV = os.path.join(_HERE, "data", "forecast_4week.csv")
if not os.path.exists(FORECAST_CSV):
    FORECAST_CSV = os.path.join(_HERE, "forecast_4week.csv")
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="MedCart Analytics",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=DM+Mono&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main { background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%); min-height: 100vh; }
    .block-container { padding-top: 1.5rem !important; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid rgba(56,189,248,0.15);
    }
    [data-testid="stSidebar"] * { color: #8b949e !important; }
    [data-testid="stSidebar"] .stButton>button {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        color: #8b949e !important;
        border-radius: 10px;
        text-align: left; width: 100%;
        transition: all 0.25s ease;
        font-size: 0.88rem;
        padding: 0.55rem 0.9rem;
        margin-bottom: 2px;
    }
    [data-testid="stSidebar"] .stButton>button:hover {
        background: rgba(56,189,248,0.1);
        border-color: rgba(56,189,248,0.35);
        color: #38bdf8 !important;
        transform: translateX(3px);
    }

    /* KPI Cards — glassmorphism */
    .kpi-card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 18px;
        padding: 1.4rem 1.6rem;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1);
        position: relative;
        overflow: hidden;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover { transform: translateY(-3px); box-shadow: 0 16px 40px rgba(0,0,0,0.4); }
    .kpi-card::before {
        content: "";
        position: absolute; top: 0; left: 0; right: 0; height: 3px;
        border-radius: 18px 18px 0 0;
    }
    .kpi-card::after {
        content: "";
        position: absolute; top: -40px; right: -40px;
        width: 120px; height: 120px;
        border-radius: 50%;
        opacity: 0.06;
    }
    .kpi-card.blue::before  { background: linear-gradient(90deg, #3b82f6, #60a5fa, #93c5fd); }
    .kpi-card.blue::after   { background: #3b82f6; }
    .kpi-card.green::before { background: linear-gradient(90deg, #10b981, #34d399, #6ee7b7); }
    .kpi-card.green::after  { background: #10b981; }
    .kpi-card.amber::before { background: linear-gradient(90deg, #f59e0b, #fbbf24, #fde68a); }
    .kpi-card.amber::after  { background: #f59e0b; }
    .kpi-card.rose::before  { background: linear-gradient(90deg, #f43f5e, #fb7185, #fda4af); }
    .kpi-card.rose::after   { background: #f43f5e; }
    .kpi-card.purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa, #c4b5fd); }
    .kpi-card.purple::after  { background: #8b5cf6; }
    .kpi-card.cyan::before  { background: linear-gradient(90deg, #06b6d4, #22d3ee, #67e8f9); }
    .kpi-card.cyan::after   { background: #06b6d4; }

    .kpi-icon  { font-size: 1.6rem; margin-bottom: 0.5rem; display: block; }
    .kpi-label { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                 text-transform: uppercase; color: rgba(255,255,255,0.45); margin-bottom: 0.3rem; }
    .kpi-value { font-size: 2.1rem; font-weight: 800; color: #f8fafc; line-height: 1; }
    .kpi-sub   { font-size: 0.78rem; color: rgba(255,255,255,0.4); margin-top: 0.35rem; }
    .kpi-delta { font-size: 0.78rem; color: #34d399; margin-top: 0.3rem; font-weight: 600; }

    /* Chart containers */
    .chart-wrap {
        background: rgba(255,255,255,0.04);
        backdrop-filter: blur(8px);
        border-radius: 16px;
        padding: 1rem 1.2rem 0.5rem 1.2rem;
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 1rem;
    }

    .section-title {
        font-size: 1.6rem; font-weight: 800; color: #f8fafc;
        margin-bottom: 0.15rem; letter-spacing: -0.02em;
    }
    .section-sub { font-size: 0.88rem; color: rgba(255,255,255,0.45); margin-bottom: 1.3rem; }

    .page-title { font-size: 1.6rem; font-weight: 800; color: #f8fafc; margin-bottom: 0.15rem; }
    .page-sub   { font-size: 0.88rem; color: rgba(255,255,255,0.45); margin-bottom: 1.3rem; }

    /* Insight cards */
    .insight-box {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-left: 4px solid #3b82f6;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin: 0.4rem 0;
        color: #e2e8f0;
        font-size: 0.88rem;
        line-height: 1.6;
    }
    .insight-box b { color: #f8fafc; }

    /* Risk pills */
    .risk-pill {
        display: inline-block; padding: 3px 12px;
        border-radius: 20px; font-size: 0.75rem; font-weight: 700;
    }
    .pill-red    { background:rgba(239,68,68,0.2);  color:#fca5a5; border:1px solid rgba(239,68,68,0.3); }
    .pill-amber  { background:rgba(245,158,11,0.2); color:#fde68a; border:1px solid rgba(245,158,11,0.3); }
    .pill-green  { background:rgba(34,197,94,0.2);  color:#86efac; border:1px solid rgba(34,197,94,0.3); }
    .pill-blue   { background:rgba(59,130,246,0.2); color:#93c5fd; border:1px solid rgba(59,130,246,0.3); }

    /* Metric override */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.05);
        border-radius: 12px; padding: 1rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 800 !important; color: #f8fafc !important; }
    div[data-testid="stMetricLabel"] { color: rgba(255,255,255,0.5) !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.04);
        border-radius: 10px; padding: 4px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .stTabs [data-baseweb="tab"] { color: rgba(255,255,255,0.5); border-radius: 8px; }
    .stTabs [aria-selected="true"] {
        background: rgba(59,130,246,0.25) !important;
        color: #93c5fd !important;
    }

    /* Dataframe */
    .stDataFrame { border-radius: 12px; overflow: hidden; }

    /* Select boxes */
    .stSelectbox [data-baseweb="select"] > div {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        color: #e2e8f0;
        border-radius: 10px;
    }

    /* Chat */
    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem 0 1rem 0;
        color: rgba(255,255,255,0.3);
        font-size: 0.8rem;
        border-top: 1px solid rgba(255,255,255,0.08);
        margin-top: 3rem;
    }
    .footer a { color: #60a5fa; text-decoration: none; }
    .footer a:hover { color: #93c5fd; text-decoration: underline; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ─── DB helpers ───────────────────────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(DB_PATH)

@st.cache_data(ttl=300)
def run_query(sql: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_metrics():
    conn = get_conn()
    rev  = pd.read_sql_query("SELECT ROUND(SUM(total_amount),2) AS v FROM orders WHERE status='completed'", conn).iloc[0,0]
    ords = pd.read_sql_query("SELECT COUNT(*) AS v FROM orders", conn).iloc[0,0]
    pats = pd.read_sql_query("SELECT COUNT(*) AS v FROM patients", conn).iloc[0,0]
    drgs = pd.read_sql_query("SELECT COUNT(*) AS v FROM drugs", conn).iloc[0,0]
    conn.close()
    return rev, ords, pats, drgs

# ─── Groq client ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_groq():
    return Groq(api_key=GROQ_API_KEY)

def groq_ask(prompt: str, max_tokens=600) -> str:
    if not GROQ_API_KEY:
        return "⚠️ No API key set. Add GROQ_API_KEY in Streamlit secrets."
    try:
        resp = get_groq().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI error: {e}"

# ─── Sidebar navigation ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💊 MedCart")
    st.markdown("##### Analytics Platform")
    st.divider()

    PAGES = {
        "📊 Dashboard":        "dashboard",
        "📦 Inventory Alerts": "inventory",
        "👥 Customers":        "customers",
        "📈 Demand Forecast":  "forecast",
        "🤖 AI Chatbot":       "chatbot",
        "🧾 Rx Scanner":       "rxscanner",
        "👤 About":            "about",
    }

    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    for label, key in PAGES.items():
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.divider()
    st.caption("Built by **Aftab Dayer**")
    st.caption("Python · SQLite · Groq · Plotly · Streamlit")
    st.markdown("""
    <div style='padding-top:8px'>
        <a href='https://github.com/aftabdayer/medcart-analytics' target='_blank'
           style='color:#60a5fa;text-decoration:none;font-size:0.82rem'>
           🔗 GitHub Repo
        </a><br>
        <a href='https://www.linkedin.com/in/aftabdayer' target='_blank'
           style='color:#60a5fa;text-decoration:none;font-size:0.82rem'>
           💼 LinkedIn
        </a>
    </div>
    """, unsafe_allow_html=True)

page = st.session_state.page

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
CHART_LAYOUT = dict(
    plot_bgcolor="rgba(255,255,255,0.03)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#94a3b8"),
    margin=dict(t=45, b=30, l=10, r=10),
    hoverlabel=dict(bgcolor="#1e293b", font_size=13, font_family="Inter",
                    font_color="white", bordercolor="rgba(255,255,255,0.2)"),
)
COLORS = ["#3b82f6","#10b981","#f59e0b","#f43f5e","#8b5cf6","#06b6d4","#ec4899","#14b8a6","#84cc16","#fb923c"]

if page == "dashboard":
    rev, ords, pats, drgs = load_metrics()

    # Extra quick metrics
    aov_df = run_query("SELECT ROUND(AVG(total_amount),0) AS v FROM orders WHERE status='completed'")
    aov = float(aov_df.iloc[0,0])
    risk_df = run_query("SELECT COUNT(*) AS v FROM v_inventory_risk WHERE risk_status != 'Healthy'")
    at_risk = int(risk_df.iloc[0,0])

    st.markdown('<p class="section-title">📊 Executive Dashboard</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="section-sub">Live overview of MedCart pharmacy performance &nbsp;·&nbsp; Last updated: {datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")}</p>', unsafe_allow_html=True)

    # ── 6 KPI Cards ───────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""<div class="kpi-card blue">
            <span class="kpi-icon">💰</span>
            <div class="kpi-label">Total Revenue</div>
            <div class="kpi-value">Rs.{rev/1e5:.2f}L</div>
            <div class="kpi-sub">Completed orders only</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="kpi-card green">
            <span class="kpi-icon">📦</span>
            <div class="kpi-label">Total Orders</div>
            <div class="kpi-value">{int(ords):,}</div>
            <div class="kpi-sub">Across all channels</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="kpi-card amber">
            <span class="kpi-icon">👥</span>
            <div class="kpi-label">Patients</div>
            <div class="kpi-value">{int(pats):,}</div>
            <div class="kpi-sub">Registered profiles</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="kpi-card rose">
            <span class="kpi-icon">💊</span>
            <div class="kpi-label">Drugs Listed</div>
            <div class="kpi-value">{int(drgs)}</div>
            <div class="kpi-sub">Active SKUs</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class="kpi-card purple">
            <span class="kpi-icon">🛒</span>
            <div class="kpi-label">Avg Order Value</div>
            <div class="kpi-value">Rs.{int(aov):,}</div>
            <div class="kpi-sub">Per completed order</div>
        </div>""", unsafe_allow_html=True)
    with c6:
        color_cls = "rose" if at_risk > 5 else "cyan"
        st.markdown(f"""<div class="kpi-card {color_cls}">
            <span class="kpi-icon">⚠️</span>
            <div class="kpi-label">SKUs At Risk</div>
            <div class="kpi-value">{at_risk}</div>
            <div class="kpi-sub">Low stock or near expiry</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Year filter ───────────────────────────────────────────────────────────
    years_df = run_query("SELECT DISTINCT STRFTIME('%Y', order_date) AS yr FROM orders WHERE status='completed' ORDER BY yr")
    all_years = years_df["yr"].tolist()
    sel_year = st.selectbox("📅 Filter by Year", ["All Years"] + all_years, index=0, key="dash_year")
    year_filter = f"AND STRFTIME('%Y', order_date) = '{sel_year}'" if sel_year != "All Years" else ""

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Revenue trend + Category donut ─────────────────────────────────
    col1, col2 = st.columns([3, 2])

    with col1:
        df_monthly = run_query(f"""
            SELECT STRFTIME('%Y-%m', order_date) AS month,
                   ROUND(SUM(total_amount)/1000,1) AS revenue_k,
                   COUNT(*) AS orders
            FROM orders WHERE status='completed' {year_filter}
            GROUP BY month ORDER BY month
        """)
        fig = go.Figure()
        fig.add_traces([
            go.Bar(x=df_monthly["month"], y=df_monthly["revenue_k"],
                   name="Revenue (Rs.K)",
                   marker=dict(color="#3b82f6", opacity=0.85,
                               line=dict(color="#2563eb", width=0.5))),
            go.Scatter(x=df_monthly["month"], y=df_monthly["orders"],
                       name="Orders", yaxis="y2",
                       line=dict(color="#f59e0b", width=2.5, shape="spline"),
                       mode="lines")
        ])
        fig.update_layout(
            **CHART_LAYOUT,
            title=dict(text="Monthly Revenue & Orders Trend", font=dict(size=15, color="#0f172a")),
            height=340,
            yaxis=dict(title="Revenue (Rs. thousands)", showgrid=True, gridcolor="#f1f5f9"),
            yaxis2=dict(title="Orders", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", y=1.12, x=0),
            xaxis=dict(showgrid=False, tickangle=-30),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("⚠️ 2026 data is partial (Jan–May only) — the drop is expected, not a trend.")

    with col2:
        df_cat = run_query("""
            SELECT d.category, ROUND(SUM(oi.quantity*oi.unit_price)/1000,1) AS rev_k
            FROM order_items oi JOIN drugs d ON d.drug_id=oi.drug_id
            JOIN orders o ON o.order_id=oi.order_id
            WHERE o.status='completed'
            GROUP BY d.category ORDER BY rev_k DESC
        """)
        fig2 = px.pie(df_cat, names="category", values="rev_k", hole=0.55,
                      color_discrete_sequence=COLORS)
        fig2.update_traces(textposition="outside", textinfo="label+percent",
                           pull=[0.05]+[0]*(len(df_cat)-1))
        fig2.update_layout(
            **CHART_LAYOUT,
            title=dict(text="Revenue by Category", font=dict(size=15, color="#0f172a")),
            height=340,
            showlegend=False,
            annotations=[dict(text=f"Rs.{df_cat.rev_k.sum()/100:.1f}L",
                              x=0.5, y=0.5, font_size=16, showarrow=False,
                              font=dict(color="#0f172a", family="DM Sans"))]
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Row 2: Top drugs + Payment + Channel ──────────────────────────────────
    col3, col4, col5 = st.columns([3, 2, 2])

    with col3:
        df_top = run_query("""
            SELECT d.name, ROUND(SUM(oi.quantity*oi.unit_price)/1000,1) AS rev_k
            FROM order_items oi JOIN drugs d ON d.drug_id=oi.drug_id
            JOIN orders o ON o.order_id=oi.order_id
            WHERE o.status='completed'
            GROUP BY d.drug_id ORDER BY rev_k DESC LIMIT 10
        """)
        df_top = df_top.sort_values("rev_k")
        fig3 = go.Figure(go.Bar(
            y=df_top["name"], x=df_top["rev_k"], orientation="h",
            marker=dict(
                color=df_top["rev_k"],
                colorscale=[[0,"#bfdbfe"],[0.5,"#3b82f6"],[1,"#1d4ed8"]],
                showscale=False,
                line=dict(color="rgba(0,0,0,0)", width=0)
            ),
            text=df_top["rev_k"].apply(lambda v: f"Rs.{v}K"),
            textposition="inside",
            insidetextanchor="end",
            textfont=dict(color="white", size=11),
        ))
        fig3.update_layout(
            **CHART_LAYOUT,
            title=dict(text="Top 10 Drugs by Revenue", font=dict(size=15, color="#0f172a")),
            height=360,
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Revenue (Rs. thousands)"),
            yaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        df_pay = run_query("SELECT payment_mode, COUNT(*) AS orders FROM orders GROUP BY payment_mode ORDER BY orders DESC")
        fig4 = px.bar(df_pay, x="payment_mode", y="orders",
                      color="payment_mode",
                      text="orders",
                      color_discrete_sequence=COLORS)
        fig4.update_traces(marker_line_width=0, texttemplate="%{text:,}", textposition="outside")
        fig4.update_layout(
            **CHART_LAYOUT,
            title=dict(text="Payment Methods", font=dict(size=15, color="#0f172a")),
            height=360, showlegend=False,
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Orders"),
            uniformtext_minsize=9,
        )
        st.plotly_chart(fig4, use_container_width=True)

    with col5:
        df_ch = run_query("""
            SELECT channel, COUNT(*) AS orders, ROUND(SUM(total_amount)/1000,1) AS rev_k
            FROM orders WHERE status='completed' GROUP BY channel
        """)
        fig5 = px.pie(df_ch, names="channel", values="rev_k", hole=0.5,
                      color_discrete_sequence=["#3b82f6","#10b981"])
        fig5.update_traces(textinfo="label+percent")
        fig5.update_layout(
            **CHART_LAYOUT,
            title=dict(text="Online vs Walk-in", font=dict(size=15, color="#0f172a")),
            height=360, showlegend=False,
        )
        st.plotly_chart(fig5, use_container_width=True)

    # ── Row 3: Order Heatmap (Day × Hour) ────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🕐 Order Activity Heatmap")
    df_heat = run_query(f"""
        SELECT
            CASE CAST(STRFTIME('%w', order_date) AS INTEGER)
                WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue'
                WHEN 3 THEN 'Wed' WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri'
                WHEN 6 THEN 'Sat'
            END AS day,
            CAST(STRFTIME('%w', order_date) AS INTEGER) AS day_num,
            CAST(STRFTIME('%H', order_date) AS INTEGER) AS hour,
            COUNT(*) AS orders
        FROM orders WHERE status='completed' {year_filter}
        GROUP BY day_num, hour ORDER BY day_num, hour
    """)
    if not df_heat.empty:
        pivot = df_heat.pivot_table(index='hour', columns='day', values='orders', fill_value=0)
        day_order = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        pivot = pivot.reindex(columns=[d for d in day_order if d in pivot.columns])
        fig_heat = px.imshow(
            pivot,
            labels=dict(x="Day of Week", y="Hour of Day", color="Orders"),
            color_continuous_scale=[[0,"#0f172a"],[0.3,"#1e3a5f"],[0.6,"#2563eb"],[1,"#60a5fa"]],
            title="Order Volume by Day × Hour",
            aspect="auto",
            text_auto=True,
        )
        fig_heat.update_layout(
            **CHART_LAYOUT,
            height=380,
            title=dict(font=dict(size=15, color="#f8fafc")),
            xaxis=dict(side="top", showgrid=False, tickfont=dict(color="#94a3b8")),
            yaxis=dict(showgrid=False, tickfont=dict(color="#94a3b8"),
                       ticktext=[f"{h:02d}:00" for h in range(24)],
                       tickvals=list(range(24))),
            coloraxis_showscale=True,
            coloraxis_colorbar=dict(tickfont=dict(color="#94a3b8"), title=dict(font=dict(color="#94a3b8"))),
        )
        fig_heat.update_traces(textfont=dict(size=9, color="rgba(255,255,255,0.6)"))
        st.plotly_chart(fig_heat, use_container_width=True)
        st.caption("💡 Darker blue = more orders. Use this to plan staffing, stock replenishment, and push notification timing.")

    # ── Row 4: Patient Age Group + Gender ─────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 👤 Patient Demographics")
    dcol1, dcol2, dcol3 = st.columns([2, 2, 1])

    with dcol1:
        df_age = run_query(f"""
            SELECT
                CASE
                    WHEN age < 18 THEN '0–17'
                    WHEN age < 30 THEN '18–29'
                    WHEN age < 40 THEN '30–39'
                    WHEN age < 50 THEN '40–49'
                    WHEN age < 60 THEN '50–59'
                    WHEN age < 70 THEN '60–69'
                    WHEN age < 80 THEN '70–79'
                    ELSE '80+'
                END AS age_group,
                COUNT(*) AS patients
            FROM patients GROUP BY age_group ORDER BY MIN(age)
        """)
        fig_age = go.Figure(go.Bar(
            x=df_age["age_group"], y=df_age["patients"],
            marker=dict(
                color=df_age["patients"],
                colorscale=[[0,"#1e3a5f"],[0.5,"#3b82f6"],[1,"#60a5fa"]],
                showscale=False,
                line=dict(width=0)
            ),
            text=df_age["patients"],
            texttemplate="%{text}",
            textposition="outside",
            textfont=dict(color="#94a3b8", size=11),
        ))
        fig_age.update_layout(
            **CHART_LAYOUT,
            title=dict(text="Patients by Age Group", font=dict(size=15, color="#f8fafc")),
            height=300,
            xaxis=dict(showgrid=False, tickfont=dict(color="#94a3b8")),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color="#94a3b8")),
        )
        st.plotly_chart(fig_age, use_container_width=True)

    with dcol2:
        df_state = run_query(f"""
            SELECT p.state, COUNT(DISTINCT p.patient_id) AS patients,
                   ROUND(SUM(o.total_amount)/1000,1) AS rev_k
            FROM patients p
            JOIN orders o ON o.patient_id=p.patient_id
            WHERE o.status='completed' {year_filter}
            GROUP BY p.state ORDER BY rev_k DESC LIMIT 10
        """)
        fig_state = px.bar(df_state, x="rev_k", y="state", orientation="h",
                           color="rev_k",
                           color_continuous_scale=[[0,"#1e3a5f"],[1,"#10b981"]],
                           labels={"rev_k":"Revenue (Rs.K)", "state":"State"},
                           title="Top States by Revenue")
        fig_state.update_layout(
            **CHART_LAYOUT,
            height=300,
            title=dict(font=dict(size=15, color="#f8fafc")),
            coloraxis_showscale=False,
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color="#94a3b8")),
            yaxis=dict(showgrid=False, tickfont=dict(color="#94a3b8")),
        )
        st.plotly_chart(fig_state, use_container_width=True)

    with dcol3:
        df_gender = run_query("SELECT gender, COUNT(*) AS count FROM patients GROUP BY gender")
        fig_gender = px.pie(df_gender, names="gender", values="count", hole=0.6,
                            color_discrete_sequence=["#3b82f6","#f43f5e","#94a3b8"],
                            title="Gender Mix")
        fig_gender.update_traces(textinfo="label+percent", textfont=dict(size=11))
        fig_gender.update_layout(
            **CHART_LAYOUT,
            height=300,
            title=dict(font=dict(size=15, color="#f8fafc")),
            showlegend=False,
        )
        st.plotly_chart(fig_gender, use_container_width=True)

    # ── Key Insights ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 💡 Key Business Insights")
    i1, i2, i3, i4 = st.columns(4)
    insights = [
        ("🏆", "Top Category", "blue", "Antibiotics leads at 17.1% revenue share — driven by consistent demand from acute illness cycles year-round."),
        ("📱", "Online Dominates", "green", "60% of orders are online. Every Rs.1 invested in mobile UX has outsized revenue impact."),
        ("💳", "UPI First", "amber", "UPI is the #1 payment method — aligns with India's rapid digital payment adoption."),
        ("📈", "Seasonal Peaks", "rose", "Revenue spikes in Nov–Feb (winter) and Jun–Aug (monsoon). Stock up 4 weeks ahead to avoid stockouts."),
    ]
    for col, (icon, title, color, text) in zip([i1,i2,i3,i4], insights):
        border_colors = {"blue":"#3b82f6","green":"#10b981","amber":"#f59e0b","rose":"#f43f5e"}
        bc = border_colors[color]
        with col:
            st.markdown(f"""<div class="insight-box" style="border-left-color:{bc}">
                <b>{icon} {title}</b><br><span style="color:rgba(255,255,255,0.6)">{text}</span>
            </div>""", unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="footer">
        💊 MedCart Intelligence Platform &nbsp;|&nbsp;
        Built by <b>Aftab Dayer</b> &nbsp;|&nbsp;
        <a href='https://github.com/aftabdayer/medcart-analytics' target='_blank'>GitHub</a> &nbsp;|&nbsp;
        <a href='https://www.linkedin.com/in/aftabdayer' target='_blank'>LinkedIn</a> &nbsp;|&nbsp;
        <span>Python · SQLite · Plotly · Groq AI · Streamlit</span>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — INVENTORY ALERTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "inventory":
    st.markdown('<p class="page-title">📦 Inventory Risk Alerts</p>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">Real-time stock and expiry monitoring</p>', unsafe_allow_html=True)

    df_inv = run_query("""
        SELECT drug_name, category, stock_qty, days_to_expiry, risk_status
        FROM v_inventory_risk ORDER BY stock_qty ASC
    """)

    risk_counts = df_inv["risk_status"].value_counts()
    out_of_stock = int(risk_counts.get("Out of Stock", 0))
    low_stock    = int(risk_counts.get("Low Stock", 0))
    near_expiry  = int(risk_counts.get("Near Expiry", 0))
    healthy      = int(risk_counts.get("Healthy", 0))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 Out of Stock", out_of_stock)
    c2.metric("🟠 Low Stock",    low_stock)
    c3.metric("🟡 Near Expiry",  near_expiry)
    c4.metric("🟢 Healthy",      healthy)

    st.divider()
    col1, col2 = st.columns([3, 2])

    with col1:
        filter_risk = st.selectbox("Filter by risk", ["All", "Out of Stock", "Low Stock", "Near Expiry", "Healthy"])
        df_show = df_inv if filter_risk == "All" else df_inv[df_inv["risk_status"] == filter_risk]
        df_display = df_show.rename(columns={
            "drug_name": "Drug Name",
            "category": "Category",
            "stock_qty": "Stock",
            "days_to_expiry": "Days to Expiry",
            "risk_status": "Risk Status"
        })
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=420)

    with col2:
        fig = px.scatter(df_inv, x="stock_qty", y="days_to_expiry",
                         color="risk_status", hover_name="drug_name",
                         color_discrete_map={
                             "Out of Stock":"#ef4444","Low Stock":"#f97316",
                             "Near Expiry":"#f59e0b","Healthy":"#22c55e"
                         },
                         title="Stock vs Expiry Matrix",
                         labels={"stock_qty":"Current Stock","days_to_expiry":"Days to Expiry"})
        fig.update_layout(height=420, margin=dict(t=50,b=30,l=10,r=10),
                          plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🤖 AI Restock Recommendations")
    if st.button("Generate AI Recommendations", type="primary"):
        problem_drugs = df_inv[df_inv["risk_status"] != "Healthy"]["drug_name"].tolist()[:10]
        prompt = f"""You are a pharmacy supply chain analyst for MedCart, an Indian online pharmacy.
Drugs needing attention: {problem_drugs}

Give 5 specific, actionable restock recommendations. For each: drug name, urgency, recommended action, and why.
Be concise and use Rs. where relevant. Format as numbered list."""
        with st.spinner("Generating recommendations..."):
            recs = groq_ask(prompt, max_tokens=700)
        st.markdown(recs)

    st.markdown("""<div class="footer">💊 MedCart Intelligence Platform &nbsp;|&nbsp; Built by <b>Aftab Dayer</b> &nbsp;|&nbsp; <a href='https://github.com/aftabdayer/medcart-analytics' target='_blank'>GitHub</a> &nbsp;|&nbsp; <a href='https://www.linkedin.com/in/aftabdayer' target='_blank'>LinkedIn</a></div>""", unsafe_allow_html=True)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "customers":
    st.markdown('<p class="page-title">👥 Customer Insights</p>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">Patient segmentation, lifetime value, and retention analytics</p>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["RFM Segmentation", "Chronic vs Regular", "Top Patients"])

    with tab1:
        df_rfm = run_query("SELECT * FROM v_rfm LIMIT 600")
        col1, col2 = st.columns(2)
        with col1:
            # Segment by frequency
            df_rfm["segment"] = pd.cut(
                df_rfm["frequency"],
                bins=[0, 2, 5, 10, 999],
                labels=["One-time (1-2)", "Occasional (3-5)", "Regular (6-10)", "VIP (10+)"]
            )
            seg_counts = df_rfm["segment"].value_counts().reset_index()
            seg_counts.columns = ["segment", "count"]
            fig = px.pie(seg_counts, names="segment", values="count",
                         title="Customer Segments",
                         color_discrete_sequence=px.colors.qualitative.Bold, hole=0.4)
            fig.update_layout(height=350, margin=dict(t=50,b=20,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.scatter(df_rfm, x="frequency", y="monetary",
                              color="segment",
                              title="Frequency vs Spend per Patient",
                              labels={"frequency":"Number of Orders","monetary":"Total Spend (Rs.)"},
                              opacity=0.7)
            fig2.update_layout(height=350, margin=dict(t=50,b=30,l=10,r=10),
                               plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        df_chronic = run_query("""
            SELECT p.is_chronic,
                   COUNT(DISTINCT p.patient_id) AS patients,
                   ROUND(AVG(o.total_amount),0) AS avg_order_value,
                   ROUND(SUM(o.total_amount)/COUNT(DISTINCT p.patient_id),0) AS lifetime_value,
                   COUNT(o.order_id) AS total_orders
            FROM patients p
            JOIN orders o ON o.patient_id=p.patient_id
            WHERE o.status='completed'
            GROUP BY p.is_chronic
        """)
        df_chronic["Type"] = df_chronic["is_chronic"].map({1:"Chronic", 0:"Regular"})

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df_chronic, x="Type", y="lifetime_value",
                         color="Type", title="Avg Lifetime Value: Chronic vs Regular",
                         color_discrete_map={"Chronic":"#3b82f6","Regular":"#94a3b8"})
            fig.update_layout(height=320, showlegend=False,
                               plot_bgcolor="white", paper_bgcolor="white",
                               margin=dict(t=50,b=30,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.bar(df_chronic, x="Type", y="avg_order_value",
                          color="Type", title="Avg Order Value: Chronic vs Regular",
                          color_discrete_map={"Chronic":"#10b981","Regular":"#94a3b8"})
            fig2.update_layout(height=320, showlegend=False,
                                plot_bgcolor="white", paper_bgcolor="white",
                                margin=dict(t=50,b=30,l=10,r=10))
            st.plotly_chart(fig2, use_container_width=True)

        df_chronic_show = df_chronic[["Type","patients","avg_order_value","lifetime_value","total_orders"]]
        st.dataframe(df_chronic_show, use_container_width=True, hide_index=True)

    with tab3:
        df_top = run_query("""
            SELECT p.name, p.city, p.age,
                   CASE WHEN p.is_chronic=1 THEN 'Chronic' ELSE 'Regular' END AS type,
                   COUNT(o.order_id) AS orders,
                   ROUND(SUM(o.total_amount),0) AS total_spent
            FROM patients p
            JOIN orders o ON o.patient_id=p.patient_id
            WHERE o.status='completed'
            GROUP BY p.patient_id ORDER BY total_spent DESC LIMIT 20
        """)
        fig = px.bar(df_top.head(10), x="name", y="total_spent",
                     color="type", title="Top 10 Patients by Lifetime Value",
                     color_discrete_map={"Chronic":"#3b82f6","Regular":"#94a3b8"})
        fig.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(t=50,b=80,l=10,r=10))
        fig.update_xaxes(tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_top, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — DEMAND FORECAST
# ══════════════════════════════════════════════════════════════════════════════
elif page == "forecast":
    st.markdown('<p class="page-title">📈 Demand Forecast</p>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">AI-powered 4-week sales forecast by drug category</p>', unsafe_allow_html=True)

    df_fc = None
    if os.path.exists(FORECAST_CSV):
        df_fc = pd.read_csv(FORECAST_CSV)

    if df_fc is None:
        st.info("Generating forecast from historical data...")
        df_hist = run_query("""
            SELECT d.category,
                   STRFTIME('%Y-%m', o.order_date) AS month,
                   SUM(oi.quantity) AS units_sold
            FROM order_items oi
            JOIN drugs d ON d.drug_id=oi.drug_id
            JOIN orders o ON o.order_id=oi.order_id
            WHERE o.status='completed'
            GROUP BY d.category, month ORDER BY d.category, month
        """)
        forecast_rows = []
        next_months = [(datetime.date.today().replace(day=1) + datetime.timedelta(days=32*i)).strftime('%Y-%m')
                       for i in range(1, 5)]
        for cat, grp in df_hist.groupby("category"):
            recent = grp.tail(3)["units_sold"].mean()
            growth = grp["units_sold"].pct_change().mean()
            growth = min(max(growth if not pd.isna(growth) else 0, -0.05), 0.1)
            for i, m in enumerate(next_months):
                predicted = int(recent * (1 + growth) ** (i + 1))
                forecast_rows.append({
                    "Category": cat, "Week": m,
                    "Forecasted_Qty": max(predicted, 0),
                    "lower": int(predicted * 0.85),
                    "upper": int(predicted * 1.15),
                })
        df_fc = pd.DataFrame(forecast_rows)

    # Normalise column names
    df_fc.columns = [c.strip() for c in df_fc.columns]
    cat_col = "Category" if "Category" in df_fc.columns else df_fc.columns[0]
    qty_col = "Forecasted_Qty" if "Forecasted_Qty" in df_fc.columns else [c for c in df_fc.columns if "qty" in c.lower() or "units" in c.lower()][0]
    week_col = "Week" if "Week" in df_fc.columns else df_fc.columns[1]

    categories = sorted(df_fc[cat_col].unique().tolist())
    selected_cat = st.selectbox("Select Drug Category", ["All"] + categories)
    df_plot = df_fc if selected_cat == "All" else df_fc[df_fc[cat_col] == selected_cat]

    if selected_cat != "All":
        fig = go.Figure()
        fig.add_scatter(x=df_plot[week_col], y=df_plot[qty_col],
                        mode="lines+markers", name="Forecast",
                        line=dict(color="#3b82f6", width=2.5), marker=dict(size=8))
        if "upper" in df_plot.columns:
            fig.add_scatter(
                x=list(df_plot[week_col]) + list(df_plot[week_col])[::-1],
                y=list(df_plot["upper"]) + list(df_plot["lower"])[::-1],
                fill="toself", fillcolor="rgba(59,130,246,0.1)",
                line=dict(color="rgba(59,130,246,0)"), name="Confidence Band")
        fig.update_layout(title=f"4-Week Demand Forecast — {selected_cat}",
                          xaxis_title="Week", yaxis_title="Units",
                          height=380, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(t=50,b=40,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = px.bar(df_plot, x=week_col, y=qty_col, color=cat_col,
                     title="4-Week Demand Forecast — All Categories",
                     barmode="group",
                     labels={qty_col:"Predicted Units", week_col:"Week"})
        fig.update_layout(height=400, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(t=50,b=40,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    total_forecast = df_fc.groupby(cat_col)[qty_col].sum().reset_index()
    total_forecast.columns = ["Category", "Forecasted Units (4 weeks)"]
    total_forecast = total_forecast.sort_values("Forecasted Units (4 weeks)", ascending=False)
    st.subheader("📋 Forecast Summary Table")
    st.dataframe(total_forecast, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🤖 AI Procurement Advice")
    if st.button("Get AI Procurement Recommendations", type="primary"):
        top_cats = total_forecast.head(5).to_string(index=False)
        prompt = f"""You are a pharmacy procurement manager for MedCart India.
Based on these 4-week demand forecasts:
{top_cats}

Give 5 specific procurement recommendations. Include: which categories to prioritise ordering,
how much buffer stock to maintain, and any seasonal factors for Indian pharmacy demand.
Be concise and actionable."""
        with st.spinner("Generating advice..."):
            advice = groq_ask(prompt, max_tokens=600)
        st.markdown(advice)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — AI CHATBOT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "chatbot":
    st.markdown('<p class="page-title">🤖 AI Chatbot</p>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">Ask anything about your pharmacy data in plain English</p>', unsafe_allow_html=True)

    rev, ords, pats, drgs = load_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Revenue", f"Rs.{rev/1e5:.2f}L")
    c2.metric("📦 Orders",  f"{int(ords):,}")
    c3.metric("👥 Patients",f"{int(pats):,}")
    c4.metric("💊 Drugs",   f"{int(drgs)}")
    st.divider()

    sample_qs = [
        "Which drug makes highest revenue?",
        "How many chronic patients do we have?",
        "Which drugs need urgent restocking?",
        "What is our average order value?",
        "Compare chronic vs regular patient spending",
        "Which payment mode is most popular?",
        "What are our monthly revenue trends?",
        "Who are the top patients by spending?",
        "Which drugs are near expiry?",
        "Give me 3 business recommendations",
        "Revenue by drug category",
        "Online vs walk-in orders comparison",
    ]

    cols = st.columns(4)
    for i, q in enumerate(sample_qs):
        if cols[i % 4].button(q, key=f"sq_{i}", use_container_width=True):
            st.session_state.pending_chat = q

    st.divider()

    def query_db_for_chat(question: str) -> str:
        q = question.lower()
        conn = get_conn()
        result = ""
        try:
            if any(w in q for w in ["highest revenue","top drug","best drug","most revenue","drug revenue","which drug","drug make"]):
                df = pd.read_sql_query("""
                    SELECT d.name, d.category,
                           ROUND(SUM(oi.quantity*oi.unit_price),0) AS revenue,
                           SUM(oi.quantity) AS units_sold
                    FROM order_items oi JOIN drugs d ON d.drug_id=oi.drug_id
                    JOIN orders o ON o.order_id=oi.order_id WHERE o.status='completed'
                    GROUP BY d.drug_id ORDER BY revenue DESC LIMIT 10
                """, conn)
                result = "Top 10 drugs by revenue:\n" + df.to_string(index=False)

            elif any(w in q for w in ["category","cardiac","diabetes","antibiotics","supplements","gastro","neuro","steroids"]):
                df = pd.read_sql_query("""
                    SELECT d.category, ROUND(SUM(oi.quantity*oi.unit_price),0) AS revenue
                    FROM order_items oi JOIN drugs d ON d.drug_id=oi.drug_id
                    JOIN orders o ON o.order_id=oi.order_id WHERE o.status='completed'
                    GROUP BY d.category ORDER BY revenue DESC
                """, conn)
                result = "Revenue by category:\n" + df.to_string(index=False)

            elif any(w in q for w in ["chronic","regular","patient type","ltv","lifetime"]):
                df = pd.read_sql_query("""
                    SELECT p.is_chronic, COUNT(DISTINCT p.patient_id) AS patients,
                           ROUND(AVG(o.total_amount),0) AS avg_order_value,
                           ROUND(SUM(o.total_amount)/COUNT(DISTINCT p.patient_id),0) AS lifetime_value
                    FROM patients p JOIN orders o ON o.patient_id=p.patient_id
                    WHERE o.status='completed' GROUP BY p.is_chronic
                """, conn)
                result = "Chronic(1) vs Regular(0):\n" + df.to_string(index=False)

            elif any(w in q for w in ["stock","inventory","expir","restock","risk"]):
                df = pd.read_sql_query("""
                    SELECT drug_name, category, stock_qty, days_to_expiry, risk_status
                    FROM v_inventory_risk WHERE risk_status != 'Healthy'
                    ORDER BY stock_qty ASC LIMIT 15
                """, conn)
                result = "Drugs needing attention:\n" + df.to_string(index=False)

            elif any(w in q for w in ["payment","upi","cash","card","net banking"]):
                df = pd.read_sql_query("""
                    SELECT payment_mode, COUNT(*) AS orders,
                           ROUND(COUNT(*)*100.0/(SELECT COUNT(*) FROM orders),1) AS pct
                    FROM orders GROUP BY payment_mode ORDER BY orders DESC
                """, conn)
                result = "Payment modes:\n" + df.to_string(index=False)

            elif any(w in q for w in ["channel","online","walk"]):
                df = pd.read_sql_query("""
                    SELECT channel, COUNT(*) AS orders, ROUND(SUM(total_amount),0) AS revenue
                    FROM orders WHERE status='completed' GROUP BY channel
                """, conn)
                result = "Order channels:\n" + df.to_string(index=False)

            elif any(w in q for w in ["top patient","best customer","highest spend","most spent"]):
                df = pd.read_sql_query("""
                    SELECT p.name, p.city, CASE WHEN p.is_chronic=1 THEN 'Chronic' ELSE 'Regular' END AS type,
                           COUNT(o.order_id) AS orders, ROUND(SUM(o.total_amount),0) AS total_spent
                    FROM patients p JOIN orders o ON o.patient_id=p.patient_id
                    WHERE o.status='completed' GROUP BY p.patient_id ORDER BY total_spent DESC LIMIT 10
                """, conn)
                result = "Top 10 patients:\n" + df.to_string(index=False)

            elif any(w in q for w in ["monthly","trend","revenue trend","month","seasonal"]):
                df = pd.read_sql_query("""
                    SELECT STRFTIME('%Y-%m', order_date) AS month,
                           COUNT(*) AS orders, ROUND(SUM(total_amount),0) AS revenue
                    FROM orders WHERE status='completed' GROUP BY month ORDER BY month DESC LIMIT 24
                """, conn)
                result = "Monthly revenue:\n" + df.to_string(index=False)

            elif any(w in q for w in ["average order","avg order","aov","average"]):
                df = pd.read_sql_query("SELECT ROUND(AVG(total_amount),2) FROM orders WHERE status='completed'", conn)
                result = f"Average order value: Rs.{df.iloc[0,0]:,.2f}"

            elif any(w in q for w in ["recommend","suggest","improve","insight","action","business"]):
                df1 = pd.read_sql_query("SELECT risk_status, COUNT(*) AS drugs FROM v_inventory_risk GROUP BY risk_status", conn)
                df2 = pd.read_sql_query("""
                    SELECT d.category, ROUND(SUM(oi.quantity*oi.unit_price),0) AS revenue
                    FROM order_items oi JOIN drugs d ON d.drug_id=oi.drug_id
                    JOIN orders o ON o.order_id=oi.order_id WHERE o.status='completed'
                    GROUP BY d.category ORDER BY revenue DESC LIMIT 5
                """, conn)
                result = f"Inventory:\n{df1.to_string(index=False)}\n\nTop categories:\n{df2.to_string(index=False)}"

            elif any(w in q for w in ["supplier","supply"]):
                df = pd.read_sql_query("SELECT name, city, state, rating FROM suppliers ORDER BY rating DESC", conn)
                result = "Suppliers:\n" + df.to_string(index=False)

            else:
                result = f"Overview: Revenue Rs.{rev/1e5:.2f}L | Orders {int(ords):,} | Patients {int(pats):,} | Drugs {int(drgs)}"

        except Exception as e:
            result = f"DB error: {e}"
        finally:
            conn.close()
        return result

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [{
            "role": "assistant",
            "content": "👋 Hi! I'm your **MedCart AI Analyst**.\n\nI have full access to your pharmacy data — **12,000 orders, 600 patients, 55 drugs**.\n\nAsk me anything in plain English, or click a sample question above!"
        }]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "💊"):
            st.markdown(msg["content"])

    if "pending_chat" in st.session_state:
        question = st.session_state.pending_chat
        del st.session_state.pending_chat
        st.session_state.chat_messages.append({"role": "user", "content": question})
        data = query_db_for_chat(question)
        prompt = f"""You are MedCart AI, an expert pharmacy data analyst for an Indian online pharmacy.
Use the data below to answer the question. Use Rs. for Indian rupees. Be concise and give actionable insights.

DATA:
{data}

QUESTION: {question}"""
        with st.chat_message("user", avatar="🧑"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="💊"):
            with st.spinner("Analysing..."):
                answer = groq_ask(prompt)
            st.markdown(answer)
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
        st.rerun()

    if user_input := st.chat_input("Ask anything about your pharmacy data..."):
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        data = query_db_for_chat(user_input)
        prompt = f"""You are MedCart AI, an expert pharmacy data analyst for an Indian online pharmacy.
Use the data below to answer the question. Use Rs. for Indian rupees. Be concise and give actionable insights.

DATA:
{data}

QUESTION: {user_input}"""
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)
        with st.chat_message("assistant", avatar="💊"):
            with st.spinner("Analysing..."):
                answer = groq_ask(prompt)
            st.markdown(answer)
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})

    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_messages = []
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — PRESCRIPTION SCANNER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "rxscanner":
    st.markdown('<p class="page-title">🧾 Prescription Scanner</p>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">Upload a prescription image — AI reads it and checks drug availability</p>', unsafe_allow_html=True)

    df_drugs = run_query("SELECT name, category, unit_price AS price FROM drugs ORDER BY name")

    uploaded = st.file_uploader("Upload Prescription Image (JPG, PNG)", type=["jpg","jpeg","png"])

    if uploaded:
        st.image(uploaded, caption="Uploaded Prescription", width=400)
        st.divider()

        img_bytes = uploaded.read()
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        media_type = "image/jpeg" if uploaded.name.lower().endswith(("jpg","jpeg")) else "image/png"

        with st.spinner("🔍 AI is reading the prescription..."):
            try:
                groq_client = get_groq()
                response = groq_client.chat.completions.create(
                    model="llama-3.2-11b-vision-preview",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64_img}"}},
                            {"type": "text", "text": """This is a medical prescription from India.
Extract all drug/medicine names mentioned.
Return ONLY a JSON list like: {"drugs": ["Drug1", "Drug2", "Drug3"]}
If no drugs found, return: {"drugs": []}
Return nothing else."""}
                        ]
                    }],
                    max_tokens=300,
                    temperature=0.1,
                )
                raw = response.choices[0].message.content.strip()
                try:
                    clean = re.sub(r"```json|```", "", raw).strip()
                    parsed = json.loads(clean)
                    extracted_drugs = parsed.get("drugs", [])
                except Exception:
                    extracted_drugs = re.findall(r'[A-Z][a-z]+(?:\s[A-Z][a-z]+)*', raw)
            except Exception as e:
                st.error(f"Vision model error: {e}")
                st.info("💡 Type drug names manually below.")
                extracted_drugs = []

        if extracted_drugs:
            st.subheader(f"💊 Found {len(extracted_drugs)} drug(s) in prescription")
            results = []
            for drug in extracted_drugs:
                drug_lower = drug.lower()
                matched = df_drugs[df_drugs["name"].str.lower().str.contains(drug_lower.split()[0], na=False)]
                if not matched.empty:
                    row = matched.iloc[0]
                    stock_df = run_query(f"""
                        SELECT stock_qty, risk_status FROM v_inventory_risk
                        WHERE LOWER(drug_name) LIKE '%{drug_lower.split()[0]}%' LIMIT 1
                    """)
                    if not stock_df.empty:
                        stock = int(stock_df.iloc[0]["stock_qty"])
                        risk  = stock_df.iloc[0]["risk_status"]
                    else:
                        stock, risk = "N/A", "Unknown"
                    results.append({
                        "Prescribed Drug": drug,
                        "Matched in Inventory": row["name"],
                        "Category": row["category"],
                        "Price (Rs.)": row["price"],
                        "Stock": stock,
                        "Status": risk
                    })
                else:
                    results.append({
                        "Prescribed Drug": drug,
                        "Matched in Inventory": "❌ Not found",
                        "Category": "-", "Price (Rs.)": "-",
                        "Stock": "-", "Status": "Not in catalog"
                    })

            df_results = pd.DataFrame(results)
            st.dataframe(df_results, use_container_width=True, hide_index=True)

            total_price = df_results[df_results["Price (Rs.)"] != "-"]["Price (Rs.)"].astype(float).sum()
            if total_price > 0:
                st.metric("💰 Estimated Prescription Cost", f"Rs. {total_price:,.2f}")

            st.divider()
            st.subheader("🤖 AI Prescription Summary")
            drugs_summary = df_results[["Prescribed Drug","Matched in Inventory","Status"]].to_string(index=False)
            prompt = f"""You are a pharmacy assistant at MedCart India.
A patient has uploaded a prescription. Here are the drugs and their availability:
{drugs_summary}

Give a helpful summary: which drugs are available, which are not, and any recommendations for the pharmacist.
Keep it brief and professional."""
            with st.spinner("Generating summary..."):
                summary = groq_ask(prompt, max_tokens=400)
            st.markdown(summary)

        else:
            st.warning("No drug names extracted. Type them manually:")
            manual = st.text_input("Enter drug names (comma separated)", placeholder="Metformin, Amlodipine, Paracetamol")

    else:
        st.info("👆 Upload a prescription image to get started. Supported formats: JPG, PNG")
        st.markdown("""
        **What this scanner does:**
        - Reads drug names from the prescription image using AI vision
        - Checks each drug against your MedCart inventory
        - Shows stock levels and availability
        - Gives an estimated cost
        - Provides a dispensing summary for the pharmacist
        """)
        st.markdown("---")
        st.markdown("**💡 Don't have a prescription to test?** Try typing drug names manually:")
        manual_test = st.text_input("Enter drug names (comma separated)", placeholder="Metformin, Amlodipine, Paracetamol, Insulin Glargine")
        if manual_test:
            drug_list = [d.strip() for d in manual_test.split(",") if d.strip()]
            df_drugs = run_query("SELECT name, category, unit_price AS price FROM drugs ORDER BY name")
            results = []
            for drug in drug_list:
                drug_lower = drug.lower()
                matched = df_drugs[df_drugs["name"].str.lower().str.contains(drug_lower.split()[0], na=False)]
                if not matched.empty:
                    row = matched.iloc[0]
                    stock_df = run_query(f"SELECT stock_qty, risk_status FROM v_inventory_risk WHERE LOWER(drug_name) LIKE '%{drug_lower.split()[0]}%' LIMIT 1")
                    stock = int(stock_df.iloc[0]["stock_qty"]) if not stock_df.empty else "N/A"
                    risk  = stock_df.iloc[0]["risk_status"] if not stock_df.empty else "Unknown"
                    results.append({"Drug": drug, "Matched": row["name"], "Category": row["category"], "Price (Rs.)": row["price"], "Stock": stock, "Status": risk})
                else:
                    results.append({"Drug": drug, "Matched": "❌ Not found", "Category": "-", "Price (Rs.)": "-", "Stock": "-", "Status": "Not in catalog"})
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
            found = [r for r in results if r["Matched"] != "❌ Not found"]
            if found:
                total = sum(r["Price (Rs.)"] for r in found if r["Price (Rs.)"] != "-")
                st.metric("💰 Estimated Cost", f"Rs. {total:,.2f}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — ABOUT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "about":
    st.markdown('<p class="page-title">👤 About This Project</p>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">Built as a portfolio project demonstrating end-to-end data analytics</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        <div style="background:white;border-radius:16px;padding:2rem;border:1px solid #e2e8f0;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <h2 style="color:#0f172a;margin-top:0">💊 MedCart Intelligence Platform</h2>
            <p style="color:#475569;font-size:1rem;line-height:1.7">
                An end-to-end pharmacy analytics platform combining SQL data modelling,
                Python EDA, ML demand forecasting, a Power BI-style dashboard, and an AI analyst —
                purpose-built to demonstrate the kind of analytics stack used at health-retail
                companies like 1mg, PharmEasy, and Apollo Pharmacy.
            </p>
            <hr style="border:none;border-top:1px solid #e2e8f0;margin:1.2rem 0">
            <h3 style="color:#0f172a">🔢 By the Numbers</h3>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:0.8rem">
                <div style="background:#eff6ff;border-radius:10px;padding:1rem;text-align:center">
                    <div style="font-size:1.6rem;font-weight:700;color:#1d4ed8">12,000</div>
                    <div style="color:#64748b;font-size:0.85rem">Orders analysed</div>
                </div>
                <div style="background:#f0fdf4;border-radius:10px;padding:1rem;text-align:center">
                    <div style="font-size:1.6rem;font-weight:700;color:#15803d">Rs.44.8L</div>
                    <div style="color:#64748b;font-size:0.85rem">Revenue modelled</div>
                </div>
                <div style="background:#fefce8;border-radius:10px;padding:1rem;text-align:center">
                    <div style="font-size:1.6rem;font-weight:700;color:#a16207">600</div>
                    <div style="color:#64748b;font-size:0.85rem">Patient profiles</div>
                </div>
                <div style="background:#fdf4ff;border-radius:10px;padding:1rem;text-align:center">
                    <div style="font-size:1.6rem;font-weight:700;color:#7e22ce">0.84</div>
                    <div style="color:#64748b;font-size:0.85rem">ML model R²</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:white;border-radius:16px;padding:2rem;border:1px solid #e2e8f0;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <h3 style="color:#0f172a;margin-top:0">🏗️ What Was Built</h3>
            <table style="width:100%;border-collapse:collapse;font-size:0.9rem">
                <tr style="background:#f8fafc">
                    <td style="padding:10px;font-weight:600;color:#0f172a;border-bottom:1px solid #e2e8f0">Layer</td>
                    <td style="padding:10px;font-weight:600;color:#0f172a;border-bottom:1px solid #e2e8f0">What</td>
                    <td style="padding:10px;font-weight:600;color:#0f172a;border-bottom:1px solid #e2e8f0">Tools</td>
                </tr>
                <tr>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">Database</td>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">7 tables, 4 analytical views, normalized schema</td>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">SQLite, SQL</td>
                </tr>
                <tr style="background:#f8fafc">
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">Data Generation</td>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">12K orders, 600 patients, 55 drugs, realistic Indian data</td>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">Python (stdlib)</td>
                </tr>
                <tr>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">EDA</td>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">10 professional charts: seasonality, RFM, inventory risk</td>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">pandas, matplotlib, seaborn</td>
                </tr>
                <tr style="background:#f8fafc">
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">ML Forecast</td>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">19 features, TimeSeriesSplit CV, 4-week demand forecast</td>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">scikit-learn RandomForest</td>
                </tr>
                <tr>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">Dashboard</td>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">6-page interactive analytics app deployed live</td>
                    <td style="padding:10px;color:#374151;border-bottom:1px solid #f1f5f9">Streamlit, Plotly</td>
                </tr>
                <tr style="background:#f8fafc">
                    <td style="padding:10px;color:#374151">AI Analyst</td>
                    <td style="padding:10px;color:#374151">Natural language Q&A on pharmacy data + Rx scanner</td>
                    <td style="padding:10px;color:#374151">Groq LLaMA 3.3</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1e3a5f,#0d1b2a);border-radius:16px;padding:2rem;color:white;text-align:center">
            <div style="font-size:4rem;margin-bottom:0.5rem">👨‍💻</div>
            <h2 style="color:white;margin:0">Aftab Dayer</h2>
            <p style="color:#94a3b8;margin:0.3rem 0 1.2rem 0;font-size:0.9rem">Data Analyst · Python · SQL · Power BI</p>
            <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:1rem 0">
            <a href="https://github.com/aftabdayer/medcart-analytics" target="_blank"
               style="display:block;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);
                      border-radius:10px;padding:0.7rem;color:white;text-decoration:none;margin-bottom:0.6rem;
                      font-size:0.9rem;transition:all 0.2s">
               🔗 GitHub Repository
            </a>
            <a href="https://www.linkedin.com/in/aftabdayer" target="_blank"
               style="display:block;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);
                      border-radius:10px;padding:0.7rem;color:white;text-decoration:none;margin-bottom:0.6rem;
                      font-size:0.9rem">
               💼 LinkedIn Profile
            </a>
            <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:1rem 0">
            <p style="color:#94a3b8;font-size:0.82rem;margin:0">
                Open to Data Analyst,<br>Business Analyst &<br>Freelance opportunities
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:white;border-radius:16px;padding:1.5rem;border:1px solid #e2e8f0;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
            <h4 style="color:#0f172a;margin-top:0">🛠️ Tech Stack</h4>
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:0.5rem">
                <span style="background:#eff6ff;color:#1d4ed8;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600">Python</span>
                <span style="background:#f0fdf4;color:#15803d;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600">SQLite</span>
                <span style="background:#fefce8;color:#a16207;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600">pandas</span>
                <span style="background:#fdf4ff;color:#7e22ce;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600">scikit-learn</span>
                <span style="background:#fff1f2;color:#be123c;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600">Plotly</span>
                <span style="background:#eff6ff;color:#1d4ed8;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600">Streamlit</span>
                <span style="background:#f0fdf4;color:#15803d;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600">Groq AI</span>
                <span style="background:#fefce8;color:#a16207;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600">Power BI</span>
                <span style="background:#fdf4ff;color:#7e22ce;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600">GitHub</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="footer">
        💊 MedCart Intelligence Platform &nbsp;|&nbsp;
        Built by <b>Aftab Dayer</b> &nbsp;|&nbsp;
        <a href='https://github.com/aftabdayer/medcart-analytics' target='_blank'>GitHub</a> &nbsp;|&nbsp;
        <a href='https://www.linkedin.com/in/aftabdayer' target='_blank'>LinkedIn</a> &nbsp;|&nbsp;
        <span>Python · SQLite · Plotly · Groq AI · Streamlit</span>
    </div>
    """, unsafe_allow_html=True)
