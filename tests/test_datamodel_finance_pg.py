import datetime
from unittest import TestCase

import pandas as pd
from sqlalchemy.orm import Session

from datamodel import LabelPrettifier
from functions import get_categorized_provisions, get_events, get_solde, get_salaries, get_max_number, get_balances, \
    get_jobs, get_numeros_reference
from engines import get_pgfin_engine
from datetime import date, timedelta


class TestSalary(TestCase):
    def test_get_salaries(self):
        e = get_pgfin_engine()
        with Session(e) as session:
            all_salaries = get_salaries(session)
            self.assertGreater(len(all_salaries), 0, 'Could not find salaries in the database')
            #            print(all_salaries[0])

            mois = all_salaries[0]['mois']
            one_salary = get_salaries(session, mois)
            self.assertGreater(len(one_salary), 0, f'Could not find a salary for the specific month : {mois}')


class TestNumber(TestCase):
    def test_get_max_number(self):
        e = get_pgfin_engine()
        with Session(e) as session:
            maxnumber = get_max_number(session)

            self.assertGreater(maxnumber, 0, 'Could not find a valid number')

            print(f'index : {maxnumber}')


class TestFunctions(TestCase):
    def test_get_events(self):
        e = get_pgfin_engine()
        with Session(e) as session:
            df = get_events(session, 'Consultations Médicales')

        self.assertGreater(len(df), 0, 'No events found')


class TestORM(TestCase):
    def setUp(self):
        self.eng = get_pgfin_engine()
        self.session = Session(self.eng)

    def test_get_balances(self):
        e = get_pgfin_engine()
        df = get_balances(e, date.today() - datetime.timedelta(weeks=12))
        print(df)

    def test_get_categorized_provisions(self):
        df = get_categorized_provisions(self.eng, category_filter='Téléphone', month=date(2025, 3, 1), economy_mode=False)

        self.assertGreater(len(df), 0, 'No categorized provisions found')

    def test_get_jobs(self):
        jobs = get_jobs(self.session, 10)

        self.assertEqual(len(jobs), 10, 'Could not find 10 jobs')

    def test_get_numeros(self):
        nos = get_numeros_reference(self.session, 20)

        self.assertEqual(len(nos), 20, 'Could not find 20 reference numbers')

    def test_get_solde(self):
        with Session(self.eng) as s:
            solde = get_solde(s, 'Crédit Agricole', date.today() - timedelta(days=30), date.today())

        self.assertGreater(len(solde), 0, 'Could not calculate a solde')


    def tearDown(self):
        self.eng.dispose()


class TestPrettifier(TestCase):
    def test_prettifier(self):
        rplc = LabelPrettifier(None)

        testlabel = 'Paiement Par Carte X5799 Caliceo Sce Sainte F 11/06 '
        replaced = rplc.clean_label(testlabel)
        self.assertEqual('Caliceo Sce Sainte F 11/06 ', replaced)
