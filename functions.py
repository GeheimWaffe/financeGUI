import datetime
import datetime as dt
from datetime import date, datetime, timedelta
from typing import Iterable

import pandas as pd
from sqlalchemy import Engine, select, and_, or_, not_, MetaData, Table, Column, String, func, Date, Numeric
from sqlalchemy.orm import Session

import engines
from datamodel import Compte, Mouvement, Job, Categorie, MapCategorie, LabelPrettifier, MapSalaire


def get_comptes(s: Session):
    """ Returns a list of accounts (class Compte)

    :returns:a list of objects of type Compte"""
    result = s.scalars(select(Compte).order_by(Compte.compte)).all()

    return result


def get_type_comptes(s: Session) -> []:
    """ returns the various compte types"""
    result = s.scalars(select(Compte.compte_type.distinct())).all()
    return result


def fetch_mouvements(s: Session, view: Iterable, offset_size, offset=0, search_filter="", sort_column=None,
                     sort_order: str = 'asc',
                     category_filter: str = None,
                     compte_filter: str = None, month_filter: datetime.date = None,
                     reimbursable: bool = False,
                     affectable: bool = False, provisions: bool = False, transactions: bool = False,
                     economy_mode: bool = False,
                     job_id: int = 0,
                     tag_filter: str = None, faits_marquants: bool = False, skip_columns=None) -> pd.DataFrame:
    """ Utilisation de l'ORM """
    if skip_columns is None:
        skip_columns = []
    stmt = select(Mouvement.index, Mouvement.description, Mouvement.label_utilisateur, Mouvement.categorie,
                  Mouvement.date, Mouvement.mois, Mouvement.depense, Mouvement.recette, Mouvement.provision_payer,
                  Mouvement.provision_recuperer, Mouvement.no_de_reference, Mouvement.fait_marquant).where(
        Mouvement.date_out_of_bound == False)

    if search_filter:
        stmt = stmt.where(Mouvement.description.ilike(f"%%{search_filter}%%"))
    if not category_filter is None:
        stmt = stmt.where(Mouvement.categorie == category_filter)
    if not compte_filter is None:
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
    if transactions:
        stmt = stmt.where(or_(Mouvement.depense != 0, Mouvement.recette != 0))
    if month_filter:
        stmt = stmt.where(Mouvement.mois == month_filter)
    if job_id > 0:
        stmt = stmt.where(Mouvement.job_id == job_id)
    if tag_filter:
        stmt = stmt.where(Mouvement.no_de_reference == tag_filter)
    if faits_marquants:
        stmt = stmt.where(Mouvement.fait_marquant != None)
    if sort_column:
        stmt = stmt.order_by(Mouvement.__table__.c[sort_column].desc())

    # Limiting and offsetting
    stmt = stmt.limit(offset_size).offset(offset)

    # returing the result
    df = pd.read_sql(stmt, s.connection())

    # Massaging the result
    df.fillna(value=0, inplace=True)
    df['Solde'] = df['Recette'] - df['Dépense']
    df['Provision'] = df['Provision à récupérer'] - df['Provision à payer']
    if not view is None:
        df = df[view]

    return df


def get_groups(s: Session) -> pd.DataFrame:
    # Selection of the patterns
    metadata_obj = MetaData()
    classes = Table('classifiers', metadata_obj,
                    Column('patterns', String),
                    Column('classes', String),
                    schema='public')
    stmt = select(classes).order_by(classes.c['classes'])
    df_classes = pd.read_sql(stmt, s.connection())
    return df_classes


def get_categorized_provisions(s: Session, category_filter: str, month: date, economy_mode: bool) -> pd.DataFrame:
    """ This function calculates, for a given category, the total expenses and recipes, comparing between actual and forecast"""
    stmt = select(Mouvement.description, Mouvement.depense, Mouvement.provision_payer, Mouvement.recette,
                  Mouvement.provision_recuperer).where(Mouvement.date_out_of_bound == False,
                                                       Mouvement.categorie == category_filter, Mouvement.mois == month)
    #                                                       Mouvement.economie == text('true') if economy_mode else text('false'))

    df_classes = get_groups(s)

    # reading the dataframe
    df = pd.read_sql(stmt, s.connection())

    # Classifying
    df['Group'] = df['Description'].apply(classify, classification_matrix=df_classes.values)

    # Grouping
    df = df.drop('Description', axis=1).groupby(['Group'], as_index=False).sum()

    # Calculating differences
    df['Δ Dépense'] = df['Provision à payer'] - df['Dépense']
    df['Δ Recette'] = df['Recette'] - df['Provision à récupérer']
    # Rounding
    df = df.round(2)
    # returning the result
    return df


