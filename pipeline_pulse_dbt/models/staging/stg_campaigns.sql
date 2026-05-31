-- Staging: raw campaigns CSV -> clean view
select * from {{ source('raw', 'campaigns') }}
