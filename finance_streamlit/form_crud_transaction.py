import streamlit as st

from datamodel import Mouvement
from engines import makesession
from functions import get_transaction, get_comptes, get_categories, import_transaction, split_value, simple_split, \
    split_mouvement

declarants = ['Vincent', 'Aurélie']


def cb_valider_transaction(editable: Mouvement, is_new: bool, description: str, datebox,
                           declarant, compte, depense: float, ref, economie: bool, label: str, mois, categorie,
                           recette: float, fait: str):
    """Callback exécuté lors de la validation."""
    # 1. Mise à jour de l'objet (Logique métier issue de ton code)
    editable.description = description
    editable.date = datebox
    editable.declarant = declarant
    editable.compte = compte
    editable.depense = float(depense)
    editable.no_de_reference = ref
    editable.economie = 'true' if economie else 'false'

    editable.label_utilisateur = label
    editable.mois = mois
    editable.categorie = categorie
    editable.recette = float(recette)
    editable.fait_marquant = fait

    # --- VERIFICATION OF COMPLETENESS
    if editable.date is None:
        st.error('Missing Date !')
    elif editable.description is None:
        st.error('Missing Description !')
    elif editable.categorie is None:
        st.error('Missing Catégorie !')
    elif editable.mois is None:
        st.error('Missing Mois !')
    else:
        try:
            with makesession() as s:
                if is_new:
                    # Case 1 : new movement
                    import_transaction(s, editable)
                else:
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

        except ValueError:
            st.error("❌ Veuillez entrer des montants valides !")


def cb_retour_main():
    """Callback simple pour l'annulation."""
    st.session_state.page = 'Main'


def cb_split_custom(index: int, splitted_values, splitted_months):
    with makesession() as session:
        splittable = get_transaction(session, index)
        solde = splittable.get_solde()
        splittable_month = splittable.mois
        simple_split(session, index, splitted_values, splitted_months)
        status_message = f"Splitting custom transaction {index} in {len(splitted_values)} parts"
        if not st.session_state.test_mode:
            session.commit()

    # Changement de page
    st.session_state.last_event = f'Transaction splitted'
    st.session_state.page = 'Main'


def cb_split_yearly(index: int):
    with makesession() as session:
        split_mouvement(session, index)
        if not st.session_state.test_mode:
            session.commit()

    # Changement de page
    st.session_state.last_event = f'Transaction splitted in yearly mode'
    st.session_state.page = 'Main'


def edit_transaction(is_new: bool):
    # --- DECLARE BASE VARIABLES ---
    # si je ne les déclare pas, j'ai une erreur
    key_values = []
    key_months = []

    # --- RETRIEVE TRANSACTION FROM DATABASE ---
    if is_new:
        editable = Mouvement()
        st.title(f"✍️ Nouvelle transaction")
    else:
        index_mouvement = st.session_state.index_mouvement
        with makesession() as s:
            editable = get_transaction(s, index_mouvement)
        st.title(f"✍️ Éditeur de transaction : {editable.description}")

    # --- REFERENTIELS ---
    with makesession() as s:
        comptes = get_comptes(s)
        compte_list = [None] + [c.compte for c in comptes]
        categories = get_categories(s)
        categorie_list = [None] + [c.categorie for c in categories]

    # --- VALEURS PAR DEFAUT ---
    # Préparation des textes par défaut (Logique héritée)
    depense_val = float(editable.depense) if editable.depense else 0.0
    recette_val = float(editable.recette) if editable.recette else 0.0
    try:
        compte_val = compte_list.index(str(editable.compte))
    except ValueError:
        compte_val = 0
    try:
        categorie_val = categorie_list.index(str(editable.categorie))
    except ValueError:
        categorie_val = 0

    # --- FORMULAIRE ---
    # Note : On n'utilise pas st.form ici pour pouvoir gérer les boutons
    # individuellement avec des callbacks on_click plus facilement.
    description = st.text_input("Description :", value=editable.description, disabled=not is_new)
    label = st.text_input("Label utilisateur :", value=editable.label_utilisateur)
    compte = st.selectbox("Compte :", options=compte_list, index=compte_val)
    categorie = st.selectbox("Catégorie :", options=categorie_list, index=categorie_val)
    depense = st.text_input("Montant Dépense (€) :", value=str(depense_val))
    recette = st.text_input("Montant Recette (€) :", value=str(recette_val))
    economie = st.checkbox("Economie ?", value=(editable.economie == 'true'))
    datebox = st.date_input("Date : ", value=editable.date)
    mois = st.date_input("Mois :", value=editable.mois)

    selected_ref = st.session_state.nos_ref.index(editable.no_de_reference) if editable.no_de_reference else None

    ref = st.selectbox("Numéro de référence :", index=selected_ref, options=st.session_state.nos_ref, accept_new_options=True)
    declarant = st.selectbox("Déclarant :", options=declarants, index=None)
    fait = st.text_area("Fait marquant :", value=editable.fait_marquant,
                        help="Entrez ici le fait marquant que vous souhaitez mettre en avant")

    st.divider()

    # --- ACTIONS ---
    btn_val, btn_ann, _ = st.columns([1, 1, 2])

    with btn_val:
        st.button("Valider ✅",
                  type="primary",
                  on_click=cb_valider_transaction,
                  args=(editable, is_new, description, datebox, declarant, compte, float(depense), ref,
                        economie, label, mois, categorie, float(recette), fait),
                  width='stretch')

    with btn_ann:
        st.button("Annuler ❌",
                  on_click=cb_retour_main,
                  width='stretch')

    # --- SPLITTING ---
    st.divider()

    c1, c2, c3 = st.columns(3)

    with c1:
        split_val = st.number_input("Split Count", value=1, min_value=1)

        if split_val > 1:
            st.text(f'Split the amount {editable.get_solde()} in {split_val} values')

            # define standard parameter
            rounding: int = 2

            # create a series of boxes
            key_values = [f"-INPUT-{split_val}-{i}" for i in range(split_val)]
            key_months = [f"-MOIS-{split_val}-{i}-" for i in range(split_val)]

            result_values = split_value(editable.get_solde(), split_val, rounding)
            result_months = [editable.mois] * split_val

            for i in range(split_val):
                col1, col2, col3 = st.columns([1, 3, 3])
                with col1:
                    st.write(f"Mois {i + 1}")
                with col2:
                    st.number_input("Montant", key=key_values[i], step=0.01, format="%.2f",
                                    value=result_values[i])
                with col3:
                    st.date_input("Mois", key=key_months[i], value=result_months[i])

            st.divider()

    with c2:
        st.space()
        st.button("✂ Split Custom", width='stretch', on_click=cb_split_custom,
                  args=(editable.index, [float(st.session_state[k]) for k in key_values],
                        [st.session_state[m] for m in key_months],))
    with c3:
        st.space()
        st.button("📅 Split Yearly", width='stretch', on_click=cb_split_yearly, args=(editable.index,))
