"""
build_marts.py
Loads the raw CSVs into DuckDB and builds dbt-style marts with the core SaaS
metrics computed in SQL. In a real dbt project each query below would be its own
model (.sql file). Kept here as one runnable script so the project works end-to-end
without a dbt install, but the SQL is exactly what you'd put in dbt models.

Metrics built: pipeline funnel by stage, conversion velocity, win rate by segment,
campaign attribution (first-touch), ARR, and account health inputs.
"""
import duckdb
import os

con = duckdb.connect("data/warehouse.duckdb")

# ---- staging: load raw sources (the "sources" in dbt terms) -------------
for t in ["accounts", "contacts", "campaigns", "opportunities", "usage"]:
    con.execute(f"CREATE OR REPLACE TABLE stg_{t} AS SELECT * FROM read_csv_auto('data/{t}.csv')")

# ---- mart: pipeline funnel by stage ------------------------------------
con.execute("""
CREATE OR REPLACE TABLE mart_funnel AS
SELECT stage,
       COUNT(*)                AS n_opps,
       ROUND(SUM(amount), 0)   AS total_amount,
       ROUND(AVG(amount), 0)   AS avg_deal_size
FROM stg_opportunities
GROUP BY stage
ORDER BY array_position(
    ['Prospecting','Qualification','Proposal','Negotiation','Closed Won','Closed Lost'], stage)
""")

# ---- mart: win rate + sales cycle by segment ---------------------------
con.execute("""
CREATE OR REPLACE TABLE mart_segment_perf AS
SELECT segment,
       COUNT(*) FILTER (WHERE is_closed)                          AS closed_deals,
       COUNT(*) FILTER (WHERE is_won)                             AS won_deals,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_won)
             / NULLIF(COUNT(*) FILTER (WHERE is_closed), 0), 1)   AS win_rate_pct,
       ROUND(AVG(DATE_DIFF('day', created_date, close_date))
             FILTER (WHERE is_won), 0)                            AS avg_cycle_days,
       ROUND(SUM(amount) FILTER (WHERE is_won), 0)                AS won_acv
FROM stg_opportunities
GROUP BY segment
ORDER BY won_acv DESC
""")

# ---- mart: campaign attribution (first-touch) + ROI --------------------
con.execute("""
CREATE OR REPLACE TABLE mart_campaign_roi AS
SELECT c.campaign_id, c.campaign_name, c.campaign_type, c.spend,
       COUNT(o.opportunity_id)                              AS influenced_opps,
       ROUND(SUM(o.amount) FILTER (WHERE o.is_won), 0)      AS won_revenue,
       ROUND(SUM(o.amount) FILTER (WHERE o.is_won)
             / NULLIF(c.spend, 0), 2)                       AS roi
FROM stg_campaigns c
LEFT JOIN stg_opportunities o ON o.campaign_id = c.campaign_id
GROUP BY c.campaign_id, c.campaign_name, c.campaign_type, c.spend
ORDER BY roi DESC NULLS LAST
""")

# ---- mart: monthly bookings (new ARR proxy) ----------------------------
con.execute("""
CREATE OR REPLACE TABLE mart_monthly_bookings AS
SELECT DATE_TRUNC('month', close_date) AS month,
       ROUND(SUM(amount) FILTER (WHERE is_won), 0) AS won_arr,
       COUNT(*) FILTER (WHERE is_won)              AS new_logos
FROM stg_opportunities
WHERE is_closed
GROUP BY 1 ORDER BY 1
""")

# ---- mart: account health (joins won opps to usage) --------------------
con.execute("""
CREATE OR REPLACE TABLE mart_account_health AS
SELECT a.account_id, a.account_name, a.segment,
       u.monthly_logins, u.features_adopted, u.support_tickets_90d,
       u.days_since_last_login,
       ROUND(100.0 * u.seats_active / NULLIF(u.seats_purchased,0), 0) AS seat_utilization_pct,
       u.is_churned
FROM stg_accounts a
JOIN stg_usage u ON u.account_id = a.account_id
""")

# ---- headline metrics ---------------------------------------------------
total_arr = con.execute("SELECT SUM(won_revenue) FROM mart_campaign_roi").fetchone()[0]
won = con.execute("SELECT SUM(won_acv) FROM mart_segment_perf").fetchone()[0]
churn_rate = con.execute("SELECT 100.0*AVG(CASE WHEN is_churned THEN 1 ELSE 0 END) FROM mart_account_health").fetchone()[0]

print("Marts built in data/warehouse.duckdb:")
for r in con.execute("SHOW TABLES").fetchall():
    if r[0].startswith("mart_"):
        print("  -", r[0])
print(f"\nTotal Won ACV: ${won:,.0f}")
print(f"Churn rate:    {churn_rate:.1f}%")
print("\nSegment performance:")
print(con.execute("SELECT * FROM mart_segment_perf").df().to_string(index=False))
con.close()
