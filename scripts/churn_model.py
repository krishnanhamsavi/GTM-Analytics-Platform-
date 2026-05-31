"""
churn_model.py
Trains a churn classifier on usage signals and exports per-account health scores.
This is the "Thursday" workflow from the training doc: which usage patterns
predict churn (logins, feature adoption, support tickets).
"""
import duckdb
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

con = duckdb.connect("data/warehouse.duckdb")
df = con.execute("SELECT * FROM mart_account_health").df()

FEATURES = ["monthly_logins", "features_adopted", "support_tickets_90d",
            "days_since_last_login", "seat_utilization_pct"]
X = df[FEATURES].fillna(0)
y = df["is_churned"].astype(int)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
clf = RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42, class_weight="balanced")
clf.fit(X_train, y_train)

auc = roc_auc_score(y_test, clf.predict_proba(X_test)[:, 1])
print(f"Churn model ROC-AUC: {auc:.3f}\n")

print("Feature importance (what drives churn):")
for f, imp in sorted(zip(FEATURES, clf.feature_importances_), key=lambda x: -x[1]):
    print(f"  {f:28s} {imp:.3f}")

# Score every account and bucket into health tiers
df["churn_risk"] = clf.predict_proba(X)[:, 1]
df["health_tier"] = pd.cut(df["churn_risk"], [0, 0.33, 0.66, 1.0],
                           labels=["Healthy", "At Risk", "Critical"])
df[["account_id", "account_name", "segment", "churn_risk", "health_tier", "is_churned"]] \
    .sort_values("churn_risk", ascending=False) \
    .to_csv("data/account_scores.csv", index=False)

con.execute("CREATE OR REPLACE TABLE mart_churn_scores AS SELECT * FROM read_csv_auto('data/account_scores.csv')")
print(f"\nScored {len(df)} accounts -> data/account_scores.csv")
print(df["health_tier"].value_counts().to_string())
con.close()
