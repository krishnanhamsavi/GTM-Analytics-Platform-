-- Staging: raw accounts CSV -> clean view
select * from {{ source('raw', 'accounts') }}
