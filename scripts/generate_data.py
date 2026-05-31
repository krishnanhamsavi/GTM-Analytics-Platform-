"""
generate_data.py
Generates a realistic synthetic SaaS dataset modeled on the Salesforce data model:
Accounts -> Contacts, Campaigns, Opportunities (with Stages), and a usage table for churn.

Why this matters for the GTM role: building this *is* how you internalize the
Salesforce schema (Leads -> Contacts -> Accounts -> Opportunities -> Stages -> Campaigns),
which the training doc flagged as the #1 gap.
"""
import random
from datetime import datetime, timedelta
import pandas as pd
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

N_ACCOUNTS = 600
START = datetime(2024, 1, 1)
END = datetime(2025, 12, 31)

SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]
SEG_WEIGHTS = [0.55, 0.30, 0.15]
# Realistic stage funnel (Salesforce-style opportunity stages)
STAGES = ["Prospecting", "Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
CAMPAIGN_TYPES = ["Webinar", "Paid Search", "Content Syndication", "Field Event", "Outbound", "Referral"]
SOURCES = ["Inbound", "Outbound", "Partner", "Marketing"]

# ---------------------------------------------------------------- Campaigns
campaigns = []
for i in range(40):
    ctype = random.choice(CAMPAIGN_TYPES)
    spend = {"Webinar": 8000, "Paid Search": 25000, "Content Syndication": 15000,
             "Field Event": 40000, "Outbound": 12000, "Referral": 3000}[ctype]
    campaigns.append({
        "campaign_id": f"CMP-{1000+i}",
        "campaign_name": f"{ctype} - {fake.bs().title()}",
        "campaign_type": ctype,
        "spend": round(spend * random.uniform(0.6, 1.6), 2),
        "start_date": fake.date_between(START, END - timedelta(days=60)),
    })
campaigns_df = pd.DataFrame(campaigns)

# ---------------------------------------------------------------- Accounts
accounts = []
for i in range(N_ACCOUNTS):
    seg = random.choices(SEGMENTS, SEG_WEIGHTS)[0]
    accounts.append({
        "account_id": f"ACC-{2000+i}",
        "account_name": fake.company(),
        "segment": seg,
        "industry": fake.random_element(["SaaS", "Fintech", "Healthcare", "Retail", "Manufacturing", "Media"]),
        "employees": {"SMB": random.randint(10, 200), "Mid-Market": random.randint(200, 2000),
                      "Enterprise": random.randint(2000, 50000)}[seg],
        "created_date": fake.date_between(START, END - timedelta(days=30)),
    })
accounts_df = pd.DataFrame(accounts)

# ---------------------------------------------------------------- Contacts
contacts = []
for acc in accounts:
    for _ in range(random.randint(1, 5)):
        contacts.append({
            "contact_id": f"CON-{len(contacts)+5000}",
            "account_id": acc["account_id"],
            "full_name": fake.name(),
            "title": fake.job(),
            "is_economic_buyer": random.random() < 0.25,
        })
contacts_df = pd.DataFrame(contacts)

# ---------------------------------------------------------------- Opportunities
reps = [fake.name() for _ in range(12)]
acv_by_seg = {"SMB": (5000, 25000), "Mid-Market": (25000, 90000), "Enterprise": (90000, 400000)}
# Base win rate by segment, plus a deliberate Q dip we can "diagnose" with AI later
win_rate_by_seg = {"SMB": 0.22, "Mid-Market": 0.28, "Enterprise": 0.34}

opps = []
for acc in accounts:
    for _ in range(random.randint(1, 3)):
        seg = acc["segment"]
        created = fake.date_between(acc["created_date"], END)
        created_dt = datetime.combine(created, datetime.min.time())
        cycle_days = {"SMB": random.randint(14, 60), "Mid-Market": random.randint(45, 120),
                      "Enterprise": random.randint(90, 240)}[seg]
        close_dt = created_dt + timedelta(days=cycle_days)
        rep = random.choice(reps)

        wr = win_rate_by_seg[seg]
        # Inject a real, diagnosable problem: one rep's Q3-2025 mid-market deals stall
        stalled = (rep == reps[3] and seg == "Mid-Market"
                   and close_dt >= datetime(2025, 7, 1) and close_dt <= datetime(2025, 9, 30))
        if stalled:
            wr *= 0.3

        if close_dt > END:
            stage = random.choice(["Prospecting", "Qualification", "Proposal", "Negotiation"])
            is_won = None
        else:
            won = random.random() < wr
            stage = "Closed Won" if won else "Closed Lost"
            is_won = won

        amount = round(random.uniform(*acv_by_seg[seg]), 2)
        opps.append({
            "opportunity_id": f"OPP-{len(opps)+7000}",
            "account_id": acc["account_id"],
            "campaign_id": random.choice(campaigns)["campaign_id"] if random.random() < 0.7 else None,
            "owner_rep": rep,
            "segment": seg,
            "lead_source": random.choices(SOURCES, [0.4, 0.25, 0.15, 0.2])[0],
            "stage": stage,
            "amount": amount,
            "n_stakeholders": random.randint(1, 6),
            "created_date": created,
            "close_date": close_dt.date(),
            "is_won": is_won,
            "is_closed": stage in ("Closed Won", "Closed Lost"),
        })
opps_df = pd.DataFrame(opps)

# ---------------------------------------------------------------- Usage (for churn)
# Only "customers" (won an opp) have usage. Churn correlates with low usage + tickets.
won_accounts = opps_df[opps_df["is_won"] == True]["account_id"].unique()
usage = []
for acc_id in won_accounts:
    base_logins = random.randint(2, 120)
    health_decay = random.random()
    churned = (base_logins < 20 and health_decay > 0.4) or (random.random() < 0.12)
    usage.append({
        "account_id": acc_id,
        "monthly_logins": base_logins,
        "features_adopted": random.randint(1, 12),
        "support_tickets_90d": random.randint(0, 15) + (8 if churned else 0),
        "days_since_last_login": random.randint(0, 10) if not churned else random.randint(20, 90),
        "seats_purchased": random.randint(5, 200),
        "seats_active": None,  # filled below
        "is_churned": churned,
    })
usage_df = pd.DataFrame(usage)
usage_df["seats_active"] = usage_df.apply(
    lambda r: max(1, int(r["seats_purchased"] * (random.uniform(0.1, 0.4) if r["is_churned"]
                                                  else random.uniform(0.5, 1.0)))), axis=1)

# ---------------------------------------------------------------- Save
import os
os.makedirs("data", exist_ok=True)
campaigns_df.to_csv("data/campaigns.csv", index=False)
accounts_df.to_csv("data/accounts.csv", index=False)
contacts_df.to_csv("data/contacts.csv", index=False)
opps_df.to_csv("data/opportunities.csv", index=False)
usage_df.to_csv("data/usage.csv", index=False)

print(f"accounts:      {len(accounts_df)}")
print(f"contacts:      {len(contacts_df)}")
print(f"campaigns:     {len(campaigns_df)}")
print(f"opportunities: {len(opps_df)}")
print(f"usage rows:    {len(usage_df)}")
print(f"customers:     {len(won_accounts)}  | churned: {usage_df['is_churned'].sum()}")
