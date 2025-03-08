import datetime
import re

from PySimpleGUI import RELIEF_GROOVE, RELIEF_SUNKEN
from dateutil.relativedelta import relativedelta
import PySimpleGUI as sg
from sqlalchemy import select, and_, or_, not_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import engines
import pandas as pd

# Imports from data model
# New
from datamodel_finance_pg import get_remaining_provisioned_expenses, get_soldes, close_provision, \
    deactivate_transaction, get_categories, get_comptes, Mouvement, \
    import_transaction, MapCategorie, import_keyword, get_transaction, get_events, get_provisions_for_month, \
    get_salaries, get_type_comptes, get_matching_keywords, split_mouvement, simple_split, apply_mass_update, \
    create_salaries

# Connexion à la base de données PostgreSQL
engine = engines.get_pgfin_engine()

# Standard parameters
default_police = 'Calibri'
sg.set_options(font=(default_police, 10))

declarants = ['Vincent', 'Aurélie']


def fetch_mouvements(offset_size, offset=0, search_filter="", sort_column=None, sort_order="asc",
                               category_filter: str = None,
                               compte_filter: str = None, month_filter: datetime.date = None,
                               reimbursable: bool = False,
                               affectable: bool = False, provisions: bool = False,
                               economy_mode: bool = False) -> pd.DataFrame:
    """ Utilisation de l'ORM """
    stmt = select(Mouvement.index, Mouvement.description, Mouvement.label_utilisateur, Mouvement.categorie,
                  Mouvement.date, Mouvement.mois, Mouvement.depense, Mouvement.recette, Mouvement.provision_payer,
                  Mouvement.provision_recuperer, Mouvement.no_de_reference).where(
        Mouvement.date_out_of_bound == False)

    if search_filter:
        stmt = stmt.where(Mouvement.description.ilike(f"%%{search_filter}%%"))
    if category_filter:
        stmt = stmt.where(Mouvement.categorie == category_filter)
    if compte_filter:
        stmt = stmt.where(Mouvement.compte == compte_filter)
    if economy_mode:
        stmt = stmt.where(Mouvement.economie == 'true')
    if reimbursable:
        stmt = stmt.where(and_(Mouvement.depense > 0,
                               or_(Mouvement.taux_remboursement == None, Mouvement.label_utilisateur == None,
                                   Mouvement.date_remboursement == None)))
    if affectable:
        stmt = stmt.where(
            and_(Mouvement.recette > 0, or_(Mouvement.label_utilisateur == None, Mouvement.date_remboursement == None)))
    if provisions:
        stmt = stmt.where(not_(and_(Mouvement.provision_payer == None, Mouvement.provision_recuperer == None)))
    if month_filter:
        stmt = stmt.where(Mouvement.mois == month_filter)

    if sort_column:
        stmt = stmt.order_by(Mouvement.__table__.c[sort_column].desc())

    # Limiting and offsetting
    stmt = stmt.limit(offset_size).offset(offset)

    # returing the result
    with engine.connect() as conn:
        df = pd.read_sql(stmt, conn)

    # Massaging the result
    df.fillna(value=0, inplace=True)
    df['Solde'] = df['Recette'] - df['Dépense']
    df['Provision'] = df['Provision à récupérer'] - df['Provision à payer']
    df.drop(['Dépense', 'Recette', 'Provision à récupérer', 'Provision à payer'], axis=1, inplace=True)
    return df


def fetch_provisions(offset_size: int, category_filter: str, month_filter: datetime.date,
                     economy_mode: bool) -> pd.DataFrame:
    df = fetch_mouvements(offset_size=offset_size, offset=0, category_filter=category_filter, month_filter=month_filter,
                          provisions=True, economy_mode=economy_mode)
    df = df[["index", "Description", "Provision"]]
    return df


def fetch_events(category_filter: str) -> pd.DataFrame:
    """ Récupère les 50 premières lignes des événements"""
    with Session(engine) as session:
        headers, data = get_events(session, category_filter)

    df = pd.DataFrame(data=data, columns=headers)
    df[["Dépense", "Recette"]] = df[["Dépense", "Recette"]].map(lambda x: f"{x:.2f} €" if x else "")
    return df


def fetch_bilans(month: datetime.date, is_courant: bool) -> pd.DataFrame:
    """ Récupère les provisions pour un mois"""
    headers, data = get_provisions_for_month(engine, month, is_courant=is_courant)

    df = pd.DataFrame(data=data, columns=headers)
    numcols = ['Dépense', 'Recette', 'Recette Provisionnée', 'Dépense Provisionnée', 'Recette Reste', 'Dépense Reste']
    df[numcols] = df[numcols].astype(float).round(2)
    return df


