# creating the engine
from sqlalchemy import create_engine
from pathlib import Path

def get_pgfin_engine(echo=False):
    return create_engine("postgresql://regular_user:userpassword@localhost:5432/finance", echo=echo)

def get_sqlite_engine(dbpath: list, echo=False):
    connection_string = 'sqlite+pysqlite:///'
    abs_path = Path().home().joinpath(*dbpath).as_posix()
    connection_string += abs_path
    return create_engine(connection_string, echo=True)
