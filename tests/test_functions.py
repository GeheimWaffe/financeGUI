from unittest import TestCase
from sqlalchemy.orm import Session

from datamodel import ViewBilansAgregation
from engines import get_pgfin_engine

from functions import get_yearly_realise, get_groups_of_category, get_grouped_transactions, get_grouped_transactions, \
    find_salary_transaction, create_salaries, get_categorized_provisions, spread_over_year, calculate_over_under
from finance_streamlit.form_crud_provision import get_provisions_for_year

from datetime import date, timedelta
import pandas as pd
from unittest.mock import MagicMock, patch

# Adapte l'import selon l'emplacement réel de ta fonction
from functions import get_yearly_bilan


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

class TestGetYearlyBilan1(TestCase):
    def test_get_yearly_bilan(self):
        e = get_pgfin_engine()
        with Session(e) as session:
            result = get_yearly_bilan(session, 2027, True)
            print(result.columns)

class TestDataframeManipulations(TestCase):
    def setUp(self) -> None:
        # DONNÉES DE TEST BRUTES ET DISCIPLINÉES, SERGENT !
        data = {
            "Catégorie Groupe": [
                "01 - Revenus", "01 - Revenus", "01 - Revenus",
                "02 - Dépenses obligatoires", "02 - Dépenses obligatoires", "02 - Dépenses obligatoires",
                "02 - Dépenses obligatoires", "02 - Dépenses obligatoires", "02 - Dépenses obligatoires",
                "02 - Dépenses obligatoires"
            ],
            "Catégorie": [
                "Ail", "Allocations Familiales", "Salaire",
                "Cotisations Assurance", "Courses Alimentaires", "Eau",
                "Ecole", "Electricité", "Emprunt Immobilier", "Essence"
            ],
            "Dépense": [
                0.00, 0.00, 0.00,
                169.01, 789.53, 52.00,
                176.00, 5.38, 2224.40, 0.00
            ],
            "Dépense Provisionnée": [
                0.00, 0.00, 0.00,
                245.43, 1100.00, 52.00,
                166.00, 6.00, 2224.40, 90.00
            ],
            "Dépense Reste": [
                0.00, 0.00, 0.00,
                76.42, 310.47, 0.00,
                0.00, 0.62, 0.00, 90.00
            ]
        }

        # CRÉATION DU DATAFRAME MILITAIRE
        self.df_provisions = pd.DataFrame(data)

        # INSPECTION VISUELLE DANS LA CONSOLE (OPTIONNELLE)
        # print(df_provisions)


    def test_over_under_indicator(self):
        enriched = calculate_over_under(self.df_provisions, "Dépense Provisionnée", "Dépense", "Check")
        print(enriched)