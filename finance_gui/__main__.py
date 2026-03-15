import datetime
import re

from collections.abc import Iterable
from PySimpleGUI import RELIEF_GROOVE, RELIEF_SUNKEN
from dateutil.relativedelta import relativedelta
import PySimpleGUI as sg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import matplotlib.pyplot as plt
from interests import generate_payment_schedule
from graphs import GraphSolde

import engines
import pandas as pd

# Imports from data model
# New
from datamodel import Mouvement, MapCategorie, Classifier
from functions import get_comptes, get_type_comptes, fetch_mouvements, get_groups, get_categorized_provisions, \
    import_transaction, get_categories, get_events, get_transaction, get_yearly_realise, get_groups_of_category, \
    get_solde, get_remaining_provisioned_expenses, close_provision, create_salaries, \
    save_capital_reimbursements, get_provisions_for_month, deactivate_transactions, deactivate_transaction, \
    apply_mass_update, import_keyword, get_matching_keywords, get_keywords, simple_split, split_mouvement, split_number, \
    get_balances, calculate_labels, find_salary_transaction, get_salary_candidates, get_jobs, get_numeros_reference, \
    save_map_categorie, identify_gaps, fetch_soldes, JobMapper, split_value, get_salaries

# Connexion à la base de données PostgreSQL
engine = engines.get_pgfin_engine()

# Standard parameters
default_police = 'Calibri'
sg.set_options(font=(default_police, 10))

declarants = ['Vincent', 'Aurélie']


def makesession() -> Session:
    return Session(engines.get_pgfin_engine())


def fetch_provisions(view: Iterable, offset_size: int, category_filter: str, month_filter: datetime.date,
                     economy_mode: bool) -> pd.DataFrame:
    with makesession() as s:
        df = fetch_mouvements(s, view=view, offset_size=offset_size, offset=0, category_filter=category_filter,
                              month_filter=month_filter,
                              provisions=True, economy_mode=economy_mode)
    df = df[["index", "Description", "Provision"]]
    return df


def fetch_keywords():
    with Session(engine) as session:
        result = session.scalars(select(MapCategorie).order_by(MapCategorie.categorie)).all()

    return result


def fetch_balances():
    first_month = datetime.date.today() - datetime.timedelta(weeks=12)
    with makesession() as session:
        result = get_balances(session, first_month)
    return result


def fetch_salary_candidates():
    result = get_salary_candidates(engine)
    return result


def format_metrics(depense: float, recette: float, solde: float):
    return f"Dépense : {round(depense, 2)} | Recette : {round(recette, 2)} | Solde : {round(solde, 2)}"


def classify(value: str, classification_matrix):
    for pattern, result in classification_matrix:
        if pattern in value:
            return pattern, result
    return None, 'Common'


def categorize_provisions(transactions: pd.DataFrame, patterns: pd.DataFrame) -> pd.DataFrame:
    """ categorizes the provisions in groups and patterns"""

    # Classifying
    transactions['Group'] = transactions['Description'].apply(classify, classification_matrix=patterns.values)

    transactions[['Pattern', 'Group']] = transactions['Group'].apply(pd.Series)
    # Returning
    result = transactions[['Group', 'Pattern', 'index', 'Description', 'Solde', 'Provision']].sort_values(
        ['Group', 'Description'])

    return result


def draw_piechart(data: pd.DataFrame, value_field_name: str):
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.pie(data[value_field_name], labels=data.index, autopct='%1.1f%', colors=['#E95420', '#2C001E'])


def common_tag_combo(numeros_reference: list, readonly: bool, default_value: str = '') -> sg.Combo:
    return sg.Combo(numeros_reference, key='-NOS-', size=(25, 1), readonly=readonly, default_value=default_value,
                    enable_events=True)


def common_job_combo(job_titles: Iterable) -> sg.Combo:
    """ Retrieves the last jobs and provides a combo with it """
    return sg.Combo(job_titles, key="-JOBS-", size=(35, 1), readonly=True, enable_events=True)


def common_category_combo(default_value=None) -> sg.Combo:
    with Session(engine) as session:
        categories = get_categories(session)
        cat_list = [c.categorie for c in categories]

    return sg.Combo(cat_list, key="-CATEGORIE-", default_value=default_value, size=(25, 1), readonly=True,
                    enable_events=True)


def common_compte_combo(default_value=None) -> sg.Combo:
    with makesession() as s:
        comptes = get_comptes(s)
    compte_list = [c.compte for c in comptes]

    return sg.Combo(compte_list, key="-COMPTE-", default_value=default_value, size=(25, 1), readonly=True,
                    enable_events=True)


def common_valider_button() -> sg.Button:
    return sg.Button("✅ Valider", size=(10, 1), button_color=("white", "green"), key="-VALIDER-")


def common_cancel_button() -> sg.Button:
    return sg.Button("❌ Annuler", size=(10, 1), button_color=("white", "red"), key="-ANNULER-")


def common_delete_button() -> sg.Button:
    return sg.Button("❌ Supprimer", size=(10, 1), button_color=("white", "red"), key="-DELETE-")


def common_status_bar() -> sg.Text:
    return sg.Text('', key='-STATUS-BAR-', relief=RELIEF_GROOVE)


def get_toggle_style(state: bool):
    return ("white", "#E95420") if state else ("white", "#555555")


def convert_to_month(value: str) -> datetime.date:
    """ Converts a string value to a date"""
    if re.match("2[0-9]{3}-[0-1][0-9]-[0-9]{2}", value):
        converted = '-'.join([value[0:7], '01'])
        return datetime.date.fromisoformat(converted)
    else:
        raise ValueError(f"The value {value} is not in the proper format")


def link_transaction(editable: Mouvement) -> Mouvement:
    """ Function that enables to link a transaction to a common event and label
    Also, it is possible to set the reimbursement ratio"""
    # Data
    with makesession() as s:
        df = get_events(s, editable.categorie)

    # parameters
    is_expense = editable.depense is not None and editable.depense > 0

    if is_expense:

        taux = str(round(editable.taux_remboursement * 100, 2)) if editable.taux_remboursement else 0
        expected = str(round(editable.depense * editable.taux_remboursement, 2)) if editable.taux_remboursement else 0

        layout = [[sg.Text("Taux de remboursement (%) : "),
                   sg.Input(key='-TAUX-', size=(10, 1), default_text=taux, enable_events=True)],
                  [sg.Text("Remboursement attendu : "), sg.Text(expected, text_color="blue", key='-EXPECTED-')]]
    else:
        layout = []

    dt_remb = ''
    if editable.date_remboursement is not None:
        dt_remb = editable.date_remboursement.strftime('%Y-%m-%d')
    label = ''
    if editable.label_utilisateur is not None:
        label = editable.label_utilisateur

    layout += [
        [sg.Text(f"Date de la transaction : {editable.date}", relief=RELIEF_SUNKEN)],
        [sg.Text("Date d'événement :", size=(15, 1)),
         sg.Input(key="-DATE-", size=(12, 1), default_text=dt_remb),
         sg.CalendarButton("Calendar", target="-DATE-", format="%Y-%m-%d")],
        [sg.Text("Libellé : ", size=(15, 1)),
         sg.Input(key="-LABEL-", size=(50, 1), default_text=label)],
        [sg.HorizontalSeparator()],
        [sg.Table(values=df.values.tolist(), headings=list(df.columns), key='-EVENTS-', enable_events=True,
                  justification="center", auto_size_columns=True,
                  num_rows=10, enable_click_events=True)],
        [sg.HorizontalSeparator()],
        [common_valider_button(), common_cancel_button()]
    ]

    # Build the window
    window = sg.Window(f"Liez une transaction à un événement, catégorie {editable.categorie}", layout, modal=True,
                       element_justification="left",
                       font=("Calibri", 12))

    # Listen to the events
    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "-ANNULER-"):
            window.close()
            return None
        elif event == '-TAUX-':
            try:
                new_taux = float(values['-TAUX-']) / 100 if values['-TAUX-'] else 0
                new_expected = new_taux * float(editable.depense)
                window['-EXPECTED-'].update(str(new_expected))
            except ValueError:
                sg.popup_error("❌ Veuillez entrer des montants valides !", font=("Calibri", 12), text_color="red")
        elif isinstance(event, tuple) and event[0] == "-EVENTS-" and event[1] == "+CLICKED+":
            row, col = event[2]  # Récupère la ligne et la colonne cliquées
            if row is None:
                status_message = f"Pas d'index sélectionné"
            elif row >= 0:
                date = df.iloc[row, 0]
                evenement = df.iloc[row, 1]
                window['-DATE-'].update(date)
                window['-LABEL-'].update(evenement)
        elif event == '-VALIDER-':
            # retrieve all the values, and try to save
            try:
                if is_expense:
                    if values['-TAUX-']:
                        new_taux = float(values['-TAUX-']) / 100
                        new_expected = new_taux * float(editable.depense)
                        editable.taux_remboursement = new_taux
                        editable.provision_recuperer = new_expected
                if values['-DATE-']:
                    editable.date_remboursement = datetime.date.fromisoformat(values['-DATE-'])
                if values['-LABEL-']:
                    editable.label_utilisateur = values['-LABEL-']
                window.close()
                return editable
            except:
                sg.popup_error("❌ Veuillez entrer des montants valides !", font=("Calibri", 12), text_color="red")


