"""
app.py  —  Pipeline Pulse AI backend
Run locally:  pip install fastapi uvicorn anthropic duckdb
              export ANTHROPIC_API_KEY=sk-ant-...
              uvicorn app:app --reload

Two endpoints:
  POST /ask       natural-language question -> Claude writes SQL -> runs it -> returns rows + chart hint
  POST /diagnose  a metric that moved -> Claude analyzes underlying rows -> proposes likely causes

This is the AI-proof core of the role: the human (you) frames the question and owns
the judgment; Claude does the mechanical SQL writing that's being automated anyway.
"""
import os, json, duckdb
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic


# Load the API key from a local .env file (project root) if it isn't already in
# the environment. This makes the key independent of which terminal launches the
# server -- no more "set the env var in the right window" gotchas.
def _load_env_file():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        # .env wins, so a stale/empty env var from an earlier terminal can't block it
        os.environ[k.strip()] = v.strip().strip('"').strip("'")


_load_env_file()

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
app = FastAPI(title="Pipeline Pulse")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
client = anthropic.Anthropic(api_key=API_KEY)  # key from .env or environment
MODEL = "claude-sonnet-4-6"
DB = "data/warehouse.duckdb"

# Schema description we give Claude so it writes correct SQL against our marts.
SCHEMA = """
Tables (DuckDB SQL):
stg_opportunities(opportunity_id, account_id, campaign_id, owner_rep, segment,
  lead_source, stage, amount, n_stakeholders, created_date, close_date, is_won, is_closed)
  -- stage in: Prospecting, Qualification, Proposal, Negotiation, Closed Won, Closed Lost
mart_segment_perf(segment, closed_deals, won_deals, win_rate_pct, avg_cycle_days, won_acv)
mart_funnel(stage, n_opps, total_amount, avg_deal_size)
mart_campaign_roi(campaign_id, campaign_name, campaign_type, spend, influenced_opps, won_revenue, roi)
mart_monthly_bookings(month, won_arr, new_logos)
mart_account_health(account_id, account_name, segment, monthly_logins, features_adopted,
  support_tickets_90d, days_since_last_login, seat_utilization_pct, is_churned)
mart_churn_scores(account_id, account_name, segment, churn_risk, health_tier, is_churned)
"""

class AskReq(BaseModel):
    question: str

class DiagnoseReq(BaseModel):
    metric: str
    context: str = ""

def run_sql(sql: str):
    con = duckdb.connect(DB, read_only=True)
    try:
        return con.execute(sql).df().to_dict(orient="records")
    finally:
        con.close()

@app.post("/ask")
def ask(req: AskReq):
  try:
    # 1) Claude writes the SQL
    msg = client.messages.create(
        model=MODEL, max_tokens=600,
        system=f"You are a GTM analytics SQL expert. Given the schema, write ONE DuckDB "
               f"SQL query answering the question. Return ONLY raw SQL, no markdown, no prose.\n{SCHEMA}",
        messages=[{"role": "user", "content": req.question}],
    )
    sql = msg.content[0].text.strip().removeprefix("```sql").removeprefix("```").removesuffix("```").strip()

    # 2) Run it
    try:
        rows = run_sql(sql)
    except Exception as e:
        return {"sql": sql, "error": str(e)}

    # 3) Claude explains the result in business language
    explain = client.messages.create(
        model=MODEL, max_tokens=400,
        system="You are a GTM analyst. Explain this query result to a non-technical sales "
               "leader in 2-3 sentences. Lead with the answer.",
        messages=[{"role": "user", "content": f"Q: {req.question}\nData: {json.dumps(rows[:30], default=str)}"}],
    )
    return {"sql": sql, "rows": rows, "explanation": explain.content[0].text}
  except Exception as e:
    return {"error": f"{type(e).__name__}: {e}"}

@app.post("/diagnose")
def diagnose(req: DiagnoseReq):
    # Pull the most relevant slice for the LLM to reason over
    rep_perf = run_sql("""
        SELECT owner_rep, segment,
               COUNT(*) FILTER (WHERE is_won) AS won,
               COUNT(*) FILTER (WHERE is_closed) AS closed,
               ROUND(100.0*COUNT(*) FILTER (WHERE is_won)/NULLIF(COUNT(*) FILTER (WHERE is_closed),0),1) AS win_rate
        FROM stg_opportunities
        WHERE close_date >= '2025-07-01' AND close_date <= '2025-09-30'
        GROUP BY owner_rep, segment HAVING closed >= 3 ORDER BY win_rate
    """)
    out = client.messages.create(
        model=MODEL, max_tokens=600,
        system="You are a senior GTM analyst. Given rep-level performance data, identify the "
               "MOST LIKELY cause of the metric movement. Name specific reps/segments. Be concrete "
               "and propose one action. This is the judgment work AI-proofs the role.",
        messages=[{"role": "user",
                   "content": f"Metric that moved: {req.metric}\nContext: {req.context}\n"
                              f"Q3 2025 rep performance: {json.dumps(rep_perf, default=str)}"}],
    )
    return {"diagnosis": out.content[0].text, "evidence": rep_perf}

@app.get("/")
def health():
    return {"status": "ok", "service": "Pipeline Pulse"}
