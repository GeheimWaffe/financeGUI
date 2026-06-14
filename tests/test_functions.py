from unittest import TestCase

from sqlalchemy.orm import Session

from engines import get_pgfin_engine

from functions import get_yearly_realise, get_groups_of_category, get_grouped_transactions, get_grouped_transactions, \
    find_salary_transaction, create_salaries, get_categorized_provisions, spread_over_year
from finance_streamlit.form_crud_provision import get_provisions_for_year

from datetime import date, timedelta
import pandas as pd


class TestSoldes(TestCase):
    def setUp(self) -> None:
        self.engine = get_pgfin_engine()

    def test_grouped_soldes(self):
        with Session(self.engine) as session:
            period_end = date.today()
            period_begin = period_end - timedelta(days=30)

            df = get_grouped_transactions(session, 'Courant', period_begin, period_end)

        print(df)

    def test_grouped_soldes_2_courant(self):
        with Session(self.engine) as session:
            period_end = date.today()
            period_begin = period_end - timedelta(days=30)

            df = get_grouped_transactions(session, 'Courant', period_begin, period_end)

        print(df)
        print(df.loc['Crédit Agricole'])

    def test_grouped_soldes_2_economies(self):
        with Session(self.engine) as session:
            period_end = date.today()
            period_begin = period_end - timedelta(days=30)

            df = get_grouped_transactions(session, 'Economies', period_begin, period_end)

        print(df.loc['Livret A'])


class TestGetRealise(TestCase):
    def setUp(self) -> None:
        self.engine = get_pgfin_engine()

    def test_get_yearly_realise_depense(self):
        with Session(self.engine) as session:
            df = get_yearly_realise(session, False, True, False, 'Cotisations Assurance', 2025)

            self.assertEqual(len(df), 12, 'Could not find 12 rows')
            self.assertTrue('Dépense' in df.columns, 'Could not find column Dépense')

        print(df)

    def test_get_yearly_provisionne_depense(self):
        with Session(self.engine) as session:
            df = get_yearly_realise(session, True, True, False, 'Cotisations Assurance', 2025)

            self.assertEqual(len(df), 12, 'Could not find 12 rows')
            self.assertTrue('Dépense Provisionnée' in df.columns, 'Could not find column Dépense Provisionnée')

        print(df)

    def test_get_yearly_realise_depense_with_group(self):
        with Session(self.engine) as session:
            df = get_yearly_realise(session, False, True, False, 'Cotisations Assurance', 2025, 'Protection Juridique')

            self.assertEqual(len(df), 12, 'Could not find 12 rows')
            self.assertTrue('Dépense' in df.columns, 'Could not find column Dépense')

        print(df)

    def test_get_yearly_provisionne_depense_with_group(self):
        with Session(self.engine) as session:
            df = get_yearly_realise(session, True, True, False, 'Cotisations Assurance', 2025, 'Protection Juridique')

            self.assertEqual(len(df), 12, 'Could not find 12 rows')
            self.assertTrue('Dépense Provisionnée' in df.columns, 'Could not find column Dépense Provisionnée')

        print(df)

    def test_get_yearly_realise_recette(self):
        with Session(self.engine) as session:
            df = get_yearly_realise(session, False, False, False, 'Salaire', 2025)

            self.assertEqual(len(df), 12, 'Could not find 12 rows')
            self.assertTrue('Recette' in df.columns, 'Could not find column Recette')

        print(df)


class TestGetGroups(TestCase):
    def setUp(self) -> None:
        self.engine = get_pgfin_engine()

    def test_get_groups_of_category(self):
        with Session(self.engine) as session:
            df = get_groups_of_category(session, 'Cotisations Assurance', 2025)

            print(df)


class TestGetSalary(TestCase):
    def test_find_transactions(self):
        mois = date.today().replace(day=1)
        with Session(get_pgfin_engine()) as session:
            result = find_salary_transaction(session, mois, 4000.0)

class TestGetCategorized(TestCase):
    def test_get_provisions(self):
        with Session(get_pgfin_engine()) as session:
            result = get_categorized_provisions(session, 'Cotisations Assurance', date(2026, 5, 1), 1, False)
        print(result)

    def test_get_categories(self):
        category = 'Cotisations Assurance'
        category = 'Essence'

        with Session(get_pgfin_engine()) as session:
            result = get_provisions_for_year(category, 'Common', 2026, True, True)

        print(result)

class TestExplode(TestCase):
    def test_explode(self):
        values = [[3, 43.5], [5, 12.5]]
        df3 = pd.DataFrame(data=values, columns=['Mois', 'Saisie'])

        exploded = spread_over_year(df3, 'Mois')
        print(exploded)
