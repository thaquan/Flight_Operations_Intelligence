-- The 10-million-row slot per source month is required for collision-free IDs.
select source_month, source_row_number
from {{ ref('fct_flights') }}
where source_row_number < 1 or source_row_number >= 10000000
