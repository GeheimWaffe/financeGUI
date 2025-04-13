import datetime as dt
from datetime import datetime, date, timedelta
from typing import List

import pandas as pd
from sqlalchemy import Boolean, ForeignKey, MetaData, Table, Column, select, or_, and_, Engine, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, Session
from sqlalchemy.orm import mapped_column
from sqlalchemy.types import String, Integer, Date, Numeric


class Base(DeclarativeBase):
    pass


class Compte(Base):
    __tablename__ = 'compte_types'

    compte: Mapped[str] = mapped_column('compte', String, primary_key=True, nullable=False)
    compte_minuscule: Mapped[str] = mapped_column('Compte Minuscule', String)
    compte_type: Mapped[str] = mapped_column('compte_type', String, nullable=False)
    compte_actif: Mapped[bool] = mapped_column('compte_actif', Boolean, nullable=True)

    mouvements: Mapped[List["Mouvement"]] = relationship(back_populates="compte_object", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Compte Nom={self.compte!r}, Minuscule={self.compte_minuscule!r}, Type={self.compte_type!r}"


class Categorie(Base):
    __tablename__ = 'categories_groupes'

    categorie: Mapped[str] = mapped_column('catégorie', String, primary_key=True)
    categorie_groupe: Mapped[str] = mapped_column('catégorie_groupe', String)
    categorie_order: Mapped[int] = mapped_column('catégorie_order', Integer)
    provision_type: Mapped[str] = mapped_column('provision_type', String)

    mouvements: Mapped[List["Mouvement"]] = relationship(back_populates="categorie_object",
                                                         cascade="all, delete-orphan")
    maps: Mapped[List["MapCategorie"]] = relationship(back_populates="categorie_object", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Catégorie Nom={self.categorie.ljust(30, ' ')}, Groupe={self.categorie_groupe!r}, Ordre={self.categorie_order!r}, Type Provision={self.provision_type!r}"


class Job(Base):
    __tablename__ = 'jobs'

    type_salary = 'salaire'
    type_import = 'import'
    type_split = 'split'
    type_shut = 'shutdown'
    type_provision = 'provision'

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_key: Mapped[str]
    job_timestamp: Mapped[datetime]
    job_mois: Mapped[datetime] = mapped_column(Date, nullable=True)

    mouvements: Mapped[List["Mouvement"]] = relationship(back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f'Job of type {self.job_key}, id {self.job_id!r}, timestamp {self.job_timestamp!r}'


class Mouvement(Base):
    __tablename__ = 'comptes'

    index: Mapped[int] = mapped_column('index', Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column('Date', Date, nullable=True)
    description: Mapped[str] = mapped_column('Description', String)
    recette: Mapped[float] = mapped_column('Recette', Numeric, nullable=True)
    depense: Mapped[float] = mapped_column('Dépense', Numeric, nullable=True)
    compte: Mapped[str] = mapped_column('Compte', ForeignKey('compte_types.compte'), nullable=True)
    categorie: Mapped[str] = mapped_column('Catégorie', ForeignKey('categories_groupes.catégorie'))
    economie: Mapped[str] = mapped_column('Economie', String, nullable=True, default='false')
    regle: Mapped[str] = mapped_column('Réglé', String, nullable=True, default='false')
    mois: Mapped[datetime] = mapped_column('Mois', Date, comment='Le mois auquel se réfère la transaction')
    date_insertion: Mapped[datetime] = mapped_column("Date insertion", Date)
    provision_payer: Mapped[float] = mapped_column('Provision à payer', Numeric, nullable=True)
    provision_recuperer: Mapped[float] = mapped_column('Provision à récupérer', Numeric, nullable=True)
    date_remboursement: Mapped[datetime] = mapped_column('Date remboursement', Date, nullable=True)
    organisme: Mapped[str] = mapped_column('Organisme', String, nullable=True)
    date_out_of_bound: Mapped[bool] = mapped_column('Date Out of Bound', Boolean, nullable=True, default=False)
    taux_remboursement: Mapped[float] = mapped_column('Taux remboursement', Numeric, nullable=True)
    fait_marquant: Mapped[str] = mapped_column('Fait marquant', String, nullable=True)
    no: Mapped[int] = mapped_column('No', Integer)
    no_de_reference: Mapped[str] = mapped_column('Numéro de référence', String, nullable=True)
    index_parent: Mapped[int] = mapped_column('index parent', Integer, nullable=True, comment='Parent transaction')
    depense_initiale: Mapped[float] = mapped_column('Dépense initiale', Numeric, nullable=True,
                                                    comment="La dépense d'origine")
    recette_initiale: Mapped[float] = mapped_column('Recette initiale', Numeric, nullable=True,
                                                    comment="La recette d'origine")
    label_utilisateur: Mapped[str] = mapped_column('Label utilisateur', String, nullable=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.job_id'))
    declarant: Mapped[str] = mapped_column('déclarant', String, nullable=True,
                                           comment="Désigne le déclarant pour un contexte d'impôts")

    compte_object: Mapped[Compte] = relationship(back_populates="mouvements")
    categorie_object: Mapped[Categorie] = relationship(back_populates="mouvements")
    job: Mapped[Job] = relationship(back_populates="mouvements")

    def __repr__(self):
        if self.compte == None:
            typ = 'Provision'
        elif self.categorie == None:
            typ = 'Virement'
        else:
            typ = 'Transaction'
        solde = self.recette if self.recette != None else 0
        solde = solde - self.depense if self.depense != None else solde

        return f'{typ} {self.description!r}, Compte : {self.compte}, Catégorie : {self.categorie}, Solde : {solde}, Provisions : {self.provision_recuperer}'

    def get_solde(self) -> float:
        result = self.recette if self.recette else 0
        result -= self.depense if self.depense else 0
        return float(result)


class MapCategorie(Base):
    __tablename__ = 'map_categories'

    keyword: Mapped[str] = mapped_column('Keyword', String, primary_key=True,
                                         comment="Le mot-clé à chercher dans la transaction")
    categorie: Mapped[str] = mapped_column('Catégorie', ForeignKey('categories_groupes.catégorie'),
                                           comment="La catégorie sur laquelle on va mapper la transaction")

    categorie_object: Mapped[Categorie] = relationship(back_populates='maps')

    def __repr__(self):
        return f'Map {self.keyword} to {self.categorie}'


class Classifier(Base):
    __tablename__ = 'classifiers'

    patterns: Mapped[str] = mapped_column('patterns', String, primary_key=True, comment='Classificateur')
    classes: Mapped[str] = mapped_column('classes', String, comment='Le groupe sur lequel agréger')

    def __repr__(self):
        return f'Classificateur: {self.patterns} pour groupe {self.classes}'


class MapOrganisme(Base):
    __tablename__ = 'map_organismes'

    keyword: Mapped[str] = mapped_column('Keyword', String, primary_key=True,
                                         comment="Le mot-clé à chercher dans la transaction")
    organisme: Mapped[str] = mapped_column('Organisme', String,
                                           comment="Organisme qui fournit une prestation de remboursement médical")

    def __repr__(self):
        return f'Map Organisme : keyword {self.keyword} to {self.organisme}'


class Salaire(Base):
    __tablename__ = 'salaires'

    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    categorie: Mapped[str] = mapped_column(String)
    poste: Mapped[str] = mapped_column(String)
    mois: Mapped[datetime] = mapped_column(Date)
    valeur: Mapped[str] = mapped_column(String, nullable=True)
    valeur_numerique: Mapped[datetime] = mapped_column('Valeur Numérique', Numeric, nullable=True)


def get_comptes(s: Session):
    """ Returns a list of accounts """
    return s.scalars(select(Compte).order_by(Compte.compte)).all()


def get_categories(s: Session):
    """ Returns a list of categories"""
    return s.scalars(select(Categorie).order_by(Categorie.categorie)).all()


def get_events(s: Session, category: str = None):
    """ returns a tuple of headers, data, for use in a dataframe"""
    result = s.execute(select(Mouvement.date_remboursement, Mouvement.label_utilisateur,
                              func.sum(Mouvement.depense).label("Dépense"),
                              func.sum(Mouvement.recette).label("Recette")).where(
        and_(Mouvement.date_remboursement != None, Mouvement.categorie == category,
             Mouvement.date_out_of_bound == False)).group_by(
        Mouvement.date_remboursement, Mouvement.label_utilisateur).order_by(
        Mouvement.date_remboursement.desc()).limit(50)).all()
    headers = ("Date Evénement", "Libellé", "Dépense", "Recette")
    return headers, result


def get_provisions_for_month(e: Engine, month: date, is_courant: bool = True):
    """ Returns all the aggregated provisions for a specific month"""
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
                      provisions.c['Dépense Economisée Provisionnée restante']).where(
            provisions.c['Mois'] == month).order_by(
            provisions.c['Catégorie Groupe'], provisions.c['Catégorie'])
    else:
        stmt = select(provisions.c['Catégorie Groupe'], provisions.c['Catégorie'], provisions.c['Recette Courante'],
                      provisions.c['Recette Courante Provisionnée'],
                      provisions.c['Recette Courante Provisionnée restante'],
                      provisions.c['Dépense Courante'], provisions.c['Dépense Courante Provisionnée'],
                      provisions.c['Dépense Courante Provisionnée non épuisée']).where(
            provisions.c['Mois'] == month).order_by(
            provisions.c['Catégorie Groupe'], provisions.c['Catégorie'])

    with Session(e) as session:
        result = session.execute(stmt).all()

    headers = ('Catégorie Groupe', 'Catégorie', 'Recette', 'Recette Provisionnée', 'Recette Reste', 'Dépense',
               'Dépense Provisionnée',
               'Dépense Reste')

    return headers, result


# définir une fonction de classification
def classify(value: str, classification_matrix):
    for pattern, result in classification_matrix:
        if pattern in value:
            return result
    return 'Common'


def get_categorized_provisions(e: Engine, category_filter: str, month: date, economy_mode: bool) -> pd.DataFrame:
    """ This function calculates, for a given category, the total expenses and recipes, comparing between actual and forecast"""
    stmt = select(Mouvement.description, Mouvement.depense, Mouvement.provision_payer, Mouvement.recette,
                  Mouvement.provision_recuperer).where(Mouvement.date_out_of_bound == False,
                                                       Mouvement.categorie == category_filter, Mouvement.mois == month)

    #                                                       Mouvement.economie == text('true') if economy_mode else text('false'))

    df_classes = get_groups(e)

    # reading the dataframe
    df = pd.read_sql(stmt, e)

    # Classifying
    df['Group'] = df['Description'].apply(classify, classification_matrix=df_classes.values)

    # Grouping
    df = df.drop('Description', axis=1).groupby(['Group'], as_index=False).sum()
    # returning the result
    return df


def get_groups(e: Engine) -> pd.DataFrame:
    # Selection of the patterns
    metadata_obj = MetaData()
    classes = Table('classifiers', metadata_obj,
                    Column('patterns', String),
                    Column('classes', String),
                    schema='public')
    df_classes = pd.read_sql(select(classes).order_by(classes.c['classes']), e)
    return df_classes


def get_type_comptes(s: Session) -> []:
    """ returns the various compte types"""
    stmt = select(Compte.compte_type.distinct())
    result = s.scalars(stmt).all()
    return result


def get_soldes(s: Session, type_compte: str):
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

    result = s.execute(select(soldes.c["Compte"], soldes.c["Date"], soldes.c["Solde Compte Actuel"]).where(
        soldes.c['Type Compte'] == type_compte)).all()

    return result


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
        result = s.execute(select(salaires))
        return [{c.key: r[i] for i, c in enumerate(salaires.columns)} for r in result]
    else:
        result = s.execute(select(salaires).where(salaires.c['mois'] == mois)).first()
        try:
            return {c.key: result[i] for i, c in enumerate(salaires.columns)}
        except IndexError:
            raise IndexError(f'could not find a salary for month : {mois}')


def get_max_number(s: Session) -> int:
    result = s.scalar(select(Mouvement.no).order_by(Mouvement.no.desc()))
    return int(result)


def get_salary_transaction(s: Session, amount: float, mois: date) -> Mouvement:
    salaire_transaction = s.scalar(
        select(Mouvement).where(and_(or_(Mouvement.recette == amount, Mouvement.recette_initiale == amount)),
                                (Mouvement.mois == mois)))

    # and (Mouvement.mois == mois)
    return salaire_transaction


def get_transaction(session: Session, index: int) -> Mouvement:
    return session.scalar(select(Mouvement).where(Mouvement.index == index))


def deactivate_transaction(e: Engine, index: int):
    with Session(e) as session:
        mvt = session.scalar(select(Mouvement).where(Mouvement.index == index))
        if not mvt is None:
            mvt.date_out_of_bound = True
            session.commit()


def update_transaction_category(e: Engine, index: int, cat: str, lab: str, mois: date):
    with Session(e) as session:
        mvt = session.scalar(select(Mouvement).where(Mouvement.index == index))
        if not mvt is None:
            mvt.categorie = cat
            mvt.label_utilisateur = lab
            mvt.mois = mois
            session.commit()


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


def apply_mass_update(e: Engine, indexes: [], template: Mouvement):
    """ Applies a mass update"""
    with Session(e) as session:
        # retrieve the movement
        for i in indexes:
            mvt = session.get(Mouvement, ident=i)
            if not mvt is None:
                mvt.label_utilisateur = template.label_utilisateur
                mvt.no_de_reference = template.no_de_reference
                mvt.date_remboursement = template.date_remboursement
                if not template.description is None:
                    mvt.description = template.description
                if not template.categorie is None:
                    mvt.categorie = template.categorie

        # save
        session.commit()
    # end


def import_transaction(e: Engine, mvt: Mouvement):
    """ Generates a transaction"""
    print(f'Importing transaction {mvt}')
    with Session(e) as session:
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

        session.flush()
        session.commit()


def create_transaction(e: Engine, transaction_date: date, description: str, compte: str, category: str,
                       depense: float, recette: float, transaction_month: date):
    """ generate a set of provision for a given year"""
    print(f'Generating a transaction for {category} with description {description}')

    with Session(e) as session:
        # retrieve the last valid number
        max_number = get_max_number(session)
        # create a job
        job = Job(job_key=Job.type_import, job_timestamp=datetime.now())
        # generate a set of provisions
        mvt = Mouvement(date=transaction_date,
                        description=description,
                        compte=compte,
                        categorie=category,
                        mois=transaction_month,
                        date_insertion=date.today(),
                        depense=depense,
                        recette=recette,
                        no=max_number + 1,
                        job=job
                        )
        session.add(mvt)
        print(f'Transaction generated : {mvt}')

        session.flush()
        session.commit()


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


def simple_split(e: Engine, index: int, values: list, months: list):
    """ This is also a splitting function, but which assumes the values and months are already defined

    :param e: the engine
    :param index: index of the transaction to split
    :param values: list of split values
    :param months: list of split months"""

    with Session(e) as session:
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
                              job=job
                              )
                )

            # Update the original transaction
            session.add(mvt)

            # end
            session.flush()
            session.commit()


def split_mouvement(e: Engine, index: int, mode: str = 'year', periods: int = 12, rounding: int = 2):
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


def create_salaries(e: Engine, mois: dt.date, declarant: str, simulate: bool):
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
                                       categorie=categorie_salaire,
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
            mvt.declarant = declarant
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


def get_balances(e: Engine, first_month: date) -> pd.DataFrame:
    """ Calculates the balances per month"""
    stmt = select(Mouvement.mois, func.sum(Mouvement.depense).label('Dépense'),
                  func.sum(Mouvement.recette).label('Recette'),
                  (func.sum(Mouvement.recette) - func.sum(Mouvement.depense)).label("Solde")).where(
        Mouvement.categorie == '',
        Mouvement.mois >= first_month,
        Mouvement.date_out_of_bound == False).group_by(
        Mouvement.mois)

    df = pd.read_sql(stmt, e)

    return df
