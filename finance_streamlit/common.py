from datetime import datetime, date
import streamlit as st

# --- REFERENTIEL DES PAGES ---
PAGE_MAIN = 'Main'
PAGE_DASHBOARD = 'Dashboard'
PAGE_MONTHLY_PROVISIONS = 'Budget Monitoring'
PAGE_YEARLY_PROVISIONS = 'Budget Planning'
PAGE_SALARIES = 'Salaries'
PAGE_PATTERN_CHECK = 'Pattern Check'
PAGE_MAPS = 'Maps'
PAGE_FACTS = 'Facts'
PAGE_COMPTES = 'Comptes'
PAGE_CATEGORIES = 'Catégories'
PAGE_JOBS = 'Jobs'
PAGE_IMPOTS = 'Impôts'
PAGE_NEW_TRANSACTION = 'New Transaction'
PAGE_EDIT_TRANSACTION = 'Edit Transaction'
PAGE_NEW_PROVISION = 'New Provision'
PAGE_LINK = 'Link'
PAGE_SALAIRES_NEW = 'Salaires (New)'

background_black = "#1E293B"
background_white = "#FFFFFF"
background_lightgrey = "#F8FAFC"


class DatabaseOperation:
    def __init__(self, operation_time: datetime, operation_description: str, success: bool):
        self.operation_time = operation_time
        self.operation_description = operation_description
        self.success = success

    def __str__(self):
        return f"{self.operation_time.strftime('%Y-%m-%d %H:%M:%S')}: {'✅' if self.success else '❌'} : {self.operation_description}"


def log_operation(value: DatabaseOperation):
    """ Logs an operation into the 'log' variable of the session state in streamlit"""
    st.session_state.log += [value]


def cb_set_filter(filter_name: str, widget_key: str):
    st.toast(f"setting '{filter_name}' filter !")
    st.session_state.global_filters[filter_name] = st.session_state[widget_key]


def colorize_red_or_green(val: float) -> str:
    return "#10B981" if val >= 0 else "#EF4444"


def custom_label_red_or_green(label: str, val: float) -> str:
    custom_color = colorize_red_or_green(val)
    formatted_value = f"{val:,.2f} €".replace(",", " ")


    return f"""
        <div style="
            background-color: {background_lightgrey}; 
            padding: 15px; 
            border-radius: 8px; 
            border-left: 5px solid {custom_color};
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        ">
            <p style="margin: 0; font-size: 14px; color: #94A3B8; font-weight: bold; text-transform: uppercase;">
                {label}
            </p>
            <p style="margin: 5px 0 0 0; font-size: 36px; font-weight: 800; color: {custom_color}; font-family: monospace;">
                {formatted_value}
            </p>
        </div>
        """


def format_mois_qui_claque(d: date) -> str:
    """Transforme une date en une chaîne 'Mois Année' explicite en français."""
    mois_fr = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
        5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
        9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }
    if not isinstance(d, date):
        return str(d)

    nom_mois = mois_fr[d.month]
    annee = d.year
    return f"{nom_mois} {annee}"


def custom_label_month(month: date) -> str:
    mois_texte = format_mois_qui_claque(month)
    label = 'Période Sélectionnée'
    return f"""
    <div style="
            background-color: {background_lightgrey}; 
            padding: 15px; 
            border-radius: 8px; 
            border-left: 5px solid {background_black};
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        ">
            <p style="margin: 0; font-size: 14px; color: #94A3B8; font-weight: bold; text-transform: uppercase;">
                {label}
            </p>
            <p style="margin: 5px 0 0 0; font-size: 36px; font-weight: 800; color: {background_black}; font-family: monospace;">
                {mois_texte}
            </p>
        </div>
    """
