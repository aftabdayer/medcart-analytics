## 🚀 Live Demo
👉 **[Open Live App](https://medcart-analytics-zr23wqxnafiy7flo2xmchp.streamlit.app/)**

Features: Executive Dashboard · Inventory Alerts · Customer Segmentation · Demand Forecast · AI Chatbot · Prescription Scanner


# 🏥 MedCart Intelligence Platform

> **End-to-end pharmacy analytics platform** combining SQL data modelling, Python EDA, and ML demand forecasting — purpose-built for health-retail companies like 1mg, PharmEasy, and Apollo Pharmacy.

---

## 📊 Project Summary

| Metric | Value |
|---|---|
| Total Revenue Analysed | ₹22.5L+ across 3 years |
| Orders | 12,000 |
| Line Items | 30,000+ |
| Patients | 600 |
| Drugs | 55 |
| Suppliers | 15 |
| ML Model R² | 0.77 – 0.84 |
| Features Engineered | 19 |

---

## 🏗️ Architecture

```
medcart_project/
├── sql/
│   ├── 01_schema.sql          ← 7 tables + 4 analytical views
│   ├── 02_generate_data.py    ← Synthetic data generation (run first)
│   ├── 03_eda.py              ← 8 professional EDA charts
│   └── 04_ml_forecast.py      ← RandomForest demand forecasting
├── data/                      ← SQLite DB + 11 CSVs (auto-created)
├── charts/                    ← 10 chart images (auto-created)
├── reports/                   ← Forecast + metrics CSVs (auto-created)
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

**Step 1 — Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 2 — Generate the data**
```bash
python sql/02_generate_data.py
```

**Step 3 — Run EDA**
```bash
python sql/03_eda.py
```

**Step 4 — Train ML model & forecast**
```bash
python sql/04_ml_forecast.py
```

> **Windows users:** Run Command Prompt or PowerShell from the `medcart_project` folder. Use `cd` to navigate there first.

---

## 📐 Database Schema

```
suppliers ──< drugs ──< order_items >── orders >── patients
                ↓                                      ↓
           inventory                            prescriptions
```

**7 tables:** `suppliers`, `drugs`, `inventory`, `patients`, `orders`, `order_items`, `prescriptions`

**4 analytical views:**
- `v_daily_revenue` — daily order count, revenue, avg order value
- `v_inventory_risk` — stock level + expiry classification per drug
- `v_rfm` — recency / frequency / monetary per patient
- `v_drug_sales` — drug-level revenue and quantity aggregates

---

## 📈 EDA Charts

| # | Chart | Key Insight |
|---|---|---|
| 1 | Monthly Revenue Trend | Seasonal spikes in winter (Nov–Feb) and monsoon (Jun–Aug) |
| 2 | Revenue by Drug Category | Cardiac leads revenue; Supplements fastest growing |
| 3 | Seasonality Heatmap | Weekday ordering significantly higher than weekends |
| 4 | RFM Segmentation | 4 customer tiers; VIP segment shows 2.3× higher LTV |
| 5 | Inventory Risk Matrix | ~40% of SKUs either low-stock or near-expiry |
| 6 | Top 15 Drugs by Revenue | Insulin Glargine highest individual revenue contributor |
| 7 | Channel & Payment Mix | 60% online orders; UPI dominates at 40% of payments |
| 8 | Chronic vs Regular Patients | Chronic patients generate 2.3× higher lifetime value |

---

## 🤖 ML Model

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
|---|---|---|---|
| Cardiac | 0.844 | 6.3 | 15.7 |
| Neuro | 0.827 | 4.3 | 9.7 |
| Analgesics | 0.826 | 4.0 | 10.1 |
| Diabetes | 0.825 | 2.6 | 6.0 |
| Antibiotics | 0.816 | 4.4 | 10.5 |
| Derma | 0.822 | 3.3 | 7.9 |

---

## 💡 Business Insights

1. **Chronic patients are gold** — representing 35% of patients but generating 2.3× LTV. Retention programmes should prioritise this segment.
2. **Inventory risk is real** — ~40% of SKUs are low-stock or near-expiry at any given time, representing potential lost revenue and wastage.
3. **Seasonal forecasting matters** — Winter and monsoon months show 25-30% higher order volume. Stock levels should be adjusted 4 weeks in advance.
4. **Online channel dominance** — 60% of orders are online; investing in mobile UX and same-day delivery directly impacts revenue.
5. **Cardiac and Diabetes categories** drive the most recurring revenue — stocking these reliably directly reduces churn.

---

## 🔧 Power BI / Tableau

Load CSVs from the `data/` folder:
- `orders.csv` + `order_items.csv` → revenue dashboards
- `v_inventory_risk.csv` → inventory alert dashboard
- `v_rfm.csv` → customer segmentation dashboard
- `v_drug_sales.csv` → drug performance dashboard
- `v_daily_revenue.csv` → executive KPI summary

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| Database | SQLite (schema in `01_schema.sql`) |
| Data Generation | Python (stdlib + random) |
| EDA | pandas, matplotlib, seaborn |
| ML | scikit-learn (RandomForest, TimeSeriesSplit) |
| BI | Power BI / Tableau (CSVs provided) |

---

## 📝 Author

Built as a portfolio project demonstrating end-to-end data analytics capabilities in the Indian health-retail sector.
