import datetime as dt
from engines import get_pgfin_engine, get_sqlite_engine
from datamodel_finance_pg import Compte, Categorie, Mouvement, Base, MapOrganisme, Job, Salaire, get_salaries, \
    get_max_number, get_salary_transaction, get_remaining_provisioned_expenses, close_provision
from sqlalchemy import select

# create the engine
e = get_pgfin_engine()

# create the session
from sqlalchemy.orm import Session


def add_months(current_date: dt.date, months_to_add: int) -> dt.date:
    return dt.date(current_date.year + (current_date.month + months_to_add - 1) // 12,
                   (current_date.month + months_to_add - 1) % 12 + 1,
                   current_date.day)


def get_text_input(entity: str) -> str:
    cname = ''
    while not (1 <= len(cname) <= 50):
        cname = input(f'Enter an {entity} label (between 1 and 50 characters): ')

    return cname


def get_int_input(entity: str) -> int:
    textinput = input(f'Enter a value for {entity} : ')
    try:
        result = int(textinput)
    except TypeError:
        print('the value was not an integer')
        result = 0

    return result


def get_list_input(listing: []) -> str:
    print('Type de comptes possibles :')
    for i, l in enumerate(listing):
        print(' - '.join([str(i), l]))
    choice = input('Quel n° choisissez-vous ? : ')
    return listing[int(choice)]


def comptes():
    print('Welcome to the Comptes interface ! ')
    stay = True
    session = Session(e, autoflush=True)
    type_comptes = session.scalars(select(Compte.compte_type).distinct()).all()

    while stay:
        print('1 Lister les comptes')
        print('2 Ajouter un nouveau compte')
        print('3 Supprimer un compte')
        choice = input('Que voulez-vous faire ? (quit pour quitter) : ')
        if choice == 'quit':
            stay = False
        if choice == '1':
            listcomptes = session.scalars(select(Compte).order_by(Compte.compte))
            for c in listcomptes:
                print(c)
        if choice == '2':
            cname = get_text_input('compte')
            ctype = get_list_input(type_comptes)
            c = Compte(compte=cname, compte_minuscule=cname.lower(), compte_type=ctype)
            session.add(c)
            session.commit()
        if choice == '3':
            cname = get_text_input('')
            to_delete = session.scalars(select(Compte).where(Compte.compte == cname)).first()
            if to_delete is None:
                print('No such account found')
            else:
                session.delete(to_delete)
                session.commit()

    print('Closing the session and exiting. thank you !')
    session.close()


def categories():
    print('Welcome to the Categories interface ! ')
    stay = True
    session = Session(e, autoflush=True)
    groupe = session.scalars(select(Categorie.categorie_groupe).distinct()).all()
    types = session.scalars(select(Categorie.provision_type).distinct()).all()

    while stay:
        print('1 Lister les catégories')
        print('2 Ajouter une nouvelle catégorie')
        print('3 Supprimer une catégorie')
        choice = input('Que voulez-vous faire ? (quit pour quitter) : ')
        if choice == 'quit':
            stay = False
        if choice == '1':
            cats = session.scalars(select(Categorie).order_by(Categorie.categorie_groupe, Categorie.categorie))
            for c in cats:
                print(c)
        if choice == '2':
            cname = get_text_input('catégorie')
            cgroupe = get_list_input(groupe)
            cordre = int(cgroupe[:2])
            ctype = get_list_input(types)
            c = Categorie(categorie=cname, categorie_groupe=cgroupe, categorie_order=cordre, provision_type=ctype)
            session.add(c)
            session.commit()
        if choice == '3':
            cname = get_text_input('catégorie')
            to_delete = session.scalars(select(Categorie).where(Categorie.categorie == cname)).first()
            if to_delete is None:
                print('No such catégorie found')
            else:
                session.delete(to_delete)
                session.commit()

    print('Closing the session and exiting. thank you !')
    session.close()


def mouvements():
    print('Welcome to the Mouvements interface ! ')
    stay = True
    with  Session(e, autoflush=True) as session:
        categories = session.scalars(select(Categorie.categorie)).all()

    while stay:
        print('1 Split Yearly')
        print('2 Split Custom')
        print('3 Reverse split')
        print('4 Salary Import')
        print('5 Close Provision')
        print('6 Generate Provision')
        choice = input('Que voulez-vous faire ? (quit pour quitter) : ')
        if choice == 'quit':
            stay = False
        if choice == '1':
            id_mouvement = get_int_input('transaction')
            split_mouvement(id_mouvement)
            print('transaction splitted')
        if choice == '2':
            id_mouvement = get_int_input('transaction')
            no_periods = get_int_input('number of splitting periods')
            split_mouvement(id_mouvement, mode='custom', periods=no_periods)
            print('transaction splitted')
        if choice == '4':
            # récupérer la liste des derniers salaires
            listmois = get_last_salary_months()
            mois = dt.date.fromisoformat(get_list_input([m.strftime('%Y-%m-%d') for m in listmois]))
            create_salaries(mois)
        if choice == '5':
            shutdown_category()
        if choice == '6':
            year = get_int_input('provision year')
            cat = ''
            while cat != 'quit':
                print('choisissez une catégorie (quit pour quitter) : ')
                cat = get_list_input(categories)
                description = get_text_input('Provision description')
                dep = get_int_input('Provision à payer')
                rec = get_int_input('Provision à récupérer')
                generate_provision(cat, year, description, dep, rec)

    print('Closing the session and exiting. Thank you !')


