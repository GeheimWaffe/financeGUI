# creating the engine
from sqlalchemy import MetaData, Table, Column, Date, String, Numeric, select
from sqlalchemy.orm import Session

from engines import get_pgfin_engine
import datetime as dt
engine = get_pgfin_engine()

# execute simple statements
from sqlalchemy import text

def select_hello_world():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 'hello world'"))
        print(result.all())

import datetime as dt

def insert_fake_values_into_datatable():
    # une transaction n'est pas exécutée automatiquement. Si on veut la committer, il faut le faire avec le commit

    # And now serious things being. We're going to try to insert some data.
    switch_insert_on = True

    if switch_insert_on:
        with engine.connect() as conn:
            sqlstatement = text('INSERT INTO datatable (datadate, datacomment) VALUES (:date, :comment)')
            insertvalues = [{"date": dt.date.today(), "comment": "The first date"},
                                 {"date": dt.date.today() + dt.timedelta(days=1), "comment": "The second date"}]
            result = conn.execute(sqlstatement, insertvalues)
            print(result)
            conn.commit()

def select_values_from_datatable():
    # and now we retrieve the results
    with engine.connect() as conn:
        result = conn.execute(text("SELECT datadate, datacomment FROM datatable"))
        for row in result:
            print(f'Date : {row.datadate}, Comment: {row.datacomment}')

        for dbid, datadate, datacomment in result:
            print(f'{datadate}, {datacomment}')
    # the rows act like named tuples.

def filter_data_from_datatable():
    # Working with parameters
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM datatable where datadate > :date"), {"date": dt.date.today()})
        for dbid, datadate, datacomment in result:
            print(f'found {datadate}, {datacomment}')

#filter_data_from_datatable()
select_values_from_datatable()

if __name__ == '__main__':
    metadata_obj = MetaData()
    salaires = Table('view_salaires_nets',
                     metadata_obj,
                     Column('mois', Date),
                     Column('salaire_net', Numeric),
                     Column('prime_net', Numeric),
                     schema='dbview_schema')

    with engine.connect() as conn:
        result = conn.execute(select(salaires).where(salaires.c['mois'] == dt.date(2024, 10, 1)))
        for r in result:
            print(r)
            print(f'Mois : {r[0]}, Indicateur : {r[1]}, Valeur : {r[2]}')

        col: Column = salaires.c[0]
        print(col.name)
    print('file selected')