def form_update_transactions(indexes: list, numeros_reference: list):
    """ Window to edit transactions en masse"""
    layout = [
        [sg.Text(f"choose properties for following transactions :{indexes}")],
        [sg.Text('Description :', size=(15, 1)), sg.Input(key='-DESCRIPTION-', size=(25, 1))],
        [sg.Text("Catégorie :", size=(15, 1)), common_category_combo()],
        [sg.Text("Label utilisateur :", size=(15, 1)), sg.Input(key="-LABEL-", size=(25, 1))],
        [sg.Text("Mois :", size=(15, 1)),
         sg.Input(key="-MOIS-", size=(12, 1)),
         sg.CalendarButton("Calendar", target="-MOIS-", format="%Y-%m-%d")],
        [sg.Text("Date d'événement :"), sg.Input(key="-DATE-", size=(12, 1)),
         sg.CalendarButton("Calendar", target="-DATE-", format="%Y-%m-%d")],
        [sg.Text("Numéro de référence : "), common_tag_combo(numeros_reference, False)],
        [sg.HorizontalSeparator()],
        [common_valider_button(), common_cancel_button()]
    ]

    window = sg.Window(f"Apply to {len(indexes)} transactions", layout, modal=True)

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "-ANNULER-"):
            window.close()
            break
        elif event == '-VALIDER-':
            result = Mouvement()
            result.description = values['-DESCRIPTION-'] if values['-DESCRIPTION-'] else None
            result.label_utilisateur = values['-LABEL-'] if values['-LABEL-'] else None
            result.no_de_reference = values['-NOS-'] if values['-NOS-'] else None
            result.date_remboursement = datetime.date.fromisoformat(values['-DATE-']) if values['-DATE-'] else None
            result.categorie = values['-CATEGORIE-'] if values['-CATEGORIE-'] else None
            if values['-MOIS-']:
                result.mois = convert_to_month(values['-MOIS-'])
            window.close()
            return result
    # return the values


def form_update_transaction(editable: Mouvement, numeros_reference: list) -> Mouvement:
    # retrieve the comptes
    if editable.depense:
        depense_text = str(round(editable.depense, 2))
    else:
        depense_text = ''
    if editable.recette:
        recette_text = str(round(editable.recette, 2))
    else:
        recette_text = ''
    if editable.fait_marquant:
        fm = editable.fait_marquant
    else:
        fm = ''
    if editable.declarant:
        dec = editable.declarant
    else:
        dec = ''

    layout = [
        [sg.Text(f"Transaction {editable.description}")],
        [sg.Text("Compte :", size=(15, 1)), common_compte_combo(editable.compte)],
        [sg.Text("Catégorie :", size=(15, 1)), common_category_combo(editable.categorie),
         sg.Button('Add Keyword', key='-KEYWORD-')],
        [sg.Text("Label utilisateur :", size=(15, 1)),
         sg.Input(key="-LABEL-", size=(25, 1), default_text=editable.label_utilisateur)],
        [sg.Text("Mois :", size=(15, 1)),
         sg.Input(key="-MOIS-", size=(12, 1), default_text=editable.mois.strftime("%Y-%m-%d")),
         sg.CalendarButton("Calendar", target="-MOIS-", format="%Y-%m-%d")],
        [sg.Text("Montant Dépense (€) :", size=(15, 1)),
         sg.InputText(key="-DEPENSE-", size=(10, 1), default_text=depense_text)],
        [sg.Text("Montant Recette (€) :", size=(15, 1)),
         sg.InputText(key="-RECETTE-", size=(10, 1), default_text=recette_text)],
        [sg.Checkbox("Economie ?", default=(editable.economie == 'true'), key="-ECONOMIE-")],
        [sg.Text("Numéro de référence : "), common_tag_combo(numeros_reference, False, editable.no_de_reference)],
        [sg.Text("Déclarant"), sg.Combo(values=declarants, key='-DECLARANT-', size=(15, 1), default_value=dec)],
        [sg.Multiline(key='-FAIT-', size=(50, 5), default_text=fm,
                      tooltip="Entrez ici le fait marquant que vous souhaitez mettre en avant")],
        [sg.HorizontalSeparator()],  # Ligne de séparation

        [common_valider_button(), common_cancel_button()]
    ]

    window = sg.Window("Editeur de transaction", layout, modal=True, element_justification="left",
                       font=("Calibri", 12))

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "-ANNULER-"):
            window.close()
            return None  # Annulation
        elif event == '-KEYWORD-':
            # select chosen category
            category = values['-CATEGORIE-']
            # ask for keyword selection
            mc: MapCategorie = form_keyword_import(editable.description, category)
            if not mc is None:
                import_keyword(engine, mc)
                sg.popup("Import successful !", title='Database import')

        elif event == "-VALIDER-":
            try:
                # Vérification des nombres
                depense = float(values["-DEPENSE-"]) if values["-DEPENSE-"] else 0.0
                recette = float(values["-RECETTE-"]) if values["-RECETTE-"] else 0.0

                editable.compte = values["-COMPTE-"] if values["-COMPTE-"] != '' else None
                editable.categorie = values["-CATEGORIE-"]
                editable.label_utilisateur = values["-LABEL-"] if values["-LABEL-"] else None
                editable.mois = convert_to_month(values["-MOIS-"])
                editable.depense = depense
                editable.recette = recette
                editable.economie = 'true' if values["-ECONOMIE-"] else 'false'
                editable.no_de_reference = values['-NOS-'] if values['-NOS-'] else None
                editable.fait_marquant = values["-FAIT-"] if values["-FAIT-"] else None
                editable.declarant = values["-DECLARANT-"] if values["-DECLARANT-"] else None
                window.close()
                return editable  # Prêt pour insertion en base

            except ValueError:
                sg.popup_error("❌ Veuillez entrer des montants valides !", font=("Calibri", 12), text_color="red")


def form_update_provision(offset_size: int, categorie: str, mois: datetime.date, economy_mode: bool = False):
    # Retrieve the provisions
    with makesession() as s:
        df_groups = get_categorized_provisions(s, category_filter=categorie, month=mois,
                                               economy_mode=economy_mode)
        df_groups.sort_values('Group', inplace=True)
        df = fetch_mouvements(s, view=None, offset_size=offset_size, category_filter=categorie, month_filter=mois,
                              economy_mode=economy_mode)
        # Retrieve the patterns (a dataframe with classes and patterns
        patterns = get_groups(s)

        # show the result
    df = categorize_provisions(df, patterns)

    layout = [
        [sg.Table(values=df_groups.values.tolist(), headings=list(df_groups.columns), key='-GROUPS-',
                  enable_events=True, enable_click_events=True)],
        [sg.Button('Delete Group', size=(15, 1), key='-DELETE-GROUP-'),
         sg.Button('New Group', size=(15, 1), key='-NEW-GROUP-')],
        [sg.Text("Provisions :")],
        [sg.Table(values=df.values.tolist(), headings=list(df.columns), key="-PROVISIONS-",
                  enable_events=True,
                  justification="center", auto_size_columns=True,
                  num_rows=20, enable_click_events=True)],
        [sg.Text("Description :", size=(25, 1)),
         sg.Input(key="-DESCRIPTION-", size=(25, 1))],
        [sg.Text("Provision Dépense (€) :", size=(15, 1)),
         sg.InputText(key="-DEPENSE-", size=(10, 1), default_text="0.00"),
         sg.Text("Provision Recette (€) :", size=(15, 1)),
         sg.InputText(key="-RECETTE-", size=(10, 1), default_text="0.00")],
        [sg.Checkbox("Create for remaining year ?", default=False, key='-ALL-YEAR-')],
        [common_valider_button()],
        [common_cancel_button()]
    ]

    # Build the window
    window = sg.Window("Editez une provision", layout, modal=True, element_justification="left", font=("Calibri", 12))
    while True:
        event, values = window.read()
        update_values = False

        if event in (sg.WIN_CLOSED, "-ANNULER-"):
            window.close()
            return None  # Annulation
        elif isinstance(event, tuple) and event[0] == "-PROVISIONS-" and event[1] == "+CLICKED+":
            row, col = event[2]  # Récupère la ligne et la colonne cliquées
            try:
                if row >= 0:
                    index = int(df.iloc[row, 2])
                else:
                    index = -1
            except TypeError:
                pass  # no row selected
        elif isinstance(event, tuple) and event[0] == '-GROUPS-' and event[1] == '+CLICKED+':
            row, col = event[2]
            pass
        elif event == '-NEW-GROUP-':
            # creating a new group from scratch
            # first, check if there is a suggestion
            selected_rows = values['-PROVISIONS-']
            if not selected_rows:
                default_keyword = ''
            else:
                indexes = df.iloc[selected_rows, 3].values.tolist()
                default_keyword = indexes[0]

            group_name = sg.PopupGetText('Group name ?', modal=True)
            keyword = sg.PopupGetText('Associated Keyword ?', modal=True, default_text=default_keyword)

            if group_name and keyword:
                # Create a new pattern
                cl = Classifier(patterns=keyword, classes=group_name)
                with Session(engine) as session:
                    session.add(cl)
                    session.commit()
                    sg.popup_ok(f'Creation of classifier : {cl} done')
                    update_values = True
        elif event == "-DELETE-":
            # identify the deleted provision
            if index >= 0:
                deactivate_transaction(engine, index)
                update_values = True
        elif event == "-VALIDER-":
            try:
                # Vérification des nombres
                depense = float(values["-DEPENSE-"]) if values["-DEPENSE-"] else 0.0
                recette = float(values["-RECETTE-"]) if values["-RECETTE-"] else 0.0
                if values["-DESCRIPTION-"] is None or values["-DESCRIPTION-"] == '':
                    raise ValueError("You need to enter a proper description")

                # create new item
                if values['-ALL-YEAR-']:
                    months = [mois + relativedelta(months=i) for i in range(13 - mois.month)]
                else:
                    months = [mois]

                # Loop
                for m in months:
                    item = Mouvement()
                    item.date = datetime.date.today()
                    item.mois = m
                    item.categorie = categorie
                    item.description = values["-DESCRIPTION-"]
                    item.provision_payer = depense
                    item.provision_recuperer = recette
                    item.economie = 'true' if economy_mode else 'false'

                    # save item
                    with makesession() as s:
                        import_transaction(s, item)
                        s.commit()
                update_values = True
            except ValueError:
                sg.popup_error(f"Error {ValueError}. ❌ Veuillez entrer des montants valides !", font=("Calibri", 12),
                               text_color="red")

        # Managing updates
        if update_values:
            with makesession() as s:
                patterns = get_groups(s)
                df_groups = get_categorized_provisions(s, category_filter=categorie, month=mois,
                                                       economy_mode=economy_mode)
                df_groups.sort_values('Group', inplace=True)

                df = fetch_mouvements(s, view=None, offset_size=offset_size, category_filter=categorie,
                                      month_filter=mois,
                                      economy_mode=economy_mode)
            df = categorize_provisions(df, patterns)
            window['-PROVISIONS-'].update(df.values.tolist())
            window['-GROUPS-'].update(df_groups.values.tolist())


