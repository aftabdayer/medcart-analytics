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

# DB is in the same folder as this script
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medcart.db")

# Forecast CSV path
FORECAST_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forecast_4week.csv")
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
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

    .main { background-color: #f0f4f8; }

    [data-testid="stSidebar"] {
        background: linear-gradient(160deg, #0d1b2a 0%, #1b2a3b 100%);
        border-right: 1px solid #1e3a5f;
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] .stButton>button {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        color: #94a3b8 !important;
        border-radius: 10px;
        text-align: left; width: 100%;
        transition: all 0.2s;
        font-size: 0.9rem;
        padding: 0.5rem 0.8rem;
    }
    [data-testid="stSidebar"] .stButton>button:hover {
        background: rgba(56,189,248,0.12);
        border-color: rgba(56,189,248,0.3);
        color: #e0f2fe !important;
    }

    .kpi-card {
        background: white;
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: "";
        position: absolute; top: 0; left: 0; right: 0; height: 4px;
    }
    .kpi-card.blue::before  { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
    .kpi-card.green::before { background: linear-gradient(90deg, #10b981, #34d399); }
    .kpi-card.amber::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
    .kpi-card.rose::before  { background: linear-gradient(90deg, #f43f5e, #fb7185); }

    .kpi-label { font-size: 0.78rem; font-weight: 600; letter-spacing: 0.08em;
                 text-transform: uppercase; color: #94a3b8; margin-bottom: 0.4rem; }
    .kpi-value { font-size: 2rem; font-weight: 700; color: #0f172a; line-height: 1; }
    .kpi-sub   { font-size: 0.8rem; color: #64748b; margin-top: 0.3rem; }

    .chart-card {
        background: white; border-radius: 16px;
        padding: 1.2rem 1.4rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 1rem;
    }
    .section-title {
        font-size: 1.5rem; font-weight: 700; color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .section-sub { font-size: 0.9rem; color: #64748b; margin-bottom: 1.2rem; }

    .risk-pill {
        display: inline-block; padding: 3px 12px;
        border-radius: 20px; font-size: 0.78rem; font-weight: 600;
    }
    .pill-red    { background:#fee2e2; color:#991b1b; }
    .pill-amber  { background:#fef3c7; color:#92400e; }
    .pill-green  { background:#dcfce7; color:#166534; }
    .pill-blue   { background:#dbeafe; color:#1e40af; }

    [data-testid="stMetric"] {
        background: white; border-radius: 12px;
        padding: 1rem; border: 1px solid #e2e8f0;
    }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700 !important; }
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
    rev  = pd.read_sql_query('SELECT ROUND(SUM(total_amount),2) FROM orders WHERE status="completed"', conn).iloc[0,0]
    ords = pd.read_sql_query('SELECT COUNT(*) FROM orders', conn).iloc[0,0]
    pats = pd.read_sql_query('SELECT COUNT(*) FROM patients', conn).iloc[0,0]
    drgs = pd.read_sql_query('SELECT COUNT(*) FROM drugs', conn).iloc[0,0]
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
    }

    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    for label, key in PAGES.items():
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.divider()
    st.caption("Built by Aftab Dayer")
    st.caption("Python · SQLite · Groq · Plotly · Streamlit")

page = st.session_state.page

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
CHART_LAYOUT = dict(
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="DM Sans, sans-serif", color="#374151"),
    margin=dict(t=45, b=30, l=10, r=10),
    hoverlabel=dict(bgcolor="white", font_size=13, font_family="DM Sans"),
)
COLORS = ["#3b82f6","#10b981","#f59e0b","#f43f5e","#8b5cf6","#06b6d4","#ec4899","#14b8a6"]

if page == "dashboard":
    rev, ords, pats, drgs = load_metrics()

    st.markdown('<p class="section-title">📊 Executive Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Live overview of MedCart pharmacy performance</p>', unsafe_allow_html=True)

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="kpi-card blue">
            <div class="kpi-label">💰 Total Revenue</div>
            <div class="kpi-value">Rs.{rev/1e5:.2f}L</div>
            <div class="kpi-sub">Completed orders only</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="kpi-card green">
            <div class="kpi-label">📦 Total Orders</div>
            <div class="kpi-value">{int(ords):,}</div>
            <div class="kpi-sub">Across all channels</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="kpi-card amber">
            <div class="kpi-label">👥 Patients</div>
            <div class="kpi-value">{int(pats):,}</div>
            <div class="kpi-sub">Registered patients</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="kpi-card rose">
            <div class="kpi-label">💊 Drugs Listed</div>
            <div class="kpi-value">{int(drgs)}</div>
            <div class="kpi-sub">Active SKUs</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Revenue trend + Category donut ─────────────────────────────────
    col1, col2 = st.columns([3, 2])

    with col1:
        df_monthly = run_query("""
            SELECT STRFTIME('%Y-%m', order_date) AS month,
                   ROUND(SUM(total_amount)/1000,1) AS revenue_k,
                   COUNT(*) AS orders
            FROM orders WHERE status='completed'
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

    with col2:
        df_cat = run_query("""
            SELECT d.category, ROUND(SUM(oi.line_total)/1000,1) AS rev_k
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
            annotations=[dict(text=f"Rs.{df_cat.rev_k.sum()/1000:.1f}L",
                              x=0.5, y=0.5, font_size=16, showarrow=False,
                              font=dict(color="#0f172a", family="DM Sans"))]
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Row 2: Top drugs + Payment + Channel ──────────────────────────────────
    col3, col4, col5 = st.columns([3, 2, 2])

    with col3:
        df_top = run_query("""
            SELECT d.name, ROUND(SUM(oi.line_total)/1000,1) AS rev_k
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
            textposition="outside",
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
                      color_discrete_sequence=COLORS)
        fig4.update_traces(marker_line_width=0)
        fig4.update_layout(
            **CHART_LAYOUT,
            title=dict(text="Payment Methods", font=dict(size=15, color="#0f172a")),
            height=360, showlegend=False,
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Orders"),
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
        st.dataframe(df_show, use_container_width=True, hide_index=True, height=420)

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


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — CUSTOMERS
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
