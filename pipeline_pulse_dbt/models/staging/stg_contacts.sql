-- Staging: raw contacts CSV -> clean view
select * from {{ source('raw', 'contacts') }}