def import_transaction(session: Session, mvt: Mouvement):
    """ Generates a transaction"""
    print(f'Importing transaction {mvt}')
    # retrieve the last valid number
    max_number = get_max_number(session)
    # create a job
    job = Job(job_key=Job.type_import, job_timestamp=datetime.now())
    # assign the movement
    mvt.job = job
    # add the metadata
    mvt.no = max_number
    mvt.date_insertion = date.today()
    session.add(mvt)
    print(f'Transaction generated')


def get_categories(s: Session):
    """ Returns a list of categories (class Catégorie)

    :returns:a list of object of type Catégorie"""
    return s.scalars(select(Categorie).order_by(Categorie.categorie)).all()


def get_events(s: Session, category: str = None):
    """ returns a tuple of headers, data, for use in a dataframe"""
    stmt = select(Mouvement.date_remboursement, Mouvement.label_utilisateur,
                  func.sum(Mouvement.depense).label("Dépense"),
                  func.sum(Mouvement.recette).label("Recette")).where(
        and_(Mouvement.date_remboursement != None, Mouvement.categorie == category,
             Mouvement.date_out_of_bound == False)).group_by(
        Mouvement.date_remboursement, Mouvement.label_utilisateur).order_by(
        Mouvement.date_remboursement.desc()).limit(50)

    return pd.read_sql(stmt, s.connection())


def get_transaction(session: Session, index: int) -> Mouvement:
    return session.scalar(select(Mouvement).where(Mouvement.index == index))


def get_yearly_realise(session: Session, is_provision: bool, is_depense: bool, is_economie: bool, category: str,
                       annee: int,
                       group: str = None) -> pd.DataFrame:
    # récupérer les mouvements
    stmt = select(Mouvement.mois, Mouvement.description, Mouvement.depense, Mouvement.recette,
                  Mouvement.provision_payer.label('Dépense Provisionnée'),
                  Mouvement.provision_recuperer.label('Recette Provisionnée')).where(
        Mouvement.date_out_of_bound == False).where(Mouvement.categorie == category).where(
        Mouvement.mois.between(date(annee, 1, 1), date(annee, 12, 1)))
    if is_economie:
        stmt = stmt.where(Mouvement.economie == 'true')

    df = pd.read_sql(stmt, session.connection())
    # récupérer les classes
    classes = get_groups(session)

    # classifier
    df['Classe'] = df['Description'].apply(classify, classification_matrix=classes.values)

    # If a group is specified, filter
    if not group is None:
        df = df.loc[df['Classe'] == group]

    # Aggregate
    if is_provision:
        df = df.groupby(['Mois'], as_index=False)[
            ['Dépense Provisionnée' if is_depense else 'Recette Provisionnée']].sum().round(2)
    else:
        df = df.groupby(['Mois'], as_index=False)[['Dépense' if is_depense else 'Recette']].sum().round(2)

    return df


def get_groups_of_category(session: Session, category: str, annee: int,
                           group: str = None) -> pd.DataFrame:
    # récupérer les mouvements
    stmt = select(Mouvement.description.distinct()).where(
        Mouvement.date_out_of_bound == False).where(Mouvement.categorie == category).where(
        Mouvement.mois.between(date(annee, 1, 1), date(annee, 12, 1)))
    df = pd.read_sql(stmt, session.connection())
    # récupérer les classes
    classes = get_groups(session)

    # classifier
    df['Classe'] = df['Description'].apply(classify, classification_matrix=classes.values)

    df = df[['Classe']].drop_duplicates()

    return df


def get_solde(s: Session, compte: str, period_begin: date, period_end: date) -> pd.DataFrame:
    """ calculates the running saldo"""
    stmt = select(Mouvement.date, Mouvement.depense, Mouvement.recette).where(Mouvement.compte == compte).where(
        Mouvement.date_out_of_bound == False)
    df = pd.read_sql(stmt, s.connection(), coerce_float=True, parse_dates='Date')

    # Transformation
    df = df.fillna(0)
    df['Solde'] = df['Recette'] - df['Dépense']
    df = df.groupby('Date')[['Solde']].sum()
    df = df.loc[df.index.date <= period_end]
    df = df.sort_index()
    df['Cumul'] = df['Solde'].cumsum()
    df = df.loc[df.index.date >= period_begin]
    # rounding
    df = df.round(2)

    # extra date
    df['Jour'] = df.index.date

    # End
    return df[['Jour', 'Solde', 'Cumul']].sort_index(ascending=True)