def form_update_keyword(description: str):
    """ displays existing keywords matching with a transaction"""
    # get matching keywords
    mcs = get_matching_keywords(engine, description)
    values = [[str(mc.keyword), str(mc.categorie)] for mc in mcs]
    headers = ['Keyword', 'Catégorie']

    # create a layout
    layout = [
        [sg.Table(values=values, headings=headers, num_rows=5, key='-KEYWORDS-')],
        [sg.HorizontalSeparator()],
        [sg.Text("Change keyword ?")],
        [common_category_combo()]
    ]

    # display
    window = sg.Window("Matching keywords", layout, modal=True, element_justification='center')

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            break
        elif event == '-CATEGORIE-':
            # user wants to change the keyword
            new_cat = values['-CATEGORIE-']
            if sg.popup_ok_cancel("Do you want to change the category ? ", keep_on_top=True) == "OK":
                with Session(engine) as session:
                    for mc in mcs:
                        mc.categorie = new_cat
                        session.add(mc)

                    session.commit()

                sg.popup("Changes saved")
                break
    window.close()


def form_keyword_import(description: str, category: str) -> MapCategorie:
    """ Proposes to insert a new keyword corresponding to the category """
    # Create the layout
    layout = [
        [sg.Text("Adjust the keyword : "), sg.InputText(key="-KEYWORD-", size=(30, 1), default_text=description)],
        [sg.HorizontalSeparator()],  # Ligne de séparation

        [common_valider_button(), common_cancel_button()]
    ]

    # generate the window
    window = sg.Window(f"Adjust the keyword for category : {category}", layout, modal=True,
                       element_justification="left", font=("Calibri", 12))

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
                sg.popup_error("❌ Veuillez entrer un mot-clé valide !", font=("Calibri", 12), text_color="red")


def create_new_provision(mois: datetime.date) -> Mouvement:
    """ creates a new provision
    :param mois: presupposes that a month has been selected
    :returns: a newly created provision"""
    layout = [
        [sg.Text("Catégorie :", size=(15, 1)), common_category_combo()],

        [sg.Text("Date :", size=(15, 1)),
         sg.Input(key="-DATE-", size=(12, 1), default_text=datetime.date.today().strftime('%Y-%m-%d')),
         sg.CalendarButton("Calendar", target="-DATE-", format="%Y-%m-%d")],

        [sg.Text("Description :", size=(15, 1)), sg.InputText(key="-DESC-", size=(30, 1))],

        [sg.Text("Dépense à provisionner (€) :", size=(15, 1)), sg.InputText(key="-DEPENSE-", size=(10, 1))],

        [sg.Text("Recette à provisionner (€) :", size=(15, 1)), sg.InputText(key="-RECETTE-", size=(10, 1))],

        [sg.Checkbox("Economie ?", key="-ECONOMIE-")],

        [sg.HorizontalSeparator()],  # Ligne de séparation

        [common_valider_button(), common_cancel_button()]
    ]
    # creates the layout

    window = sg.Window("Saisie d'une provision", layout, modal=True, element_justification="left",
                       font=("Calibri", 12))

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
                data.categorie = values["-CATEGORIE-"]
                data.mois = mois
                data.provision_payer = depense
                data.provision_recuperer = recette
                data.economie = 'true' if values["-ECONOMIE-"] else 'false'

                window.close()
                return data  # Prêt pour insertion en base

            except ValueError:
                sg.popup_error("❌ Veuillez entrer des montants valides !", font=("Calibri", 12), text_color="red")


def create_new_mouvement():
    # retrieve the comptes
    layout = [
        [sg.Text("Description :", size=(15, 1)), sg.InputText(key="-DESC-", size=(30, 1))],

        [sg.Text("Date :", size=(15, 1)),
         sg.Input(key="-DATE-", size=(12, 1)),
         sg.CalendarButton("Calendar", target="-DATE-", format="%Y-%m-%d")],

        [sg.Text("Compte :", size=(15, 1)), common_compte_combo()],

        [sg.Text("Catégorie :", size=(15, 1)), common_category_combo()],

        [sg.Text("Mois :", size=(15, 1)),
         sg.Input(key="-MOIS-", size=(12, 1)),
         sg.CalendarButton("Calendar", target="-MOIS-", format="%Y-%m-%d")],

        [sg.Text("Montant Dépense (€) :", size=(15, 1)), sg.InputText(key="-DEPENSE-", size=(10, 1))],

        [sg.Text("Montant Recette (€) :", size=(15, 1)), sg.InputText(key="-RECETTE-", size=(10, 1))],

        [sg.HorizontalSeparator()],  # Ligne de séparation

        [common_valider_button(), common_cancel_button()]
    ]

    window = sg.Window("Saisie d'une transaction", layout, modal=True, element_justification="left",
                       font=("Calibri", 12))

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
                sg.popup_error("❌ Veuillez entrer des montants valides !", font=("Calibri", 12), text_color="red")


def form_reimbursement_plan(account: str):
    """ displays a GUI which enables creation and backup of a savings plan"""
    layout = [
        [sg.Column(
            [[sg.Text("Interest Rate"), sg.InputText(default_text="0.0", size=(3, 1), key='-TAUX-')],
             [sg.Text('Montant emprunté'), sg.InputText(default_text="0.0", size=(9, 1), key='-EMPRUNT-')],
             [sg.Text('Durée (mois)'), sg.InputText(default_text="0", size=(3, 1), key='-DUREE-')],
             [sg.Text('Mois de départ'), sg.Input(key="-MOIS-", size=(12, 1)),
              sg.CalendarButton("Calendar", target="-MOIS-", format="%Y-%m-%d")],
             [sg.Button('Calculate')]]
        ), sg.VerticalSeparator(),
            sg.Column(
                [[sg.Table(values=[], headings=('Capital Restant Dû', 'Capital', 'Intérêts'), key='-PLAN-')],
                 [sg.Button('Save')]])
        ]
    ]

    window = sg.Window(f"Manage Reimbursement scheme for {account}", layout=layout, modal=True)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        elif event == "Calculate":
            rate = float(values['-TAUX-']) / 100
            due = float(values['-EMPRUNT-'])
            nb_mois = int(values['-DUREE-'])
            start_date = convert_to_month(values['-MOIS-'])
            # generate the scheme
            df = generate_payment_schedule(start_date, nb_mois, due, rate)
            # display
            window['-PLAN-'].update(values=df.values.tolist())
        elif event == 'Save':
            # get the reimbursement scheme
            if not df is None:
                scheme = df['Capital']
                save_capital_reimbursements(engine, scheme, account, 'Emprunt Immobilier', start_date)
                sg.PopupOK('Saved')
    window.close()


