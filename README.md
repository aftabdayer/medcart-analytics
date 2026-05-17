# 🏥 MedCart Intelligence Platform

> **End-to-end pharmacy analytics platform** — SQL data modelling, Python EDA, ML demand forecasting, RFM segmentation, Power BI dashboards, and an NL-to-SQL AI chatbot. Purpose-built for health-retail companies like 1mg, PharmEasy, and Apollo Pharmacy.

👉 **[Live App](https://medcart-analytics-zr23wqxnafiy7flo2xmchp.streamlit.app/)**  
Features: Executive Dashboard · Inventory Alerts · Customer Segmentation · Demand Forecast · AI Chatbot · Prescription Scanner

---

## Project Summary

| Metric | Value |
|--------|-------|
| Total Revenue Analysed | ₹22.5L+ across 3 years |
| Orders | 12,000 |
| Line Items | 30,000+ |
| Patients | 600 |
| Drugs | 55 |
| Suppliers | 15 |
| ML Model R² | 0.77 – 0.84 |
| Features Engineered | 19 |
| Demand Forecast Improvement | +22% over ARIMA baseline |

---

## What It Does

MedCart is a 6-page Streamlit analytics app backed by a 7-table SQLite schema. It covers the full analytics stack a health-retail business needs — from raw data to board-ready reporting.

| Module | What It Delivers |
|--------|-----------------|
| **Executive Dashboard** | Daily revenue KPIs, order trends, channel and payment mix |
| **Inventory Risk** | Low-stock and near-expiry alerts across all SKUs |
| **Customer Segmentation** | RFM segmentation — 4 tiers, chronic vs one-time buyer analysis |
| **Demand Forecast** | RandomForest model with 19 engineered features; per-category R² 0.82–0.84 |
| **AI Chatbot** | GPT-3.5 NL-to-SQL — natural language questions answered from live DB in seconds |
| **Prescription Scanner** | Prescription-level patient and drug tracking |

---

## Database Schema

```
suppliers ──< drugs ──< order_items >── orders >── patients
                ↓                                      ↓
           inventory                            prescriptions
```

**7 tables:** `suppliers`, `drugs`, `inventory`, `patients`, `orders`, `order_items`, `prescriptions`

**4 analytical views:**

| View | Purpose |
|------|---------|
| `v_daily_revenue` | Daily order count, revenue, avg order value |
| `v_inventory_risk` | Stock level + expiry classification per drug |
| `v_rfm` | Recency / Frequency / Monetary per patient |
| `v_drug_sales` | Drug-level revenue and quantity aggregates |

---

## ML Model

**Algorithm:** RandomForestRegressor (scikit-learn)  
**Target:** Weekly units sold per drug category  
**Validation:** TimeSeriesSplit (3-fold CV)

### 19 Engineered Features

- **Lag features:** lag_1, lag_2, lag_3, lag_4, lag_8, lag_12
- **Rolling stats:** 4-week, 8-week, 12-week mean + std
- **Calendar:** month, quarter
- **Cyclical encoding:** month_sin, month_cos (captures seasonal periodicity)
- **Seasonal flags:** is_winter, is_monsoon

### Model Performance

| Category | R² | MAE | CV-MAE |
|----------|----|-----|--------|
| Cardiac | 0.844 | 6.3 | 15.7 |
| Neuro | 0.827 | 4.3 | 9.7 |
| Analgesics | 0.826 | 4.0 | 10.1 |
| Diabetes | 0.825 | 2.6 | 6.0 |
| Antibiotics | 0.816 | 4.4 | 10.5 |
| Derma | 0.822 | 3.3 | 7.9 |

**+22% improvement over ARIMA baseline** (median R² 0.76 → 0.82+ across 12 drug categories)

---

## EDA — Key Findings

| # | Chart | Insight |
|---|-------|---------|
| 1 | Monthly Revenue Trend | Seasonal spikes in winter (Nov–Feb) and monsoon (Jun–Aug) |
| 2 | Revenue by Drug Category | Cardiac leads revenue; Supplements fastest growing |
| 3 | Seasonality Heatmap | Weekday ordering significantly higher than weekends |
| 4 | RFM Segmentation | VIP segment (chronic patients) shows 2.3× higher LTV |
| 5 | Inventory Risk Matrix | ~40% of SKUs low-stock or near-expiry at any given time |
| 6 | Top 15 Drugs by Revenue | Insulin Glargine highest individual revenue contributor |
| 7 | Channel & Payment Mix | 60% online orders; UPI dominates at 40% of payments |
| 8 | Chronic vs Regular | Chronic patients (35% of users) drive 2.3× higher order frequency |

---

## Business Insights

1. **Chronic patients drive disproportionate revenue** — 35% of patients generate 2.3× order frequency. Retention programmes should prioritise this segment above all others.
2. **Inventory risk is a hidden revenue leak** — ~40% of SKUs are low-stock or near-expiry at any given time. Proactive restocking of Cardiac and Diabetes lines alone reduces this significantly.
3. **Seasonal forecasting has a 4-week lead time** — Winter and monsoon months see 25–30% higher order volume. Stock adjustments made 4 weeks ahead prevent stockouts at peak demand.
4. **Online channel is the primary growth lever** — 60% of orders are online. Mobile UX investment and same-day delivery capability directly impact revenue.
5. **NL-to-SQL cuts ad hoc query turnaround from hours to seconds** — non-technical teams can self-serve data questions without SQL dependency.

---

## Power BI / Tableau

Load the CSVs from `data/` to replicate the 4-page Power BI dashboard:

| CSV | Dashboard Page |
|-----|---------------|
| `orders.csv` + `order_items.csv` | Executive KPIs |
| `v_inventory_risk.csv` | Inventory Risk Alerts |
| `v_rfm.csv` | Customer Segmentation |
| `v_drug_sales.csv` | Drug Performance |
| `v_daily_revenue.csv` | Revenue Trend |

---

## Project Structure

```
medcart-analytics/
├── sql/
│   ├── 01_schema.sql          ← 7 tables + 4 analytical views
│   ├── 02_generate_data.py    ← Synthetic data generation (run first)
│   ├── 03_eda.py              ← 8 EDA charts
│   └── 04_ml_forecast.py      ← RandomForest demand forecasting
├── medcart_app.py             ← 6-page Streamlit app
├── medcart_chatbot.py         ← GPT-3.5 NL-to-SQL chatbot
├── data/                      ← SQLite DB + 11 CSVs (auto-created)
├── reports/                   ← Forecast + metrics CSVs (auto-created)
└── requirements.txt
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate synthetic data
python sql/02_generate_data.py

# 3. Run EDA
python sql/03_eda.py

# 4. Train ML model & generate forecasts
python sql/04_ml_forecast.py

# 5. Launch the Streamlit app
streamlit run medcart_app.py
```

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Database | SQLite — 7-table schema, 4 analytical views, window functions |
| Data Generation | Python (pandas, random) |
| EDA | pandas, matplotlib, seaborn |
| ML Forecasting | scikit-learn (RandomForest, TimeSeriesSplit) |
| App | Streamlit, Plotly |
| AI Chatbot | GPT-3.5 NL-to-SQL |
| BI Reporting | Power BI (DAX, Star Schema) / Tableau |

---

## Author

**Aftab Dayer** · [LinkedIn](https://linkedin.com/in/aftabdayer) · [GitHub](https://github.com/aftabdayer)  
NIT Hamirpur 2025 · IEEE Published · Microsoft Power BI Certified (PL-300)
