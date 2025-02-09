from unittest import TestCase

from sqlalchemy.orm import Session

from datamodel_finance_pg import get_salaries, get_max_number, get_salary_transaction, \
    get_remaining_provisioned_expenses
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
            print(one_salary)

    def test_get_salary_transaction(self):
        amount = 5968.56
        mois = date(2024, 10, 1)

        e = get_pgfin_engine()
        with Session(e) as session:
            mvt = get_salary_transaction(session, amount, mois)
            print(mvt)
            self.assertIsNotNone(mvt, 'Could not find a proper transaction')


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