def get_grouped_transactions(s: Session, compte_type: str, period_begin: date, period_end: date) -> pd.DataFrame:
    """ calculates the running saldo for all accounts"""
    stmt = select(Compte.compte_type, Mouvement.compte, Mouvement.date, Mouvement.depense, Mouvement.recette).join(
        Compte).where(
        Mouvement.date_out_of_bound == False).where(Mouvement.date <= period_end).where(
        Compte.compte_type == compte_type)
    df = pd.read_sql(stmt, s.connection(), coerce_float=True, parse_dates='Date')
    # fill the values with zero, else the calculation of the solde doesn't work properly
    df = df.fillna(0)
    df['Solde'] = df['Recette'] - df['Dépense']
    df = df.groupby(['compte_type', 'Compte', 'Date'])[['Solde']].sum().sort_index()
    df['Cumul'] = df.groupby(level='Compte')['Solde'].cumsum()
    df = df.loc[df.index.get_level_values('Date') >= pd.to_datetime(period_begin)]
    # rounding
    df = df.round(2)

    # End
    return df[['Solde', 'Cumul']].sort_index(ascending=True)


def get_grouped_transactions_2(s: Session, compte_type: str, period_begin: date, period_end: date) -> pd.DataFrame:
    """ calculates the running saldo for all accounts"""
    # --- STEP 1 : calculates the starting saldos
    stmt = select(Mouvement.compte, Mouvement.depense, Mouvement.recette).join(
        Compte).where(
        Mouvement.date_out_of_bound == False).where(Mouvement.date < period_begin).where(
        Compte.compte_type == compte_type).where(Compte.compte_actif == True)
    df = pd.read_sql(stmt, s.connection(), coerce_float=True, parse_dates='Date')

    # aggregate
    df = df.groupby(['Compte'])[['Dépense', 'Recette']].sum().fillna(0).round(2)
    df['Solde'] = df['Recette'] - df['Dépense']
    df = df.drop(columns=['Dépense', 'Recette'])
    df = df.reset_index()
    df['Date'] = period_begin

    # 2. Création de la plage de dates complète
    all_dates = pd.date_range(start=period_begin, end=period_end, freq='D')

    # Création d'un MultiIndex complet
    full_index = pd.MultiIndex.from_product(
        [df['Compte'].unique(), all_dates],
        names=['Compte', 'Date']
    )

    # 4. On réindexe le dataframe
    # On met d'abord l'index sur Compte et Date, puis on réindexe avec le complet
    df_exploded = (
        df.set_index(['Compte', 'Date'])
        .reindex(full_index)
        .sort_index()
    )

    # 5. REMPLISSAGE (La partie magique)
    # On groupe par compte pour ne pas mélanger les soldes, et on remplit vers le bas
    df_exploded['Solde'] = df_exploded.groupby(level='Compte')['Solde'].ffill().fillna(0)

    #  --- STEP 2 : calculates the variations in the period ---
    stmt = select(Mouvement.compte, Mouvement.date, Mouvement.depense, Mouvement.recette).join(
        Compte).where(
        Mouvement.date_out_of_bound == False).where(Mouvement.date >= period_begin).where(
        Mouvement.date <= period_end).where(
        Compte.compte_type == compte_type)
    df = pd.read_sql(stmt, s.connection(), coerce_float=True, parse_dates='Date')

    # aggregate
    df = df.groupby(['Compte', 'Date'])[['Dépense', 'Recette']].sum().fillna(0).round(2).sort_index()
    df['Delta'] = df['Recette'] - df['Dépense']
    df['Cumul'] = df.groupby(level='Compte')['Delta'].cumsum()
    df = df.drop(columns=['Dépense', 'Recette', 'Delta'])

    # --- STEP 3 : join the saldos and the variations ---
    df_all = df_exploded.join(df)
    df_all['Cumul'] = df_all.groupby(level='Compte')['Cumul'].ffill().fillna(0)

    # --- END : calculation
    df_all['Solde'] = df_all['Solde'] + df_all['Cumul']

    return df_all


def fetch_soldes(s: Session, compte_type: str) -> pd.DataFrame:
    """ Récupère les soldes des comptes courants"""
    """ Returns the current accounts"""
    metadata_obj = MetaData()
    soldes = Table('view_solde_actuel',
                   metadata_obj,
                   Column('Compte', String),
                   Column('Type Compte', String),
                   Column('Date', Date),
                   Column('Solde Compte Actuel', Numeric),
                   schema='dbview_schema'
                   )

    values = pd.read_sql(select(soldes.c["Compte"], soldes.c["Date"], soldes.c["Solde Compte Actuel"]).where(
        soldes.c['Type Compte'] == compte_type), s.connection())

    return values


