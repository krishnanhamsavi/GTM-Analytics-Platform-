import React, { useState } from "react";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, FunnelChart, Funnel, LabelList } from "recharts";

// ---- Real data computed from the dbt marts (DuckDB) ----
const FUNNEL = [
  { stage: "Prospecting", n: 81 }, { stage: "Qualification", n: 78 },
  { stage: "Proposal", n: 83 }, { stage: "Negotiation", n: 88 },
  { stage: "Closed Won", n: 221 }, { stage: "Closed Lost", n: 670 },
];
const SEGMENT = [
  { segment: "Enterprise", win_rate: 28.2, cycle: 154, acv: 5509050 },
  { segment: "Mid-Market", win_rate: 28.6, cycle: 78, acv: 3760278 },
  { segment: "SMB", win_rate: 22.6, cycle: 38, acv: 1890344 },
];
const BOOKINGS = [
  { month: "2025-04", arr: 974865, logos: 13 }, { month: "2025-05", arr: 578022, logos: 15 },
  { month: "2025-06", arr: 1053548, logos: 19 }, { month: "2025-07", arr: 1002639, logos: 15 },
  { month: "2025-08", arr: 920487, logos: 16 }, { month: "2025-09", arr: 974005, logos: 18 },
  { month: "2025-10", arr: 874643, logos: 20 }, { month: "2025-11", arr: 1112278, logos: 22 },
  { month: "2025-12", arr: 904105, logos: 31 },
];
const CAMPAIGNS = [
  { name: "Referral — Back-End Apps", type: "Referral", roi: 313.8, rev: 630251 },
  { name: "Content Syndication — Granular", type: "Content Syndication", roi: 63.0, rev: 663212 },
  { name: "Outbound — Proactive Schemas", type: "Outbound", roi: 47.9, rev: 395114 },
  { name: "Referral — One-To-One", type: "Referral", roi: 92.0, rev: 355400 },
  { name: "Referral — Sticky Functions", type: "Referral", roi: 142.7, rev: 330049 },
];
const HEALTH = [
  { tier: "Healthy", n: 18, color: "#3fb950" },
  { tier: "At Risk", n: 1, color: "#d29922" },
  { tier: "Critical", n: 44, color: "#f85149" },
];
const AT_RISK = [
  { name: "Wright-Leblanc", seg: "SMB", risk: 100 }, { name: "Anderson-Brewer", seg: "Mid-Market", risk: 100 },
  { name: "Contreras-Travis", seg: "SMB", risk: 100 }, { name: "Robinson-Graham", seg: "SMB", risk: 100 },
  { name: "Graham, Meyer & Drake", seg: "SMB", risk: 100 }, { name: "Stewart, Green & Santiago", seg: "Mid-Market", risk: 100 },
];

const fmt = (n) => "$" + (n / 1e6).toFixed(2) + "M";
const C = { bg: "#0d1117", panel: "#161b22", border: "#30363d", text: "#e6edf3", dim: "#8b949e", accent: "#58a6ff", green: "#3fb950", red: "#f85149" };

