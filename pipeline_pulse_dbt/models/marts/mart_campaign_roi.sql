-- Campaign ROI with first-touch attribution
select
    c.campaign_id,
    c.campaign_name,
    c.campaign_type,
    c.spend,
    count(o.opportunity_id)                            as influenced_opps,
    round(sum(o.amount) filter (where o.is_won), 0)    as won_revenue,
    round(sum(o.amount) filter (where o.is_won)
          / nullif(c.spend, 0), 2)                     as roi
from {{ ref('stg_campaigns') }} c
left join {{ ref('stg_opportunities') }} o
    on o.campaign_id = c.campaign_id
group by c.campaign_id, c.campaign_name, c.campaign_type, c.spend
order by roi desc nulls last
