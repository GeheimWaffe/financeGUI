import datetime as dt
from datetime import datetime, date
from typing import List

from sqlalchemy import Boolean, ForeignKey, Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column, validates
from sqlalchemy.types import String, Integer, Date, Numeric


class Base(DeclarativeBase):
    pass


class Compte(Base):
    __tablename__ = 'compte_types'

    compte: Mapped[str] = mapped_column('compte', String, primary_key=True, nullable=False)
    compte_minuscule: Mapped[str] = mapped_column('Compte Minuscule', String)
    compte_type: Mapped[str] = mapped_column('compte_type', String, nullable=False)
    compte_actif: Mapped[bool] = mapped_column('compte_actif', Boolean, default=True, nullable=True)

    mouvements: Mapped[List["Mouvement"]] = relationship(back_populates="compte_object", cascade="all, delete-orphan")
    map_salaires: Mapped[List["MapSalaire"]] = relationship(back_populates="compte_object",
                                                            cascade="all, delete-orphan")

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
    employeur: Mapped[str] = mapped_column('employeur', String, nullable=True,
                                           comment="Désigne l'employeur et permet de déterminer les salaires")

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

    @validates('mois')
    def validate_mois(self, key, value):

        # Si c'est un objet datetime, on le convertit en date
        if isinstance(value, datetime):
            value = value.date()

        # On force le jour au 1er du mois
        if isinstance(value, date):
            value = value.replace(day=1)

        return value

    def get_solde(self) -> float:
        result = self.recette if self.recette else 0
        result -= self.depense if self.depense else 0
        return float(result)

    def get_inverted(self):
        result = Mouvement()
        result.date = self.date + dt.timedelta(days=2)
        result.description = self.description
        result.compte = self.compte
        result.categorie = self.categorie
        result.regle = self.regle
        result.mois = self.mois
        result.no = self.no
        result.label_utilisateur = self.label_utilisateur
        result.declarant = self.declarant
        # inverting the amounts
        if self.get_solde() > 0:
            result.depense = self.recette

        if self.get_solde() < 0:
            result.recette = self.depense

        return result


class MapCategorie(Base):
    __tablename__ = 'map_categories'

    keyword: Mapped[str] = mapped_column('Keyword', String, primary_key=True,
                                         comment="Le mot-clé à chercher dans la transaction")
    categorie: Mapped[str] = mapped_column('Catégorie', ForeignKey('categories_groupes.catégorie'),
                                           comment="La catégorie sur laquelle on va mapper la transaction")
    declarant: Mapped[str] = mapped_column('déclarant', String, nullable=True,
                                           comment='Le déclarant sur lequel mapper le mouvement')
    organisme: Mapped[str] = mapped_column('organisme', String, nullable=True,
                                           comment="L'oragnisme sur lequel mapper le mouvement")
    monthshift: Mapped[str] = mapped_column('monthshift', Integer, nullable=True,
                                            comment='Un entier positif ou négatif pour décaler le mois de la transaction')
    inactif: Mapped[bool] = mapped_column('inactif', Boolean, default=False,
                                          comment='Indique si le mapping a été inactivé')
    employeur: Mapped[str] = mapped_column('employeur', String, nullable=True,
                                           comment="Permet de rattacher à un employeur et d'identifier la ligne comme un salaire")

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


class MapSalaire(Base):
    __tablename__ = 'map_salaires'

    map_salaire_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern: Mapped[str] = mapped_column(String, unique=True,
                                         comment='Pattern de recherche dans les transactions')
    declarant: Mapped[str] = mapped_column(String,
                                           comment='Déclarant associé à la règle')
    compte: Mapped[str] = mapped_column(String, ForeignKey('compte_types.compte'),
                                        comment='Compte sur lequel rechercher')
    active: Mapped[bool] = mapped_column(Boolean, default=True,
                                         comment='Indicates if the rule is active')
    last_job_id: Mapped[int] = mapped_column(Integer, nullable=True,
                                             comment='The last id of the scanned jobs')

    compte_object: Mapped[Compte] = relationship(back_populates="map_salaires")


class LabelPrettifier:
    __replacements__ = {}

    def __init__(self, e: Engine):
        if e is None:
            self.__replacements__ = {'Paiement Par Carte X5799 ': '',
                                     'Virement En Votre Faveur': '',
                                     'Prelevement ': '',
                                     'Virement Emis Web ': ''}
        else:
            pass

    def clean_label(self, label: str) -> str:
        result = label
        for k, v in self.__replacements__.items():
            result = result.replace(k, v)
        # end
        return result

# définir une fonction de classification