def get_salaries(s: Session, mois: date = None) -> list:
    """ calls the salaries and provides a list of values"""
    metadata_obj = MetaData()
    salaires = Table('view_salaires_nets',
                     metadata_obj,
                     Column('mois', Date),
                     Column('salaire_net', Numeric),
                     Column('prime_net', Numeric),
                     Column('impot_salaire', Numeric),
                     Column('impot_prime', Numeric),
                     Column('logement', Numeric),
                     Column('autre', Numeric),
                     Column('total', Numeric),
                     schema='dbview_schema')

    if mois == None:
        return pd.read_sql(select(salaires), s.connection(), parse_dates='mois')
    else:
        return pd.read_sql(select(salaires).where(salaires.c['mois'] == mois), s.connection(), parse_dates='mois')


def get_max_number(s: Session) -> int:
    result = s.scalar(select(Mouvement.no).order_by(Mouvement.no.desc()))
    return int(result)


def get_remaining_provisioned_expenses(s: Session):
    """ function to get an ordered list of remaining provisioned expenses
    :returns: set of tuples (Mois, Catégorie, Dépenses Courante Provisionnée Non Epuisée)"""
    metadata_obj = MetaData()
    remaining_table = Table('view_bilans_agregation',
                            metadata_obj,
                            Column('Mois', Date),
                            Column('Catégorie', String),
                            Column('Dépense Courante Provisionnée non épuisée', Numeric),
                            Column('Recette Economisée Provisionnée restante', Numeric),
                            schema='dbview_schema')

    results = s.execute(
        select(remaining_table).where(
            and_(
                remaining_table.c['Dépense Courante Provisionnée non épuisée'] > 0,
                remaining_table.c['Mois'] < date.today() - timedelta(days=date.today().day - 1),
                remaining_table.c['Dépense Courante Provisionnée non épuisée'] != remaining_table.c[
                    'Recette Economisée Provisionnée restante']
            )).order_by(remaining_table.c['Mois'].desc())
    )
    return results


def close_provision(s: Session, mois: date, category: str, remaining: float):
    # and we create a transaction for it.
    # Create a new job
    job = Job(job_key=Job.type_shut, job_timestamp=datetime.now())
    s.add(Mouvement(date=date.today(),
                    description='Automatic closing of provision',
                    categorie=category,
                    mois=mois,
                    date_insertion=date.today(),
                    provision_payer=-remaining,
                    no=0,
                    job=job
                    ))
    print(f'Mouvement créé. Committing...')
    # end
    s.flush()
    s.commit()


def create_salaries(e: Engine, parent_id: int, mois: dt.date, simulate: bool):
    """ Créer des salaires pour un mois donné"""
    print(f'Attempting to generate salary for month : {mois}')

    # Constants
    compte = 'Crédit Agricole'
    categorie_salaire = 'Salaire'
    categorie_impot = 'Impôt Revenu'
    categorie_ail = 'Ail'
    categorie_note_de_frais = 'Notes De Frais'
    date_insertion = dt.date.today()

    with Session(e) as session:
        # Création du numéro de transaction
        maxnumber = get_max_number(session) + 1
        print(f'max number retrieved : {maxnumber}')
        # retrieve salarial data
        salaire_infos = get_salaries(session, mois)
        print(f'infos salaires retrieved : {salaire_infos}')
        # try to find the original salary

        # salaire found. Do it.
        salaire_transaction = session.get(Mouvement, parent_id)
        date_salaire = salaire_transaction.date
        print(f'salary transaction found : {salaire_transaction}')

        # Create the job
        salaire_job = Job(job_key=Job.type_salary, job_mois=mois, job_timestamp=dt.datetime.now())
        session.add(salaire_job)
        print(f'Job created : {salaire_job}')

        # Create the transactions
        to_insert = []
        to_insert.append(Mouvement(description=f'Salaire net pour le mois {mois}',
                                   recette=salaire_infos['salaire_net'],
                                   depense=0,
                                   categorie=categorie_salaire,
                                   )
                         )

        to_insert.append(Mouvement(description=f'Impôt revenu sur le salaire du {mois}',
                                   recette=0,
                                   depense=-salaire_infos['impot_salaire'],
                                   categorie=categorie_impot,
                                   )
                         )

        to_insert.append(Mouvement(description=f'AIL net pour le mois {mois}',
                                   recette=salaire_infos['logement'],
                                   depense=0,
                                   categorie=categorie_ail,
                                   )
                         )

        if salaire_infos['autre'] > 0:
            to_insert.append(Mouvement(description=f'Notes de frais pour le {mois}',
                                       recette=salaire_infos['autre'],
                                       depense=0,
                                       categorie=categorie_note_de_frais,
                                       )
                             )

        if salaire_infos['prime_net'] > 0:
            to_insert.append(Mouvement(description=f'Prime nette pour le mois {mois}',
                                       recette=salaire_infos['prime_net'],
                                       depense=0,
                                       categorie=categorie_salaire,
                                       economie='true',
                                       )
                             )

            to_insert.append(Mouvement(description=f'Impôt sur la prime pour le mois {mois}',
                                       recette=0,
                                       depense=-salaire_infos['impot_prime'],
                                       categorie=categorie_impot,
                                       economie='true',
                                       )
                             )
        # add the general metadata
        for mvt in to_insert:
            mvt.date = date_salaire
            mvt.date_insertion = date_insertion
            mvt.no = maxnumber
            mvt.index_parent = parent_id
            mvt.job = salaire_job
            mvt.label_utilisateur = mvt.description
            mvt.declarant = salaire_transaction.declarant
            mvt.employeur = salaire_transaction.employeur
            mvt.mois = mois
            mvt.compte = compte
            # appending to the session
            session.add(mvt)

        # modify the original salary
        if salaire_transaction != None:
            salaire_transaction.recette_initiale = salaire_transaction.recette
            salaire_transaction.recette = 0
            session.add(salaire_transaction)
            print(f'Original transaction neutralized')

        # Closing the session and committing
        session.flush()
        if not simulate:
            session.commit()
            print(f'Salary import done')
        else:
            print(f'No import, just simulating')


