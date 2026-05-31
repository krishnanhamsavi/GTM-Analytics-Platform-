-- Win rate, sales cycle, and won ACV by segment
select
    segment,
    count(*) filter (where is_closed)                          as closed_deals,
    count(*) filter (where is_won)                             as won_deals,
    round(100.0 * count(*) filter (where is_won)
          / nullif(count(*) filter (where is_closed), 0), 1)   as win_rate_pct,
    round(avg(date_diff('day', created_date, close_date))
          filter (where is_won), 0)                            as avg_cycle_days,
    round(sum(amount) filter (where is_won), 0)                as won_acv
from {{ ref('stg_opportunities') }}
group by segment
order by won_acv desc
