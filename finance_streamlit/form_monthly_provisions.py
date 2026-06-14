import streamlit as st
from datetime import date, timedelta
import plotly.express as px

from finance_gui.__main__ import categorize_provisions
from functions import get_provisions_for_month, makesession, get_categorized_provisions, \
    fetch_mouvements, get_groups, close_provision, get_categories
from datamodel import Classifier, Mouvement
from datetime import date


# --- PERSISTANCE
# widgets
key_is_depense = 'mp_widget_is_depense'
key_is_courant = 'mp_widget_is_courant'
key_categorie_selectbox = 'mp_widget_categorie'


def cb_is_depense():
    st.session_state.global_filters['is_depense'] = st.session_state[key_is_depense]


def cb_is_courant():
    st.session_state[key_is_courant] = not st.session_state[key_is_courant]


def cb_change_category():
    st.session_state.global_filters['category'] = st.session_state[key_categorie_selectbox]


def cb_previous_month():
    st.session_state.current_month -= timedelta(days=2)
    st.session_state.current_month = st.session_state.current_month.replace(day=1)


def cb_next_month():
    st.session_state.current_month += timedelta(days=32)
    st.session_state.current_month = st.session_state.current_month.replace(day=1)


def cb_save_group():
    pattern = st.session_state.mp_pattern
    group = st.session_state.mp_group
    cl = Classifier(patterns=pattern, classes=group)
    with makesession() as s:
        s.add(cl)
        if not st.session_state.test_mode:
            s.commit()
        st.toast(f'New classifier {cl} saved !')


def cb_new_provision():
    """ Launch the creation of a new provision """
    if st.session_state.global_filters['category']:
        st.session_state.page = 'New Provision'
    else:
        st.toast('Pas de catégorie sélectionnée !')


def cb_close_provision(remainder: float):
    """ Closes the provision"""
    with makesession() as s:
        close_provision(s, st.session_state.current_month, st.session_state.global_filters['category'], remainder)
        if st.session_state.test_mode:
            st.toast('Test mode activated. No save done !')
        else:
            s.commit()
            st.toast('Provision closed !')