def form_manage_salaries() -> bool:
    """ interface for managing the salaries

    :returns: boolean to indicate if an update did happen"""
    ##########
    # STANDARD
    ##########
    update_values: bool = False
    status_message: str = ''

    # Variables d'état
    with makesession() as s:
        df = get_salaries(s)

    # Layout
    layout = [
        [sg.Table(values=df.values.tolist(), headings=list(df.columns), key='-SALARIES-', justification="center",
                  auto_size_columns=True,
                  num_rows=12, enable_events=True, enable_click_events=True)],
        [sg.HorizontalSeparator()],
        [sg.Button("Simulate", size=(15, 1)),
         sg.Button("Import Selected", size=(15, 1), button_color=("white", "green"))],
        [sg.HorizontalSeparator()],
        [common_status_bar()]
    ]

    window = sg.Window("Salaires", layout=layout, modal=True)

    # display
    to_update = False
    salary: Mouvement

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            break
        elif isinstance(event, tuple) and event[0] == '-SALARIES-' and event[1] == '+CLICKED+':
            row, col = event[2]
            if row >= 0:
                selected_month = df.iloc[row, 0]
                amount = df.iloc[row, 7]
                # searches for a transaction
                salary = find_salary_transaction(engine, selected_month, amount)
                # Alternatives
                if salary is None:
                    status_message = "No salary transaction found, import impossible"
                elif salary.recette_initiale is not None:
                    status_message = f"Salary found and already imported, index : {salary.index} on date : {salary.date}, label : {salary.description}"
                else:
                    status_message = f"Salary found, ready to import, index : {salary.index} on date : {salary.date}, label : {salary.description}"
        elif event == "Import Selected":
            if not salary is None:
                if salary.recette_initiale is not None:
                    status_message = "Import already done"
                else:
                    create_salaries(engine, salary.index, selected_month, False)
                    status_message = 'Import done'
                    to_update = True
            else:
                status_message = "No salary selected"
        elif event == "Simulate":
            if not salary is None:
                if salary.recette_initiale is not None:
                    status_message = "Import already done"
                else:
                    create_salaries(engine, salary.index, selected_month, True)
                    status_message = 'Simulation done'
        # updates
        window["-STATUS-BAR-"].update(status_message)

    # end of the function
    window.close()
    return to_update


def form_manage_yearly_provisions():
    """ interface for creating yearly provisions"""
    ##########
    # STANDARD
    ##########
    update_values: bool = False
    update_groups: bool = False
    status_message: str = ''
    toggle_state = True

    # Variables d'état
    annee = datetime.date.today().year + 1
    is_economie: bool = False
    categorie = ''
    group = None
    monthly_keys = [f'-MOIS-{str(i)}' for i in range(1, 13)]
    with makesession() as s:
        classifiers = get_groups(s)
        realise = get_yearly_realise(s, False, toggle_state, is_economie, categorie, annee - 1)
        provisionne = get_yearly_realise(s, True, toggle_state, is_economie, categorie, annee)

    # Layout
    realise_pane = [
        [sg.Text("Réalisé année précédente")],
        [sg.Table(values=realise.values.tolist(), headings=list(realise.columns), key='-REALISE-', num_rows=12)],
        [sg.Text(f"Total : {realise['Dépense'].sum() if toggle_state else realise['Recette'].sum():.2f} €",
                 key='-TOTALREALISE-')],
        [sg.Text(f"Moyenne : {realise['Dépense'].mean() if toggle_state else realise['Recette'].mean():.2f} €",
                 key='-MOYENNEREALISE-')],
    ]

    provisionne_pane = [
        [sg.Text("Déjà Provisionné")],
        [sg.Table(values=provisionne.values.tolist(), headings=list(provisionne.columns), key='-PROVISIONNE-',
                  num_rows=12)],
        [sg.Text(
            f"Total : {provisionne['Dépense Provisionnée'].sum() if toggle_state else provisionne['Recette Provisionnée'].sum():.2f} €",
            key='-TOTALPROVISIONNE-')],
        [sg.Text(
            f"Moyenne : {provisionne['Dépense Provisionnée'].mean() if toggle_state else provisionne['Recette Provisionnée'].mean():.2f} €",
            key='-MOYENNEPROVISIONNE-')],

    ]

    editing_pane = [
        [sg.Text('Créer une nouvelle provision'),
         sg.HorizontalSeparator(),
         sg.Text("Description : ", size=(15, 1)),
         sg.InputText(key='-DESCRIPTION-', default_text='', size=(50, 1), enable_events=True),
         sg.Text('', key='-MATCH-')],
        [sg.Table(values=classifiers.values.tolist(), headings=list(classifiers.columns), key='-CLASSIFIERS-',
                  justification="center", num_rows=5, enable_events=True, enable_click_events=True)],
        [sg.Text("Valeur Globale :"), sg.InputText(key='-GLOBAL-', size=(9, 1))],
        [sg.Button('Fill'), sg.Button('Spread')]
    ]
    editing_pane += [[sg.Text(f"Mois {str(i + 1)} "), sg.InputText(key=monthly_keys[i], size=(9, 1))] for i in
                     range(12)]

    layout = [
        [common_category_combo()],
        [sg.Text("Année :", size=(15, 1)), sg.InputText(str(annee), key='-YEAR-', size=(4, 1))],
        [sg.Text("Type : "), sg.Button('Dépense', key='-TOGGLE-', button_color=get_toggle_style(toggle_state)),
         sg.Checkbox(key='-ECONOMIE-', text='Economie ?', enable_events=True)],
        [sg.Text("Sous-groupe : "), sg.Combo([], key='-GROUP-', size=(30, 1), enable_events=True),
         sg.Button("Reset Group")],
        [sg.HorizontalSeparator()],
        [sg.Column(realise_pane), sg.Column(provisionne_pane), sg.Column(editing_pane)],
    ]

    layout += [[common_valider_button(), common_cancel_button()],
               [common_status_bar()]]

    # Display
    window = sg.Window(f"Créer des provisions annuelles pour {categorie}", layout=layout, modal=True)

    while True:
        event, values = window.read()
        # Pick the selected value
        try:
            description = values['-DESCRIPTION-']
        except TypeError:
            description = ''
        try:
            valeur_globale = float(values['-GLOBAL-']) if values['-GLOBAL-'] else 0.0
        except TypeError:
            valeur_globale = 0.0
        try:
            annee = int(values['-YEAR-']) if values['-YEAR-'] else 0
        except TypeError:
            annee = datetime.date.today().year
        try:
            is_economie = values['-ECONOMIE-']
        except TypeError:
            is_economie = False

        if event in (sg.WIN_CLOSED, 'Quitter'):
            break
        elif event == '-CATEGORIE-':
            categorie = values['-CATEGORIE-']
            status_message = f"Catégorie {categorie} sélectionnée"
            update_values = True
            update_groups = True
        elif event == '-TOGGLE-':
            toggle_state = not toggle_state
            status_message = 'Switch between Dépense et Provision'
            update_values = True
        elif event == '-ECONOMIE-':
            status_message = 'Switch between Economie and Courant'
            update_values = True
        elif event == '-GROUP-':
            group = values['-GROUP-']
            status_message = f"Groupe {group} sélectionné"
            update_values = True
        elif event == 'Reset Group':
            group = None
            status_message = "Group reset"
            update_values = True
        elif event == '-DESCRIPTION-':
            if len(description) > 3:
                filtered = classifiers[classifiers['patterns'].apply(lambda x: isinstance(x, str) and x in description)]
                window['-MATCH-'].update(f'{len(filtered)} matches found',
                                         text_color='green' if len(filtered) > 0 else 'red')
        elif event == 'Fill':
            for i in range(12):
                window[monthly_keys[i]].update(valeur_globale)
            status_message = f"Filled with value"
        elif event == 'Spread':
            splitted = split_number(valeur_globale, 12, 2)
            for i in range(12):
                window[monthly_keys[i]].update(splitted[i])
                status_message = "Splitted"
        elif event == '-VALIDER-':
            # Generate the 12 provisions
            if description == '':
                error_message = 'Description is too short. Please extend'
            elif any([values[monthly_keys[i]] == '' for i in range(12)]):
                error_message = 'There are missing monthly values'
            else:
                error_message = ''

            if error_message == '':
                provisions = [Mouvement(date=datetime.date(annee, i + 1, 1),
                                        description=description,
                                        provision_payer=values[monthly_keys[i]] if toggle_state else None,
                                        provision_recuperer=values[monthly_keys[i]] if not toggle_state else None,
                                        categorie=categorie,
                                        mois=datetime.date(annee, i + 1, 1),
                                        label_utilisateur=description,
                                        economie='true' if is_economie else 'false',
                                        ) for i in range(12)]
                # Save
                with makesession() as s:
                    for p in provisions:
                        import_transaction(s, p)
                        s.flush()
                        s.commit()

                status_message = "Save successfull"
            else:
                sg.PopupError(error_message)

        if update_groups:
            with makesession() as s:
                groups = get_groups_of_category(s, categorie, annee - 1)
            window['-GROUP-'].update(values=groups['Classe'].values.tolist())
            group = None

            update_groups = False

        if update_values:
            window['-TOGGLE-'].update('Dépense' if toggle_state else 'Recette',
                                      button_color=get_toggle_style(toggle_state))

            # update réalisé et provisionné
            with makesession() as s:
                realise = get_yearly_realise(s, False, toggle_state, is_economie, categorie, annee - 1, group)
                provisionne = get_yearly_realise(s, True, toggle_state, is_economie, categorie, annee, group)

            window['-REALISE-'].update(realise.values.tolist())
            window['-TOTALREALISE-'].update(
                f"Total : {realise['Dépense'].sum() if toggle_state else realise['Recette'].sum():.2f} €")
            window['-MOYENNEREALISE-'].update(
                f"Moyenne : {realise['Dépense'].mean() if toggle_state else realise['Recette'].mean():.2f} €")

            window['-PROVISIONNE-'].update(provisionne.values.tolist())
            window['-TOTALPROVISIONNE-'].update(
                f"Total : {provisionne['Dépense Provisionnée'].sum() if toggle_state else provisionne['Recette Provisionnée'].sum():.2f} €")
            window['-MOYENNEPROVISIONNE-'].update(
                f"Moyenne : {provisionne['Dépense Provisionnée'].mean() if toggle_state else provisionne['Recette Provisionnée'].mean():.2f} €")

            window['-STATUS-BAR-'].update(status_message)
            update_values = False

    window.close()

    # TODO : pour une catégorie et une année donnée, récupérer toutes les transactions, classifier
    # puis extraire la liste distincte des groupes pour peupler un combobox
    # TODO : introduire un filtre économie versus courant
    # TODO : implémenter le comportement où, sur sélection d'un groupe, il déclenche un refresh pour filtrer la catégorie


