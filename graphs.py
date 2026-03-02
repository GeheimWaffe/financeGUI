""" A module dedicated to wrapping up graph stuff"""
import matplotlib.pyplot as plt
from pandas import DataFrame
from matplotlib.ticker import MultipleLocator
from datetime import date, datetime


class GraphSolde:
    def __init__(self, compte: str):
        self.__fig__, self.__ax__ = plt.subplots()
        self.__compte__ = compte
        # set transparency

    @property
    def ax(self) -> plt.Axes:
        return self.__ax__

    @property
    def fig(self) -> plt.Figure:
        return self.__fig__

    def plot_solde(self, df: DataFrame, linestyle: str, marker: str, linewidth: float):
        self.__ax__.clear()
        self.__ax__.set_xlabel("Jours", fontsize=9)
        self.__ax__.set_ylabel("€")
        self.__ax__.plot(df["Cumul"], linestyle=linestyle, marker=marker, linewidth=linewidth)
        self.__ax__.yaxis.set_minor_locator(MultipleLocator(500))
        self.__ax__.minorticks_on()
        try:
            self.__ax__.set_ylim(bottom=min(df["Cumul"].min(), 0))
        except ValueError:
            self.__ax__.set_ylim(bottom=0)
        self.__ax__.patch.set_alpha(0.5)
        # Labels
        labels = [d.strftime('%Y-%m-%d') for d in df.index.date]
        self.__ax__.set_xticklabels(labels, fontsize=8)
