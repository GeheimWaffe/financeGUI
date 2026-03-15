import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta


def show_facts():
    """Formulaire dédié à l'affichage des faits marquants (Portage Streamlit)"""
    st.title("📊 Faits Marquants")
    st.divider()

    # Importez vos fonctions backend ici
    from engines import makesession
    from functions import fetch_mouvements

    # 1. Initialisation des variables d'état (Session State)
    if 'current_month_facts' not in st.session_state:
        st.session_state.current_month_facts = datetime.date.today().replace(day=1)

    # 2. Définition des Callbacks pour la navigation
    def cb_previous_month():
        st.session_state.current_month_facts -= relativedelta(months=1)

    def cb_next_month():
        st.session_state.current_month_facts += relativedelta(months=1)

    # Zone de navigation (équivalent du header PySimpleGUI)
    col_date, col_prev, col_next, _ = st.columns([3, 1, 1, 5])

    with col_date:
        mois_str = st.session_state.current_month_facts.strftime('%Y-%m-%d')
        st.subheader(f"Mois : :blue[{mois_str}]")

    with col_prev:
        st.button("Mois Précédent", on_click=cb_previous_month, width='stretch')

    with col_next:
        st.button("Mois Suivant", on_click=cb_next_month, width='stretch')

    st.divider()

    # 4. Récupération des données (Logique métier)
    # On récupère les données basées sur l'état actuel de session_state
    try:
        with makesession() as s:
            df = fetch_mouvements(
                s,
                ['Date', 'Label utilisateur', 'Fait marquant'],
                offset_size=100,
                month_filter=st.session_state.current_month_facts,
                faits_marquants=True
            )

        # 5. Affichage du tableau (équivalent sg.Table)
        if not df.empty:
            st.dataframe(
                df,
                width='stretch',
                hide_index=True,
                column_config={
                    "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                    "Fait marquant": st.column_config.TextColumn("Description du Fait Marquant")
                }
            )
        else:
            st.info(f"Aucun fait marquant enregistré pour le mois de {mois_str}.")

    except Exception as e:
        st.error(f"Erreur lors de la récupération des données : {e}")