def form_manage_monthly_provisions():
    """ interface for managing a monthly provision"""
    ##########
    # STANDARD
    ##########
    update_values: bool = False
    status_message: str = ''

    # Variables d'état
    current_month: datetime.date = datetime.date.today() - datetime.timedelta(days=datetime.date.today().day - 1)
    is_courant = True
    df = get_provisions_for_month(engine, current_month, is_courant=is_courant)

    # Layout
    layout = [
        [sg.Text("Mois :", size=(15, 1)),
         sg.Input(key="-DATE-", size=(12, 1), default_text=current_month.strftime('%Y-%m-%d'), enable_events=True),
         sg.Button("<<", key="-PREVIOUS-"), sg.Button(">>", key="-NEXT-"),
         sg.Button("Courant", key="-TOGGLE-", button_color=get_toggle_style(is_courant))
         ],

        [sg.Table(values=df.values.tolist(), headings=list(df.columns), key="-PROVISIONS-", enable_events=True,
                  justification="center", auto_size_columns=True,
                  num_rows=30, enable_click_events=True),
         sg.VerticalSeparator(),
         sg.Column([[sg.Text(f"Dépense : {round(df['Dépense'].sum(), 0)}", key='-DEPENSE-', font=("Calibri", 18))]
                       , [sg.Text(f"Recette : {round(df['Recette'].sum(), 0)}", key='-RECETTE-', font=("Calibri", 18))]
                       , [sg.Text(f"Solde : : {round(df['Recette'].sum() - df['Dépense'].sum(), 0)}", key='-SOLDE-',
                                  font=("Calibri", 18))]
                    ])],
        [sg.Button("Manage", size=(15, 1)),
         sg.Button("Close Expense", size=(15, 1)),
         sg.Button("New Provision", size=(15, 1))],

        [sg.HorizontalSeparator()],
        [common_valider_button(), common_cancel_button()],
        [sg.HorizontalSeparator()],
        [common_status_bar()]
    ]

    # Display
    window = sg.Window("Provisions", layout=layout, modal=True)

    category = None

    # Events
    while True:
        event, values = window.read()
        update_values = False

        if event in (sg.WIN_CLOSED, "-ANNULER-"):
            break
        elif event == '-DATE-':
            # change of dates. Refresh
            current_month = datetime.date.fromisoformat(values['-DATE-'])
            status_message = f"month changed to {current_month}"
            update_values = True
        elif event == "-PREVIOUS-":
            current_month = current_month - relativedelta(months=1)
            status_message = f"month changed to {current_month}"
            update_values = True
        elif event == "-NEXT-":
            current_month += relativedelta(months=1)
            status_message = f"month changed to {current_month}"
            update_values = True
        elif event == '-TOGGLE-':
            is_courant = not is_courant
            # Mise à jour du button
            window["-TOGGLE-"].update(text='Courant' if is_courant else 'Economie',
                                      button_color=get_toggle_style(is_courant))
            update_values = True
        elif isinstance(event, tuple) and event[0] == "-PROVISIONS-" and event[1] == "+CLICKED+":
            row, col = event[2]  # Récupère la ligne et la colonne cliquées
            if row is None:
                status_message = f"Pas d'index sélectionné"
                category = None
            elif row >= 0:
                category = df.iloc[row, 1]
                status_message = f"Catégorie sélectionnée : {df.iloc[row, 1]}"
        elif event == "Manage":  # Launch new editor
            form_update_provision(offset_size=20, categorie=category, mois=current_month, economy_mode=not is_courant)
            status_message = f"Provisions of type {category} edited"
            update_values = True
        elif event == "Close Expense":
            if not category is None:
                # Close the corresponding expense
                # Calculate the remaining
                remaining = float(df.loc[df["Catégorie"] == category]["Dépense Reste"].sum())
                if remaining > 0:
                    with Session(engine) as session:
                        close_provision(session, current_month, category=category, remaining=remaining)
                    status_message = f"Category closed, remaining : {remaining} was solded"
                    update_values = True
                else:
                    status_message = f"No remaining expenses for {category}"
            else:
                status_message = f"No category selected"
        elif event == "New Provision":
            # ask for a new transaction
            new_provision = create_new_provision(current_month)
            if not new_provision is None:
                # save to the database
                with makesession() as s:
                    import_transaction(s, new_provision)
                    s.commit()
                # update the values
                update_values = True

        # Conditional update
        window['-STATUS-BAR-'].update(status_message)
        if update_values:
            df = get_provisions_for_month(engine, current_month, is_courant)
            window["-DATE-"].update(current_month.strftime("%Y-%m-%d"))
            window['-PROVISIONS-'].update(df.values.tolist())
            window['-DEPENSE-'].update(f"Dépense : {round(df['Dépense'].sum(), 0)}")
            window['-RECETTE-'].update(f"Recette : {round(df['Recette'].sum(), 0)}")
            window['-SOLDE-'].update(f"Solde : {round(df['Recette'].sum() - df['Dépense'].sum(), 0)}")

    # End of the function
    window.close()


def form_manage_remaining_provisions():
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
        elif event == "Close Expense":
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


def form_get_custom_split(no_periods: int, initial_amount: float, initial_month: datetime.date):
    """ asks the user for a custom split

    :returns: an array with a series of split values"""
    # define st andard parameter
    rounding: int = 2

    # create a series of boxes
    key_values = [f"-INPUT-{i}" for i in range(no_periods)]
    key_months = [f"-MOIS-{i}-" for i in range(no_periods)]

    result_values = split_value(initial_amount, no_periods, rounding)
    result_months = [initial_month] * no_periods

    inputs = [[sg.Text(f"Amount to split : {initial_amount}")]]

    inputs += [
        [sg.Text(f"Values {i + 1} : "), sg.Input(key=key_values[i], size=(15, 1), default_text=str(result_values[i])),
         sg.Text("Month : "),
         sg.Input(key=key_months[i], size=(10, 1), default_text=result_months[i].strftime('%Y-%m-%d'))] for
        i in
        range(no_periods)]

    inputs += [
        [sg.Text("Amount correctly splitted", text_color="green", key='-CHECK-')],
        [sg.HorizontalSeparator()],
        [common_valider_button(), common_cancel_button()]
    ]
    # create window
    window = sg.Window(layout=inputs, modal=True, title='Split the periods')

    # display
    total: float = initial_amount
    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "Quitter"):
            break
        elif event == '-VALIDER-':
            # get new value
            try:
                result_values = [float(values[key]) for key in key_values]
                result_months = [convert_to_month(values[key]) for key in key_months]

                total = round(sum(result_values), rounding)
                # check if the total matches with the input
                diff = round(initial_amount - total, rounding)
                if diff == 0:
                    window["-CHECK-"].update("Amount correctly splitted", text_color="green")
                    # we can stop the window
                    break
                else:
                    # we suggest the correct remaining amount
                    subtotal = result_values[:len(result_values) - 1]
                    suggested = round(initial_amount - sum(subtotal), rounding)

                    window["-CHECK-"].update(
                        f"Incorrect split, initial amount - your input = {diff}, suggested as a last amount : {suggested}",
                        text_color="red")
            except ValueError:
                sg.PopupError("Please enter valid numbers !")
    window.close()

    return result_values, result_months


def form_check_keywords(df: pd.DataFrame, offset_size: int):
    """ GUI for checking whether the keywords are properly matching
    The GUI contains following components :
    - a calculation of the rate of transactions matching with a pattern
    - a table with the unmatched transactions
    """

    layout = [
        [sg.Text("", key='-COUNTER-')],
        [sg.Text("", key='-PERCENT-')],
        [sg.Table(values=df.values.tolist(), headings=list(df.columns), key="-MVTS-",
                  enable_events=True,
                  justification="center", auto_size_columns=True,
                  num_rows=20, enable_click_events=True)],
        [sg.Button("Add Keyword", key='-MATCH-', size=(15, 1))],
        [sg.HorizontalSeparator()],
        [sg.Text("", key='-STATUS-BAR-')]
    ]

    # display
    window = sg.Window("Checking efficiency of pattern recognition", layout, modal=True, finalize=True)

    # Loop
    update_values = True
    status_message = 'Initialized'
    while True:
        # calculate values
        if update_values:
            # retrieve the keywords
            keywords = fetch_keywords()
            kw_list = [kw.keyword for kw in keywords]
            df['Matched ?'] = df.apply(lambda x: any([True if kw in x.Description else False for kw in kw_list]),
                                       axis=1)
            unmatched = df.loc[~df['Matched ?']]
            percentage = 1 - len(unmatched) / len(df)
            # update layout
            window['-COUNTER-'].update(f"{len(keywords)} keywords retrieved")
            window['-PERCENT-'].update(f"{percentage * 100:.2f} % of the transactions were matched")
            window['-MVTS-'].update(values=unmatched.values.tolist())
            # ensure no further updates are done
            update_values = False

        # start of the loop
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            window.close()
            break
        elif event == '-MATCH-':
            # request a new keyword
            row = values['-MVTS-'][0]
            if row >= 0:
                description = unmatched.iloc[row, 1]
                category = unmatched.iloc[row, 3]
                mc = form_keyword_import(description, category)
                if not mc is None:
                    try:
                        import_keyword(engine, mc)
                        status_message = f"Keyword imported for category"
                        update_values = True
                    except IntegrityError:
                        status_message = f"keyword already exists"
        elif isinstance(event, tuple) and event[0] == '-MVTS-' and event[1] == '+CLICKED+':
            row, col = event[2]
            if row:
                if row >= 0:
                    description = unmatched.iloc[row, 1]
                    status_message = f"selected transaction {description} at position {row}"

        window['-STATUS-BAR-'].update(status_message)


