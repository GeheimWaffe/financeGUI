from datetime import date
import streamlit as st
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.orm import Session

# Adaptations des imports selon la structure de ton projet
from datamodel import Declarant, SalaireNew, SalairePostes, SalaireComponents


# =============================================================================
# FUNCTIONS : INTERACTIONS AVEC LA BASE DE DONNÉES (CRUD & QUERIES)
# =============================================================================

def db_delete_salaire(session: Session, id_salaire: int):
    """Supprime un salaire et tous ses composants associés en cascade."""
    salaire = session.get(SalaireNew, id_salaire)
    if salaire:
        session.delete(salaire)
        session.commit()


def db_get_declarants(session: Session) -> list[Declarant]:
    """Récupère la liste de tous les déclarants triés par nom."""
    result = session.scalars(select(Declarant).order_by(Declarant.declarant)).all()
    if len(result) == 0:
        return []
    else:
        return list(result)


def db_get_salaires_view(session: Session, id_declarant: int) -> pd.DataFrame:
    """
    Récupère l'historique des salaires d'un déclarant avec la somme des composants.
    Retourne un DataFrame formaté pour l'affichage de gauche.
    """
    stmt = (
        select(
            SalaireNew.id_salaire.label("ID"),
            SalaireNew.mois.label("Mois"),
            SalaireNew.entreprise.label("Entreprise"),
            func.coalesce(func.sum(SalaireComponents.valeur), 0.0).label("Total (€)")
        )
        .join(SalaireComponents, SalaireNew.id_salaire == SalaireComponents.id_salaire, isouter=True)
        .where(SalaireNew.id_declarant == id_declarant)
        .group_by(SalaireNew.id_salaire, SalaireNew.mois, SalaireNew.entreprise)
        .order_by(SalaireNew.mois.desc())
    )
    df = pd.read_sql_query(stmt, session.bind)
    if not df.empty:
        df["Mois"] = pd.to_datetime(df["Mois"]).dt.strftime("%Y-%m")
    return df


def db_get_salaire_details(session: Session, id_salaire: int) -> pd.DataFrame:
    """Récupère les lignes de composants d'un salaire spécifique pour l'édition."""
    stmt = (
        select(
            SalaireComponents.id_component.label("ID Component"),
            SalairePostes.poste.label("Poste"),
            SalairePostes.poste_groupe.label("Groupe"),
            SalaireComponents.valeur.label("Valeur (€)")
        )
        .join(SalairePostes, SalaireComponents.id_poste == SalairePostes.id_poste)
        .where(SalaireComponents.id_salaire == id_salaire)
    )
    return pd.read_sql_query(stmt, session.bind)


def db_update_salaire_components(session: Session, df_edited: pd.DataFrame):
    """Met à jour les valeurs modifiées des composants en base de données."""
    for _, row in df_edited.iterrows():
        comp = session.get(SalaireComponents, int(row["ID Component"]))
        if comp:
            comp.valeur = float(row["Valeur (€)"])
    session.commit()


def db_get_postes_for_copy(session: Session, id_salaire_source: int) -> pd.DataFrame:
    """Récupère les postes et valeurs d'un ancien salaire pour initialiser une copie."""
    stmt = (
        select(
            SalairePostes.id_poste.label("id_poste"),
            SalairePostes.poste.label("Poste"),
            SalaireComponents.valeur.label("Valeur (€)")
        )
        .join(SalaireComponents, SalairePostes.id_poste == SalaireComponents.id_poste)
        .where(SalaireComponents.id_salaire == id_salaire_source)
    )
    return pd.read_sql_query(stmt, session.bind)


def db_get_all_postes(session: Session) -> pd.DataFrame:
    """Récupère la totalité du référentiel des postes disponibles."""
    stmt = select(SalairePostes.id_poste, SalairePostes.poste).order_by(SalairePostes.poste)
    return pd.read_sql_query(stmt, session.bind)


def db_create_full_salaire(session: Session, id_declarant: int, mois: date, entreprise: str,
                           df_components: pd.DataFrame) -> int:
    """Crée un nouvel en-tête Salaire et insère l'ensemble de ses lignes de composants."""
    nouveau_salaire = SalaireNew(
        id_declarant=id_declarant,
        mois=mois,
        entreprise=entreprise
    )
    session.add(nouveau_salaire)
    session.flush()  # Pour récupérer l'id_salaire généré automatiquement

    lignes_inserees = 0
    for _, row in df_components.iterrows():
        # Sécurisation si saisie manuelle brute sans id_poste associé
        id_p = row.get("id_poste")
        if pd.isna(id_p):
            # Recherche alternative par le nom du poste
            stmt_p = select(SalairePostes.id_poste).where(SalairePostes.poste == row["Poste"])
            id_p = session.execute(stmt_p).scalar_one_or_none()

        if id_p:
            comp = SalaireComponents(
                id_salaire=nouveau_salaire.id_salaire,
                id_poste=int(id_p),
                valeur=float(row["Valeur (€)"])
            )
            session.add(comp)
            lignes_inserees += 1

    session.commit()
    return lignes_inserees