def show_monthly_provisions():
    st.title("Provisions mensuelles")

    st.divider()

    if not 'current_month' in st.session_state:
        st.session_state.current_month = date.today().replace(day=1)

    # setting the result
    st.session_state.current_consumption = 0.0

    # --- PROVISIONS MENSUELLES
    col_provision_type, col_previous, col_date, col_next, col_mode = st.columns(5)

    with col_provision_type:
        is_depense = st.toggle("Dépense / Recette", value=True, key=key_is_depense, on_change=cb_is_depense)

    with col_previous:
        st.button("Previous", on_click=cb_previous_month)

    with col_date:
        st.text(st.session_state.current_month.strftime("%d/%m/%Y"))

    with col_next:
        st.button("Next", on_click=cb_next_month)

    with col_mode:
        is_courant = st.toggle("Courant / Economie", value=True, key=key_is_courant, on_change=cb_is_courant)

    # CHIFFRES-CLES
    kpi_container = st.container()
    st.divider()

    # --- TABLE DES PROVISIONS
    col_provisions, col_groups = st.columns(2)

    with makesession() as s:
        provisions = get_provisions_for_month(s, st.session_state.current_month, is_courant)
        categories = get_categories(s)
        cat_list = [c.categorie for c in categories]

    # Affichage des chiffres-clés
    with kpi_container:
        metric1, metric2 = st.columns(2)
        with metric1:
            st.metric("Solde incluant Provisions", provisions['Solde avec provisions'].sum(), format="euro")
        with metric2:
            st.metric("Solde Sans Provisions", provisions['Solde sans provisions'].sum(), format="euro")

    # tri suivant qu'on a les dépenses ou les recettes
    if is_depense:
        directed_provisions = provisions.drop(columns=['Recette', 'Recette Provisionnée', 'Recette Reste'])
    else:
        directed_provisions = provisions.drop(columns=['Dépense', 'Dépense Provisionnée', 'Dépense Reste'])

    with col_provisions:
        dt_provisions = st.dataframe(directed_provisions, width='stretch', hide_index=True, on_select='rerun',
                                     selection_mode='single-cell')

        # --- NEW
        st.selectbox('Catégorie', help='Créer une nouvelle provision', options=cat_list, index=0,
                     key=key_categorie_selectbox, on_change=cb_change_category)
        st.button('New', help='Create a new provision', on_click=cb_new_provision, type='primary')

    with col_groups:
        tab_piechart, tab_restes, tab_groups = st.tabs(['Répartition par groupe', 'Reste', 'Détail Groupe'])

    # --- Ecoute de la sélection d'une catégorie
    cells = dt_provisions.selection['cells']
    if cells:
        row_index = cells[0][0]
        # retrieving the category and saving to cache
        category = provisions.iloc[row_index]['Catégorie']
        st.session_state.global_filters['category'] = category

        # Calculating the remainder
        if is_depense:
            remainder = provisions.iloc[row_index]['Dépense Reste']
            st.session_state.current_consumption = provisions.iloc[row_index]['Dépense Provisionnée']
        else:
            remainder = provisions.iloc[row_index]['Recette Reste']
            st.session_state.current_consumption = provisions.iloc[row_index]['Recette Provisionnée']

        with col_provisions:
            st.success(f"Catégorie {category} selected. Reste : {remainder} €")
            if remainder > 0:
                st.button('Close Expense', type='primary', on_click=cb_close_provision, args=(remainder,))

        # Displaying the provision groups
        # Retrieve the provisions
        with makesession() as s:
            df_groups = get_categorized_provisions(s, category_filter=category, month=st.session_state.current_month, number_months=1,
                                                   economy_mode=not is_courant)
            df_groups.sort_values('Group', inplace=True)

            df = fetch_mouvements(s, view=None, offset_size=20, category_filter=category,
                                  month_filter=st.session_state.current_month,
                                  economy_mode=not is_courant)
            # Retrieve the patterns (a dataframe with classes and patterns)
            patterns = get_groups(s)

            # show the result
        df = categorize_provisions(df, patterns)
        df.drop(columns=['Pattern', 'index'], inplace=True)
        df_grouped = df.groupby('Group', as_index=False)[['Solde']].sum()
        df_grouped['Répartition'] = df_grouped['Solde'].abs()

        # --- TAB with piechart
        with tab_piechart:
            # Graphe
            # TUILE : Camembert
            fig_pie = px.pie(
                df_grouped,
                values='Répartition',
                names='Group',
                hole=0.4,
                title=f"Répartition par groupe"
            )
            st.plotly_chart(fig_pie, width='stretch')

        # --- TAB with remaining by group
        with tab_restes:
            if is_depense:
                df_groups.drop(columns=['Recette', 'Provision à récupérer', 'Δ Recette'], inplace=True)
            else:
                df_groups.drop(columns=['Dépense', 'Provision à payer', 'Δ Dépense'], inplace=True)
            st.dataframe(df_groups, width='stretch', hide_index=True)

        # --- TAB with the details
        with tab_groups:
            # --- Groupes de transactions
            dt_groups = st.dataframe(df, width='stretch', hide_index=True, on_select='rerun',
                                     selection_mode='single-cell')

            # --- Ecoute de la sélection d'une transaction
            selected_groups = dt_groups.selection['cells']
            if selected_groups:
                row_index = selected_groups[0][0]
                column = selected_groups[0][1]
                if column == 'Description':
                    st.text_input("Pattern", key='mp_pattern', value=df.iloc[row_index][column])
                    st.text_input("Group", key='mp_group', help='Please enter a group')
                    st.button('Save', type='primary', on_click=cb_save_group)
