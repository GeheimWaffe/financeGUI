from datetime import timedelta
from unittest import TestCase
import datetime as dt
from interests import generate_payment_schedule


class Test(TestCase):
    def test_generate_payment_schedule(self):
        start_date = dt.date.today()-timedelta(days=dt.date.today().day-1)
        df = generate_payment_schedule(start_date, 12, 10000,3.5)
        print(df)
        print(df.index.dtype)
        for d in df.index:
            print(d.year)

