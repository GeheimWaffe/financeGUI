import datetime

import PySimpleGUI as sg
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import engines
import pandas as pd

from datamodel_finance_pg import get_remaining_provisioned_expenses, get_soldes, close_provision, \
    deactivate_transaction, get_categories, get_comptes, Mouvement, \
    import_transaction, MapCategorie, import_keyword, get_transaction
from finance_orm_cli.masterdata import split_mouvement

# Connexion à la base de données PostgreSQL
engine = engines.get_pgfin_engine()

# global parameters
offset_size = 20


def fetch_mouvements(offset=0, search_filter="", sort_column=None, sort_order="asc", category_filter: str = None,
                     compte_filter: str = None, reimbursable: bool = False, affectable: bool = False):
    """Récupère 20 lignes de la table Mouvements avec option de tri et filtre."""
    query = 'SELECT c.index, c."Description", c."Label utilisateur", c."Catégorie",  c."Date", c."Mois", c."Dépense",' \
            'c."Recette", c."Provision à payer", c."Provision à récupérer" FROM public.comptes c' \
            ' WHERE c."Date Out of Bound" is FALSE'
    if search_filter:
        query += f" AND c.\"Description\"::TEXT ILIKE '%%{search_filter}%%'"
    if not category_filter is None:
        query += f' AND c."Catégorie" = \'{category_filter}\''
    if not compte_filter is None:
        query += f' AND c."Compte" = \'{compte_filter}\''
    if reimbursable:
        query += f' AND c."Dépense" > 0 AND (c."Taux remboursement IS NULL OR c."Label utilisateur" IS NULL or c."Date remboursement" IS NULL)'
    if affectable:
        query += f' AND c."Recette" > 0 AND (c."Label utilisateur" IS NULL or c."Date remboursement" IS NULL)'
    if sort_column:
        query += f" ORDER BY {sort_column} {sort_order}"
    query += f" LIMIT {offset_size} OFFSET {offset}"
    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    # Calculations
    df.fillna(value=0, inplace=True)
    df['Solde'] = df['Recette'] - df['Dépense']
    df['Provision'] = df['Provision à récupérer'] - df['Provision à payer']
    df.drop(['Dépense', 'Recette', 'Provision à récupérer', 'Provision à payer'], axis=1, inplace=True)
    return df


def fetch_soldes():
    """ Récupère les soldes des comptes courants"""
    with Session(engine) as session:
        soldes = get_soldes(session, 'Courant')
    values = [[s[0], s[1], f"{s[2]:.2f} €"] for s in soldes]
    return values


def common_category_combo(default_value=None) -> sg.Combo:
    with Session(engine) as session:
        categories = get_categories(session)
        cat_list = [c.categorie for c in categories]

    return sg.Combo(cat_list, key="-CATEGORIE-", default_value=default_value, size=(25, 1), readonly=True,
                    enable_events=True)


def common_compte_combo(default_value=None) -> sg.Combo:
    with Session(engine) as session:
        comptes = get_comptes(session)
        compte_list = [c.compte for c in comptes]

    return sg.Combo(compte_list, key="-COMPTE-", default_value=default_value, size=(25, 1), readonly=True,
                    enable_events=True)


def common_valider_button() -> sg.Button:
    return sg.Button("✅ Valider", size=(10, 1), button_color=("white", "green"), key="-VALIDER-")


def common_cancel_button() -> sg.Button:
    return sg.Button("❌ Annuler", size=(10, 1), button_color=("white", "red"), key="-ANNULER-")


