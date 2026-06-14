import streamlit as st
import pandas as pd
from sqlalchemy import select
from datamodel import Categorie
from functions import fetch_mouvements


def manage_categories(session):
    st.title("🗂️ Configuration des Catégories")

    sort_order = st.selectbox("Ordre de tri", options=['Nom', 'Groupe'])

    # 1. Chargement des données
    if sort_order == 'Nom':
        df_current = pd.read_sql(select(Categorie).order_by(Categorie.categorie), session.connection())
    else:
        df_current = pd.read_sql(select(Categorie).order_by(Categorie.categorie_groupe), session.connection())

    # 2. L'éditeur de données
    # On bloque la modification de 'compte' et 'compte_minuscule' pour les lignes existantes
    edited_result = st.data_editor(
        df_current,
        key="editor_categories",
        num_rows="dynamic",
        width='stretch',
        hide_index=True,
        column_config={
            Categorie.categorie.name: st.column_config.TextColumn(
                "Nom de la catégorie (Clé)",
                required=True,
            ),
            Categorie.categorie_groupe.name:st.column_config.TextColumn(
                "Groupe",
                required=True,
            ),
            Categorie.categorie_order.name: st.column_config.NumberColumn(
                "Ordre",
                min_value=1,
                max_value=5,
                required=True
            ),
            Categorie.provision_type.name: st.column_config.TextColumn(
                "Type de Provision"
            )
        }
    )
    # 3. Logique de sauvegarde
    if st.button("Enregistrer les modifications", type="primary"):
        state = st.session_state.editor_categories
        try:
            # --- AJOUTS (Ici on récupère bien le minuscule saisi) ---
            for row in state.get("added_rows", []):
                nom = row.get(Categorie.categorie.name)
                groupe = row.get(Categorie.categorie_groupe.name)
                ordre = row.get(Categorie.categorie_order.name)
                type = row.get(Categorie.provision_type.name)

                if nom and groupe and ordre:
                    nouvel_obj = Categorie(
                        categorie=nom,
                        categorie_groupe=groupe,
                        categorie_order=ordre,
                        provision_type=type
                    )
                    session.add(nouvel_obj)
                else:
                    st.error("Manque un nom, un groupe ou un ordre")

            # --- MODIFICATIONS (Seuls le groupe et l'ordre seront mis à jour) ---
            for index_pos, updates in state.get("edited_rows", {}).items():
                nom_pk = df_current.iloc[index_pos][Categorie.categorie.name]
                obj = session.get(Categorie, nom_pk)

                if obj:
                    # On ne traite que les colonnes autorisées
                    if Categorie.categorie_groupe.name in updates:
                        obj.categorie_groupe = updates[Categorie.categorie_groupe.name]
                    if Categorie.categorie_order.name in updates:
                        obj.categorie_order = updates[Categorie.categorie_order.name]
                    if Categorie.provision_type.name in updates:
                        obj[Categorie.provision_type.name] = updates[Categorie.provision_type.name]

            session.commit()
            st.success("Base de données mise à jour !")
            st.rerun()

        except Exception as e:
            session.rollback()
            st.error(f"Erreur : {e}")

    # --- CHECK IF CATEGORY HAS TRANSACTIONS
    category = st.selectbox("Test a category", options=df_current[Categorie.categorie.name].tolist(), index=None)
    if category:
        mvts = fetch_mouvements(session, view=['index', 'Description', 'Catégorie', 'Solde', 'Date', 'Mois'],
                                offset_size=20, offset=0, category_filter=category,sort_column='Date',
                                sort_order='desc')
        if len(mvts) > 0:
            st.dataframe(mvts, width='stretch', hide_index=True)
        else:
            st.error("Pas de mouvements trouvés pour ce filtre")

