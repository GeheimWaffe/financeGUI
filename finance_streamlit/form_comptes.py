import streamlit as st
import pandas as pd
from sqlalchemy import select
from datamodel import Compte
from functions import get_type_comptes

def manage_comptes(session):
    st.title("🏦 Configuration des Comptes")

    #1. Récupération du référentiel
    type_comptes = get_type_comptes(session)

    # 1. Chargement des données
    df_current = pd.read_sql(select(Compte).order_by(Compte.compte), session.connection())

    # 2. L'éditeur de données
    # On bloque la modification de 'compte' et 'compte_minuscule' pour les lignes existantes
    edited_result = st.data_editor(
        df_current,
        key="editor_comptes",
        num_rows="dynamic",
        width='stretch',
        hide_index=True,
        column_config={
            "compte": st.column_config.TextColumn(
                "Nom du Compte (Clé)",
                required=True,
                disabled=True  # Désactivé pour l'édition des lignes existantes
            ),
            "compte_minuscule": st.column_config.TextColumn(
                "Nom Minuscule",
                required=True,
                disabled=True  # Désactivé pour l'édition des lignes existantes
            ),
            "compte_type": st.column_config.SelectboxColumn(
                "Type",
                options=type_comptes,
                required=True
            ),
            "compte_actif": st.column_config.CheckboxColumn("Actif", default=True)
        }
    )

    # Note technique : Streamlit permet TOUJOURS de saisir les colonnes 'disabled'
    # pour les NOUVELLES lignes (added_rows), mais les bloque pour les lignes existantes.

    # 3. Logique de sauvegarde
    if st.button("Enregistrer les modifications", type="primary"):
        state = st.session_state.editor_comptes
        try:
            # --- AJOUTS (Ici on récupère bien le minuscule saisi) ---
            for row in state.get("added_rows", []):
                nom = row.get("compte")
                nom_min = row.get("compte_minuscule")

                if nom and nom_min:
                    nouvel_obj = Compte(
                        compte=nom,
                        compte_minuscule=nom_min,  # Valeur spécifiée par l'utilisateur
                        compte_type=row.get("compte_type", "Courant"),
                        compte_actif=row.get("compte_actif", True)
                    )
                    session.add(nouvel_obj)
                else:
                    st.error("Manque un nom de compte ou un nom minuscule")

            # --- MODIFICATIONS (Seuls Type et Actif seront mis à jour) ---
            for index_pos, updates in state.get("edited_rows", {}).items():
                nom_pk = df_current.iloc[index_pos]["compte"]
                obj = session.get(Compte, nom_pk)

                if obj:
                    # On ne traite que les colonnes autorisées
                    if "compte_type" in updates:
                        obj.compte_type = updates["compte_type"]
                    if "compte_actif" in updates:
                        obj.compte_actif = updates["compte_actif"]
                    # 'compte' et 'compte_minuscule' ne seront jamais dans 'updates'
                    # car désactivés dans l'UI

            session.commit()
            st.success("Base de données mise à jour !")
            st.rerun()

        except Exception as e:
            session.rollback()
            st.error(f"Erreur : {e}")