def show_transaction_editor(editable: Mouvement) -> Mouvement:
    # retrieve the comptes
    depense_text = str(round(editable.depense, 2))
    recette_text = str(round(editable.recette, 2))
    layout = [
        [sg.Text("Catégorie :", size=(15, 1)), common_category_combo(editable.categorie)],
        [sg.Text("Label utilisateur :", size=(15, 1)),
         sg.Input(key="-LABEL-", size=(25, 1), default_text=editable.label_utilisateur)],
        [sg.Text("Mois :", size=(15, 1)),
         sg.Input(key="-MOIS-", size=(12, 1), default_text=editable.mois.strftime("%Y-%m-%d")),
         sg.CalendarButton("📅", target="-MOIS-", format="%Y-%m-%d")],
        [sg.Text("Montant Dépense (€) :", size=(15, 1)),
         sg.InputText(key="-DEPENSE-", size=(10, 1), default_text=depense_text)],
        [sg.Text("Montant Recette (€) :", size=(15, 1)),
         sg.InputText(key="-RECETTE-", size=(10, 1), default_text=recette_text)],
        [sg.Checkbox("Economie ?", default=(editable.economie == 'true'), key="-ECONOMIE-")],
        [sg.HorizontalSeparator()],  # Ligne de séparation

        [common_valider_button(), common_cancel_button()]
    ]

    window = sg.Window("Choisissez une catégorie", layout, modal=True, element_justification="left", font=("Arial", 12))

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "-ANNULER-"):
            window.close()
            return None  # Annulation

        elif event == "-VALIDER-":
            try:
                # Vérification des nombres
                depense = float(values["-DEPENSE-"]) if values["-DEPENSE-"] else 0.0
                recette = float(values["-RECETTE-"]) if values["-RECETTE-"] else 0.0

                editable.categorie = values["-CATEGORIE-"]
                editable.label_utilisateur = values["-LABEL-"] if values["-LABEL-"] else None
                editable.mois = datetime.date.fromisoformat(values["-MOIS-"])
                editable.depense = depense
                editable.recette = recette
                editable.economie = 'true' if values["-ECONOMIE-"] else 'false'
                window.close()
                return editable  # Prêt pour insertion en base

            except ValueError:
                sg.popup_error("❌ Veuillez entrer des montants valides !", font=("Arial", 12), text_color="red")


def show_keyword_import(description: str, category: str) -> MapCategorie:
    """ Proposes to insert a new keyword corresponding to the category """
    # Create the layout
    layout = [
        [sg.Text("Adjust the keyword : "), sg.InputText(key="-KEYWORD-", size=(30, 1), default_text=description)],
        [sg.HorizontalSeparator()],  # Ligne de séparation

        [common_valider_button(), common_cancel_button()]
    ]

    # generate the window
    window = sg.Window(f"Adjust the keyword for category : {category}", layout, modal=True,
                       element_justification="left", font=("Arial", 12))

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "-ANNULER-"):
            window.close()
            return None  # Annulation

        elif event == "-VALIDER-":
            try:

                # Données validée
                data = MapCategorie()
                data.categorie = category
                data.keyword = values["-KEYWORD-"]

                window.close()
                return data  # Prêt pour insertion en base

            except ValueError:
                sg.popup_error("❌ Veuillez entrer un mot-clé valide !", font=("Arial", 12), text_color="red")


def show_new_transaction_editor():
    # retrieve the comptes
    layout = [
        [sg.Text("Description :", size=(15, 1)), sg.InputText(key="-DESC-", size=(30, 1))],

        [sg.Text("Date :", size=(15, 1)),
         sg.Input(key="-DATE-", size=(12, 1)),
         sg.CalendarButton("📅", target="-DATE-", format="%Y-%m-%d")],

        [sg.Text("Compte :", size=(15, 1)), common_compte_combo()],

        [sg.Text("Catégorie :", size=(15, 1)), common_category_combo()],

        [sg.Text("Mois :", size=(15, 1)),
         sg.Input(key="-MOIS-", size=(12, 1)),
         sg.CalendarButton("📅", target="-MOIS-", format="%Y-%m-%d")],

        [sg.Text("Montant Dépense (€) :", size=(15, 1)), sg.InputText(key="-DEPENSE-", size=(10, 1))],

        [sg.Text("Montant Recette (€) :", size=(15, 1)), sg.InputText(key="-RECETTE-", size=(10, 1))],

        [sg.HorizontalSeparator()],  # Ligne de séparation

        [common_valider_button(), common_cancel_button()]
    ]

    window = sg.Window("Saisie d'une transaction", layout, modal=True, element_justification="left", font=("Arial", 12))

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "-ANNULER-"):
            window.close()
            return None  # Annulation

        elif event == "-VALIDER-":
            try:
                # Vérification des nombres
                depense = float(values["-DEPENSE-"]) if values["-DEPENSE-"] else 0.0
                recette = float(values["-RECETTE-"]) if values["-RECETTE-"] else 0.0

                # Données validée
                data = Mouvement()
                data.description = values["-DESC-"]
                data.date = values["-DATE-"]
                data.compte = values["-COMPTE-"]
                data.categorie = values["-CATEGORIE-"]
                data.mois = values["-MOIS-"]
                data.depense = depense
                data.recette = recette

                window.close()
                return data  # Prêt pour insertion en base

            except ValueError:
                sg.popup_error("❌ Veuillez entrer des montants valides !", font=("Arial", 12), text_color="red")


