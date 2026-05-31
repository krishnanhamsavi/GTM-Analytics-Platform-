"""
pull_salesforce.py
Connects to a real Salesforce org (Developer Edition) via its REST API and pulls
the standard GTM objects with SOQL -- the live counterparts of the synthetic
tables this project models. Saves each object to data/salesforce/<object>.csv.

This is the "make it yours" step: it proves you can authenticate to Salesforce
and extract data with SOQL, not just imitate the schema with fake data.

Setup (one time) -- OAuth 2.0 Client Credentials flow via an External Client App:
  1. Setup -> App Manager -> New External Client App
       - Enable OAuth; callback URL any https URL; scopes: api, refresh_token
       - Enable the Client Credentials Flow
  2. In the app's Policies, set a "Run As" user (yourself) for the flow.
  3. From the app's OAuth settings, copy the Consumer Key + Consumer Secret.
  4. Add to the project .env file:
       SF_CLIENT_ID=the-app-consumer-key
       SF_CLIENT_SECRET=the-app-consumer-secret
  5. python scripts/pull_salesforce.py
"""
import os
import sys
from pathlib import Path

# Use the OS (Windows) certificate store for SSL verification. Without this,
# Python can fail with CERTIFICATE_VERIFY_FAILED on machines where network
# security software intercepts TLS -- the corporate/root CA lives in the OS
# trust store (which the browser uses) but not in Python's bundled certifi.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import pandas as pd
import requests
from simple_salesforce import Salesforce

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "salesforce"

# OAuth 2.0 token endpoint. The Client Credentials flow is NOT supported on the
# generic login.salesforce.com -- it must hit the org's own "My Domain" URL.
# Set SF_DOMAIN_URL in .env (e.g. https://your-org.my.salesforce.com).
DEFAULT_DOMAIN = "https://login.salesforce.com"
# Client Credentials flow needs only the External Client App's key + secret.
REQUIRED = ("SF_CLIENT_ID", "SF_CLIENT_SECRET")

# SOQL for the standard objects that mirror this project's synthetic tables.
# (Salesforce object  ->  project table)
QUERIES = {
    "Account": (
        "accounts",
        "SELECT Id, Name, Industry, NumberOfEmployees, Type, CreatedDate "
        "FROM Account",
    ),
    "Contact": (
        "contacts",
        "SELECT Id, AccountId, Name, Title, Email FROM Contact",
    ),
    "Opportunity": (
        "opportunities",
        "SELECT Id, AccountId, Name, StageName, Amount, CloseDate, Type, "
        "LeadSource, IsClosed, IsWon FROM Opportunity",
    ),
    "Campaign": (
        "campaigns",
        "SELECT Id, Name, Type, Status, BudgetedCost, ActualCost FROM Campaign",
    ),
}


def load_env_file():
    """Load SF_* credentials from the project .env (same pattern as backend/app.py)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_credentials():
    load_env_file()
    creds = {k: os.environ.get(k) for k in REQUIRED}
    missing = [k for k, v in creds.items() if not v]
    if missing:
        print("ERROR: missing credentials in .env: " + ", ".join(missing))
        print("Add all of these to the .env file: " + ", ".join(REQUIRED))
        print("SF_CLIENT_ID / SF_CLIENT_SECRET are the Connected App's "
              "Consumer Key / Consumer Secret (see this script's header).")
        sys.exit(1)
    return creds


def oauth_login(creds):
    """OAuth 2.0 client-credentials flow -> (instance_url, access_token)."""
    domain = os.environ.get("SF_DOMAIN_URL", DEFAULT_DOMAIN).rstrip("/")
    token_url = f"{domain}/services/oauth2/token"
    resp = requests.post(token_url, data={
        "grant_type": "client_credentials",
        "client_id": creds["SF_CLIENT_ID"],
        "client_secret": creds["SF_CLIENT_SECRET"],
    })
    if resp.status_code != 200:
        print(f"OAUTH LOGIN FAILED ({resp.status_code}): {resp.text}\n")
        print("Common fixes:")
        print("  - 'request not supported on this domain' -> set SF_DOMAIN_URL in "
              ".env to your My Domain (https://your-org.my.salesforce.com).")
        print("  - Wait ~2-10 min: a new External Client App takes time to activate.")
        print("  - In the app's OAuth settings, enable the Client Credentials Flow.")
        print("  - In the app's Policies, set a 'Run As' user for that flow.")
        print("  - Re-check SF_CLIENT_ID / SF_CLIENT_SECRET (the Consumer Key / Secret).")
        sys.exit(1)
    data = resp.json()
    return data["instance_url"], data["access_token"]


def to_dataframe(records):
    """Strip Salesforce's per-row 'attributes' metadata and return a DataFrame."""
    cleaned = [{k: v for k, v in r.items() if k != "attributes"} for r in records]
    return pd.DataFrame(cleaned)


def main():
    creds = get_credentials()

    instance_url, access_token = oauth_login(creds)
    sf = Salesforce(instance_url=instance_url, session_id=access_token)

    print(f"Connected to Salesforce ({instance_url})\n")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"{'Salesforce object':18}  {'-> project table':20}  rows")
    print("-" * 50)
    for sf_object, (table, soql) in QUERIES.items():
        result = sf.query_all(soql)
        df = to_dataframe(result["records"])
        out_path = OUT_DIR / f"{table}.csv"
        df.to_csv(out_path, index=False)
        print(f"{sf_object:18}  -> {table:20}  {len(df)}")

    print(f"\nSaved CSVs to {OUT_DIR}")

    # Show a sample of the live Opportunities -- note the real StageName values,
    # the same 'stage' concept the synthetic generator modeled.
    opps_csv = OUT_DIR / "opportunities.csv"
    if opps_csv.exists():
        opps = pd.read_csv(opps_csv)
        if not opps.empty:
            cols = [c for c in ["Name", "StageName", "Amount", "IsWon"] if c in opps.columns]
            print("\nSample live Opportunities (real Salesforce stages):")
            print(opps[cols].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
