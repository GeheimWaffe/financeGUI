import streamlit as st
import sys
import os


# Récupère le chemin du dossier parent (FinanceGUI)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# L'ajoute au chemin de recherche de Python s'il n'y est pas déjà
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from engines import makesession
from finance_streamlit.form_jobs import view_log
from finance_streamlit.form_comptes import manage_comptes
from finance_streamlit.form_categories import manage_categories
from finance_streamlit.form_facts import show_facts
from finance_streamlit.form_maps import manage_maps
from finance_streamlit.form_monthly_provisions import show_monthly_provisions
from finance_streamlit.form_pattern_check import show_pattern_check
from finance_streamlit.form_salaries import manage_salaries
from finance_streamlit.form_yearly_provisions import show_yearly_provisions
from finance_streamlit.form_dashboard import show_dashboard
from finance_streamlit.form_link import manage_links
from form_main import show_main_form
from form_crud_transaction import edit_transaction
from form_crud_provision import create_provision

# --- REFERENTIEL DES PAGES ---
PAGE_MAIN = 'Main'
PAGE_DASHBOARD = 'Dashboard'
PAGE_MONTHLY_PROVISIONS = 'Monthly Provisions'
PAGE_YEARLY_PROVISIONS = 'Yearly Provisions'
PAGE_SALARIES = 'Salaries'
PAGE_PATTERN_CHECK = 'Pattern Check'
PAGE_MAPS = 'Maps'
PAGE_FACTS = 'Facts'
PAGE_COMPTES = 'Comptes'
PAGE_CATEGORIES = 'Catégories'
PAGE_JOBS = 'Jobs'

PAGE_NEW_TRANSACTION = 'New Transaction'
PAGE_EDIT_TRANSACTION = 'Edit Transaction'
PAGE_NEW_PROVISION = 'New Provision'
PAGE_LINK = 'Link'

# --- FILTRES
if 'global_filters' not in st.session_state:
    st.session_state.global_filters = {"label_filter": None,
                                       "is_depense": True,
                                       "is_courant": False,
                                       "category": None,
                                       "compte": None,
                                       "reference": None,
                                       "job": None,
                                       "reimbursable": False,
                                       "affectable": False,
                                       "deactivated": False,
                                       "empty_transactions": False}

# --- NAVIGATION PRINCIPALE ---
if 'page' not in st.session_state:
    st.session_state.page = PAGE_MAIN
if 'log' not in st.session_state:
    st.session_state.log = []

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Finance Interface", layout="wide")

# --- BARRE DE MENUS DE GAUCHE - ACTIONS GENERALES ---
with st.sidebar:
    st.title('💰 Finance App')
    st.markdown('---')

    # Menu de navigation principal
    if st.button(PAGE_DASHBOARD, width='stretch'):
        st.session_state.page = PAGE_DASHBOARD

    if st.button(PAGE_MAIN, icon="🏠", width='stretch'):
        st.session_state.page = PAGE_MAIN

    if st.button(PAGE_MONTHLY_PROVISIONS, width='stretch'):
        st.session_state.page = PAGE_MONTHLY_PROVISIONS

    if st.button(PAGE_YEARLY_PROVISIONS, width='stretch'):
        st.session_state.page = PAGE_YEARLY_PROVISIONS

    if st.button(PAGE_SALARIES, width='stretch'):
        st.session_state.page = PAGE_SALARIES

    if st.button(PAGE_PATTERN_CHECK, width='stretch'):
        st.session_state.page = PAGE_PATTERN_CHECK

    if st.button(PAGE_MAPS, width='stretch'):
        st.session_state.page = PAGE_MAPS

    if st.button(PAGE_FACTS, width='stretch'):
        st.session_state.page = PAGE_FACTS

    if st.button(PAGE_COMPTES, width='stretch'):
        st.session_state.page = PAGE_COMPTES

    if st.button(PAGE_CATEGORIES, width='stretch'):
        st.session_state.page = PAGE_CATEGORIES

    if st.button(PAGE_JOBS, width='stretch'):
        st.session_state.page = PAGE_JOBS

    st.divider()

    # Test mode
    testmode = st.toggle("Test Mode", value=False)
    st.session_state.test_mode = testmode

    st.divider()

    if st.session_state.test_mode:
        st.write(st.session_state.global_filters)

# --- ROUTAGE ---
if st.session_state.page == PAGE_MAIN:
    show_main_form()
if st.session_state.page == PAGE_DASHBOARD:
    show_dashboard()
if st.session_state.page == PAGE_MONTHLY_PROVISIONS:
    show_monthly_provisions()
if st.session_state.page == PAGE_YEARLY_PROVISIONS:
    show_yearly_provisions()
if st.session_state.page == PAGE_SALARIES:
    # show_salaries()
    with makesession() as session:
        manage_salaries(session)
if st.session_state.page == PAGE_PATTERN_CHECK:
    show_pattern_check()
if st.session_state.page == PAGE_MAPS:
    with makesession() as s:
        manage_maps(s)
if st.session_state.page == PAGE_FACTS:
    show_facts()
if st.session_state.page == PAGE_COMPTES:
    with makesession() as session:
        manage_comptes(session)
if st.session_state.page == PAGE_CATEGORIES:
    with makesession() as session:
        manage_categories(session)
if st.session_state.page == PAGE_NEW_TRANSACTION:
    edit_transaction(is_new=True)
if st.session_state.page == PAGE_EDIT_TRANSACTION:
    edit_transaction(is_new=False)
if st.session_state.page == PAGE_NEW_PROVISION:
    create_provision(True)
if st.session_state.page == PAGE_LINK:
    manage_links()
if st.session_state.page == PAGE_JOBS:
    view_log()