def save_capital_reimbursements(e: Engine, reimbursement_scheme: pd.Series, target_account: str, target_category: str,
                                start_date: date):
    """ Loads the reimbursements"""
    # create the session
    with Session(e) as session:
        # deactivate the previous ones
        previous_payments = session.scalars(select(Mouvement).where(Mouvement.compte == target_account))
        for p in previous_payments:
            p.date_out_of_bound = True
        # Create the new ones
        # retrieve the last valid number
        max_number = get_max_number(session)
        # create a job
        job = Job(job_key=Job.type_import, job_timestamp=datetime.now())
        # Generate the initial reimbursement
        max_number += 1
        initial_date = reimbursement_scheme.index[0]
        mvt = Mouvement(date=initial_date - timedelta(days=1),
                        description=f"initialisation du remboursement",
                        compte=target_account,
                        categorie=target_category,
                        mois=initial_date,
                        date_insertion=date.today(),
                        depense=float(reimbursement_scheme.sum()),
                        no=max_number,
                        economie='true',
                        job=job
                        )
        session.add(mvt)

        # generate a set of provisions

        for d in reimbursement_scheme.index:
            max_number += 1
            mvt = Mouvement(date=d,
                            description=f"Remboursement du capital restant dû",
                            compte=target_account,
                            categorie=target_category,
                            mois=d,
                            date_insertion=date.today(),
                            recette=float(reimbursement_scheme[d]),
                            no=max_number,
                            job=job
                            )
            session.add(mvt)

        # save
        session.flush()
        session.commit()


def get_provisions_for_month(e: Engine, month: date, is_courant: bool = True) -> pd.DataFrame:
    """ Returns all the aggregated provisions for a specific month

    :returns:a Dataframe with the necessary columns"""

    metadata_obj = MetaData()
    provisions = Table('view_bilans_agregation',
                       metadata_obj,
                       Column('Catégorie Groupe', String),
                       Column('Catégorie', String),
                       Column('Mois', Date),
                       Column('Recette Courante', Numeric),
                       Column('Recette Courante Provisionnée', Numeric),
                       Column('Recette Courante Provisionnée restante', Numeric),
                       Column('Dépense Courante', Numeric),
                       Column('Dépense Courante Provisionnée', Numeric),
                       Column('Dépense Courante Provisionnée non épuisée', Numeric),
                       Column('Recette Economisée', Numeric),
                       Column('Recette Economisée Provisionnée', Numeric),
                       Column('Recette Economisée Provisionnée restante', Numeric),
                       Column('Dépense Economisée', Numeric),
                       Column('Dépense Economisée Provisionnée', Numeric),
                       Column('Dépense Economisée Provisionnée restante', Numeric),

                       schema='dbview_schema')

    if not is_courant:
        stmt = select(provisions.c['Catégorie Groupe'], provisions.c['Catégorie'], provisions.c['Recette Economisée'],
                      provisions.c['Recette Economisée Provisionnée'],
                      provisions.c['Recette Economisée Provisionnée restante'],
                      provisions.c['Dépense Economisée'], provisions.c['Dépense Economisée Provisionnée'],
                      provisions.c['Dépense Economisée Provisionnée restante'])
    else:
        stmt = select(provisions.c['Catégorie Groupe'], provisions.c['Catégorie'], provisions.c['Recette Courante'],
                      provisions.c['Recette Courante Provisionnée'],
                      provisions.c['Recette Courante Provisionnée restante'],
                      provisions.c['Dépense Courante'], provisions.c['Dépense Courante Provisionnée'],
                      provisions.c['Dépense Courante Provisionnée non épuisée'])

    stmt = stmt.where(
        provisions.c['Mois'] == month).order_by(
        provisions.c['Catégorie Groupe'], provisions.c['Catégorie'])

    result = pd.read_sql(stmt, e, coerce_float=True, parse_dates=('Mois'))

    if not is_courant:
        result.rename(inplace=True, columns={'Recette Economisée': 'Recette',
                                             'Recette Economisée Provisionnée': 'Recette Provisionnée',
                                             'Recette Economisée Provisionnée restante': 'Recette Reste',
                                             'Dépense Economisée': 'Dépense',
                                             'Dépense Economisée Provisionnée': 'Dépense Provisionnée',
                                             'Dépense Economisée Provisionnée restante': 'Dépense Reste'})
    else:
        result.rename(inplace=True, columns={'Recette Courante': 'Recette',
                                             'Recette Courante Provisionnée': 'Recette Provisionnée',
                                             'Recette Courante Provisionnée restante': 'Recette Reste',
                                             'Dépense Courante': 'Dépense',
                                             'Dépense Courante Provisionnée': 'Dépense Provisionnée',
                                             'Dépense Courante Provisionnée non épuisée': 'Dépense Reste'})

    return result


