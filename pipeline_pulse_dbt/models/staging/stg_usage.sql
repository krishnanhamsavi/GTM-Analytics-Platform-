-- Staging: raw usage CSV -> clean view
select * from {{ source('raw', 'usage') }}
