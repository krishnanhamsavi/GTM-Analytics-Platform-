-- Pipeline funnel: deal count and dollars at each stage
select
    stage,
    count(*)              as n_opps,
    round(sum(amount), 0) as total_amount,
    round(avg(amount), 0) as avg_deal_size
from {{ ref('stg_opportunities') }}
group by stage
order by array_position(
    ['Prospecting', 'Qualification', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost'],
    stage)