def show_period_editor():
    # Définition des variables d'état
    current_year = datetime.datetime.now().year
    # Récupération des provisions non fermées
    session = Session(engine)
    data = get_remaining_provisioned_expenses(session).fetchall()
    displayed_data = [[r[0], r[1], f"{float(r[2]):.2f}"] for r in data]

    headers = ('Mois', 'Catégorie', 'Dépense Courante Restante')
    # Définition de la structure de la fenêtre
    layout = [
        [sg.Table(values=displayed_data, headings=headers, key='-UCP-', enable_events=True,
                  justification="center", auto_size_columns=True,
                  num_rows=10, enable_click_events=True)],
        [sg.Button("Close Provision", size=(15, 1))],
        [common_cancel_button()]
    ]

    # Création de la fenêtre
    window = sg.Window("Provisions", layout, element_justification='center')

    # Boucle d'événements
    while True:
        event, values = window.read()
        update_values = False
        if event in (sg.WIN_CLOSED, "-ANNULER-"):
            break
        elif event == "Close Provision":
            # retrieve the current values
            row = displayed_data[values['-UCP-'][0]]
            mois = row[0]
            category = row[1]
            remaining = float(row[2])
            # close the provision
            close_provision(session, mois, category, remaining)
            update_values = True
            # window['-STATUS-BAR-'].update(f"Provision closed for {mois} and {category}")

        if update_values:
            # if values have to be updated
            data = get_remaining_provisioned_expenses(session).fetchall()
            displayed_data = [[r[0], r[1], f"{float(r[2]):.2f}"] for r in data]
            window['-UCP-'].update(displayed_data)

    session.close()
    window.close()
    print("end of period editor method")


