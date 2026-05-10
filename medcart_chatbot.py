"""
MedCart AI Analyst — Powered by Groq (Free, Fast, No Quota Issues)
===================================================================
Author : Aftab Dayer
Run    : streamlit run medcart_chatbot.py

Install: pip install streamlit groq pandas
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
from groq import Groq

# ══════════════════════════════════════════════════════════════
# PASTE YOUR GROQ API KEY HERE
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
# ══════════════════════════════════════════════════════════════

DB_PATH = r"C:\Users\Aftab Dayer\Desktop\verilofd\Project\medcart_project\data\medcart.db"

client = Groq(api_key=GROQ_API_KEY)

st.set_page_config(page_title="MedCart AI Analyst", page_icon="💊", layout="wide")
st.markdown("<style>.main{background-color:#f8fafc;}</style>", unsafe_allow_html=True)


@st.cache_data
def load_metrics():
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    rev  = pd.read_sql_query('SELECT ROUND(SUM(total_amount),2) AS v FROM orders WHERE status="completed"', conn).iloc[0,0]
    ords = pd.read_sql_query('SELECT COUNT(*) AS v FROM orders', conn).iloc[0,0]
    pats = pd.read_sql_query('SELECT COUNT(*) AS v FROM patients', conn).iloc[0,0]
    drgs = pd.read_sql_query('SELECT COUNT(*) AS v FROM drugs', conn).iloc[0,0]
    conn.close()
    return {"revenue": rev, "orders": ords, "patients": pats, "drugs": drgs}


def query_db(question: str) -> str:
    q = question.lower()
    conn = sqlite3.connect(DB_PATH)
    result = ""
    try:
        if any(w in q for w in ["highest revenue", "top drug", "best drug", "most revenue", "drug revenue", "which drug", "drug make"]):
            df = pd.read_sql_query("""
                SELECT d.name, d.category,
                       ROUND(SUM(oi.quantity*oi.unit_price),0) AS revenue,
                       SUM(oi.quantity) AS units_sold
                FROM order_items oi
                JOIN drugs d ON d.drug_id=oi.drug_id
                JOIN orders o ON o.order_id=oi.order_id
                WHERE o.status='completed'
                GROUP BY d.drug_id ORDER BY revenue DESC LIMIT 10
            """, conn)
            result = "Top 10 drugs by revenue:\n" + df.to_string(index=False)

        elif any(w in q for w in ["category", "cardiac", "diabetes", "antibiotics", "supplements", "gastro", "neuro"]):
            df = pd.read_sql_query("""
                SELECT d.category, ROUND(SUM(oi.quantity*oi.unit_price),0) AS revenue
                FROM order_items oi
                JOIN drugs d ON d.drug_id=oi.drug_id
                JOIN orders o ON o.order_id=oi.order_id
                WHERE o.status='completed'
                GROUP BY d.category ORDER BY revenue DESC
            """, conn)
            result = "Revenue by category:\n" + df.to_string(index=False)

        elif any(w in q for w in ["chronic", "regular", "patient type", "ltv", "lifetime"]):
            df = pd.read_sql_query("""
                SELECT p.is_chronic,
                       COUNT(DISTINCT p.patient_id) AS patients,
                       ROUND(AVG(o.total_amount),0) AS avg_order_value,
                       ROUND(SUM(o.total_amount)/COUNT(DISTINCT p.patient_id),0) AS lifetime_value
                FROM patients p
                JOIN orders o ON o.patient_id=p.patient_id
                WHERE o.status='completed'
                GROUP BY p.is_chronic
            """, conn)
            result = "Chronic(1) vs Regular(0) patients:\n" + df.to_string(index=False)

        elif any(w in q for w in ["stock", "inventory", "expir", "restock", "risk"]):
            df = pd.read_sql_query("""
                SELECT drug_name, category, stock_qty, days_to_expiry, risk_status
                FROM v_inventory_risk
                WHERE risk_status != 'Healthy'
                ORDER BY stock_qty ASC LIMIT 15
            """, conn)
            result = "Drugs needing attention:\n" + df.to_string(index=False)

        elif any(w in q for w in ["payment", "upi", "cash", "card", "net banking"]):
            df = pd.read_sql_query("""
                SELECT payment_mode, COUNT(*) AS orders,
                       ROUND(COUNT(*)*100.0/(SELECT COUNT(*) FROM orders),1) AS pct
                FROM orders GROUP BY payment_mode ORDER BY orders DESC
            """, conn)
            result = "Payment modes:\n" + df.to_string(index=False)

        elif any(w in q for w in ["channel", "online", "walk"]):
            df = pd.read_sql_query("""
                SELECT channel, COUNT(*) AS orders, ROUND(SUM(total_amount),0) AS revenue
                FROM orders WHERE status='completed' GROUP BY channel
            """, conn)
            result = "Order channels:\n" + df.to_string(index=False)

        elif any(w in q for w in ["top patient", "best customer", "highest spend", "most spent"]):
            df = pd.read_sql_query("""
                SELECT p.name, p.city,
                       CASE WHEN p.is_chronic=1 THEN 'Chronic' ELSE 'Regular' END AS type,
                       COUNT(o.order_id) AS orders,
                       ROUND(SUM(o.total_amount),0) AS total_spent
                FROM patients p
                JOIN orders o ON o.patient_id=p.patient_id
                WHERE o.status='completed'
                GROUP BY p.patient_id ORDER BY total_spent DESC LIMIT 10
            """, conn)
            result = "Top 10 patients by spending:\n" + df.to_string(index=False)

        elif any(w in q for w in ["monthly", "trend", "2022", "2023", "2024", "2025", "revenue trend", "month", "seasonal"]):
            df = pd.read_sql_query("""
                SELECT STRFTIME('%Y-%m', order_date) AS month,
                       COUNT(*) AS orders, ROUND(SUM(total_amount),0) AS revenue
                FROM orders WHERE status='completed'
                GROUP BY month ORDER BY month DESC LIMIT 24
            """, conn)
            result = "Monthly revenue (last 24 months):\n" + df.to_string(index=False)

        elif any(w in q for w in ["average order", "avg order", "aov", "average"]):
            df = pd.read_sql_query("""
                SELECT ROUND(AVG(total_amount),2) AS avg_order_value FROM orders WHERE status='completed'
            """, conn)
            result = f"Average order value: Rs.{df.iloc[0,0]:,.2f}"

        elif any(w in q for w in ["recommend", "suggest", "improve", "insight", "action", "business"]):
            df1 = pd.read_sql_query("SELECT risk_status, COUNT(*) AS drugs FROM v_inventory_risk GROUP BY risk_status", conn)
            df2 = pd.read_sql_query("""
                SELECT d.category, ROUND(SUM(oi.quantity*oi.unit_price),0) AS revenue
                FROM order_items oi JOIN drugs d ON d.drug_id=oi.drug_id
                JOIN orders o ON o.order_id=oi.order_id
                WHERE o.status='completed' GROUP BY d.category ORDER BY revenue DESC LIMIT 5
            """, conn)
            result = f"Inventory risk summary:\n{df1.to_string(index=False)}\n\nTop categories:\n{df2.to_string(index=False)}"

        elif any(w in q for w in ["supplier", "supply"]):
            df = pd.read_sql_query("SELECT name, city, state, rating FROM suppliers ORDER BY rating DESC", conn)
            result = "Suppliers:\n" + df.to_string(index=False)

        else:
            result = "Business overview: Total Revenue Rs.44.81L | Orders: 12,000 | Patients: 600 | Drugs: 55 | Top category: Antibiotics | Top drug: Insulin Glargine | Chronic patients: ~35% | Online orders: 60%"

    except Exception as e:
        result = f"Data error: {str(e)}"
    finally:
        conn.close()

    return result


def ask_groq(question: str) -> str:
    data = query_db(question)
    prompt = f"""You are MedCart AI, an expert pharmacy data analyst for an Indian online pharmacy.
