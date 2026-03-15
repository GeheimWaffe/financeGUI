import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from functions import get_salaries, makesession, find_salary_transaction, create_salaries


def manage_salaries(session:Session) -> bool:
    """Interface Streamlit utilisant la sélection native sur st.dataframe"""
    st.header("💸 Gestion des Salaires")

    # 1. État interne (pour persister les messages entre les clics)
    if 'status_msg' not in st.session_state:
        st.session_state.status_msg = "Sélectionnez une ligne dans le tableau"
    if 'selected_salary_obj' not in st.session_state:
        st.session_state.selected_salary_obj = None

    df = pd.DataFrame(get_salaries(session))

    # 2. Affichage du DataFrame avec sélection de ligne unique
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=False,
        on_select="rerun",
        selection_mode="single_row"
    )

    # 3. Logique de détection de sélection (Équivalent de ton event loop)
    # event.selection.rows contient l'index de la ligne cliquée
    selected_rows = event.get("selection", {}).get("rows", [])

    if selected_rows:
        row_idx = selected_rows[0]
        selected_month = df.iloc[row_idx, 0]
        amount = df.iloc[row_idx, 7]

        # Recherche de la transaction via SQLAlchemy
        salary = find_salary_transaction(session, selected_month, amount)
        st.session_state.selected_salary_obj = salary
        st.session_state.current_month = selected_month

        # Mise à jour du message de statut selon ton ancienne logique
        if salary is None:
            st.session_state.status_msg = "❌ Aucun mouvement trouvé, import impossible"
        elif salary.recette_initiale is not None:
            st.session_state.status_msg = f"✅ Déjà importé (Index: {salary.index})"
        else:
            st.session_state.status_msg = f"✨ Prêt : {salary.description} ({salary.date})"

    # 4. Affichage du statut et des boutons
    st.info(f"**Statut :** {st.session_state.status_msg}")

    salary = st.session_state.selected_salary_obj
    selected_month = st.session_state.get('current_month')

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Simulate", disabled=(salary is None), use_container_width=True):
            if salary.recette_initiale is None:
                create_salaries(engine, salary.index, selected_month, True)
                st.toast("Simulation effectuée", icon="🧪")
            else:
                st.warning("Import déjà fait")

    with col2:
        if st.button("Import Selected", type="primary", disabled=(salary is None), use_container_width=True):
            if salary.recette_initiale is None:
                create_salaries(engine, salary.index, selected_month, False)
                st.success("Import réussi !")
                return True  # to_update = True
            else:
                st.warning("Import déjà fait")

    return False