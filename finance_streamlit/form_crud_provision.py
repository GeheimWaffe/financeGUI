import streamlit as st

from datetime import date
from datamodel import Mouvement
from engines import makesession
from finance_streamlit.common import log_operation, DatabaseOperation
from functions import import_transaction, get_groups, get_categorized_provisions, makesession, spread_over_year

import pandas as pd
import datetime

# --- KEYS
key_category = 'key_cp_category'
key_group = 'key_cp_group'
key_description = 'key_cp_description'
key_amount = 'key_cp_amount'
key_metric = 'key_cp_metric'
key_provision_editor = 'key_provision_editor'
key_provision_dataframe = 'key_provision_dataframe'


def colorier_lignes_passees(row, mois_limite):
    # On compare maintenant avec la variable dynamique passée en argument
    if row['Mois'] < mois_limite:
        return ['background-color: #f0f2f6; color: #7d8590;'] * len(row)
    return [''] * len(row)


def get_provisions_for_year(category: str, group: str, year: int, is_depense: bool, is_courant: bool):
    """ Cette fonction permet de comprendre les provisions prévues pour toute l'année en cours
    par rapport à la catégorie, et au groupe sélectionné. Cela permet de comprendre l'impact de rajouter
    une provision sur la catégorie.

    :returns: Dataframe avec pour colonnes : """

    with makesession() as s:
        df = get_categorized_provisions(s, category, date(year, 1, 1), 12, not is_courant)

    # common columns
    df = df.loc[df['Group'] == group]
    df['Saisie'] = 0.0
    if is_depense:
        df['Provision'] = pd.to_numeric(df['Provision à payer'])
        df['Résultat'] = df['Provision']
        df = df[['Mois', 'Dépense', 'Provision', 'Saisie', 'Résultat']]
    else:
        df['Provision'] = pd.to_numeric(df['Provision à récupérer'])
        df['Résultat'] = df['Provision']
        df = df[['Mois', 'Recette', 'Provision', 'Saisie', 'Résultat']]

    # Répartition
    df = spread_over_year(df, 'Mois')

    return df


def handle_editor_change():
    changes = st.session_state[key_provision_editor]

    if changes["edited_rows"]:
        df: pd.DataFrame = st.session_state[key_provision_dataframe]

        for index, row_changes in changes["edited_rows"].items():
            if "Saisie" in row_changes:
                rowmonth = int(df.at[int(index), "Mois"])
                if rowmonth < st.session_state.current_month.month:
                    # 1. Récupérer la nouvelle valeur saisie
                    new_val = float(0)
                else:
                    # 1. Récupérer la nouvelle valeur saisie
                    new_val = float(row_changes["Saisie"])

                existing_val = float(df.at[int(index), "Provision"])
                # 2. Mettre à jour la colonne Saisie
                df.at[int(index), "Saisie"] = new_val
                # 3. Recalculer le Résultat
                df.at[int(index), "Résultat"] = existing_val + new_val

        # Sauvegarder le DF mis à jour dans le state
        st.session_state[key_provision_dataframe] = df


def cb_retour_main():
    """Callback simple pour l'annulation."""
    st.session_state.page = 'Monthly Provisions'

    # Suppression du dataframe stocké dans la session
    st.session_state[key_provision_dataframe] = None


def cb_set_global_amount():
    new_value = float(st.session_state[key_amount])
    # pour tous les mois au-delà du mois actuel
    # mettre la saisie à la nouvelle valeur
    # recalculer le résultat
    curmonth: date = st.session_state.current_month
    df: pd.DataFrame = st.session_state[key_provision_dataframe]

    df.loc[df['Mois'] >= curmonth.month, "Saisie"] = new_value
    df.loc[df['Mois'] >= curmonth.month, "Résultat"] = df["Provision"] + df["Saisie"]

    st.toast(f"Global amount set to {new_value}")


def cb_change_group(groups: pd.DataFrame, is_courant: bool):
    group = st.session_state[key_group]
    category = st.session_state.global_filters['category']
    is_depense = st.session_state.global_filters['is_depense']

    if group:
        if group == 'Common':
            default_value = f'Provision pour {category}'
        else:
            # on sélectionne le premier pattern trouvé
            first_pattern = groups.loc[groups['classes'] == group]['patterns'].tolist()[0]
            default_value = f'Provision pour {category}, pattern : {first_pattern}'
    else:
        default_value = (f'Provision pour {category}f')

    # on règle le contenu du text box avec la nouvelle valeur
    st.session_state[key_description] = default_value

    # update the dataframe
    st.session_state[key_provision_dataframe] = get_provisions_for_year(category, group,
                                                                        st.session_state.current_month.year,
                                                                        is_depense, is_courant)


