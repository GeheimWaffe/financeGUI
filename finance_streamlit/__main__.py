import streamlit as st
import sys
import os

from finance_streamlit.form_monthly_provisions import show_monthly_provisions
from form_main import show_main_form
from form_crud_transaction import edit_transaction

# Récupère le chemin du dossier parent (FinanceGUI)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# L'ajoute au chemin de recherche de Python s'il n'y est pas déjà
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# --- REFERENTIEL DES PAGES ---
PAGE_MAIN = 'Main'
PAGE_MONTHLY_PROVISIONS = 'Monthly Provisions'
PAGE_YEARLY_PROVISIONS = 'Yearly Provisions'
PAGE_SALARIES = 'Salaries'
PAGE_PATTERN_CHECK = 'Pattern Check'
PAGE_SALARY_MONITOR = 'Salary Monitor'
PAGE_MAPS = 'Maps'
PAGE_FACTS = 'Facts'

PAGE_NEW_TRANSACTION = 'New Transaction'
PAGE_EDIT_TRANSACTION = 'Edit Transaction'


# --- NAVIGATION PRINCIPALE ---
if 'page' not in st.session_state:
    st.session_state.page = 'Main'

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Finance Interface", layout="wide")

# --- BARRE DE MENUS DE GAUCHE - ACTIONS GENERALES ---
with st.sidebar:
    st.title('💰 Finance App')
    st.markdown('---')

    # Menu de navigation principal
    if st.button("Main", icon="🏠", use_container_width=True):
        st.session_state.page = PAGE_MAIN

    if st.button(PAGE_MONTHLY_PROVISIONS, use_container_width=True):
        st.session_state.page = PAGE_MONTHLY_PROVISIONS

    if st.button(PAGE_YEARLY_PROVISIONS, use_container_width=True):
        st.session_state.page = PAGE_YEARLY_PROVISIONS

    if st.button(PAGE_SALARIES, use_container_width=True):
        st.session_state.page = PAGE_SALARIES

    if st.button(PAGE_PATTERN_CHECK, use_container_width=True):
        st.session_state.page = PAGE_PATTERN_CHECK

    if st.button(PAGE_SALARY_MONITOR, use_container_width=True):
        st.session_state.page = PAGE_SALARY_MONITOR

    if st.button(PAGE_MAPS, use_container_width=True):
        st.session_state.page = PAGE_MAPS

    if st.button(PAGE_FACTS, use_container_width=True):
        st.session_state.page = PAGE_FACTS

# --- ROUTAGE ---
if st.session_state.page == PAGE_MAIN:
    show_main_form()
if st.session_state.page == PAGE_MONTHLY_PROVISIONS:
    show_monthly_provisions()
if st.session_state.page == PAGE_YEARLY_PROVISIONS:
    pass
if st.session_state.page == PAGE_SALARIES:
    pass
if st.session_state.page == PAGE_PATTERN_CHECK:
    pass
if st.session_state.page == PAGE_SALARY_MONITOR:
    pass
if st.session_state.page == PAGE_MAPS:
    pass
if st.session_state.page == PAGE_FACTS:
    pass
if st.session_state.page == PAGE_NEW_TRANSACTION:
    edit_transaction(is_new=True)
if st.session_state.page == PAGE_EDIT_TRANSACTION:
    edit_transaction(is_new=False)