def form_salary_monitor():
    """ Displays a monitor with salaries"""
    # Perform the initial download
    df = fetch_salary_candidates()

    # First Tab
    tab1 = sg.Tab("Règles", [
        [sg.Table(values=(), headings=("Keyword", "Compte", "Déclarant")),
         sg.Column([[sg.Button("New")], [sg.Button("Deactivate")]])],
        [sg.Button("Scan last import"), sg.Button("Re-scan all")]
    ])

    tab2 = sg.Tab("Transactions", [
        [sg.Text("Salaires détectés mais non documentés")],
        [sg.Table(values=df.values.tolist(), headings=list(df.columns), key='-DETECTED-')],
        [sg.Text("Salaires détectés et importables")],
        [sg.Table(values=(), headings=("index", "Description", "Date", "Mois"))],
        [sg.Button("Import", button_color=("white", "green"))],
        [sg.Text("Salaires importés")],
        [sg.Table(values=(), headings=("index", "Description", "Date", "Mois"))]
    ])

    """
    tab3 = sg.Tab("Salaires renseignés", [
        [sg.Text("Salaires")],
        [sg.Table(values=(), headings=("Mois", "Déclarant", "Salaire Net", "Total"))]
    ])
    """

    layout = [
        [sg.TabGroup([[tab1, tab2]])],
        [common_valider_button(), common_cancel_button()]
    ]

    window = sg.Window("Manage the salaries", layout=layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            window.close()
            break


def form_solde_bancaire(compte: str):
    """ Affiche le solde des comptes"""
    # Définition des paramètres (fenêtre temporelle)
    period_end = datetime.date.today()
    period_begin = period_end - datetime.timedelta(days=30)

    # Appel du solde
    with makesession() as s:
        solde = get_solde(s, compte, period_begin, period_end)

    # Création du graphique
    gs = GraphSolde(compte)
    gs.plot_solde(solde, linestyle='-', marker='o', linewidth=2.0)

    # Création du layout
    layout = [
        [sg.Text(f"Formulaire pour afficher le solde bancaire du compte {compte}")],
        [sg.Text("Début :", size=(15, 1)),
         sg.Input(key="-DEBUT-", size=(12, 1), default_text=period_begin.strftime("%Y-%m-%d"), enable_events=True),
         sg.CalendarButton("Début", target="-DEBUT-", format="%Y-%m-%d")],
        [sg.Text("Fin :", size=(15, 1)),
         sg.Input(key="-FIN-", size=(12, 1), default_text=period_end.strftime("%Y-%m-%d"), enable_events=True),
         sg.CalendarButton("Fin", target="-FIN-", format="%Y-%m-%d")],
        [sg.Canvas(key='-CANVAS-'),
         sg.Table(values=solde.values.tolist(), headings=list(solde.columns), key='-SOLDES-', num_rows=30)],
        [sg.HorizontalSeparator()],
        [common_valider_button()]
    ]

    window = sg.Window(f"Solde du compte {compte}", layout, finalize=True)

    # Dessiner le graphique sur le canevas
    canvas = FigureCanvasTkAgg(gs.fig, master=window["-CANVAS-"].TKCanvas)
    canvas.draw()
    canvas.get_tk_widget().pack(side="top", fill="both", expand=1)

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "Quitter"):
            break
        elif event in ('-DEBUT-', '-FIN-'):
            period_begin = datetime.date.fromisoformat(values['-DEBUT-'])
            period_end = datetime.date.fromisoformat(values['-FIN-'])
            with makesession() as s:
                solde = get_solde(s, compte, period_begin, period_end)
            window['-SOLDES-'].update(values=solde.values.tolist())
            # Update the graph
            gs.plot_solde(solde, linestyle='-', marker='o', linewidth=2.0)
            canvas.draw()


class StringParser:
    def display(self, value):
        return '' if value is None else value

    def parse(self, value, label: str, min_length: int = 0) -> str:
        if value == '':
            return None
        else:
            try:
                result = str(value)
            except TypeError:
                raise TypeError(f"Could not convert the input '{value}' for label {label} to a string")
            if len(result) < min_length:
                raise TypeError(f"The length for label {label} is insufficient, {min_length} characters expected")
            return result


def form_faits_marquants():
    """ Formulaire dédié à l'affichage des faits marquants"""
    ##################
    # Variables d'état
    ##################
    current_month = datetime.date.today().replace(day=1)
    with makesession() as s:
        df = fetch_mouvements(s, ['Date', 'Fait marquant'], offset_size=100, month_filter=current_month,
                              faits_marquants=True)

    ########
    # Layout
    ########
    layout = [
        [sg.Text(f"Mois : {current_month.strftime('%Y-%m-%d')}", size=(20, 1), key='-MOIS-',
                 font=(default_police, 18, 'bold'), colors='blue'),
         sg.Button("<<", key="-PREVIOUS-"), sg.Button(">>", key="-NEXT-")
         ],
        [sg.Table(values=df.values.tolist(), headings=list(df.columns), auto_size_columns=False,
                  col_widths=[10, 100],
                  key="-FM-", enable_events=True,
                  justification="left",
                  num_rows=10, enable_click_events=True, row_height=50)]
    ]

    ###########
    # Behaviour
    ###########
    window = sg.Window('Faits Marquants', layout, finalize=True)

    while True:
        event, values = window.read()
        update_values = False
        # Fermeture de la fenêtre
        if event == sg.WIN_CLOSED:
            break
        elif event == "-PREVIOUS-":
            current_month = current_month - relativedelta(months=1)
            status_message = f"month changed to {current_month}"
            update_values = True
        elif event == "-NEXT-":
            current_month += relativedelta(months=1)
            status_message = f"month changed to {current_month}"
            update_values = True

        if update_values:
            with makesession() as s:
                df = fetch_mouvements(s, ['Date', 'Fait marquant'], offset_size=100, month_filter=current_month,
                                      faits_marquants=True)
            window['-FM-'].update(values=df.values.tolist())
            window['-MOIS-'].update(value=f"Mois : {current_month.strftime('%Y-%m-%d')}")


