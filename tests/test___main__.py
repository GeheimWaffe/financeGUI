import random
from unittest import TestCase

from finance_gui.__main__ import get_custom_split, fetch_mouvements_alternate
import datetime
import pandas as pd

class Test(TestCase):
    def test_get_custom_split(self):
        result, months = get_custom_split(random.randint(2,5), round(random.random()*200, 2), datetime.date(2025,2, 1))
        print(result)
        print(months)

    def test_dataframe_from_orm(self):
        df = fetch_mouvements_alternate(50, economy_mode=True, reimbursable=True)
        print(f"Number of rows : {len(df)}")
        self.assertGreater(len(df), 0, "Could not load dataframe")
