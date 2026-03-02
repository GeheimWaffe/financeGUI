import random
from unittest import TestCase

from finance_gui.__main__ import form_get_custom_split, form_faits_marquants
import datetime
import pandas as pd

class Test(TestCase):
    def test_get_custom_split(self):
        result, months = form_get_custom_split(random.randint(2, 5), round(random.random() * 200, 2), datetime.date(2025, 2, 1))
        print(result)
        print(months)

    def test_faits_marquants(self):
        form_faits_marquants()