def form_manage_keywords():
    """ A global keyword manager"""
    candidate: MapCategorie | None
    selected_map: MapCategorie | None
    show_actif = True
    maps_df = get_keywords(engine, show_actif).fillna('')
    st_new = 'new'
    st_selected = 'saved'
    st_idle = 'idle'
    form_state = st_idle
    parser = StringParser()
    mvt_columns = ['Description', 'Date', 'Mois', 'Catégorie', 'Solde']
    mvt_test_df: pd.DataFrame

    # create a layout
    layout = [
        [sg.Button("Actif", key='-FLAG-ACTIF-', button_color='green'), sg.Button("+", key="-ADD-")],
        [sg.Table(values=maps_df.values.tolist(), headings=list(maps_df.columns), key='-MAPS-', num_rows=20,
                  enable_events=True, enable_click_events=True),
         sg.Column(layout=[
             [sg.Text("Keyword : "), sg.InputText(key='-KEYWORD-', readonly=True, disabled=True)],
             [sg.Text("Catégorie : "), common_category_combo()],
             [sg.Text("Organisme : "), sg.InputText(key='-ORGANISME-')],
             [sg.Text("Month Shift : "), sg.InputText(key='-SHIFT-')],
             [sg.Text("Employeur : "), sg.InputText(key='-EMPLOYEUR-')],
             [sg.Text("Déclarant : "), sg.InputText(key='-DECLARANT-')],
             [sg.Checkbox(text="Désactivé : ", key='-INACTIF-')],
             [sg.Text("Idle", key='-STATUS-')],
             [common_valider_button()],
             [sg.HorizontalSeparator()],
             [sg.Button("Test", key='-TEST-'), sg.Text("for"), sg.InputText(default_text="10", key='-LIMIT-'),
              sg.Text("rows")],
             [sg.Button("Count Gaps"), sg.Button("Fix Gaps")]
         ])],
        [sg.HorizontalLine()],
        [sg.Table(values=[], headings=mvt_columns, key='-SAMPLES-', expand_x=True)]
    ]

    # display
    window = sg.Window("Maps", layout, modal=True, element_justification='center')

    while True:
        event, values = window.read()
        update_values = False
        status_message = ''
        # Fermeture de la fenêtre
        if event == sg.WIN_CLOSED:
            break
        # Sélection d'une nouvelle map
        elif isinstance(event, tuple) and event[0] == "-MAPS-" and event[1] == "+CLICKED+":
            row, col = event[2]
            # Récupération de la clé
            if not row is None:
                key = maps_df['Keyword'].iat[row]
                # Récupération de la map
                with Session(engine) as session:
                    selected_map = session.get(MapCategorie, key)

                window['-KEYWORD-'].update(value=selected_map.keyword, readonly=True, disabled=True)
                window['-CATEGORIE-'].update(value=selected_map.categorie)
                window['-ORGANISME-'].update(value=parser.display(selected_map.organisme))
                window['-SHIFT-'].update(value=selected_map.monthshift if selected_map.monthshift else 0)
                window['-EMPLOYEUR-'].update(value=parser.display(selected_map.employeur))
                window['-DECLARANT-'].update(value=parser.display(selected_map.declarant))
                window['-INACTIF-'].update(value=parser.display(selected_map.inactif))
                window['-STATUS-'].update(value=f"currently editing the map '{key}'")

                # update le status
                status_message = f"Map selected : '{selected_map.keyword}'"
                form_state = st_selected
        elif event == '-FLAG-ACTIF-':
            show_actif = not show_actif
            # update le statut
            form_state = st_idle
            # update l'affichage
            status_message = f"Switched to other active states"

            update_values = True
        elif event == "-ADD-":
            # Ajout d'une nouvelle map
            window['-KEYWORD-'].update(value='', readonly=False, disabled=False)
            window['-CATEGORIE-'].update(value='')
            window['-ORGANISME-'].update(value='')
            window['-SHIFT-'].update(value='')
            window['-EMPLOYEUR-'].update(value='')
            window['-DECLARANT-'].update(value='')
            window['-STATUS-'].update(value=f"Creating new map")

            # update le status
            status_message = f"Adding new map..."
            form_state = st_new

        elif event == '-VALIDER-':
            if form_state in (st_new, st_selected):
                try:
                    if form_state == st_new:
                        selected_map = MapCategorie()
                        selected_map.keyword = parser.parse(values['-KEYWORD-'], 'Keyword', 10)

                    # fill the selected_map
                    key = parser.parse(values['-CATEGORIE-'], 'Catégorie')
                    selected_map.categorie = key
                    selected_map.organisme = parser.parse(values['-ORGANISME-'], 'Organisme', 3)
                    selected_map.declarant = parser.parse(values['-DECLARANT-'], 'Déclarant', 6)
                    selected_map.employeur = parser.parse(values['-EMPLOYEUR-'], 'Employeur', 5)
                    selected_map.monthshift = int(values['-SHIFT-']) if values['-SHIFT-'] else 0
                    selected_map.inactif = values['-INACTIF-']
                    # insertion successful
                    status_message = f"Map saved : '{selected_map.keyword}'"

                    # Attempting to save
                    save_map_categorie(engine, selected_map, form_state == st_new)

                    form_state = st_selected
                    update_values = True
                    # reselect the session
                    with Session(engine) as session:
                        selected_map = session.get(MapCategorie, key)

                except Exception as e:
                    sg.PopupError(e)
        elif event == '-TEST-':
            test_key = values['-KEYWORD-']
            if test_key:
                offset_size = int(values['-LIMIT-']) if values['-LIMIT-'] else 1
                with makesession() as s:
                    mvt_test_df = fetch_mouvements(s, mvt_columns, offset_size=offset_size, offset=0,
                                                   search_filter=test_key,
                                                   transactions=True, sort_column='Date', sort_order='desc')
                window['-SAMPLES-'].update(values=mvt_test_df[mvt_columns].values.tolist())
        elif event == 'Count Gaps':
            if form_state == st_selected:
                with makesession() as s:
                    mvt_test_df = identify_gaps(s, selected_map)

                window['-SAMPLES-'].update(values=mvt_test_df[mvt_columns].values.tolist())

        elif event == 'Fix Gaps':
            pass

        if update_values:
            window['-STATUS-'].update(value=status_message)
            maps_df = get_keywords(engine, show_actif)
            window['-MAPS-'].update(values=maps_df.fillna('').values.tolist())
            window['-FLAG-ACTIF-'].update(text='Actif' if show_actif else 'Inactif',
                                          button_color='green' if show_actif else 'orange')
    window.close()