def main():
    ##########
    # STANDARD
    ##########
    update_values: bool = False
    status_message: str = ''

    # Définition des variables d'état
    offset = 0
    df = fetch_mouvements(sort_column="index", sort_order="desc")
    selected_row = -1
    category_filter = None
    compte_filter = None
    desc_filter = None
    reimbursable_filter = False
    affectable_filter = False

    # Soldes bancaires
    soldes = fetch_soldes()
    solde_headers = ('Compte', 'Date', 'Solde')

    # Définition de la structure de la fenêtre
    layout = [
        [sg.Button("Provisions", size=(15, 1), button_color=("green", "black")),
         sg.Text("🔍 Filter By :"),
         common_category_combo(),
         common_compte_combo(),
         sg.Button("Reimbursable Expenses", size=(20, 1), key="-REIMBURSABLE-"),
         sg.Button("Affectable Payments", size=(20,1), key='-AFFECTABLE-'),
         sg.InputText(key='-FILTER-', size=(20, 1), enable_events=True),
         sg.Button("✖ Clear", key="-CLEAR-")
         ],
        [sg.Table(values=df.values.tolist(), headings=list(df.columns), key="-MVTS-", enable_events=True,
                  justification="center", auto_size_columns=True,
                  num_rows=30, enable_click_events=True),
         sg.Column([
             [sg.Table(values=soldes, headings=solde_headers, key="-SOLDES-",
                       justification='center', auto_size_columns=True)],
             [sg.Button("New Transaction", size=(15, 1))],
             [sg.Button("Deactivate", size=(15, 1))],
             [sg.Button("Edit", size=(15, 1))],
             [sg.Button("Add Keyword", size=(15, 1))],
             [sg.InputText(default_text="2", key='-SPLIT-COUNT-', size=(10, 1))],
             [sg.Button("Split Custom", size=(15, 1))],
             [sg.Button("Split Yearly", size=(15, 1))]], element_justification='top')
         ],
        [sg.Button("Previous", size=(15, 1)), sg.Button("Next", size=(15, 1))],
        [sg.Button("Quitter", size=(15, 1), button_color=("white", "red"))],
        [sg.Text("", key="-STATUS-BAR-")]  # Affiche la colonne sélectionnée
    ]

    # Création de la fenêtre
    window = sg.Window("Finance Interface", layout)

    # Boucle d'événements
    while True:
        event, values = window.read()
        update_values = False
        if selected_row > -1:
            index = int(df.iloc[selected_row, 0])
            description = df.iloc[selected_row, 1]
            label_utilisateur = df.iloc[selected_row, 2]
            category = df.iloc[selected_row, 3]
            mois = df.iloc[selected_row, 5]
        else:
            index = -1

        if event in (sg.WIN_CLOSED, "Quitter"):
            break
        elif event == "Provisions":
            show_period_editor()
            print("Period Editor closed")
        elif event == "-CLEAR-":
            category_filter = None
            compte_filter = None
            desc_filter = None
            reimbursable_filter = False
            affectable_filter = False
            update_values = True
        elif event == "-CATEGORIE-":
            category_filter = values["-CATEGORIE-"]
            update_values = True
        elif event == "-COMPTE-":
            compte_filter = values["-COMPTE-"]
            update_values = True
        elif event == '-REIMBURSABLE':
            reimbursable_filter = True
            update_values = True
        elif event == '-AFFECTABLE-':
            affectable_filter = True
            update_values = True
        elif event == '-FILTER-':
            desc_filter = values["-FILTER-"]
            update_values = True
        elif event == "Previous":
            # Revenir aux lignes précédentes
            if offset > 0:
                offset -= offset_size
                update_values = True
        elif event == "Next":
            offset += offset_size
            update_values = True
        elif event == "New Transaction":
            data = show_new_transaction_editor()

            if not data is None:
                import_transaction(engine, data)
                status_message = f"Transaction créée"
                update_values = True
        elif isinstance(event, tuple) and event[0] == "-MVTS-" and event[1] == "+CLICKED+":
            row, col = event[2]  # Récupère la ligne et la colonne cliquées
            if row is None:
                status_message = f"Pas d'index sélectionné"
            elif row >= 0:
                selected_row = row
                status_message = f"Index sélectionné: {df.iloc[row, 0]} pour {df.iloc[row, 1]}"
        elif event == "Edit":
            with Session(engine) as session:
                editable = get_transaction(session, index)
                editable = show_transaction_editor(editable)
                if not editable is None:
                    session.commit()
                    status_message = "Catégorie et label mis à jour"
                    update_values = True
        elif event == "Add Keyword":
            mc = show_keyword_import(description, category)
            if not mc is None:
                try:
                    import_keyword(engine, mc)
                    status_message = f"Keyword imported for category"
                except IntegrityError:
                    status_message = f"keyword already exists"
        elif event == "Split Custom":
            try:
                split_periods = int(values["-SPLIT-COUNT-"])
                index = int(df.iloc[selected_row, 0])
                # Executing the split
                split_mouvement(index, mode='custom', periods=split_periods)
                status_message = f"Splitting custom transaction {index} in {split_periods} parts"
                update_values = True
            except ValueError:
                sg.popup_error("Enter a valid number", title="Enter a number", button_color="red")
        elif event == "Split Yearly":
            # Executing the split
            split_mouvement(index)
            status_message = f"Splitting yearly transaction {index}"
            update_values = True
        elif event == "Deactivate":
            # Deactivate the movement
            deactivate_transaction(engine, index)
            status_message = f"Transaction deactivated {index}"
            update_values = True
        if update_values:
            df = fetch_mouvements(offset, desc_filter, "index", "desc", category_filter=category_filter,
                                  compte_filter=compte_filter, reimbursable=reimbursable_filter, affectable=affectable_filter)
            window["-MVTS-"].update(values=df.values.tolist())
            soldes = fetch_soldes()
            window["-SOLDES-"].update(values=soldes)
        # Updating the status bar
        window["-STATUS-BAR-"].update(status_message)
    # Fermeture de la fenêtre
    window.close()


if __name__ == "__main__":
    main()
