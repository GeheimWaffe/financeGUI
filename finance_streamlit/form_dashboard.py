import streamlit as st
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from engines import makesession
from functions import get_type_comptes, get_grouped_transactions, get_grouped_transactions_2


def show_dashboard():
    st.title("📊 Dashboard des Soldes")


    # --- 1. BARRE DE FILTRES (INPUTS) ---
    with st.container(border=True):
        col_type, col_start, col_end = st.columns(3)

        with col_type:
            # Récupération des types via ta fonction
            with makesession() as s:
                types_disponibles = get_type_comptes(s)
            default_index = types_disponibles.index("Courant") if "Courant" in types_disponibles else 0
            selected_type = st.selectbox("Type de compte", options=types_disponibles, index=default_index)

        with col_start:
            start_date = st.date_input("Date de début", value=date.today() - timedelta(days=30))

        with col_end:
            end_date = st.date_input("Date de fin", value=date.today())

    # --- 2. RÉCUPÉRATION DES DONNÉES ---
    # On appelle ta fonction de regroupement
    with makesession() as s:
        df = get_grouped_transactions_2(s, selected_type, start_date, end_date)

    if df.empty:
        st.warning("Aucune donnée trouvée pour cette période.")
        return

    # Extraction des données aux bornes (Date de fin et Date de début)
    # L'index est (compte_type, Compte, Date)
    df_reset = df.reset_index()
    df_reset['Date'] = pd.to_datetime(df_reset['Date']).dt.date

    df_end = df_reset[df_reset['Date'] == end_date]
    df_start = df_reset[df_reset['Date'] == start_date]

    # --- 3. AFFICHAGE DES TUILES (KPIs) ---
    total_fin = df_end['Solde'].sum()
    total_debut = df_start['Solde'].sum()
    delta_global = total_fin - total_debut

    c1, c2 = st.columns([1, 2])

    with c1:
        # TUILE : Somme Totale
        st.metric(
            label=f"Solde Total ({selected_type})",
            value=f"{total_fin:,.2f} €",
            delta=f"{delta_global:,.2f} € vs début"
        )

    with c2:
        # TUILE : Liste des comptes avec indicateurs
        with st.expander("Détail des soldes par compte", expanded=True):
            # Préparation d'un petit tableau comparatif
            df_comp = df_end[['Compte', 'Solde']].rename(columns={'Solde': 'Fin'})
            df_comp = df_comp.merge(df_start[['Compte', 'Solde']], on='Compte', how='left').rename(
                columns={'Solde': 'Début'})
            df_comp['Delta'] = df_comp['Fin'] - df_comp['Début'].fillna(0)

            st.dataframe(
                df_comp,
                column_config={
                    "Fin": st.column_config.NumberColumn("Solde Fin", format="%.2f €"),
                    "Début": st.column_config.NumberColumn("Solde Début", format="%.2f €"),
                    "Delta": st.column_config.NumberColumn("Variation", format="%.2f €")
                },
                hide_index=True,
                width='stretch'
            )

    st.divider()

    # --- 4. TUILES GRAPHIQUES ---
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Évolution Temporelle")
        # TUILE : Linechart interactif
        fig_line = px.line(
            df_reset,
            x="Date",
            y="Solde",
            color="Compte",
            title="Solde cumulé par compte",
            render_mode="svg"  # Meilleur rendu pour le surlignage
        )
        fig_line.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.3))
        st.plotly_chart(fig_line, width='stretch')

    with col_chart2:
        st.subheader("Répartition à date de fin")
        # TUILE : Camembert
        fig_pie = px.pie(
            df_end,
            values='Solde',
            names='Compte',
            hole=0.4,
            title=f"Répartition au {end_date}"
        )
        st.plotly_chart(fig_pie, width='stretch')