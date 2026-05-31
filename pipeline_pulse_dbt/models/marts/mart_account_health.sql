-- Account health: join customers to their usage signals
select
    a.account_id,
    a.account_name,
    a.segment,
    u.monthly_logins,
    u.features_adopted,
    u.support_tickets_90d,
    u.days_since_last_login,
    round(100.0 * u.seats_active / nullif(u.seats_purchased, 0), 0) as seat_utilization_pct,
    u.is_churned
from {{ ref('stg_accounts') }} a
join {{ ref('stg_usage') }} u
    on u.account_id = a.account_id
