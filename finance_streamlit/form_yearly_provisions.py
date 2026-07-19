import streamlit as st
from datetime import date
from engines import makesession
import finance_streamlit.common as c
from functions import get_yearly_bilan

# CLES DES WIDGETS HERITANT DE FILTRES UTILISATEURS COMMUNS A TOUTES LES PAGES
st_is_courant = 'yp_widget_courant'

# INTERACTIVITE : FONCTIONS CHANGEANT LE COMPORTEMENT DE LA PAGE
def cb_new_provision_depense():
    """ Launch the creation of a new provision """
    # Insère ici ta logique ou ton ouverture de modal/formulaire
    st.session_state.global_filters['is_depense'] = True
    st.session_state.previous_page = c.PAGE_YEARLY_PROVISIONS
    st.session_state.page = c.PAGE_NEW_PROVISION


def cb_new_provision_recette():
    """ Launch the creation of a new provision """
    st.session_state.global_filters['is_depense'] = False
    st.session_state.previous_page = c.PAGE_YEARLY_PROVISIONS
    st.session_state.page = c.PAGE_NEW_PROVISION

# CONSTRUCTION DE L'IHM
def show_yearly_provisions():
    # INITIALISATION DE L'ETAT
    st.session_state[st_is_courant] = st.session_state.global_filters['is_courant']

    # CONSTRUCTION DU FORMULAIRE
    st.title("🎯 Budget Planning")

    # 1. Configuration des filtres en haut de page
    current_year = date.today().year
    next_year = current_year + 1

    col_yr, col_mode = st.columns(2)

    with col_yr:
        # Sélection de l'année (Par défaut : l'an prochain)
        year_options = [current_year, next_year]
        selected_year = st.selectbox(
            "Choisir l'année :",
            options=year_options,
            index=1,  # Index 1 correspond à l'an prochain
            format_func=lambda x: f"{x} (Année Actuelle)" if x == current_year else f"{x} (An Prochain)"
        )

    with col_mode:
        # Sélection du mode (Courant ou Économie)
        mode_display = st.toggle('Economy Mode', key=st_is_courant, on_change=c.cb_set_filter,
                                 args=('is_courant', st_is_courant))

    st.divider()

    # 2. Récupération des données via la session SQL Alchemy
    with makesession() as session:
        # On appelle ta fonction get_yearly_bilan (renommée ou adaptée selon ton besoin)
        df_bilan = get_yearly_bilan(session=session, annee=selected_year, is_courant=not mode_display)

    if df_bilan.empty:
        st.warning(f"⚠️ Aucune donnée disponible pour l'année {selected_year} en mode {mode_display}.")
        return

    # On applique le formatage uniquement sur les deux colonnes cibles de l'année A
    col_dep_a_1 = df_bilan.columns[3]
    col_dep_a = df_bilan.columns[4]
    col_rec_a_1 = df_bilan.columns[5]
    col_rec_a = df_bilan.columns[6]
    col_cat = df_bilan.columns[2]

    # 4. Affichage du DataFrame avec sélection de ligne unique
    st.subheader("📊 Tableau récapitulatif des enveloppes")

    selection_event = st.dataframe(
        df_bilan,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",  # Force le rafraîchissement au clic pour afficher les boutons
        selection_mode="single-row",  # Autorise la sélection d'une seule ligne à la fois
        column_config={col_dep_a_1: st.column_config.NumberColumn(format="%,.2f €"),
                       col_rec_a_1: st.column_config.NumberColumn(format="%,.2f €"),
                       col_dep_a: st.column_config.NumberColumn(format="%,.2f €"),
                       col_rec_a: st.column_config.NumberColumn(format="%,.2f €"),
                       }
    )

    # 5. Logique d'affichage des boutons d'actions sur sélection
    # On extrait l'index de la ligne sélectionnée
    selected_rows = selection_event.get("selection", {}).get("rows", [])

    if selected_rows:
        row_index = selected_rows[0]
        # On récupère le nom de la catégorie sélectionnée depuis le DataFrame d'origine
        categorie_selectionnee = df_bilan.iloc[row_index][col_cat]

        # Pour que le formulaire de manipulation des provisions fonctionne
        # il faut régler les filtres dans le session state
        st.session_state.global_filters['category'] = categorie_selectionnee
        st.session_state.current_month = date(selected_year, 1, 1)

        st.write("")  # Espacement micro
        st.info(f"🛠️ **Actions pour la catégorie : {categorie_selectionnee}**")

        col_btn1, col_btn2, _ = st.columns([1, 1, 2])

        with col_btn1:
            st.button("💰 Budgétiser Dépense", use_container_width=True, on_click=cb_new_provision_depense)

        with col_btn2:
            st.button("📈 Budgétiser Recette", use_container_width=True, on_click=cb_new_provision_recette)
    else:
        st.caption(
            "💡 *Cliquez sur la case à gauche d'une ligne du tableau pour faire apparaître les options de budgétisation.*")