def classify(value: str, classification_matrix):
    for pattern, result in classification_matrix:
        if pattern in value:
            return result
    return 'Common'


def deactivate_transactions(s: Session, indexes: list[int]):
    mvts = s.scalars(select(Mouvement).where(Mouvement.index.in_(indexes))).all()
    for m in mvts:
        m.date_out_of_bound = True
        s.add(m)
    s.flush()
    s.commit()


def deactivate_transaction(s: Session, index: int):
    mvt = s.scalar(select(Mouvement).where(Mouvement.index == index))
    if not mvt is None:
        mvt.date_out_of_bound = True
        s.commit()


def update_transaction_category(e: Engine, index: int, cat: str, lab: str, mois: date):
    with Session(e) as session:
        mvt = session.scalar(select(Mouvement).where(Mouvement.index == index))
        if not mvt is None:
            mvt.categorie = cat
            mvt.label_utilisateur = lab
            mvt.mois = mois
            session.commit()


def apply_mass_update(session: Session, indexes: list[int], template: Mouvement):
    """ Applies a mass update"""
    # retrieve the movement
    for i in indexes:
        mvt = session.get(Mouvement, ident=i)
        if not mvt is None:
            if template.label_utilisateur:
                mvt.label_utilisateur = template.label_utilisateur
            if template.no_de_reference:
                mvt.no_de_reference = template.no_de_reference
            mvt.date_remboursement = template.date_remboursement
            if not template.description is None:
                mvt.description = template.description
            if not template.categorie is None:
                mvt.categorie = template.categorie
            if not template.mois is None:
                mvt.mois = template.mois


def import_keyword(e: Engine, value: MapCategorie):
    with Session(e) as session:
        session.add(value)
        session.commit()


def get_matching_keywords(e: Engine, description: str) -> []:
    """ filters all the keywords to find the ones corresponding to the description"""
    stmt = select(MapCategorie)
    with Session(e) as session:
        mcs = session.scalars(stmt).all()

    # filters the keywords
    result = [mc for mc in mcs if mc.keyword in description]

    # return the results
    return result


def get_keywords(e: Engine, active_flag: bool) -> pd.DataFrame:
    """ Retrieves all the keywords"""
    return pd.read_sql(select(MapCategorie).where(MapCategorie.inactif != active_flag).order_by(MapCategorie.categorie),
                       e)


def simple_split(session: Session, index: int, values: list, months: list):
    """ This is also a splitting function, but which assumes the values and months are already defined

    :param session: the session
    :param index: index of the transaction to split
    :param values: list of split values
    :param months: list of split months"""

    mvt = session.get(Mouvement, ident=index)
    if not mvt is None:
        # initier les variables
        mvt.recette_initiale = mvt.recette
        mvt.depense_initiale = mvt.depense
        mvt.recette = 0
        mvt.depense = 0

        # Create a new job
        job = Job(job_key=Job.type_split, job_timestamp=dt.datetime.now())

        # create the sub-transactions
        for i in range(len(values)):
            session.add(
                Mouvement(date=mvt.date,
                          description=mvt.description,
                          recette=values[i] if values[i] > 0 else 0,
                          depense=-values[i] if values[i] < 0 else 0,
                          compte=mvt.compte,
                          categorie=mvt.categorie,
                          economie=mvt.economie,
                          regle=mvt.regle,
                          mois=months[i],
                          date_insertion=mvt.date_insertion,
                          provision_payer=mvt.provision_payer,
                          provision_recuperer=mvt.provision_recuperer,
                          date_remboursement=mvt.date_remboursement,
                          organisme=mvt.organisme,
                          date_out_of_bound=mvt.date_out_of_bound,
                          taux_remboursement=mvt.taux_remboursement,
                          fait_marquant=mvt.fait_marquant,
                          no=mvt.no,
                          no_de_reference=mvt.no_de_reference,
                          index_parent=mvt.index_parent,
                          label_utilisateur=mvt.label_utilisateur,
                          declarant=mvt.declarant,
                          employeur=mvt.employeur,
                          job=job
                          )
            )

        # Update the original transaction
        session.add(mvt)


