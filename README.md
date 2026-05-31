# Pipeline Pulse — GTM Analytics + AI Co-Pilot

A portfolio project for breaking into **GTM Data Analyst / Analytics Engineer** roles at SaaS companies. It proves the two things JDs ask for: (1) you understand the Salesforce data model and SaaS metrics, and (2) you can use AI to do the mechanical work while you own the judgment.

---

## What it does

1. **SaaS metrics dashboard** — pipeline funnel, win rate & sales cycle by segment, monthly bookings (ARR), campaign ROI with first-touch attribution, and a customer health/churn view.
2. **AI Co-Pilot** — type a plain-English question → Claude writes the SQL → it runs against the warehouse → Claude explains the answer to a non-technical leader.
3. **AI "Why" diagnosis + churn model** — when a metric moves, Claude analyzes the underlying rows and proposes a cause; a scikit-learn model scores every account Healthy / At Risk / Critical.

The dataset has a **deliberately planted problem** (one rep's Q3 Mid-Market deals stall), so the diagnosis feature has something real to find — exactly the Monday-morning "why did Stage 2 conversion drop?" scenario.

---

## Architecture / stack

```
data (Faker)  ->  DuckDB / Snowflake  ->  dbt-style marts  ->  React dashboard
                                       \->  scikit-learn churn model
                                       \->  FastAPI + Claude API (text-to-SQL, diagnosis)
```

- **Salesforce schema:** Accounts → Contacts, Campaigns, Opportunities (with Stages). Building this is how you learn the model that JDs require.
- **Marts (dbt-style SQL):** every query in `scripts/build_marts.py` is what you'd drop into a `models/*.sql` file in a real dbt project.
- **AI:** `backend/app.py` — `/ask` (NL→SQL→answer) and `/diagnose` (root-cause).

---

## How to build it (step by step)

**Phase 1 — Data + metrics (the foundation; impressive on its own)**
1. `pip install faker pandas duckdb scikit-learn`
2. `python scripts/generate_data.py` — creates the 5 CSVs in `data/`
3. `python scripts/build_marts.py` — loads DuckDB, builds the metric marts
4. Open `dashboard.jsx` in any React sandbox (or the included artifact) to see it live

**Phase 2 — Churn model**
5. `python scripts/churn_model.py` — trains the classifier, scores accounts, prints feature importance

**Phase 3 — AI Co-Pilot (needs your own API key)**
6. `pip install fastapi uvicorn anthropic`
7. `export ANTHROPIC_API_KEY=sk-ant-...`
8. `uvicorn backend.app:app --reload`
9. `curl -X POST localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"which segment has the highest win rate?"}'`

**Phase 4 — Make it yours (the part that gets you hired)**
- Swap DuckDB for a free **Snowflake** trial to say "Snowflake" truthfully
- Convert `build_marts.py` queries into a real **dbt** project (`dbt init`)
- Connect a free **Salesforce Developer Edition** org and pull real schema
- Memorize the benchmarks (Bessemer, OpenView) and know what "good" looks like for each metric

---

## Resume bullets you can use after building this

- Built an end-to-end GTM analytics platform (DuckDB/dbt/React) modeling the Salesforce schema across 600 accounts and 1,200+ opportunities, computing pipeline velocity, win rate by segment, CAC/LTV inputs, and first-touch campaign attribution.
- Shipped an AI co-pilot (Claude API + FastAPI) that converts natural-language questions to SQL and generates root-cause diagnoses of metric movements, automating the mechanical reporting layer.
- Trained a churn-prediction model (scikit-learn) scoring accounts into health tiers; identified seat utilization and login recency as the dominant churn signals.

---

## Interview talking points

- *"Walk me through the Salesforce data model"* → you literally built it
- *"How would you calculate NDR / win rate / pipeline velocity in SQL?"* → it's in `build_marts.py`
- *"How do you use AI in your workflow?"* → "AI writes the SQL; I frame the question and own the diagnosis the CRO has to trust"
- *"What's a hard analysis you did?"* → the planted Q3 rep-stall problem and how you found it

> Note: the churn model's AUC is ~1.0 here only because the synthetic data has clean signal. Real data is messier — say so in interviews; it shows you understand the difference.