Use the data below to answer the question. Use Rs. for Indian rupees. Be concise and give actionable insights.

DATA:
{data}

QUESTION: {question}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.3,
    )
    return response.choices[0].message.content


# ── UI ────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💊 MedCart AI")
    st.caption("Pharmacy Data Analyst")
    st.divider()
    st.markdown("**💡 Sample Questions**")
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
    for q in sample_qs:
        if st.button(q, use_container_width=True, key=q):
            st.session_state.pending = q
    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption("Built by Aftab Dayer")
    st.caption("Python · SQLite · Groq AI · Streamlit")


st.title("💊 MedCart AI Analyst")
st.caption("Ask me anything about your pharmacy data in plain English")

metrics = load_metrics()

if metrics is None:
    st.error(f"Database not found at: {DB_PATH}")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Revenue",  f"Rs.{metrics['revenue']/1e5:.2f}L")
col2.metric("📦 Orders",   f"{int(metrics['orders']):,}")
col3.metric("👥 Patients", f"{int(metrics['patients']):,}")
col4.metric("💊 Drugs",    f"{int(metrics['drugs'])}")

st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "👋 Hi! I'm your **MedCart AI Analyst**.\n\nI have full access to your pharmacy data — **12,000 orders, 600 patients, 55 drugs**.\n\nAsk me anything in plain English, or click a sample question on the left!"
    }]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "💊"):
        st.markdown(msg["content"])

if "pending" in st.session_state:
    question = st.session_state.pending
    del st.session_state.pending
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(question)
    with st.chat_message("assistant", avatar="💊"):
        with st.spinner("🔍 Analysing..."):
            answer = ask_groq(question)
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()

if user_input := st.chat_input("Ask anything about your pharmacy data..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)
    with st.chat_message("assistant", avatar="💊"):
        with st.spinner("🔍 Analysing..."):
            answer = ask_groq(user_input)
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
