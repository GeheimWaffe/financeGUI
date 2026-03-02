from unittest import TestCase

from sqlalchemy.orm import Session

from engines import get_pgfin_engine

from functions import get_yearly_realise, get_groups_of_category


class TestGetRealise(TestCase):
    def setUp(self) -> None:
        self.engine = get_pgfin_engine()

    def test_get_yearly_realise_depense(self):
        with Session(self.engine) as session:
            df = get_yearly_realise(session, False, True, False,'Cotisations Assurance', 2025)

            self.assertEqual(len(df), 12, 'Could not find 12 rows')
            self.assertTrue('Dépense' in df.columns, 'Could not find column Dépense')

        print(df)

    def test_get_yearly_provisionne_depense(self):
        with Session(self.engine) as session:
            df = get_yearly_realise(session, True, True, False,'Cotisations Assurance', 2025)

            self.assertEqual(len(df), 12, 'Could not find 12 rows')
            self.assertTrue('Dépense Provisionnée' in df.columns, 'Could not find column Dépense Provisionnée')

        print(df)

    def test_get_yearly_realise_depense_with_group(self):
        with Session(self.engine) as session:
            df = get_yearly_realise(session, False, True, False,'Cotisations Assurance', 2025, 'Protection Juridique')

            self.assertEqual(len(df), 12, 'Could not find 12 rows')
            self.assertTrue('Dépense' in df.columns, 'Could not find column Dépense')

        print(df)

    def test_get_yearly_provisionne_depense_with_group(self):
        with Session(self.engine) as session:
            df = get_yearly_realise(session, True, True, False,'Cotisations Assurance', 2025, 'Protection Juridique')

            self.assertEqual(len(df), 12, 'Could not find 12 rows')
            self.assertTrue('Dépense Provisionnée' in df.columns, 'Could not find column Dépense Provisionnée')

        print(df)

    def test_get_yearly_realise_recette(self):
        with Session(self.engine) as session:
            df = get_yearly_realise(session, False, False, False,'Salaire', 2025)

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
