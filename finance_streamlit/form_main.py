import streamlit as st
import sys
import os
from datetime import date, timedelta

from datamodel import Mouvement
from functions import fetch_mouvements, fetch_soldes, get_type_comptes, get_categories, get_comptes, \
    get_numeros_reference, get_jobs, JobMapper, deactivate_transactions, get_transaction, import_transaction, \
    apply_mass_update, get_balances

# Récupère le chemin du dossier parent (FinanceGUI)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# L'ajoute au chemin de recherche de Python s'il n'y est pas déjà
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from engines import makesession

# Colonnes à voir dans le formulaire
view_columns = ["index", "Label utilisateur",
                "Catégorie", "Date", "Mois", "Solde", "Numéro de référence"]

# ELEMENTS DU SESSION STATE
st_categorie = 'new_categorie'
st_compte = 'new_compte'
st_mois = 'new_mois'
st_ref = 'new_ref'

def cb_new_transaction():
    st.session_state.page = 'New Transaction'


def cb_edit_transaction():
    if not st.session_state.index_mouvement is None:
        st.session_state.page = 'Edit Transaction'

def cb_new_keyword():
    st.session_state.page = 'Maps'

def cb_link():
    st.session_state.page = 'Link'

def cb_invert_transaction():
    if not st.session_state.index_mouvement is None:
        with makesession() as session:
            existing = get_transaction(session, st.session_state.index_mouvement)
            inverted = existing.get_inverted()
            import_transaction(session, inverted)
            session.commit()

        st.session_state.last_event = "Transaction inverted !"


def cb_deactivate_transactions(pks_to_update: list[int]):
    print(f"Deactivation of {len(pks_to_update)} lignes")
    # deactivate the transactions
    with makesession() as s:
        print(f'creating the session')
        deactivate_transactions(s, pks_to_update)
    print('Transactions deactivated')
    st.success(f"Désactivation de {len(pks_to_update)} transactions")


def cb_mass_update(pks_to_update: list[int]):
    # Récupération des attributs
    template = Mouvement()
    if st_compte in st.session_state:
        template.compte = st.session_state[st_compte]
    if st_categorie in st.session_state:
        template.categorie = st.session_state[st_categorie]
    if st_mois in st.session_state:
        template.mois = st.session_state[st_mois]
    if st_ref in st.session_state:
        template.no_de_reference = st.session_state[st_ref]

    # mise à jour
    with makesession() as s:
        apply_mass_update(s, pks_to_update, template)
        s.commit()
        st.success('Mass update done !')
        st.session_state.last_event = 'Mass upate done'