function Kpi({ label, value, sub }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 10, padding: "18px 20px" }}>
      <div style={{ color: C.dim, fontSize: 12, textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
      <div style={{ color: C.text, fontSize: 28, fontWeight: 700, marginTop: 6, fontFamily: "Georgia, serif" }}>{value}</div>
      {sub && <div style={{ color: C.green, fontSize: 12, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function Panel({ title, children, span }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 10, padding: 20, gridColumn: span ? `span ${span}` : "auto" }}>
      <div style={{ color: C.text, fontSize: 14, fontWeight: 600, marginBottom: 16 }}>{title}</div>
      {children}
    </div>
  );
}

const QUESTIONS = {
  "Why did Mid-Market win rate dip in Q3?": {
    sql: `SELECT owner_rep, COUNT(*) FILTER (WHERE is_won) won,\n       COUNT(*) FILTER (WHERE is_closed) closed\nFROM stg_opportunities\nWHERE segment='Mid-Market'\n  AND close_date BETWEEN '2025-07-01' AND '2025-09-30'\nGROUP BY owner_rep ORDER BY won/closed;`,
    answer: "Mid-Market win rate held at the segment level, but one rep (owner #4) closed 9 deals in Q3 at a 9% win rate vs. the 28% segment average — dragging that cohort down. The other 11 reps were on-trend. This is a rep-coaching issue, not a market problem.",
  },
  "Which campaign type has the best ROI?": {
    sql: `SELECT campaign_type, ROUND(AVG(roi),1) avg_roi,\n       SUM(won_revenue) revenue\nFROM mart_campaign_roi\nGROUP BY campaign_type ORDER BY avg_roi DESC;`,
    answer: "Referral campaigns deliver the highest ROI by far (avg ~140x) because spend is tiny relative to the revenue they influence. Content Syndication drives the most raw revenue but at a fraction of the efficiency. Recommendation: expand the referral program before scaling paid.",
  },
  "Which accounts are most likely to churn?": {
    sql: `SELECT account_name, segment, churn_risk\nFROM mart_churn_scores\nWHERE health_tier='Critical'\nORDER BY churn_risk DESC LIMIT 10;`,
    answer: "44 accounts score Critical. The top drivers are low seat utilization (48% importance) and days-since-last-login (39%) — engagement, not support volume, is the leading churn signal. CS should prioritize seat-activation outreach on the Critical tier.",
  },
};

export default function Dashboard() {
  const [q, setQ] = useState(null);
  const tabs = Object.keys(QUESTIONS);

  return (
    <div style={{ background: C.bg, minHeight: "100vh", padding: 24, fontFamily: "ui-sans-serif, system-ui", color: C.text }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 4 }}>
          <h1 style={{ fontSize: 26, margin: 0, fontFamily: "Georgia, serif" }}>Pipeline Pulse</h1>
          <span style={{ color: C.dim, fontSize: 13 }}>GTM Analytics + AI Co-Pilot · demo data</span>
        </div>
        <div style={{ color: C.dim, fontSize: 13, marginBottom: 20 }}>SaaS go-to-market metrics from a synthetic Salesforce-schema dataset (600 accounts · 1,221 opportunities)</div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 14 }}>
          <Kpi label="Won ACV" value="$11.16M" sub="↑ trailing 12mo" />
          <Kpi label="Blended Win Rate" value="24.8%" />
          <Kpi label="New Logos / mo" value="20" sub="↑ trending up" />
          <Kpi label="Churn Rate" value="23.9%" sub="44 critical accounts" />
        </div>

        {/* AI Co-pilot */}
        <div style={{ background: C.panel, border: `1px solid ${C.accent}`, borderRadius: 10, padding: 20, marginBottom: 14 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>🤖 Ask the AI Co-Pilot</div>
          <div style={{ color: C.dim, fontSize: 12, marginBottom: 14 }}>Natural-language → Claude writes SQL → runs it → explains the answer. (Live version uses your API key; demo shows canned runs.)</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
            {tabs.map((t) => (
              <button key={t} onClick={() => setQ(t)} style={{ background: q === t ? C.accent : "transparent", color: q === t ? C.bg : C.text, border: `1px solid ${q === t ? C.accent : C.border}`, borderRadius: 6, padding: "8px 12px", fontSize: 12, cursor: "pointer" }}>{t}</button>
            ))}
          </div>
          {q && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <div>
                <div style={{ color: C.dim, fontSize: 11, marginBottom: 6 }}>GENERATED SQL</div>
                <pre style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: 12, fontSize: 11, color: C.green, overflow: "auto", margin: 0, whiteSpace: "pre-wrap" }}>{QUESTIONS[q].sql}</pre>
              </div>
              <div>
                <div style={{ color: C.dim, fontSize: 11, marginBottom: 6 }}>AI EXPLANATION</div>
                <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: 12, fontSize: 13, lineHeight: 1.5 }}>{QUESTIONS[q].answer}</div>
              </div>
            </div>
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <Panel title="Pipeline Funnel (opportunity count by stage)">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={FUNNEL} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" stroke={C.dim} fontSize={11} />
                <YAxis dataKey="stage" type="category" stroke={C.dim} fontSize={11} width={80} />
                <Tooltip contentStyle={{ background: C.bg, border: `1px solid ${C.border}` }} />
                <Bar dataKey="n" radius={4}>
                  {FUNNEL.map((e, i) => <Cell key={i} fill={e.stage === "Closed Won" ? C.green : e.stage === "Closed Lost" ? C.red : C.accent} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="Monthly Bookings (won ARR)">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={BOOKINGS}>
                <CartesianGrid stroke={C.border} strokeDasharray="3 3" />
                <XAxis dataKey="month" stroke={C.dim} fontSize={10} />
                <YAxis stroke={C.dim} fontSize={10} tickFormatter={(v) => "$" + v / 1e6 + "M"} />
                <Tooltip contentStyle={{ background: C.bg, border: `1px solid ${C.border}` }} formatter={(v) => fmt(v)} />
                <Line dataKey="arr" stroke={C.accent} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="Win Rate & Cycle by Segment">
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead><tr style={{ color: C.dim, textAlign: "left", fontSize: 11 }}>
                <th style={{ padding: 8 }}>Segment</th><th>Win Rate</th><th>Cycle</th><th>Won ACV</th></tr></thead>
              <tbody>{SEGMENT.map((s) => (
                <tr key={s.segment} style={{ borderTop: `1px solid ${C.border}` }}>
                  <td style={{ padding: 8 }}>{s.segment}</td>
                  <td style={{ color: C.accent }}>{s.win_rate}%</td>
                  <td>{s.cycle}d</td>
                  <td>{fmt(s.acv)}</td>
                </tr>))}</tbody>
            </table>
          </Panel>

          <Panel title="Customer Health (churn model output)">
            <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
              <div style={{ display: "flex", gap: 8 }}>
                {HEALTH.map((h) => (
                  <div key={h.tier} style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 26, fontWeight: 700, color: h.color, fontFamily: "Georgia, serif" }}>{h.n}</div>
                    <div style={{ fontSize: 10, color: C.dim }}>{h.tier}</div>
                  </div>
                ))}
              </div>
              <div style={{ flex: 1, fontSize: 11 }}>
                <div style={{ color: C.dim, marginBottom: 6 }}>TOP AT-RISK ACCOUNTS</div>
                {AT_RISK.slice(0, 4).map((a) => (
                  <div key={a.name} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0" }}>
                    <span>{a.name} <span style={{ color: C.dim }}>· {a.seg}</span></span>
                    <span style={{ color: C.red }}>{a.risk}%</span>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          <Panel title="Campaign ROI (first-touch attribution)" span={2}>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={CAMPAIGNS} margin={{ bottom: 5 }}>
                <CartesianGrid stroke={C.border} strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke={C.dim} fontSize={9} interval={0} angle={-8} textAnchor="end" height={50} />
                <YAxis stroke={C.dim} fontSize={10} />
                <Tooltip contentStyle={{ background: C.bg, border: `1px solid ${C.border}` }} formatter={(v) => v + "x ROI"} />
                <Bar dataKey="roi" radius={4} fill={C.green} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
        </div>

        <div style={{ color: C.dim, fontSize: 11, marginTop: 20, textAlign: "center" }}>
          Stack: DuckDB/Snowflake · dbt-style marts · scikit-learn churn model · FastAPI + Claude API · React
        </div>
      </div>
    </div>
  );
}
