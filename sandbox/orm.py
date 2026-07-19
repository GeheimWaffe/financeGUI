from venv import create

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session

# create the engine
engine = create_engine('postgresql://regular_user:userpassword@localhost:5432/finance', echo=True)

# create a select statement
with Session(engine) as session:
    result = session.execute(text('SELECT datadate, datacomment FROM datatable WHERE datacomment LIKE :search'),
                             {"search": '%first%'})
    for r in result:
        print(r)