def split_mouvement(index: int, mode: str = 'year', periods: int = 12, rounding: int = 2):
    """ The function splits a row in the database
    It has two modes :
    - year : spreads over a calendar year
    - custom : spreads over a custom number of periods (by default : 12)
    """
    with Session(e) as session:
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

            deps = [split_dep] * 11 + [rest_dep]
            recs = [split_rec] * 11 + [rest_rec]

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
                              job=job
                              )
                )

            # Update the original transaction
            session.add(mvt)

            # end
            session.flush()
            session.commit()


def generate_provision(category: str, year: int, description: str, depense: float, recette: float):
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


def shutdown_category():
    """ This function takes a category, a month.
     It calculates the remaining amount
     and create a corresponding provision, negative or positive."""
    with Session(e) as session:
        # first step is to calculate the remaining expense
        results = get_remaining_provisioned_expenses(session)
        # ask the user
        rdct = {}
        for i, r in enumerate(results):
            print(f'{i} : {r[0]} {r[1]}, remaining : {r[2]}')
            rdct[i] = [r[0], r[1], r[2]]
        selection = int(input('What do you want to close ?'))

        # we assume a row has been selected.
        mois = rdct[selection][0]
        cat = rdct[selection][1]
        remain = rdct[selection][2]

        # we close the provision
        close_provision(session, mois, cat, remain)


def get_last_salary_months() -> list:
    with Session(e) as session:
        salary_months = session.scalars(select(Salaire.mois).where(Salaire.valeur_numerique.is_not(None)).order_by(
            Salaire.mois.desc()).distinct()).fetchmany(5)
        return [salary_months[i] for i in range(5)]


def create_salaries(mois: dt.date):
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
        print(f'trying to find a transaction for month {mois} and amount : {salaire_infos["total"]}')
        salaire_transaction = get_salary_transaction(session, salaire_infos['total'], mois)

        if salaire_transaction == None:
            # no salaire found. Proceed anyway
            parent_id = None
            date_salaire = mois - dt.timedelta(days=2)
            print('could not find a salary transaction')
        else:
            # salaire found. Do it.
            parent_id = salaire_transaction.index
            date_salaire = salaire_transaction.date
            print(f'salary transaction found : {salaire_transaction}')

        # Création de la session initiale
        previous_salaire_job = session.scalar(
            select(Job).where(Job.job_key == Job.type_salary and Job.job_mois == mois))

        # Create the job
        salaire_job = Job(job_key=Job.type_salary, job_mois=mois, job_timestamp=dt.datetime.now())
        session.add(salaire_job)
        print(f'Job created : {salaire_job}')

        # Create the transactions
        session.add(Mouvement(date=date_salaire,
                              description=f'Salaire net pour le mois {mois}',
                              recette=salaire_infos['salaire_net'],
                              depense=0,
                              compte=compte,
                              categorie=categorie_salaire,
                              mois=mois,
                              date_insertion=date_insertion,
                              no=maxnumber,
                              index_parent=None,
                              job=salaire_job
                              )
                    )

        session.add(Mouvement(date=date_salaire,
                              description=f'Impôt revenu sur le salaire du {mois}',
                              recette=0,
                              depense=-salaire_infos['impot_salaire'],
                              compte=compte,
                              categorie=categorie_impot,
                              mois=mois,
                              date_insertion=date_insertion,
                              no=maxnumber,
                              index_parent=parent_id,
                              job=salaire_job
                              )
                    )

        session.add(Mouvement(date=date_salaire,
                              description=f'AIL net pour le mois {mois}',
                              recette=salaire_infos['logement'],
                              depense=0,
                              compte=compte,
                              categorie=categorie_ail,
                              mois=mois,
                              date_insertion=date_insertion,
                              no=maxnumber,
                              index_parent=parent_id,
                              job=salaire_job
                              )
                    )

        if salaire_infos['autre'] > 0:
            session.add(Mouvement(date=date_salaire,
                                  description=f'Notes de frais pour le {mois}',
                                  recette=salaire_infos['autre'],
                                  depense=0,
                                  compte=compte,
                                  categorie=categorie_note_de_frais,
                                  mois=mois,
                                  date_insertion=date_insertion,
                                  no=maxnumber,
                                  index_parent=parent_id,
                                  job=salaire_job
                                  )
                        )

        if salaire_infos['prime_net'] > 0:
            session.add(Mouvement(date=date_salaire,
                                  description=f'Prime nette pour le mois {mois}',
                                  recette=salaire_infos['prime_net'],
                                  depense=0,
                                  compte=compte,
                                  categorie=categorie_salaire,
                                  mois=mois,
                                  economie='true',
                                  date_insertion=date_insertion,
                                  no=maxnumber,
                                  index_parent=parent_id,
                                  job=salaire_job
                                  )
                        )

            session.add(Mouvement(date=date_salaire,
                                  description=f'Impôt sur la prime pour le mois {mois}',
                                  recette=0,
                                  depense=-salaire_infos['impot_prime'],
                                  compte=compte,
                                  categorie=categorie_salaire,
                                  mois=mois,
                                  economie='true',
                                  date_insertion=date_insertion,
                                  no=maxnumber,
                                  index_parent=parent_id,
                                  job=salaire_job
                                  )
                        )

        # modify the original salary
        if salaire_transaction != None:
            salaire_transaction.recette_initiale = salaire_transaction.recette
            salaire_transaction.recette = 0
            session.add(salaire_transaction)
            print(f'Original transaction neutralized')

        # Closing the session and committing
        session.flush()
        session.commit()
        print(f'Salary import done')


