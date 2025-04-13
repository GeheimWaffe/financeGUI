import datetime
from unittest import TestCase

import pandas as pd
from sqlalchemy import select, Column
from sqlalchemy.orm import Session

from datamodel_finance_pg import get_salaries, get_max_number, get_salary_transaction, \
    get_remaining_provisioned_expenses, get_events, Mouvement, get_balances, get_categorized_provisions
from engines import get_pgfin_engine
from datetime import date

class TestSalary(TestCase):
    def test_get_salaries(self):
        e = get_pgfin_engine()
        with Session(e) as session:
            all_salaries = get_salaries(session)
            self.assertGreater(len(all_salaries), 0, 'Could not find salaries in the database')
            print(all_salaries[0])

            mois = all_salaries[0]['mois']
            one_salary = get_salaries(session, mois)
            self.assertGreater(len(one_salary), 0, f'Could not find a salary for the specific month : {mois}')

    def test_get_salary_transaction(self):
        amount = 5968.56
        mois = date(2024, 10, 1)

        e = get_pgfin_engine()
        with Session(e) as session:
            mvt = get_salary_transaction(session, amount, mois)

        self.assertIsNotNone(mvt, f"couldn't find transaction of {amount}")


class TestNumber(TestCase):
    def test_get_max_number(self):
        e = get_pgfin_engine()
        with Session(e) as session:
            maxnumber = get_max_number(session)

            self.assertGreater(maxnumber, 0, 'Could not find a valid number')

            print(f'index : {maxnumber}')


class TestProvisions(TestCase):
    def test_get_remaining_expenses(self):
        e = get_pgfin_engine()
        with Session(e) as session:
            results = get_remaining_provisioned_expenses(session)

            for r in results:
                print(r)

            self.assertGreater(len(results), 0, 'No remaining provisions found')

class TestFunctions(TestCase):
    def test_get_events(self):
        e = get_pgfin_engine()
        with Session(e) as session:
            headers, data = get_events(session, 'Consultations Médicales')
            df = pd.DataFrame(data=data, columns=headers)
            print(df)

class TestORM(TestCase):
    def test_select_column(self):
        stmt = select(Mouvement)

        c: Column = Mouvement.__table__.c['Numéro de référence']
        print(c.name)
        print(c.key)


    def test_get_balances(self):
        e = get_pgfin_engine()
        df = get_balances(e, date.today() - datetime.timedelta(weeks=12))
        print(df)

    def test_get_categorized_provisions(self):
        e = get_pgfin_engine()
        df = get_categorized_provisions(e, category_filter='Téléphone', month=date(2025, 3, 1), economy_mode=False)

        print(df)