def cb_valider_transaction(datebox: date, is_courant: bool):
    """Callback exécuté lors de la validation."""
    # --- VERIFICATION OF COMPLETENESS
    if datebox is None:
        st.error('Missing Date !')
    elif description is None:
        st.error('Missing Description !')
    else:
        with makesession() as s:
            # Sauvegarde
            try:
                # --- CONSTRUIRE LES PROVISIONS
                df: pd.DataFrame = st.session_state[key_provision_dataframe]
                for i in range(len(df)):
                    # si la saisie est non null, alors il faut créer une provision
                    saisie = float(df.at[i, 'Saisie'])

                    if saisie > 0:
                        no_mois = int(df.at[i, 'Mois'])
                        mois = date(st.session_state.current_month.year, no_mois, 1)

                        # champs nécessaires : date, description, catégorie, economie, mois, provision_payer, provision_récupérer,
                        editable = Mouvement()
                        editable.categorie = st.session_state.global_filters['category']
                        editable.description = st.session_state[key_description]
                        editable.label_utilisateur = st.session_state[key_description]
                        editable.economie = 'false' if is_courant else 'true'
                        editable.date = datebox
                        editable.mois = st.session_state.current_month
                        is_depense = st.session_state.global_filters['is_depense']
                        if is_depense:
                            editable.provision_payer = saisie
                        else:
                            editable.provision_recuperer = saisie

                        # IMPORT de la transaction valide
                        import_transaction(s, editable)
                        log_operation(
                            DatabaseOperation(datetime.datetime.now(), f"Insertion of Mouvement : {editable}", True))

            except ValueError:
                st.error("❌ Veuillez entrer des montants valides !")

            # Update
            s.flush()
            # if no test mode, we update
            if not st.session_state.test_mode:
                s.commit()

        # Suppression du dataframe stocké dans la session
        st.session_state[key_provision_dataframe] = None

        # 3. Changement de page
        st.toast('Provisions created !')
        st.session_state.last_event = f'Transaction updated'
        st.session_state.page = 'Monthly Provisions'


def create_provision(is_courant: bool):
    is_depense = st.session_state.global_filters['is_depense']
    category = st.session_state.global_filters['category']
    previous_provision = st.session_state.current_consumption
    editable = Mouvement()

    st.title(f"✍️ Créer une provision de type {'Dépense' if is_depense else 'Recette'}")

    # --- EN-TÊTE
    st.badge(f"Mode : {'Courant' if is_courant else 'Economie'}")
    st.badge(f"Sens : {'Dépense' if is_depense else 'Recette'}")
    st.badge(f"Catégorie : {st.session_state.global_filters['category']}")
    st.badge(f"Current Month : {st.session_state.current_month}")
    # --- REFERENTIELS ---
    with makesession() as s:
        available_groups = get_categorized_provisions(s, category_filter=category,
                                                      month=st.session_state.current_month,
                                                      number_months=1,
                                                      economy_mode=not is_courant)
        groups = get_groups(s)

    # --- VALEURS PAR DEFAUT ---*
    # --- FORMULAIRE ---
    # Note : On n'utilise pas st.form ici pour pouvoir gérer les boutons
    # individuellement avec des callbacks on_click plus facilement
    group_options = available_groups['Group'].tolist()
    if not 'Common' in group_options:
        group_options = ['Common'] + group_options

    group = st.selectbox("Groupe :", options=group_options, key=key_group,
                         on_change=cb_change_group, args=(groups, is_courant))

    description = st.text_input("Description :", key=key_description)

    datebox = st.date_input("Date : ", value='today')

    st.divider()

    col_amount, col_spread = st.columns(2)
    with col_amount:
        st.text_input('Saisie Globale', value=0, help='Si vous voulez appliquer un montant global', key=key_amount)
    with col_spread:
        st.space()
        st.button('Fill Down', on_click=cb_set_global_amount)

    # Initialisation paresseuse : si pas dans le session state
    if key_provision_dataframe not in st.session_state:
        st.session_state[key_provision_dataframe] = None

    if st.session_state[key_provision_dataframe] is None:
        st.session_state[key_provision_dataframe] = get_provisions_for_year(category, group,
                                                                            st.session_state.current_month.year,
                                                                            is_depense, is_courant)

    df_styled = st.session_state[key_provision_dataframe].style.apply(colorier_lignes_passees, axis=1,
                                                                      args=(st.session_state.current_month.month,))

    monthly_profile = st.data_editor(df_styled, height='content', hide_index=True,
                                     key=key_provision_editor,
                                     on_change=handle_editor_change, column_config={
            "Mois": st.column_config.Column(disabled=True),
            "Provision": st.column_config.NumberColumn("Provision (€)", disabled=True, format="%.2f"),
            "Dépense": st.column_config.NumberColumn("Dépense (€)", disabled=True,
                                                     format="%.2f"),
            "Recette": st.column_config.NumberColumn("Recette (€)", disabled=True,
                                                     format="%.2f"),
            "Saisie": st.column_config.NumberColumn("Nouvelle Saisie (€)", format="%.2f"),
            "Résultat": st.column_config.NumberColumn("Résultat final (€)", disabled=True, format="%.2f")})

    # Count the modified values
    df: pd.DataFrame = st.session_state[key_provision_dataframe]
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="# de Provisions à créer", value=len(df.loc[df['Saisie'] != 0]))
    with col2:
        st.metric(label='Montant correspondant', value=df['Saisie'].sum())

    # --- ACTIONS ---
    btn_val, btn_ann, _ = st.columns([1, 1, 2])

    with btn_val:
        st.button("Valider ✅",
                  type="primary",
                  on_click=cb_valider_transaction,
                  args=(datebox, is_courant),
                  width='stretch')

    with btn_ann:
        st.button("Annuler ❌",
                  on_click=cb_retour_main,
                  width='stretch')
