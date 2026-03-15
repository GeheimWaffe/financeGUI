import streamlit as st
from datetime import date
from functions import makesession, get_transaction, get_events
from datamodel import Mouvement


def cb_valider_transaction(editable: Mouvement, taux: float, provision: float, date_remboursement: date, label: str):
    """Callback exécuté lors de la validation."""
    # 1. Mise à jour de l'objet (Logique métier issue de ton code)
    if taux:
        editable.taux_remboursement = taux
        editable.provision_recuperer = provision

    editable.date_remboursement = date_remboursement
    editable.label_utilisateur = label

    with makesession() as s:
        # Case 2 : update
        print(f"Updating the record {editable}")
        s.add(editable)
        # Update
        s.flush()
        # if no test mode, we update
        if not st.session_state.test_mode:
            s.commit()

    # 3. Changement de page
    st.session_state.last_event = f'Transaction updated'
    st.session_state.page = 'Main'


def cb_retour_main():
    """Callback simple pour l'annulation."""
    st.session_state.page = 'Main'


def manage_links():
    """Portage Streamlit pour lier une transaction à un événement et libellé"""
    st.subheader(f"🔗 Liaison de transaction")

    # --- 1. CHARGEMENT DES DONNÉES (Événements) ---
    index_mouvement = st.session_state.index_mouvement
    with makesession() as s:
        editable = get_transaction(s, index_mouvement)
        df_events = get_events(s, editable.categorie)

    # --- 2. LOGIQUE DE CALCUL DU REMBOURSEMENT (DÉPENSES) ---
    is_expense = editable.depense is not None and editable.depense > 0

    new_taux = float(editable.taux_remboursement or 0.0)
    new_provision = float(editable.provision_recuperer or 0.0)

    if is_expense:
        with st.container(border=True):
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                # Utilisation d'un slider ou d'un number_input pour le taux
                input_taux = st.number_input(
                    "Taux de remboursement (%)",
                    min_value=0.0, max_value=100.0,
                    value=float(new_taux * 100),
                    step=5.0
                )
                new_taux = input_taux / 100
            with col_t2:
                new_provision = round(float(editable.depense) * new_taux, 2)
                st.metric("Remboursement attendu", f"{new_provision} €")

    # --- 3. FORMULAIRE DE SAISIE ---
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        # Date d'événement
        current_dt = editable.date_remboursement or date.today()
        selected_date = st.date_input("Date d'événement", value=current_dt)

    with col_d2:
        # Libellé utilisateur
        current_label = editable.label_utilisateur or ""
        selected_label = st.text_input("Libellé personnalisé", value=current_label)

    st.divider()

    # --- 4. TABLEAU DES ÉVÉNEMENTS (SÉLECTION) ---
    st.write("### 📅 Sélectionner un événement existant")

    # On utilise st.dataframe avec sélection native
    event_selection = st.dataframe(
        df_events,
        width='stretch',
        hide_index=False,
        on_select="rerun",
        selection_mode="single-row",
        height='content'  # Ajusté pour voir plus de lignes
    )

    # Logique de mise à jour automatique si une ligne est cliquée
    selected_rows = event_selection.get("selection", {}).get("rows", [])
    if selected_rows:
        row_idx = selected_rows[0]
        # On injecte les valeurs de la ligne dans les variables (équivalent du CLICKED)
        selected_date = df_events.iloc[row_idx, 0]
        selected_label = df_events.iloc[row_idx, 1]
        st.success(f"Événement sélectionné : {selected_label}")

    # --- 5. ACTIONS (VALIDER / ANNULER) ---
    st.divider()

    st.button("💾 Valider la liaison", type="primary", width='stretch', on_click=cb_valider_transaction,
              args=(editable, new_taux, new_provision, selected_date, selected_label))
    st.button("❌ Annuler", width='stretch', on_click=cb_retour_main)
