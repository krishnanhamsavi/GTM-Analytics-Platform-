-- Staging: raw opportunities CSV -> clean view
select * from {{ source('raw', 'opportunities') }}