def show_main_form():
    # --- INITIALISATION DE L'ÉTAT (SESSION STATE) ---
    if 'offset' not in st.session_state:
        st.session_state.offset = 0
    if 'offset_size' not in st.session_state:
        st.session_state.offset_size = 20
    if 'last_event' not in st.session_state:
        st.session_state.last_event = 'Idle'

    # Type de comptes
    with makesession() as s:
        type_comptes = get_type_comptes(s)
        default_index = type_comptes.index('Courant')
        categories = get_categories(s)
        cat_list = [c.categorie for c in categories]
        comptes = get_comptes(s)
        compte_list = [c.compte for c in comptes]
        # Numéros de référence
        st.session_state.nos_ref = get_numeros_reference(s, 20)
        # Jobs
        jobs = get_jobs(s, 20)
        jobmapper = JobMapper()
        jobmapper.set_jobs(jobs)

    # --- PAGE : Main ---
    st.subheader("Mes transactions financières")
    # --- BARRE DE RECHERCHE
    search_term = st.text_input("🔍", placeholder="Rechercher une transaction...", label_visibility='hidden')

    # --- ZONE DE FILTRES ---
    with st.expander("🔍 Autres Filtres et Recherche", expanded=False):
        f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 3])

        with f_col1:
            cat_filter = st.selectbox("Catégorie", cat_list, index=None)
            reimb = st.checkbox("Reimbursable Expenses")

        with f_col2:
            compte_filter = st.selectbox("Compte", compte_list, index=None)
            affect = st.checkbox("Affectable Payments")

        with f_col3:
            tag_filter = st.selectbox("Réf.", st.session_state.nos_ref, index=None)
            economy = st.toggle("Economy Mode", value=False)

        with f_col4:
            job_filter = st.selectbox("Job", jobmapper.get_job_descriptions(), index=None)
            deactivated = st.toggle("Deactivated Transactions", value=False)

    # --- ZONE DE BILANS ---
    with st.expander("Soldes", expanded=False):
        col_solde, col_balance = st.columns([1, 1])
        with col_solde:
            selected_type = st.selectbox("Type", type_comptes, index=default_index)

            with makesession() as s:
                soldes = fetch_soldes(s, selected_type)

            st.dataframe(data=soldes, hide_index=True,
                             column_config={"Solde Compte Actuel": st.column_config.NumberColumn(format="%.2f €")})
        with col_balance:
            st.text('Balances')
            st.space()
            with makesession() as s:
                balances = get_balances(s, date.today() - timedelta(weeks=12))

            st.dataframe(data=balances, hide_index=True)


    st.divider()

    # --- CORPS PRINCIPAL ---
    col_trn, col_actions = st.columns([9, 1])

    with col_trn:
        # Container pour la table des mouvements
        st.subheader("Mouvements")
        mouvements_container = st.container()

        # Container pour le menu contextuel
        context_menu_container = st.container()

        # Pagination
        p1, p2, p3 = st.columns([1, 1, 1])
        with p1:
            st.space()
            if st.button("⬅Précédent", width='stretch'):
                if st.session_state.offset >= st.session_state.offset_size:
                    st.session_state.offset -= st.session_state.offset_size
                else:
                    st.session_state.offset = 0
        with p2:
            st.session_state.offset_size = st.selectbox(label='Taille', options=[20, 50, 100], index=0)

        with p3:
            st.space()
            if st.button("Suivant➡", width='stretch'):
                st.session_state.offset += st.session_state.offset_size

        # Création du dataframe
        # FILTRES - récupération

        with mouvements_container:
            with makesession() as s:
                df_data = fetch_mouvements(s, view_columns, st.session_state.offset_size, st.session_state.offset,
                                           sort_column='index', sort_order='desc', category_filter=cat_filter,
                                           compte_filter=compte_filter, tag_filter=tag_filter,
                                           search_filter=search_term, reimbursable=reimb,
                                           affectable=affect, economy_mode=economy,
                                           job_id=jobmapper.get_job_id(job_filter))

            mvt_table = st.dataframe(
                df_data,
                width='stretch',
                height='content',
                hide_index=True,
                column_config={"Solde": st.column_config.NumberColumn(format="%.2f €")},
                key="main_table",
                on_select="rerun",
                selection_mode="multi-row"
            )

    # --- BARRE D'ACTIONS ---
    with col_actions:
        # GESTION DYNAMIQUE - Cas mono-ligne
        selected_rows = mvt_table.selection.rows
        st.session_state.index_mouvement = None

        st.subheader("Actions")
        st.button("➕ New", width='stretch', on_click=cb_new_transaction)

        if len(selected_rows) > 0:
            # On récupère les identifiants uniques (PK) des lignes sélectionnées
            # Supposons que votre PK est 'id' ou 'description'
            pks_to_update = [int(df_data.iloc[i][0]) for i in selected_rows]
            labels = [df_data.iloc[i][1] for i in selected_rows]

            # On fixe l'identifiant de la transaction à adapter
            st.session_state.index_mouvement = int(pks_to_update[0])
            st.session_state.label_mouvement = str(labels[0])

            st.success(f"⚡ {len(pks_to_update)} sélectionnées")

            if len(selected_rows) == 1:
                st.button("📝 Edit", width='stretch', on_click=cb_edit_transaction)
                st.button("🔄 Invert", width='stretch', on_click=cb_invert_transaction)
                st.button("🔗 Link", width='stretch', on_click=cb_link)
                st.button("Map", width='stretch', on_click=cb_new_keyword)

            # --- BANDEAU D'ACTION ---
            st.button("Désactiver", type="primary", on_click=cb_deactivate_transactions, args=(pks_to_update,))

            st.selectbox("Nouvelle Catégorie", cat_list, key=st_categorie, index=None)
            st.selectbox("Nouveau Compte", compte_list, key=st_compte, index=None)
            st.date_input("Nouveau Mois", key=st_mois)
            st.selectbox("Nouvelle Ref.", key=st_ref, options=st.session_state.nos_ref)

            st.button("Mettre à jour", type="primary", on_click=cb_mass_update, args=(pks_to_update,))

    # --- STATUS BAR (FIXÉE EN BAS) ---
    st.markdown(
        f"""
        <div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: #f0f2f6; padding: 5px; text-align: center; border-top: 1px solid #ddd;">
            {"TEST MODE" if st.session_state.test_mode else "PRODUCTION"} | Offset: {st.session_state.offset} | Mode: {"Économie" if economy else "Standard"} 
            | Row selected : {st.session_state.index_mouvement}
            | Last event : {st.session_state.last_event}
        </div>
        """,
        unsafe_allow_html=True
    )
