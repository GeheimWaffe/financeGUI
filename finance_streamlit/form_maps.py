import streamlit as st
import pandas as pd
from sqlalchemy import select
from datamodel import MapCategorie
from functions import find_active_maps, fetch_mouvements


def manage_maps(session):
    st.title("📑️ Configuration des Maps")

    # Display
    if not 'log' in st.session_state:
        st.session_state.log = []

    if 'label_mouvement' in st.session_state:
        selected_label = st.session_state.label_mouvement
    else:
        selected_label = None

    c1, c2, c3 = st.columns([6, 2, 1])
    with c1:
        sort_order = st.selectbox("Ordre de tri", options=['keyword', 'Catégorie'])
    with c2:
        search_term = st.text_input("Filtre par mot-clé", value=selected_label)
    with c3:
        st.space()
        actif = st.toggle("Records actifs", value=True)

    # 1. Chargement des données
    if sort_order == 'keyword':
        df_current = pd.read_sql(
            select(MapCategorie).where(MapCategorie.inactif != actif).where(MapCategorie.keyword.contains(search_term)).order_by(MapCategorie.keyword),
            session.connection())
    else:
        df_current = pd.read_sql(
            select(MapCategorie).where(MapCategorie.inactif != actif).where(MapCategorie.keyword.contains(search_term)).order_by(MapCategorie.categorie),
            session.connection())

    # 2. L'éditeur de données
    # On bloque la modification de 'compte' et 'compte_minuscule' pour les lignes existantes
    edited_result = st.data_editor(
        df_current,
        key="editor_maps",
        num_rows="dynamic",
        width='stretch',
        hide_index=True,
        column_config={
            MapCategorie.keyword.name: st.column_config.TextColumn(
                "Mot-Clé (Clé)",
                required=True,
            ),
            MapCategorie.categorie.name: st.column_config.TextColumn(
                "Catégorie",
                required=True,
            ),
            MapCategorie.declarant.name: st.column_config.TextColumn(
                "Déclarant"
            ),
            MapCategorie.organisme.name: st.column_config.TextColumn(
                "Organisme"
            ),
            MapCategorie.monthshift.name: st.column_config.NumberColumn(
                "Monthly Shift",
                min_value=-12,
                max_value=12
            ),
            MapCategorie.employeur.name: st.column_config.TextColumn(
                "Employeur"
            ),
            MapCategorie.inactif.name: st.column_config.CheckboxColumn(
                "Inactif"
            )
        }
    )

    # Affichage du log
    if len(st.session_state.log) > 0:
        with st.status("Bilan des opérations : ", expanded=True):
            for l in st.session_state.log:
                st.write(l)

    # 3. Logique de sauvegarde
    if st.button("Enregistrer les modifications", type="primary"):
        state = st.session_state.editor_maps
        # reinit the log
        st.session_state.log = []

        try:
            # --- AJOUTS (Ici on récupère bien le minuscule saisi) ---
            added = state.get("added_rows", [])
            if len(added) > 0:
                st.session_state.log += [f"🔍 {len(state.get('added_rows', []))} nouvelles lignes créées. Analyse... "
                                         f""]
            for row in added:
                nouvel_obj = MapCategorie(
                    keyword=row.get(MapCategorie.keyword.name),
                    categorie=row.get(MapCategorie.categorie.name),
                    declarant=row.get(MapCategorie.declarant.name),
                    organisme=row.get(MapCategorie.organisme.name),
                    monthshift=row.get(MapCategorie.monthshift.name),
                    inactif=row.get(MapCategorie.inactif.name),
                    employeur=row.get(MapCategorie.employeur.name)
                )
                # Le nouvel objet ne peut être ajouté que si il n'est pas en conflit avec des objets existants
                conflicting_maps = find_active_maps(session, nouvel_obj.keyword)
                if len(conflicting_maps) == 0:
                    session.add(nouvel_obj)
                    st.session_state.log += [f"Map Categorie créée : {nouvel_obj}"]
                else:
                    st.session_state.log += [f"the map {nouvel_obj} is in conflict with {len(conflicting_maps)} other maps"]

            # --- MODIFICATIONS (Seuls le groupe et l'ordre seront mis à jour) ---
            updated = state.get("edited_rows", {})
            if len(updated) > 0:
                st.session_state.log += [f"🔍{len(state.get('edited_rows', []))} lignes mises à jour. Analyse..."]
            for index_pos, updates in state.get("edited_rows", {}).items():
                nom_pk = df_current.iloc[index_pos][MapCategorie.keyword.name]
                obj: MapCategorie = session.get(MapCategorie, nom_pk)

                if obj:
                    updateable = False
                    # Analyse des différents cas de figure
                    if MapCategorie.inactif.name in updates:
                        # Le statut d'activité a été modifié.
                        inactif = bool(updates[MapCategorie.inactif.name])
                        if inactif:
                            # 1. L'objet est passé au statut inactif. Alors aucune vérification n'est à faire, on peut sauvegarder tel quel
                            updateable = True
                        else:
                            # 2. Tentative de réactiver l'objet : cela ne marche que si il n'est pas en conflit avec d'autres maps actives
                            conflicting_maps = find_active_maps(session, nom_pk)
                            updateable = len(conflicting_maps) == 0
                    else:
                        # Le statut d'activité n'a pas été modifié. Le keyword ne peut pas avoir été modifié non plus
                        updateable = True

                    # La vérification d'actualisation a été faite
                    if updateable:
                        if MapCategorie.categorie.name in updates:
                            obj.categorie = updates[MapCategorie.categorie.name]
                        if MapCategorie.declarant.name in updates:
                            obj.declarant = updates[MapCategorie.declarant.name]
                        if MapCategorie.organisme.name in updates:
                            obj.organisme = updates[MapCategorie.organisme.name]
                        if MapCategorie.monthshift.name in updates:
                            obj.monthshift = updates[MapCategorie.monthshift.name]
                        if MapCategorie.employeur.name in updates:
                            obj.employeur = updates[MapCategorie.employeur.name]
                        if MapCategorie.inactif.name in updates:
                            obj.inactif = updates[MapCategorie.inactif.name]
                        st.session_state.log += [f"Map '{obj}' updated"]
                    else:
                        st.session_state.log += [f"The map {nom_pk} is conflicting with others. maps found : {', '.join([k.keyword for k in conflicting_maps])}"]
            session.commit()
            st.rerun()

        except Exception as e:
            session.rollback()
            st.error(f"Erreur : {e}")

    if st.button("Test the map", type='secondary'):
        mvts = fetch_mouvements(session, view=['index', 'Description', 'Catégorie', 'Solde', 'Date', 'Mois'], offset_size=20, offset=0, search_filter=search_term, sort_column='Date', sort_order='desc')
        mvts = mvts.loc[mvts['Solde'] != 0]
        if len(mvts) > 0:
            st.dataframe(mvts, width='stretch', hide_index=True)
        else:
            st.error("Pas de mouvements trouvés pour ce filtre")