def database():
    print('Welcome to the Database interface ! ')
    stay = True
    session = Session(e, autoflush=True)

    while stay:
        print('1 Backup')
        print('2 Schema update')
        choice = input('Que voulez-vous faire ? (quit pour quitter) : ')
        if choice == 'quit':
            stay = False
        if choice == '1':
            backup()
        if choice == '2':
            update_schema()

    print('Closing the session and exiting. Thank you !')
    session.close()


def backup():
    """ Backup the postgres database to a SQLite extract """
    # create a new name
    backupname = '_'.join(['finance_backup_', dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), '.sqlite'])
    # create a new engine
    backupengine = get_sqlite_engine(['FinanceBackups', backupname])

    # reflect the model
    Base.metadata.create_all(backupengine)

    # collect the data from the postgres
    with Session(e) as session:
        listcomptes = session.scalars(select(Compte)).all()
        listcategories = session.scalars(select(Categorie)).all()
        listmapo = session.scalars(select(MapOrganisme)).all()
        listjobs = session.scalars(select(Job)).all()
        mvts = session.scalars(select(Mouvement)).all()

    # Backup
    with Session(backupengine) as backup_session:
        for c in listcomptes:
            new_c = Compte(compte=c.compte, compte_type=c.compte_type, compte_minuscule=c.compte_minuscule)
            backup_session.add(new_c)

        for cat in listcategories:
            new_cat = Categorie(categorie=cat.categorie, categorie_groupe=cat.categorie_groupe,
                                categorie_order=cat.categorie_order, provision_type=cat.provision_type)
            backup_session.add(new_cat)

        for mo in listmapo:
            new_mo = MapOrganisme(keyword=mo.keyword, organisme=mo.organisme)
            backup_session.add(new_mo)

        for j in listjobs:
            new_job = Job(job_id=j.job_id, job_key=j.job_key, job_timestamp=j.job_timestamp, job_mois=j.job_mois)
            backup_session.add(new_job)

        for m in mvts:
            j = backup_session.get(Job, m.job_id)
            new_mvt = Mouvement(date=m.date,
                                description=m.description,
                                recette=m.recette,
                                depense=m.depense,
                                compte=m.compte,
                                categorie=m.categorie,
                                economie=m.economie,
                                regle=m.regle,
                                mois=m.mois,
                                date_insertion=m.date_insertion,
                                provision_payer=m.provision_payer,
                                provision_recuperer=m.provision_recuperer,
                                date_remboursement=m.date_remboursement,
                                organisme=m.organisme,
                                date_out_of_bound=m.date_out_of_bound,
                                taux_remboursement=m.taux_remboursement,
                                fait_marquant=m.fait_marquant,
                                no=m.no,
                                no_de_reference=m.no_de_reference,
                                index_parent=m.index_parent,
                                depense_initiale=m.depense_initiale,
                                recette_initiale=m.recette_initiale,
                                label_utilisateur=m.label_utilisateur,
                                job=j)
            backup_session.add(new_mvt)

        backup_session.flush()
        backup_session.commit()

    # End
    print(f'Backup done, database saved as : {backupname}')


def update_schema():
    Base.metadata.create_all(e)
    print("schema reflected")
