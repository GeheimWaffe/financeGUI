import datetime as dt

# creating the engine
from sqlalchemy import create_engine, Table, Select, Engine
from sqlalchemy import MetaData
from sqlalchemy.orm import Session

def get_finance_engine():
    return create_engine("postgresql://regular_user:userpassword@localhost:5432/finance")


def pl(message: str, add_separator: bool = False):
    to_print = ' - '.join([dt.datetime.now().strftime('%H:%M:%S %d-%m-%Y'), message])
    if add_separator:
        print('#' * len(to_print))

    print(to_print)


def main():
    pl('Connection to the Database', add_separator=True)

    e = get_finance_engine()
    # Loading the database schema
    m = MetaData()
    m.reflect(e)

    print('List of the tables')

    # Main Loop
    exit = False
    while not exit:
        tbl_indexes = {}
        for i, t in enumerate(m.tables):
            print(' - '.join([str(i), t]))
            tbl_indexes[i] = t
        choice = input('which table do you want to analyse (press q for exiting)?')
        try:
            number = int(choice)
            print(f'table {tbl_indexes[number]} selected')
            cli_table(tbl_indexes[number], m, e)
        except ValueError:
            if choice == 'q':
                exit = True
            else:
                pl('wrong input')

    pl('exiting application')

def cli_table(tablename: str, metadata_obj: MetaData, e: Engine):
    exit = False
    tbl: Table = metadata_obj.tables[tablename]
    while not exit:
        print('1 : list column names')
        print('2 : show top 10 table values')
        print('q : exit')
        choice = input('What do you want to do ?')
        if choice == 'q':
            exit = True

        if choice == '1':
            for c in tbl.columns:
                print(f'key : {c.key} | info : {c.info}')

        if choice == '2':
            with Session(e) as session:
                values = session.execute(Select(tbl.columns).limit(10))
                for v in values:
                    print(v)

        tbl.insert()

if __name__ == '__main__':
    main()