def split_mouvement(session: Session, index: int, mode: str = 'year', periods: int = 12, rounding: int = 2):
    """ The function splits a row in the database
    It has two modes :
    - year : spreads over a calendar year
    - custom : spreads over a custom number of periods (by default : 12)
    """
    mvt = session.get(Mouvement, ident=index)
    if not mvt is None:
        # initier les variables
        rec = mvt.recette
        dep = mvt.depense

        # Logique spécifique au split annuel
        if mode == 'year':
            mois = [dt.date(mvt.mois.year, i + 1, 1) for i in range(periods)]
        else:
            mois = [mvt.mois] * periods

        if rec is None:
            split_rec = None
            rest_rec = None
        else:
            split_rec = round(rec / periods, rounding)
            rest_rec = rec - (periods - 1) * split_rec
            mvt.recette_initiale = rec
            mvt.recette = 0

        if dep is None:
            split_dep = None
            rest_dep = None
        else:
            split_dep = round(dep / periods, rounding)
            rest_dep = dep - (periods - 1) * split_dep
            mvt.depense_initiale = dep
            mvt.depense = 0

        deps = [split_dep] * (periods - 1) + [rest_dep]
        recs = [split_rec] * (periods - 1) + [rest_rec]

        # Create a new job
        job = Job(job_key=Job.type_split, job_timestamp=dt.datetime.now())

        # create the sub-transactions
        for i in range(periods):
            session.add(
                Mouvement(date=mvt.date,
                          description=mvt.description,
                          recette=recs[i],
                          depense=deps[i],
                          compte=mvt.compte,
                          categorie=mvt.categorie,
                          economie=mvt.economie,
                          regle=mvt.regle,
                          mois=mois[i],
                          date_insertion=mvt.date_insertion,
                          provision_payer=mvt.provision_payer,
                          provision_recuperer=mvt.provision_recuperer,
                          date_remboursement=mvt.date_remboursement,
                          organisme=mvt.organisme,
                          date_out_of_bound=mvt.date_out_of_bound,
                          taux_remboursement=mvt.taux_remboursement,
                          fait_marquant=mvt.fait_marquant,
                          no=mvt.no,
                          no_de_reference=mvt.no_de_reference,
                          index_parent=mvt.index_parent,
                          depense_initiale=mvt.depense_initiale,
                          recette_initiale=mvt.recette_initiale,
                          label_utilisateur=mvt.label_utilisateur,
                          declarant=mvt.declarant,
                          employeur=mvt.employeur,
                          job=job
                          )
            )

        # Update the original transaction
        session.add(mvt)


def split_number(to_split: float, periods: int, rounding: int) -> Iterable:
    if to_split is None:
        split = None
        rest = None
    else:
        split = round(to_split / periods, rounding)
        rest = to_split - split * (periods - 1)
    return [split] * 11 + [rest]


def generate_provision(e: Engine, category: str, year: int, description: str, depense: float, recette: float):
    """ generate a set of provision for a given year"""
    print(f'Generating a set of provisions for category {category} in year {year} with description {description}')

    with Session(e) as session:
        # create a job
        job = Job(job_key=Job.type_provision, job_timestamp=dt.datetime.now())
        # generate a set of provisions
        for i in range(12):
            mvt = Mouvement(date=dt.date(year, 1, 1),
                            description=description,
                            categorie=category,
                            mois=dt.date(year, i + 1, 1),
                            date_insertion=dt.date.today(),
                            provision_payer=depense,
                            provision_recuperer=recette,
                            no=0,
                            job=job
                            )
            session.add(mvt)
            print(f'Transaction generated : {mvt}')

        session.flush()
        session.commit()


def get_balances(session: Session, first_month: date) -> pd.DataFrame:
    """ Calculates the balances per month"""
    stmt = select(Mouvement.mois, func.sum(Mouvement.depense).label('Dépense'),
                  func.sum(Mouvement.recette).label('Recette'),
                  (func.sum(Mouvement.recette) - func.sum(Mouvement.depense)).label("Solde")).where(
        Mouvement.categorie == '',
        Mouvement.mois >= first_month,
        Mouvement.date_out_of_bound == False).group_by(
        Mouvement.mois)

    df = pd.read_sql(stmt, session.connection())

    return df


