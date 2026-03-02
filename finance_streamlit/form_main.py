import streamlit as st
import sys
import os

# Récupère le chemin du dossier parent (FinanceGUI)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# L'ajoute au chemin de recherche de Python s'il n'y est pas déjà
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from engines import makesession

# Colonnes à voir dans le formulaire
view_columns = ["index", "Label utilisateur",
                "Catégorie", "Date", "Mois", "Solde", "Numéro de référence"]


def cb_new_transaction():
    st.session_state.page = 'New Transaction'


def cb_edit_transaction():
    st.session_state.page = 'Edit Transaction'


def show_main_form():

    # Simulation des fonctions backend (à importer de votre projet original)
    # from backend import fetch_mouvements, fetch_soldes, fetch_balances, ...
    from functions import fetch_mouvements, fetch_soldes, get_type_comptes, get_categories, get_comptes, \
        get_numeros_reference, get_jobs, JobMapper

    # --- INITIALISATION DE L'ÉTAT (SESSION STATE) ---
    if 'offset' not in st.session_state:
        st.session_state.offset = 0
    if 'offset_size' not in st.session_state:
        st.session_state.offset_size = 20
    if 'filters' not in st.session_state:
        st.session_state.filters = {
            'category': None, 'compte': None, 'job': 0,
            'tag': None, 'desc': None, 'economy': False
        }

    # Type de comptes
    with makesession() as s:
        type_comptes = get_type_comptes(s)
        default_index = type_comptes.index('Courant')
        categories = get_categories(s)
        cat_list = [c.categorie for c in categories]
        comptes = get_comptes(s)
        compte_list = [c.compte for c in comptes]
        # Numéros de référence
        nos_ref = get_numeros_reference(s, 20)
        # Jobs
        jobs = get_jobs(s, 20)
        jobmapper = JobMapper()
        jobmapper.set_jobs(jobs)

    # --- PAGE : Main ---
    st.title("Mouvements")

    # --- ZONE DE FILTRES ---
    with st.expander("🔍 Filtres et Recherche", expanded=True):
        f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 3])

        with f_col1:
            cat_filter = st.selectbox("Catégorie", cat_list, index=None)
            compte_filter = st.selectbox("Compte", compte_list, index=None)

        with f_col2:
            job_filter = st.selectbox("Job", jobmapper.get_job_descriptions(), index=None)
            tag_filter = st.selectbox("Réf.", nos_ref, index=None)

        with f_col3:
            st.write("")  # Padding
            reimb = st.checkbox("Reimbursable Expenses")
            affect = st.checkbox("Affectable Payments")
            economy = st.toggle("Economy Mode", value=st.session_state.filters['economy'])

        with f_col4:
            search_term = st.text_input("Recherche libre", placeholder="Libellé...")
            c1, c2 = st.columns(2)
            if c1.button("✅ Appliquer", width='stretch'):
                st.session_state.filters['desc'] = search_term
            if c2.button("✖ Effacer", width='stretch'):
                st.rerun()

    # --- ZONE DE BILANS ---
    with st.expander("Soldes", expanded=True):
        col_solde, col_solde_charts = st.columns([1, 1])
        with col_solde:
            selected_type = st.selectbox("Type", type_comptes, index=default_index)

            with makesession() as s:
                soldes = fetch_soldes(s, selected_type)
                st.dataframe(data=soldes, hide_index=True,
                             column_config={"Solde Compte Actuel": st.column_config.NumberColumn(format="%.2f €")})

        with col_solde_charts:
            st.bar_chart(data=soldes, x='Compte', y='Solde Compte Actuel')
    st.divider()

    # --- CORPS PRINCIPAL ---
    col_trn, col_actions = st.columns([9, 1])

    with col_trn:
        st.subheader("Mouvements")
        # st.data_editor permet la sélection de lignes contrairement à st.dataframe

        mouvements_container = st.container()

        # Pagination
        p1, p2, p3 = st.columns([1, 1, 1])
        if p1.button("⬅Précédent", width='stretch'):
            if st.session_state.offset >= st.session_state.offset_size:
                st.session_state.offset -= st.session_state.offset_size
            else:
                st.session_state.offset = 0

        st.session_state.offset_size = p2.selectbox(label='Taille', options=[20, 50, 100], index=0)

        if p3.button("Suivant➡", width='stretch'):
            st.session_state.offset += st.session_state.offset_size

        # Création du dataframe
        # FILTRES - récupération

        with mouvements_container:
            with makesession() as s:
                df_data = fetch_mouvements(s, view_columns, st.session_state.offset_size, st.session_state.offset,
                                           sort_column='index', sort_order='desc', category_filter=cat_filter,
                                           compte_filter=compte_filter, tag_filter=tag_filter)

            mvt_table = st.dataframe(
                df_data,
                width='stretch',
                hide_index=True,
                column_config={"Solde": st.column_config.NumberColumn(format="%.2f €")},
                key="main_table",
                on_select="rerun",
                selection_mode="single-row"
            )

    # --- BARRE D'ACTIONS ---
    with col_actions:
        st.subheader("Actions")
        st.button("➕ New Transaction", width='stretch', on_click=cb_new_transaction)

        st.button("🔄 Invert", width='stretch')
        st.button("📝 Edit", width='stretch', on_click=cb_edit_transaction)
        st.button("🔗 Link", width='stretch')

        st.divider()
        split_val = st.number_input("Split Count", value=2, min_value=1)
        st.button("✂ Split Custom", width='stretch')
        st.button("📅 Split Yearly", width='stretch')

    # --- selected row
    if len(mvt_table.selection['rows']) > 0:
        st.session_state.index_mouvement = int(df_data.iloc[mvt_table.selection['rows'][0], 0])
    else:
        st.session_state.index_mouvement = None

    # --- STATUS BAR (FIXÉE EN BAS) ---
    st.markdown(
        f"""
        <div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: #f0f2f6; padding: 5px; text-align: center; border-top: 1px solid #ddd;">
            Comptes Interface | Offset: {st.session_state.offset} | Mode: {"Économie" if economy else "Standard"} | {"Row selected" if st.session_state.index_mouvement else "No row selected"}
        </div>
        """,
        unsafe_allow_html=True
    )