# =============================================================================
# INTERFACE UTILISATEUR (STREAMLIT VIEW)
# =============================================================================

def render_salaires_page(session: Session):
    """Affiche la page de gestion globale des salaires."""

    # --- EN-TÊTE DE LA PAGE AVEC GESTION DE FERMETURE & MASTER DATA ---
    col_title, col_md, col_close = st.columns([0.8, 0.1, 0.1])

    with col_title:
        st.title("💼 Gestion des Salaires")

    with col_md:
        # Toggle de l'interface Master Data à l'aide de la session_state
        if "show_master_data" not in st.session_state:
            st.session_state.show_master_data = False
        if st.button("⚙️", help="Configurer les Master Data"):
            st.session_state.show_master_data = not st.session_state.show_master_data
            st.rerun()

    with col_close:
        if st.button("Fermer", type="secondary", help="Revenir au menu principal"):
            st.session_state.current_page = "main"  # Variable exemple pour ton routeur
            st.success("Retour à la page d'accueil...")
            st.rerun()

    st.markdown("---")

    # =========================================================================
    # AFFICHAGE CONDITIONNEL : MODE MASTER DATA
    # =========================================================================
    if st.session_state.show_master_data:
        st.subheader("🛠️ Configuration des Master Data (Référentiels)")

        tab_md_declarant, tab_md_postes = st.tabs(["👤 Déclarants", "📊 Salaires Postes"])

        with tab_md_declarant:
            st.write("Gestion des Déclarants (Ajouter/Modifier directement dans le tableau)")
            df_decl = pd.read_sql_query(select(Declarant.id_declarant, Declarant.declarant), session.bind)
            edited_decl = st.data_editor(df_decl, num_rows="dynamic", key="editor_md_decl", use_container_width=True)
            if st.button("Enregistrer Déclarants"):
                # Logique rapide de synchro ORM (Exemple simplifié pour l'exercice)
                for _, row in edited_decl.iterrows():
                    if pd.isna(row["id_declarant"]):
                        session.add(Declarant(declarant=row["declarant"]))
                session.commit()
                st.success("Déclarants mis à jour !")
                st.rerun()

        with tab_md_postes:
            st.write("Gestion des Postes de Salaire")
            df_pst = pd.read_sql_query(select(SalairePostes.id_poste, SalairePostes.poste, SalairePostes.poste_groupe),
                                       session.bind)
            edited_pst = st.data_editor(df_pst, num_rows="dynamic", key="editor_md_postes", use_container_width=True)
            if st.button("Enregistrer Postes"):
                for _, row in edited_pst.iterrows():
                    if pd.isna(row["id_poste"]):
                        session.add(SalairePostes(poste=row["poste"], poste_groupe=row["poste_groupe"]))
                session.commit()
                st.success("Référentiel des postes enregistré !")
                st.rerun()
        return  # On coupe l'affichage ici tant que la roue dentée est active

    # =========================================================================
    # AFFICHAGE NORMAL : REQUÊTAGE ET WORKFLOW SALAIRES
    # =========================================================================
    declarants = db_get_declarants(session)
    if not declarants:
        st.warning(
            "⚠️ Aucun déclarant trouvé en base de données. Veuillez en ajouter via la roue dentée (Master Data).")
        return

    # Selectbox principal des Déclarants
    declarant_options = {d.id_declarant: d.declarant for d in declarants}
    selected_decl_id = st.selectbox(
        "Sélectionner le déclarant :",
        options=list(declarant_options.keys()),
        format_func=lambda x: declarant_options[x]
    )

    # Séparation de la vue en deux sections (Gauche / Droite)
    left_col, right_col = st.columns([0.45, 0.55], gap="large")

    # --- SECTION DE GAUCHE : LISTE DES SALAIRES SAISIS ---
    with left_col:
        st.subheader("📑 Historique des salaires")
        df_salaires = db_get_salaires_view(session, selected_decl_id)

        if df_salaires.empty:
            st.info("Aucun salaire enregistré pour ce déclarant.")
            dt_salaire = None
            selected_salaire_id = None
        else:
            # Formatage d'affichage monétaire propre
            dt_salaire = st.dataframe(
                df_salaires.style.format({"Total (€)": "{:,.2f} €"}),
                hide_index=True,
                use_container_width=True,
                on_select='rerun',
                selection_mode='single-cell'
            )
            # --- Ecoute de la sélection d'une catégorie
            selected_month = None
            selected_salaire_id = None
            if dt_salaire:
                cells = dt_salaire.selection['cells']
                if cells:
                    row_index = cells[0][0]
                    # retrieving the category and saving to cache
                    selected_month = df_salaires.iloc[row_index]['Mois']
                    selected_salaire_id = int(df_salaires.iloc[row_index]['ID'])

                    st.markdown("---")  # Petite ligne de séparation visuelle

                # --- SECTION DE GAUCHE (Suite) ---
                # (Juste après le bloc d'écoute de la sélection de cellules)

                st.markdown("---")  # Petite ligne de séparation visuelle

                if selected_salaire_id is not None:
                    st.warning(f"👉 Salaire sélectionné pour suppression : **{selected_month}**")

                    # Utilisation d'un bouton de confirmation pour éviter les erreurs de manipulation
                    if st.button("🗑️ Supprimer ce salaire", type="secondary", use_container_width=True):
                        st.session_state.confirm_delete = True

                    # Si l'utilisateur a cliqué sur Supprimer, on affiche la confirmation finale
                    if st.session_state.get("confirm_delete", False):
                        st.error(
                            "⚠️ Êtes-vous sûr de vouloir supprimer définitivement ce salaire et TOUS ses composants ?")

                        col_conf_oui, col_conf_non = st.columns(2)
                        with col_conf_oui:
                            if st.button("🔴 Oui, supprimer", type="primary", use_container_width=True):
                                db_delete_salaire(session, selected_salaire_id)
                                st.toast("Salaire supprimé avec succès !", icon="🗑️")
                                st.session_state.confirm_delete = False
                                st.rerun()
                        with col_conf_non:
                            if st.button("Annuler", use_container_width=True):
                                st.session_state.confirm_delete = False
                                st.rerun()
                else:
                    # Bouton désactivé si aucune ligne n'est sélectionnée
                    st.button("🗑️ Supprimer ce salaire", disabled=True, use_container_width=True,
                              help="Sélectionnez un salaire dans le tableau ci-dessus pour le supprimer.")

    # --- SECTION DE DROITE : DEUX TABS (EDITION & CRÉATION) ---
    with right_col:
        tab_edition, tab_creation, tab_chart = st.tabs(["✏️ Édition", "➕ Création", "📊 Graphique"])

        # TAB 1 : ÉDITION DU SALAIRE SÉLECTIONNÉ
        with tab_edition:
            if selected_salaire_id is None:
                st.info("Sélectionnez un salaire existant dans l'historique de gauche pour l'éditer.")
            else:
                st.subheader("Détail des composants")
                df_details = db_get_salaire_details(session, selected_salaire_id)

                # Éditeur de données Pandas interactif
                edited_df_details = st.data_editor(
                    df_details,
                    disabled=["ID Component", "Poste", "Groupe"],  # On verrouille la structure
                    column_config={"ID Component": None},
                    hide_index=True,
                    use_container_width=True,
                    key=f"editor_edit_{selected_salaire_id}"
                )

                if st.button("Sauvegarder les modifications", type="primary"):
                    db_update_salaire_components(session, edited_df_details)
                    st.success("Modifications enregistrées avec succès !")
                    st.rerun()

        # TAB 2 : CRÉATION D'UN NOUVEAU SALAIRE
        with tab_creation:
            st.subheader("Enregistrer une nouvelle fiche")

            # 1. Option "Copy From" (SelectPrevious)
            if not df_salaires.empty:
                copy_options = {0: "--- Rester vide (Aucun) ---"}
                for _, r in df_salaires.iterrows():
                    copy_options[r["ID"]] = f"{r['Mois']} ({r['Entreprise']})"

                select_previous = st.selectbox(
                    "Copy From",
                    options=list(copy_options.keys()),
                    format_func=lambda x: copy_options[x]
                )
            else:
                select_previous = 0
                st.caption("Aucun historique disponible pour faire une copie.")

            # 2. Formulaire des métadonnées obligatoires
            mois_selector = st.date_input("MoisSelector (Choisir un jour du mois)", value=date.today())
            entreprise_selector = st.text_input("EntrepriseSelector", placeholder="Nom de l'employeur...")

            # Gestion de l'état d'initialisation du DataFrame de saisie
            if "df_new_entries" not in st.session_state:
                st.session_state.df_new_entries = pd.DataFrame(columns=["id_poste", "Poste", "Valeur (€)"])

            if st.button("New"):
                if not entreprise_selector.strip():
                    st.error("❌ Erreur : Le champ 'EntrepriseSelector' doit être saisi.")
                else:
                    if select_previous != 0:
                        # On pré-charge la structure et les montants du précédent salaire sélectionné
                        st.session_state.df_new_entries = db_get_postes_for_copy(session, select_previous)
                        st.toast("Structure copiée avec succès !", icon="📋")
                    else:
                        # On initialise un tableau vide basé sur l'ensemble complet du référentiel des postes à 0.0 €
                        df_all_p = db_get_all_postes(session)
                        df_all_p["Valeur (€)"] = 0.0
                        st.session_state.df_new_entries = df_all_p
                        st.toast("Nouveau formulaire vierge prêt.", icon="🆕")

            # 3. Data Editor interactif pour remplir les montants ligne par ligne
            if not st.session_state.df_new_entries.empty:
                st.markdown("##### Saisie des composants du bulletin :")

                # Configuration des colonnes de l'éditeur
                # Récupération de la liste des postes triés pour alimenter la Selectbox interne du tableau
                df_ref_postes = db_get_all_postes(session)
                liste_noms_postes = df_ref_postes["poste"].tolist()
                config_colonnes = {
                    "id_poste": None,  # On masque l'ID technique pour l'utilisateur
                    "Poste": st.column_config.SelectboxColumn(
                        "Poste",
                        options=liste_noms_postes,
                        required=True,
                    ),
                    "Valeur (€)": st.column_config.NumberColumn(
                        "Valeur (€)",
                        min_value=-10000.0,
                        max_value=10000.0,
                        format="%.2f €",
                        required=True
                    )
                }
                # Le data_editor permet d'ajouter dynamiquement des lignes ou de modifier les existantes
                edited_new_df = st.data_editor(
                    st.session_state.df_new_entries,
                    disabled=["id_poste"] if select_previous != 0 else [],
                    column_config=config_colonnes,
                    hide_index=True,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="editor_creation_salaires"
                )

                # Affichage dynamique du total
                # Dès qu'une cellule est modifiée dans l'éditeur, 'edited_new_df' est réévalué immédiatement
                total_calculé = edited_new_df["Valeur (€)"].sum()

                # Affichage du bandeau de totalisation juste en-dessous du tableau
                st.markdown(
                    f"""
                                    <div style="background-color:#1E293B; padding:10px; border-radius:5px; text-align:right; margin-bottom:15px;">
                                        <span style="color:#94A3B8; font-size:14px; font-weight:bold;">TOTAL BULLETIN :</span>
                                        <span style="color:#38BDF8; font-size:18px; font-weight:bold; margin-left:10px;">{total_calculé:,.2f} €</span>
                                    </div>
                                    """,
                    unsafe_allow_html=True
                )

                # 4. Bouton de sauvegarde finale en base
                if st.button("Sauvegarder le salaire", type="primary"):
                    try:
                        lignes_creees = db_create_full_salaire(
                            session=session,
                            id_declarant=selected_decl_id,
                            mois=mois_selector,
                            entreprise=entreprise_selector,
                            df_components=edited_new_df
                        )
                        st.success(f"🎉 Succès ! Nouveau salaire enregistré. {lignes_creees} lignes insérées en base.")
                        # Nettoyage du cache de création
                        st.session_state.df_new_entries = pd.DataFrame(
                            columns=["id_poste", "Poste", "Valeur (€)"])
                        st.rerun()
                    except Exception as e:
                        st.error(f"Une erreur est survenue lors de la sauvegarde : {e}")
            # =========================================================================
            # TAB 3 : GRAPHIQUE DES SALAIRES
            # =========================================================================
            with tab_chart:
                st.subheader("📈 Évolution des revenus")

                # Saisie du nombre de mois avec un number_input (plus robuste pour les entiers qu'un text_input)
                nb_mois = st.number_input(
                    "Nombre de mois à afficher :",
                    min_value=1,
                    max_value=60,
                    value=12,  # Par défaut : 12 mois
                    step=1,
                    key="nb_mois_chart"
                )

                if df_salaires.empty:
                    st.info("Aucune donnée disponible pour générer le graphique.")
                else:
                    # Configuration du DataFrame pour que st.bar_chart prenne automatiquement "Mois" en axe X
                    df_chart_ready = df_salaires.set_index("Mois")[["Total (€)"]]
                    df_chart_ready = df_chart_ready.iloc[0:nb_mois]

                    # Affichage du Bar Chart natif de Streamlit
                    st.bar_chart(df_chart_ready, use_container_width=True)

                    # Optionnel : Petit récapitulatif textuel en-dessous
                    salaire_moyen = df_chart_ready["Total (€)"].mean()
                    st.caption(
                        f"💡 Salaire moyen calculé sur les {len(df_chart_ready)} derniers mois saisis : **{salaire_moyen:,.2f} €**")