def form_main():
    ##########
    # STANDARD
    ##########
    status_message: str = 'Welcome to the Comptes interface'

    # Colonnes à voir dans le formulaire
    view_columns = ["index", "Label utilisateur",
                    "Catégorie", "Date", "Mois", "Solde", "Numéro de référence"]

    # Définition des variables d'état
    offset_size = 30  # Default value
    offset = 0

    tag_filter = None
    job_filter = 0
    category_filter = None
    compte_filter = None
    desc_filter = None
    reimbursable_filter = False
    affectable_filter = False
    economy_mode = False
    sort_column = 'index'
    index: int = -1
    description = ''
    category = ''
    selected_type = 'Courant'
    toggle_past = False

    with makesession() as s:
        # mouvements
        df = fetch_mouvements(s, view=view_columns, offset_size=offset_size, sort_column="index", sort_order="desc")
        # Soldes bancaires
        soldes = fetch_soldes(s, selected_type)

        # Jobs
        jobs = get_jobs(s, 20)
        jobmapper = JobMapper()
        jobmapper.set_jobs(jobs)

        # type de comptes
        ctypes = get_type_comptes(s)
        # Numéros de référence
        nos_ref = get_numeros_reference(s, 20)

    # balasnces
    balances = fetch_balances()

    # Définition de la structure de la fenêtre
    layout = [
        [sg.Button("Provisions", size=(15, 1), button_color=("white", "blue")),
         sg.Button("Monthly Provisions", size=(15, 1), button_color=("white", "blue")),
         sg.Button("Yearly Provisions", size=(15, 1), button_color=("white", "blue")),
         sg.Button("Salaries", size=(15, 1), button_color=("white", "blue")),
         sg.Button("Pattern Check", size=(15, 1), button_color=("white", "blue")),
         sg.Button("Salary Monitor", size=(15, 1), button_color=("white", "blue")),
         sg.Button("Maps", size=(15, 1), button_color=("white", "blue")),
         sg.Button("Facts", size=(15, 1), button_color=("white", "blue"))],
        [sg.Text("Filter By :"),
         sg.Text("Catégorie : "), common_category_combo(),
         sg.Text("Compte : "), common_compte_combo(),
         sg.Button("Reimbursable Expenses", size=(20, 1), key="-REIMBURSABLE-"),
         sg.Button("Affectable Payments", size=(20, 1), key='-AFFECTABLE-'),
         sg.Button("All Expenses", size=(15, 1), key='-ECONOMY-', button_color=get_toggle_style(economy_mode)),
         sg.InputText(key='-FILTER-', size=(20, 1)),
         sg.Button("%", key='-APPLY-FILTER-'),
         sg.Button("✖ Clear", key="-CLEAR-")
         ],
        [sg.Text("Job : "), common_job_combo(jobmapper.get_job_descriptions()), sg.Text("Réf. : "),
         common_tag_combo(nos_ref, True),
         sg.Button('Passé' if toggle_past else 'Futur', key='-TIME-', button_color=get_toggle_style(toggle_past))],
        [sg.Button('⇅ Date', key='-SORT-DATE-', size=(6, 1)), sg.Button('⇅ index', key='-SORT-INDEX-', size=(7, 1))],
        [sg.Table(values=df.values.tolist(), headings=list(df.columns), key="-MVTS-", enable_events=True,
                  justification="center", auto_size_columns=True,
                  num_rows=offset_size, enable_click_events=True,
                  right_click_menu=["", ["Filtrer par cette catégorie..."]]),
         sg.Column([
             [sg.Combo(values=ctypes, default_value=selected_type, key='-CTYPES-', enable_events=True)],
             [sg.Table(values=soldes.values.tolist(), headings=list(soldes.columns), key="-SOLDES-",
                       justification='center', auto_size_columns=True, enable_events=True, enable_click_events=True)],
             [sg.Text('Equilibre des virements')],
             [sg.Table(values=balances.values.tolist(), headings=list(balances.columns), key='-BALANCES-',
                       justification='center', auto_size_columns=True)]
         ], vertical_alignment='top'),
         sg.Column([
             [sg.Button("New Transaction", size=(15, 1))],
             [sg.Button("Invert", size=(15, 1))],
             [sg.Button("Deactivate", size=(15, 1))],
             [sg.Button("Edit", size=(15, 1))],
             [sg.Button("Mass edit", size=(15, 1))],
             [sg.Button("Check Keywords", size=(15, 1))],
             [sg.Button("Add Keyword", size=(15, 1))],
             [sg.Button("Link", size=(15, 1))],
             [sg.InputText(default_text="2", key='-SPLIT-COUNT-', size=(10, 1))],
             [sg.Button("Split Custom", size=(15, 1))],
             [sg.Button("Split Yearly", size=(15, 1))],
             [sg.Button("Reimbursement Scheme", size=(15, 1))],
             [sg.Button("Prettify Labels", size=(15, 1))]
         ], vertical_alignment='top')
         ],
        [sg.Button("Previous", size=(15, 1)), sg.Button("Next", size=(15, 1)),
         sg.Combo(values=[20, 50, 100], default_value=20, readonly=True, enable_events=True, key='-OFFSET-',
                  tooltip="Choose pagination size"), sg.Text('', size=(50, 1), key='-METRICS-')],
        [sg.Button("Quitter", size=(15, 1), button_color=("white", "red"))],
        [common_status_bar()]  # Affiche la colonne sélectionnée
    ]

    # Création de la fenêtre
    window = sg.Window("Finance Interface", layout)

    # Boucle d'événements
    while True:
        event, values = window.read()
        update_values = False
        update_tags = False

        if event in (sg.WIN_CLOSED, "Quitter"):
            break
        elif event == "Provisions":
            form_manage_remaining_provisions()
            update_values = True
        elif event == "Monthly Provisions":
            form_manage_monthly_provisions()
            update_values = True
        elif event == "Yearly Provisions":
            form_manage_yearly_provisions()
            update_values = True
        elif event == "Salaries":
            update_values = form_manage_salaries()
        elif event == "Pattern Check":
            form_check_keywords(df, offset_size)
        elif event == "Salary Monitor":
            form_salary_monitor()
        elif event == "Maps":
            form_manage_keywords()
        elif event == "Facts":
            form_faits_marquants()
        elif event == "-CLEAR-":
            job_filter = 0
            tag_filter = None
            category_filter = None
            compte_filter = None
            desc_filter = None
            reimbursable_filter = False
            affectable_filter = False
            window['-CATEGORIE-'].update(value='')
            window['-COMPTE-'].update(value='')
            window['-FILTER-'].update(value='')
            window['-JOBS-'].update(value='')
            window['-NOS-'].update(value='')
            update_values = True
        elif event == "-CATEGORIE-":
            category_filter = values["-CATEGORIE-"]
            update_values = True
        elif event == "Filtrer par cette catégorie...":
            selected_row = values["-MVTS-"]
            if selected_row:
                category_filter = df.iloc[selected_row[0], 2]
                update_values = True
        elif event == "-COMPTE-":
            compte_filter = values["-COMPTE-"]
            update_values = True
        elif event == '-REIMBURSABLE-':
            reimbursable_filter = True
            affectable_filter = False
            update_values = True
        elif event == '-AFFECTABLE-':
            affectable_filter = True
            reimbursable_filter = False
            update_values = True
        elif event == '-ECONOMY-':
            economy_mode = not economy_mode
            update_values = True
        elif event == '-TIME-':
            toggle_past = not toggle_past
            update_values = True
        elif event == '-APPLY-FILTER-':
            desc_filter = values["-FILTER-"]
            update_values = True
        elif event == '-JOBS-':
            job_filter = jobmapper.get_job_id(values['-JOBS-'])
            update_values = True
        elif event == '-NOS-':
            tag_filter = values['-NOS-']
            update_values = True
        elif event == '-SORT-DATE-':
            sort_column = 'Date'
            update_values = True
        elif event == '-SORT-INDEX-':
            sort_column = 'index'
            update_values = True
        elif event == "Previous":
            # Revenir aux lignes précédentes
            if offset > 0:
                offset -= offset_size
                offset = max(offset, 0)
                update_values = True
        elif event == "Next":
            offset += offset_size
            update_values = True
        elif event == "-OFFSET-":
            offset_size = int(values["-OFFSET-"])
            status_message = f"Offset size changed to {offset}"
            update_values = True
        elif event == '-CTYPES-':
            selected_type = values['-CTYPES-']
            update_values = True
        elif event == "New Transaction":
            data = create_new_mouvement()

            if not data is None:
                with makesession() as s:
                    import_transaction(s, data)
                    s.commit()
                status_message = f"Transaction créée"
                update_values = True
        elif event == "Invert":
            if index > 0:
                with makesession() as session:
                    existing = get_transaction(session, index)
                    inverted = existing.get_inverted()
                    import_transaction(session, inverted)
                    session.commit()

                # update the values
                update_values = True
                status_message = f"Transaction {existing} inverted"

        elif isinstance(event, tuple) and event[0] == "-MVTS-" and event[1] == "+CLICKED+":
            row, col = event[2]  # Récupère la ligne et la colonne cliquées
            if row is None:
                status_message = f"Pas d'index sélectionné"
                index = -1
            elif row >= 0:
                index = int(df.iloc[row, 0])
                label_utilisateur = df.iloc[row, 1]
                category = df.iloc[row, 2]

                status_message = f"Index sélectionné: {df.iloc[row, 0]} pour {df.iloc[row, 1]}"
        elif isinstance(event, tuple) and event[0] == "-SOLDES-" and event[1] == "+CLICKED+":
            row, col = event[2]
            if row is None:
                pass
            elif row >= 0:
                compte = soldes.iloc[row, 0]
                # Afficher le formulaire
                form_solde_bancaire(compte)
        elif event == "Edit":
            with Session(engine) as session:
                editable = get_transaction(session, index)
                editable = form_update_transaction(editable, nos_ref)
                if not editable is None:
                    session.commit()
                    status_message = "Catégorie et label mis à jour"
                    # Special case : numéro de reference
                    if not editable.no_de_reference in nos_ref:
                        nos_ref = [editable.no_de_reference] + nos_ref
                        update_tags = True
                    update_values = True
        elif event == "Mass edit":
            selected_rows = values['-MVTS-']
            if not selected_rows:
                sg.PopupOK("No rows selected !")
            else:
                indexes = df.iloc[selected_rows, 0].values.tolist()
                template = form_update_transactions(indexes, nos_ref)
                if not template is None:
                    with makesession() as session:
                        apply_mass_update(session, indexes, template)
                        session.commit()
                    if not template.no_de_reference in nos_ref:
                        nos_ref = [template.no_de_reference] + nos_ref
                        update_tags = True
                    update_values = True
                else:
                    sg.PopupOK("No changes made")
        elif event == "Add Keyword":
            mc = form_keyword_import(description, category)
            if not mc is None:
                try:
                    import_keyword(engine, mc)
                    status_message = f"Keyword imported for category"
                except IntegrityError:
                    status_message = f"keyword already exists"
        elif event == "Check Keywords":
            form_update_keyword(description)
        elif event == "Link":
            with Session(engine) as session:
                editable = get_transaction(session, index)
                editable = link_transaction(editable)
                if not editable is None:
                    session.commit()
                    status_message = "Lié à un événement"
                    update_values = True
        elif event == "Split Custom":
            try:
                split_periods = int(values["-SPLIT-COUNT-"])
                # Executing the split
                #                split_mouvement(index, mode='custom', periods=split_periods)
                with makesession() as session:
                    splittable = get_transaction(session, index)
                    solde = splittable.get_solde()
                    splittable_month = splittable.mois
                    splitted_values, splitted_months = form_get_custom_split(split_periods, solde, splittable_month)
                    simple_split(session, index, splitted_values, splitted_months)
                    # committing
                    session.flush()
                    session.commit()
                status_message = f"Splitting custom transaction {index} in {split_periods} parts"
                update_values = True
            except ValueError:
                sg.popup_error("Enter a valid number", title="Enter a number", button_color="red")
        elif event == "Split Yearly":
            # Executing the split
            with makesession() as session:
                split_mouvement(session, index)
                session.flush()
                session.commit()
            status_message = f"Splitting yearly transaction {index}"
            update_values = True
        elif event == "Deactivate":
            # Deactivate the movement
            selected_rows = values['-MVTS-']
            if not selected_rows:
                sg.PopupOK("No rows selected !")
            else:
                indexes = df.iloc[selected_rows, 0].values.tolist()
                with makesession() as s:
                    deactivate_transactions(s, indexes)
                    s.commit()
                status_message = f"Transactions deactivated : {str(len(indexes))}"
                update_values = True
        elif event == "Reimbursement Scheme":
            # retrieve the account
            account = values['-SOLDES-']
            if len(account) > 0:
                # get the corresponding account label
                account_label = soldes[account[0]][0]
                form_reimbursement_plan(account_label)
        elif event == "Prettify Labels":
            # retrieve the indexes
            indexes = df['index'].values.tolist()
            # get corresponding transactions
            affected_records = calculate_labels(engine, indexes)
            sg.PopupOK(f'Prettification done, affected records : {affected_records}')
            # update the display
            update_values = True
        if update_values:
            with makesession() as s:
                df = fetch_mouvements(s, view=view_columns, offset_size=offset_size, offset=offset,
                                      search_filter=desc_filter,
                                      sort_column=sort_column, sort_order="desc", category_filter=category_filter,
                                      compte_filter=compte_filter, reimbursable=reimbursable_filter,
                                      affectable=affectable_filter, economy_mode=economy_mode, job_id=job_filter,
                                      tag_filter=tag_filter)
                soldes = fetch_soldes(s, selected_type)

            window["-MVTS-"].update(values=df.values.tolist())
            window["-SOLDES-"].update(values=soldes.values.tolist())
            balances = fetch_balances()
            window['-BALANCES-'].update(values=balances.values.tolist())
            window['-ECONOMY-'].update(text='Economies' if economy_mode else 'All Expenses',
                                       button_color=get_toggle_style(economy_mode))
            window['-TIME-'].update(text='Passé' if toggle_past else 'Futur',
                                    button_color=get_toggle_style(toggle_past))
            if update_tags:
                window['-NOS-'].update(values=nos_ref)
            # Metrics
            metric_label = format_metrics(df.loc[df['Solde'] < 0]['Solde'].sum(),
                                          df.loc[df['Solde'] > 0]['Solde'].sum(), df['Solde'].sum())
            window['-METRICS-'].update(metric_label)
        # Updating the status bar
        window["-STATUS-BAR-"].update(status_message)
    # Fermeture de la fenêtre
    window.close()


if __name__ == "__main__":
    form_main()