def fetch_soldes(compte_type: str):
    """ Récupère les soldes des comptes courants"""
    with Session(engine) as session:
        soldes = get_soldes(session, compte_type)
    values = [[s[0], s[1], f"{s[2]:.2f} €"] for s in soldes]
    return values


def fetch_salaries() -> pd.DataFrame:
    with Session(engine) as session:
        values = get_salaries(session)

    df = pd.DataFrame(data=values)
    return df


def fetch_compte_types() -> []:
    with Session(engine) as session:
        result = get_type_comptes(session)

    return result


def fetch_keywords():
    with Session(engine) as session:
        result = session.scalars(select(MapCategorie).order_by(MapCategorie.categorie)).all()

    return result


def split_value(value: float, no_periods: int, rounding: int) -> []:
    """ returns a correct split with rounded values"""
    result = [round(value / no_periods, rounding)] * (no_periods - 1)
    quotient = sum(result)
    result += [round(value - quotient, rounding)]
    return result


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
    df = fetch_events(editable.categorie)
    headers = ('Date', 'Evénement', 'Dépense', 'Recette')

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
        [sg.Table(values=df.values.tolist(), headings=list(headers), key='-EVENTS-', enable_events=True,
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


def show_mass_transaction_editor(indexes: list):
    """ Window to edit transactions en masse"""
    layout = [
        [sg.Text(f"choose properties for following transactions :{indexes}")],
        [sg.Text("Label utilisateur :", size=(15, 1)), sg.Input(key="-LABEL-", size=(25, 1))],
        [sg.Text("Date d'événement :"), sg.Input(key="-DATE-", size=(12, 1)),
         sg.CalendarButton("Calendar", target="-DATE-", format="%Y-%m-%d")],
        [sg.Text("Numéro de référence : "), sg.InputText(size=(25, 1), key='-NO-REFERENCE-')],
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
            result.label_utilisateur = values['-LABEL-'] if values['-LABEL-'] else None
            result.no_de_reference = values['-NO-REFERENCE-'] if values['-NO-REFERENCE-'] else None
            result.date_remboursement = datetime.date.fromisoformat(values['-DATE-']) if values['-DATE-'] else None
            window.close()
            return result
    # return the values


def show_transaction_editor(editable: Mouvement) -> Mouvement:
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
    if editable.no_de_reference:
        no_ref = editable.no_de_reference
    else:
        no_ref = ''

    layout = [
        [sg.Text(f"Transaction {editable.description}")],
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
        [sg.Text("Numéro de référence : "), sg.InputText(default_text=no_ref, size=(15, 1), key='-NO-REFERENCE-')],
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
            mc: MapCategorie = show_keyword_import(editable.description, category)
            if not mc is None:
                import_keyword(engine, mc)
                sg.popup("Import successful !", title='Database import')

        elif event == "-VALIDER-":
            try:
                # Vérification des nombres
                depense = float(values["-DEPENSE-"]) if values["-DEPENSE-"] else 0.0
                recette = float(values["-RECETTE-"]) if values["-RECETTE-"] else 0.0

                editable.categorie = values["-CATEGORIE-"]
                editable.label_utilisateur = values["-LABEL-"] if values["-LABEL-"] else None
                editable.mois = convert_to_month(values["-MOIS-"])
                editable.depense = depense
                editable.recette = recette
                editable.economie = 'true' if values["-ECONOMIE-"] else 'false'
                editable.no_de_reference = values['-NO-REFERENCE-'] if values['-NO-REFERENCE-'] else None
                editable.fait_marquant = values["-FAIT-"] if values["-FAIT-"] else None
                editable.declarant = values["-DECLARANT-"] if values["-DECLARANT-"] else None
                window.close()
                return editable  # Prêt pour insertion en base

            except ValueError:
                sg.popup_error("❌ Veuillez entrer des montants valides !", font=("Calibri", 12), text_color="red")


def show_provision_editor(offset_size: int, categorie: str, mois: datetime.date, economy_mode: bool = False):
    # Retrieve the data
    df = fetch_provisions(offset_size=offset_size, category_filter=categorie, month_filter=mois,
                          economy_mode=economy_mode)

    layout = [
        [sg.Text("Description :", size=(25, 1)),
         sg.Input(key="-DESCRIPTION-", size=(25, 1))],
        [sg.Text("Provision Dépense (€) :", size=(15, 1)),
         sg.InputText(key="-DEPENSE-", size=(10, 1), default_text="0.00"),
         sg.Text("Provision Recette (€) :", size=(15, 1)),
         sg.InputText(key="-RECETTE-", size=(10, 1), default_text="0.00")],
        [sg.Checkbox("Create for remaining year ?", default=False, key='-ALL-YEAR-')],
        [sg.HorizontalSeparator()],  # Ligne de séparation

        [common_valider_button(), common_cancel_button()],
        [sg.HorizontalSeparator()],
        [sg.Table(values=df.values.tolist(), headings=list(df.columns), key="-PROVISIONS-", enable_events=True,
                  justification="center", auto_size_columns=True,
                  num_rows=20, enable_click_events=True)],
        [common_delete_button()]
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
            if row >= 0:
                index = int(df.iloc[row, 0])
            else:
                index = -1

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
                    months = [mois + relativedelta(months=i) for i in range(12 - mois.month)]
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
                    import_transaction(engine, item)
                update_values = True
            except ValueError:
                sg.popup_error(f"Error {ValueError}. ❌ Veuillez entrer des montants valides !", font=("Calibri", 12),
                               text_color="red")

        # Managing updates
        if update_values:
            df = fetch_provisions(offset_size=offset_size, category_filter=categorie, month_filter=mois,
                                  economy_mode=economy_mode)
            window['-PROVISIONS-'].update(df.values.tolist())


def show_existing_keywords(description: str):
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


def show_new_transaction_editor():
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


def manage_salaries() -> bool:
    """ interface for managing the salaries

    :returns: boolean to indicate if an update did happen"""
    ##########
    # STANDARD
    ##########
    update_values: bool = False
    status_message: str = ''

    # Variables d'état
    df = fetch_salaries()

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
    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            break
        elif isinstance(event, tuple) and event[0] == '-SALARIES-' and event[1] == '+CLICKED+':
            row, col = event[2]
            if row >= 0:
                selected_month = df.iloc[row, 0]
                status_message = f"Month selected : {selected_month}"
        elif event == "Import Selected":
            if row >= 0:
                selected_month = df.iloc[row, 0]
                create_salaries(engine, selected_month, 'Vincent', False)
                status_message = 'Import done'
                to_update = True
        elif event == "Simulate":
            if row >= 0:
                selected_month = df.iloc[row, 0]
                create_salaries(engine, selected_month, 'Vincent', True)
                status_message = 'Simulation done'

        # updates
        window["-STATUS-BAR-"].update(status_message)

    # end of the function
    window.close()
    return to_update


def manage_monthly_provisions():
    """ interface for managing a monthly provision"""
    ##########
    # STANDARD
    ##########
    update_values: bool = False
    status_message: str = ''

    # Variables d'état
    current_month: datetime.date = datetime.date.today() - datetime.timedelta(days=datetime.date.today().day - 1)
    is_courant = True
    df = fetch_bilans(current_month, is_courant=is_courant)

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
        [sg.Button("Manage", size=(15, 1)), sg.Button("Close Expense", size=(15, 1))],

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
            show_provision_editor(offset_size=20, categorie=category, mois=current_month, economy_mode=not is_courant)
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
        # Conditional update
        window['-STATUS-BAR-'].update(status_message)
        if update_values:
            df = fetch_bilans(current_month, is_courant)
            window["-DATE-"].update(current_month.strftime("%Y-%m-%d"))
            window['-PROVISIONS-'].update(df.values.tolist())
            window['-DEPENSE-'].update(f"Dépense : {round(df['Dépense'].sum(), 0)}")
            window['-RECETTE-'].update(f"Recette : {round(df['Recette'].sum(), 0)}")
            window['-SOLDE-'].update(f"Solde : {round(df['Recette'].sum() - df['Dépense'].sum(), 0)}")

    # End of the function
    window.close()


def manage_remaining_provisions():
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


def get_custom_split(no_periods: int, initial_amount: float, initial_month: datetime.date):
    """ asks the user for a custom split

    :returns: an array with a series of split values"""
    # define standard parameter
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


def manage_keywords(df: pd.DataFrame, offset_size: int):
    """ GUI for checking whether the keywords are properly matching
    The GUI contains following components :
    - a calculation of the rate of transactions matching with a pattern
    - a table with the unmatched transactions
    """
    # retrieve the keywords
    keywords = fetch_keywords()
    kw_list = [kw.keyword for kw in keywords]

    df['Matched ?'] = df.apply(lambda x: any([True if kw in x.Description else False for kw in kw_list]), axis=1)

    percentage = len(df.loc[df['Matched ?']]) / len(df)
    layout = [
        [sg.Text(f"{len(keywords)} keywords retrieved")],
        [sg.Text(f"{percentage * 100} % of the transactions were matched")],
        [sg.Table(values=df.loc[~df['Matched ?']].values.tolist(), headings=list(df.columns), key="-MVTS-",
                  enable_events=True,
                  justification="center", auto_size_columns=True,
                  num_rows=offset_size, enable_click_events=True)]
    ]

    # display
    window = sg.Window("Checking efficiency of pattern recognition", layout, modal=True)

    # Loop
    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            window.close()
            break


def main():
    ##########
    # STANDARD
    ##########
    status_message: str = 'Welcome to the Comptes interface'

    # Définition des variables d'état
    offset_size = 30  # Default value
    offset = 0
    df = fetch_mouvements(offset_size, sort_column="index", sort_order="desc")
    category_filter = None
    compte_filter = None
    desc_filter = None
    reimbursable_filter = False
    affectable_filter = False
    economy_mode = False
    sort_column='index'
    index: int = -1
    row: int = -1
    description = ''
    category = ''
    selected_type = 'Courant'

    # Soldes bancaires
    soldes = fetch_soldes(selected_type)
    solde_headers = ('Compte', 'Date', 'Solde')

    # type de comptes
    ctypes = fetch_compte_types()

    # Définition de la structure de la fenêtre
    layout = [
        [sg.Button("Provisions", size=(15, 1), button_color=("white", "blue")),
         sg.Button("Monthly Provisions", size=(15, 1), button_color=("white", "blue")),
         sg.Button("Salaries", size=(15, 1), button_color=("white", "blue")),
         sg.Button("Pattern Check", size=(15, 1), button_color=("white", "blue"))],
        [sg.Text("Filter By :"),
         common_category_combo(),
         common_compte_combo(),
         sg.Button("Reimbursable Expenses", size=(20, 1), key="-REIMBURSABLE-"),
         sg.Button("Affectable Payments", size=(20, 1), key='-AFFECTABLE-'),
         sg.Button("All Expenses", size=(15, 1), key='-ECONOMY-', button_color=get_toggle_style(economy_mode)),
         sg.InputText(key='-FILTER-', size=(20, 1)),
         sg.Button("%", key='-APPLY-FILTER-'),
         sg.Button("✖ Clear", key="-CLEAR-")
         ],
        [sg.Button('⇅ Date', key='-SORT-DATE-', size=(6, 1)), sg.Button('⇅ index', key='-SORT-INDEX-', size=(7, 1))],
        [sg.Table(values=df.values.tolist(), headings=list(df.columns), key="-MVTS-", enable_events=True,
                  justification="center", auto_size_columns=True,
                  num_rows=offset_size, enable_click_events=True),
         sg.Column([
             [sg.Combo(values=ctypes, default_value=selected_type, key='-CTYPES-', enable_events=True)],
             [sg.Table(values=soldes, headings=solde_headers, key="-SOLDES-",
                       justification='center', auto_size_columns=True)],
             [sg.Button("New Transaction", size=(15, 1))],
             [sg.Button("Deactivate", size=(15, 1))],
             [sg.Button("Edit", size=(15, 1))],
             [sg.Button("Mass edit", size=(15, 1))],
             [sg.Button("Check Keywords", size=(15, 1))],
             [sg.Button("Add Keyword", size=(15, 1))],
             [sg.Button("Link", size=(15, 1))],
             [sg.InputText(default_text="2", key='-SPLIT-COUNT-', size=(10, 1))],
             [sg.Button("Split Custom", size=(15, 1))],
             [sg.Button("Split Yearly", size=(15, 1))]], element_justification='top')
         ],
        [sg.Button("Previous", size=(15, 1)), sg.Button("Next", size=(15, 1)),
         sg.Combo(values=[20, 50, 100], default_value=20, readonly=True, enable_events=True, key='-OFFSET-',
                  tooltip="Choose pagination size")],
        [sg.Button("Quitter", size=(15, 1), button_color=("white", "red"))],
        [common_status_bar()]  # Affiche la colonne sélectionnée
    ]

    # Création de la fenêtre
    window = sg.Window("Finance Interface", layout)

    # Boucle d'événements
    while True:
        event, values = window.read()
        update_values = False

        if event in (sg.WIN_CLOSED, "Quitter"):
            break
        elif event == "Provisions":
            manage_remaining_provisions()
            update_values = True
        elif event == "Monthly Provisions":
            manage_monthly_provisions()
            update_values = True
        elif event == "Salaries":
            update_values = manage_salaries()
        elif event == "Pattern Check":
            manage_keywords(df, offset_size)
        elif event == "-CLEAR-":
            category_filter = None
            compte_filter = None
            desc_filter = None
            reimbursable_filter = False
            affectable_filter = False
            window['-CATEGORIE-'].update(value='')
            window['-COMPTE-'].update(value='')
            window['-FILTER-'].update(value='')
            update_values = True
        elif event == "-CATEGORIE-":
            category_filter = values["-CATEGORIE-"]
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
        elif event == '-APPLY-FILTER-':
            desc_filter = values["-FILTER-"]
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
            data = show_new_transaction_editor()

            if not data is None:
                import_transaction(engine, data)
                status_message = f"Transaction créée"
                update_values = True
        elif isinstance(event, tuple) and event[0] == "-MVTS-" and event[1] == "+CLICKED+":
            row, col = event[2]  # Récupère la ligne et la colonne cliquées
            if row is None:
                status_message = f"Pas d'index sélectionné"
                index = -1
            elif row >= 0:
                index = int(df.iloc[row, 0])
                description = df.iloc[row, 1]
                label_utilisateur = df.iloc[row, 2]
                category = df.iloc[row, 3]
                mois = df.iloc[row, 5]

                status_message = f"Index sélectionné: {df.iloc[row, 0]} pour {df.iloc[row, 1]}"
        elif event == "Edit":
            with Session(engine) as session:
                editable = get_transaction(session, index)
                editable = show_transaction_editor(editable)
                if not editable is None:
                    session.commit()
                    status_message = "Catégorie et label mis à jour"
                    update_values = True
        elif event == "Mass edit":
            selected_rows = values['-MVTS-']
            if selected_rows == []:
                sg.PopupOK("No rows selected !")
            else:
                indexes = df.iloc[selected_rows, 0].values.tolist()
                template = show_mass_transaction_editor(indexes)
                if not template is None:
                    apply_mass_update(engine, indexes, template)
                    update_values = True
                else:
                    sg.PopupOK("No changes made")
        elif event == "Add Keyword":
            mc = show_keyword_import(description, category)
            if not mc is None:
                try:
                    import_keyword(engine, mc)
                    status_message = f"Keyword imported for category"
                except IntegrityError:
                    status_message = f"keyword already exists"
        elif event == "Check Keywords":
            show_existing_keywords(description)
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
                with Session(engine) as session:
                    splittable = get_transaction(session, index)
                    solde = splittable.get_solde()
                    splittable_month = splittable.mois
                splitted_values, splitted_months = get_custom_split(split_periods, solde, splittable_month)
                simple_split(engine, index, splitted_values, splitted_months)
                status_message = f"Splitting custom transaction {index} in {split_periods} parts"
                update_values = True
            except ValueError:
                sg.popup_error("Enter a valid number", title="Enter a number", button_color="red")
        elif event == "Split Yearly":
            # Executing the split
            split_mouvement(engine, index)
            status_message = f"Splitting yearly transaction {index}"
            update_values = True
        elif event == "Deactivate":
            # Deactivate the movement
            deactivate_transaction(engine, index)
            status_message = f"Transaction deactivated {index}"
            update_values = True
        if update_values:
            df = fetch_mouvements(offset_size=offset_size, offset=offset, search_filter=desc_filter,
                                            sort_column=sort_column, sort_order="desc", category_filter=category_filter,
                                            compte_filter=compte_filter, reimbursable=reimbursable_filter,
                                            affectable=affectable_filter, economy_mode=economy_mode)
            window["-MVTS-"].update(values=df.values.tolist())
            soldes = fetch_soldes(selected_type)
            window["-SOLDES-"].update(values=soldes)
            window['-ECONOMY-'].update(text='Economies' if economy_mode else 'All Expenses', button_color=get_toggle_style(economy_mode))
        # Updating the status bar
        window["-STATUS-BAR-"].update(status_message)
    # Fermeture de la fenêtre
    window.close()


if __name__ == "__main__":
    main()
