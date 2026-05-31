-- Monthly bookings (new ARR proxy) from closed-won deals
select
    date_trunc('month', close_date)             as month,
    round(sum(amount) filter (where is_won), 0) as won_arr,
    count(*) filter (where is_won)              as new_logos
from {{ ref('stg_opportunities') }}
where is_closed
group by 1
order by 1
