import random
from unittest import TestCase
from finance_gui.__main__ import get_custom_split
import datetime

class Test(TestCase):
    def test_get_custom_split(self):
        result, months = get_custom_split(random.randint(2,5), round(random.random()*200, 2), datetime.date(2025,2, 1))
        print(result)
        print(months)
