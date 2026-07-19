# Create metadata
from importlib.metadata import metadata

from sqlalchemy import MetaData, nulls_last
from sqlalchemy.sql.ddl import DropTable

metadata_obj = MetaData()

# Import the basic types
from sqlalchemy import Table, Column, Integer, String, Date

user_table = Table("user_account", metadata_obj,
                   Column("id", Integer, primary_key=True),
                   Column("name", String(30)),
                   Column("fullname", String),
                   Column('surname', String(50)))

# The metadata object can be in a "models" or "dbschema" package. I did it that way too.
print(user_table.c.keys())
print(user_table.primary_key)

for c in user_table.c:
    print(f'column description : {c.key}, {c.name}, {c.type}')

# Declaring another table
from sqlalchemy import ForeignKey
address_table = Table("address", metadata_obj,
                      Column("id", Integer, primary_key=True),
                      Column("user_id", ForeignKey("user_account.id"), nullable=False),
                      Column("email_address", String, nullable=False))

# Declaring the datatable table
datatable = Table('datatable', metadata_obj,
                  Column('id', Integer, primary_key=True),
                  Column('datadate', Date),
                  Column('datacomment', String(255))
                  )

# clean the existing tables
import engines as pg
e = pg.get_pgfin_engine()

with e.connect() as conn:
    conn.execute(DropTable(datatable, if_exists=True))
    conn.execute(DropTable(address_table, if_exists=True))
    conn.execute(DropTable(user_table, if_exists=True))
    conn.commit()

# Create the schema
e = pg.get_pgfin_engine()
metadata_obj.create_all(e)


