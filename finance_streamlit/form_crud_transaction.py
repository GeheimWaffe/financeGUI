import streamlit as st
from datamodel import Mouvement
from functions import get_transaction, get_comptes, get_categories
from engines import makesession

declarants = ['Vincent', 'Aurélie']

def cb_valider_transaction(editable, values):
    """Callback exécuté lors de la validation."""
    try:
        # 1. Mise à jour de l'objet (Logique métier issue de ton code)
        editable.compte = values["compte"] if values["compte"] else None
        editable.categorie = values["categorie"] if values["categories"] else None
        editable.label_utilisateur = values["label"] if values["label"] else None

        # Streamlit renvoie un objet date, on le convertit si nécessaire
        editable.mois = values["mois"]

        editable.depense = float(values["depense"]) if values["depense"] else 0.0
        editable.recette = float(values["recette"]) if values["recette"] else 0.0
        editable.economie = 'true' if values["economie"] else 'false'
        editable.no_de_reference = values["ref"] if values["ref"] else None
        editable.fait_marquant = values["fait"] if values["fait"] else None
        editable.declarant = values["declarant"] if values["declarant"] else None

        # 2. Ici, tu appelles ta fonction de sauvegarde : engines.save(editable)

        # 3. Changement de page
        st.session_state.page = 'Main'
        st.success("Transaction enregistrée !")
    except ValueError:
        st.error("❌ Veuillez entrer des montants valides !")


def cb_retour_main():
    """Callback simple pour l'annulation."""
    st.session_state.page = 'Main'


def edit_transaction(is_new: bool):
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
    c1, c2 = st.columns(2)
    with c1:
        description = st.text_input("Description :", value=editable.description, disabled=not is_new)
        declarant = st.selectbox("Déclarant :", options=declarants, index=None)
        compte = st.selectbox("Compte :", options=compte_list, index=compte_val)
        depense = st.text_input("Montant Dépense (€) :", value=str(depense_val))
        ref = st.text_input("Numéro de référence :", value=editable.no_de_reference)
        economie = st.checkbox("Economie ?", value=(editable.economie == 'true'))
    with c2:
        label = st.text_input("Label utilisateur :", value=editable.label_utilisateur)
        mois = st.date_input("Mois :", value=editable.mois)
        categorie = st.selectbox("Catégorie :", options=categorie_list, index=categorie_val)
        recette = st.text_input("Montant Recette (€) :", value=str(recette_val))
        #     ref = st.selectbox("Numéro de référence :", options=numeros_reference)
        fait = st.text_area("Fait marquant :", value=editable.fait_marquant,
                        help="Entrez ici le fait marquant que vous souhaitez mettre en avant")


    st.divider()

    # --- ACTIONS ---
    # On prépare le dictionnaire des valeurs actuelles pour le callback
    current_values = {
        "description"
        "compte": compte, "categorie": categorie, "label": label,
        "mois": mois, "depense": depense, "recette": recette,
        "economie": economie, "ref": ref, "declarant": declarant, "fait": fait
    }

    btn_val, btn_ann, _ = st.columns([1, 1, 2])

    with btn_val:
        st.button("Valider ✅",
                  type="primary",
                  on_click=cb_valider_transaction,
                  args=(editable, current_values),
                  use_container_width=True)

    with btn_ann:
        st.button("Annuler ❌",
                  on_click=cb_retour_main,
                  use_container_width=True)
