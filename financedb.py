######################
# Standard section
# ####################
from psycopg2 import connect

from engines import get_pgfin_engine
e = get_pgfin_engine()

from sqlalchemy import MetaData
finance_metadata = MetaData()

finance_metadata.reflect(e, schema='public')

# exploiting the information
for t in finance_metadata.tables:
    print(t)
    print(finance_metadata.tables[t].columns)

# select a table
from sqlalchemy import Table
datatable: Table = finance_metadata.tables['public.compte_types']

from sqlalchemy import Select
q = Select(datatable).where(datatable.c['compte'] == 'Parking')
with e.connect() as conn:
    result = conn.execute(q)
    for r in result:
        print(r)