def calculate_labels(e: Engine, indexes: []) -> int:
    """ Calculates nice labels for every transaction, and saves it to the database"""
    affected_records: int = 0
    # get the replacers
    rplc = LabelPrettifier(None)
    # retrieves the transaction
    with Session(e) as session:
        # get all transactions
        stmt = select(Mouvement).where(Mouvement.index.in_(indexes))
        # prettify the transactions
        mvts = session.scalars(stmt)
        m: Mouvement
        for m in mvts:
            if m.label_utilisateur is None:
                affected_records += 1
                m.label_utilisateur = rplc.clean_label(m.description)
            else:
                # a label is already present
                pass
        # save
        session.flush()
        session.commit()

    return affected_records


def find_salary_transaction(e: Engine, mois: date, amount: float) -> Mouvement:
    """ Searches for a transaction with corresponding amount"""
    with Session(e) as session:
        stmt = select(Mouvement).where(Mouvement.date >= mois - timedelta(days=7),
                                       or_(Mouvement.recette == amount, Mouvement.recette_initiale == amount))
        mvt = session.scalar(stmt)

    return mvt


def get_salary_candidates(e: Engine):
    """ Checks all the salary candidates and returns a dataframe"""
    with Session(e) as session:
        # get all salary rules
        rules = session.scalars(select(MapSalaire))
        # iterate over the rules
        result = []
        for r in rules:
            mvts = session.scalars(
                select(Mouvement).where(Mouvement.description.contains(r.pattern),
                                        Mouvement.compte == r.compte,
                                        Mouvement.declarant is None,
                                        Mouvement.recette > 0))
            result += mvts
        # Convert to a dataframe
        m: Mouvement
        data = [[m.index, m.description, m.date, m.mois] for m in result]
        df = pd.DataFrame(data=data, columns=['Index', 'Description', 'Date', 'Solde'])

    # end
    return df


def get_jobs(s: Session, limit: int = 10):
    """ Get the last jobs, ordered by execution date """
    stmt = select(Job).order_by(Job.job_id.desc()).limit(limit)
    jobs = s.scalars(stmt).all()
    return jobs


def get_numeros_reference(s: Session, limit: int = 20):
    """ Get the latest tags"""
    stmt = select(Mouvement.no_de_reference, func.max(Mouvement.date)).where(
        Mouvement.no_de_reference != None).group_by(
        Mouvement.no_de_reference).order_by(func.max(Mouvement.date).desc()).limit(limit)
    return s.scalars(stmt).all()


def save_map_categorie(e: Engine, value: MapCategorie, check_duplicates: bool):
    with Session(e) as session:
        existing_keys = session.scalars(select(MapCategorie.keyword)).all()
        # Check that the item to save is not already existing
        if check_duplicates and (
                any([value.keyword in k for k in existing_keys]) or any([k in value.keyword for k in existing_keys])):
            raise KeyError(f"the keyword {value.keyword} can already be found in the existing maps")

        session.add(value)
        session.commit()


def find_active_maps(s: Session, keyword: str) -> list[MapCategorie]:
    """ Checks if there are any conflicting maps """
    existing_keys = s.scalars(select(MapCategorie).where(not_(MapCategorie.inactif))).all()

    result = [mc for mc in existing_keys if (mc.keyword in keyword) or (keyword in mc.keyword)]

    return result


def identify_gaps(s: Session, value: MapCategorie):
    stmt = select(Mouvement).where(Mouvement.date_out_of_bound == False).where(
        Mouvement.description.contains(value.keyword))
    stmt = stmt.where(or_(Mouvement.employeur != value.employeur, Mouvement.declarant != value.declarant,
                          Mouvement.organisme != value.organisme))

    df = pd.read_sql(stmt, s.connection())
    return df


class JobMapper:
    def __init__(self):
        self.__jobs__ = []
        self.__job_dict__ = {}

    def set_jobs(self, jobs: Iterable):
        self.__jobs__ = jobs
        j: Job
        self.__job_dict__ = {
            f"Job {j.job_id} '{j.job_key}' on {j.job_timestamp.strftime('%d-%m-%y %H:%M:%S')}": j.job_id for j in jobs}

    def get_job_id(self, description: str) -> int:
        if description in self.__job_dict__:
            return self.__job_dict__[description]
        else:
            return 0

    def get_job_descriptions(self) -> Iterable:
        return list(self.__job_dict__.keys())


def makesession() -> Session:
    return Session(engines.get_pgfin_engine())


def split_value(value: float, no_periods: int, rounding: int) -> Iterable:
    """ returns a correct split with rounded values"""
    result = [round(value / no_periods, rounding)] * (no_periods - 1)
    quotient = sum(result)
    result += [round(value - quotient, rounding)]
    return result
