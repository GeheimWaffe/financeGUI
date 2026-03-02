import datetime as dt
from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd

def generate_payment_schedule(start_date: dt.date, nb_mois: int, due: float, rate: float) -> pd.DataFrame:
    # calcul de la mensualité
    monthly_rate = (due * rate / 12) / (1 - (1 + rate / 12) ** (-nb_mois))

    # Initialisation de la date
    dates = [start_date + relativedelta(months=i) for i in range(nb_mois)]
    cap_restant_du = np.empty(nb_mois)
    intérêts = np.empty(nb_mois)
    capital = np.empty(nb_mois)
    # Calcul des rate
    prêt_initial = due

    for i in range(nb_mois):
        intérêts[i] = prêt_initial * rate / 12
        capital[i] = monthly_rate - intérêts[i]

        cap_restant_du[i] = prêt_initial - capital[i]
        prêt_initial = cap_restant_du[i]

    # construire le dataframe
    df = pd.DataFrame(index=dates)
    df.index = pd.to_datetime(df.index)
    df['Capital Restant Dû'] = np.round(cap_restant_du, 2)
    df['Capital'] = np.round(capital, 2)
    df['Intérêts'] = np.round(intérêts, 2)

    return df