import datetime as dt
from datetime import datetime, date
from typing import List

from sqlalchemy import Boolean, ForeignKey, Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column, validates
from sqlalchemy.types import String, Integer, Date, Numeric, Float


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


class ViewBilansAgregation(Base):
    __tablename__ = 'view_bilans_agregation'
    __table_args__ = {'schema': 'dbview_schema'}

    # --- Métadonnées et Clés de regroupement ---
    # Clé primaire composite nécessaire pour que l'ORM mappe une vue SQL
    Catégorie: Mapped[str] = mapped_column(String, primary_key=True)
    Mois: Mapped[Date] = mapped_column(Date, primary_key=True)  # Type date d'après la capture

    # Autres métadonnées de regroupement
    Catégorie_Groupe: Mapped[str] = mapped_column("Catégorie Groupe", String)
    Catégorie_Order: Mapped[int] = mapped_column("Catégorie Order", Integer)  # int4 d'après la capture
    Type_Provision: Mapped[str] = mapped_column("Type Provision", String)
    Mois_Year: Mapped[float] = mapped_column("Mois Year", Float)  # float8 d'après la capture

    # --- Données du Mode "Courant" (float8) ---
    Recette_Courante: Mapped[float] = mapped_column("Recette Courante", Float)
    Recette_Courante_Provisionnée: Mapped[float] = mapped_column("Recette Courante Provisionnée", Float)
    Recette_Courante_Provisionnée_restante: Mapped[float] = mapped_column("Recette Courante Provisionnée restante",
                                                                          Float)
    Dépense_Courante: Mapped[float] = mapped_column("Dépense Courante", Float)
    Dépense_Courante_Provisionnée: Mapped[float] = mapped_column("Dépense Courante Provisionnée", Float)
    Dépense_Courante_Provisionnée_non_épuisée: Mapped[float] = mapped_column(
        "Dépense Courante Provisionnée non épuisée", Float)

    # --- Données du Mode "Économisé" (float8) ---
    Recette_Economisee: Mapped[float] = mapped_column("Recette Economisée", Float)
    Recette_Economisée_Provisionnée: Mapped[float] = mapped_column("Recette Economisée Provisionnée", Float)
    Recette_Economisée_Provisionnée_restante: Mapped[float] = mapped_column("Recette Economisée Provisionnée restante",
                                                                            Float)
    Dépense_Economisee: Mapped[float] = mapped_column("Dépense Economisée", Float)
    Dépense_Economisée_Provisionnée: Mapped[float] = mapped_column("Dépense Economisée Provisionnée", Float)
    Dépense_Economisée_Provisionnée_restante: Mapped[float] = mapped_column("Dépense Economisée Provisionnée restante",
                                                                            Float)

    # --- Soldes et Totaux (float8) ---
    Solde_Courant_Provisionné: Mapped[float] = mapped_column("Solde Courant Provisionné", Float)
    Solde_Courant: Mapped[float] = mapped_column("Solde Courant", Float)
    Solde_Courant_plus_Provision: Mapped[float] = mapped_column("Solde Courant + Provision", Float)
    Solde_Total: Mapped[float] = mapped_column("Solde Total", Float)
    Solde_Total_plus_Provision: Mapped[float] = mapped_column("Solde Total + Provision", Float)

    def __repr__(self) -> str:
        return f"<ViewBilansAgregation {self.Catégorie} ({self.Mois})>"


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

from typing import Optional
from sqlalchemy import Integer, Float, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Impot(Base):
    __tablename__ = 'impots'  # Adapte le nom de la table si nécessaire

    # int4 / Identity Always / Not Null [v] -> Clé primaire
    id_impot: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # int4 / Not Null [v]
    annee: Mapped[int] = mapped_column(Integer, nullable=False)

    # float4 / Not Null [v]
    revenu_imposable_1: Mapped[float] = mapped_column(Float, nullable=False)
    revenu_imposable_2: Mapped[float] = mapped_column(Float, nullable=False)

    # float4 / Nullable [ ]
    impot_avant_reduction: Mapped[Optional[float]] = mapped_column(Float, nullable=True,
                                                                   comment="L'impôt avant réduction")
    dons: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    impot_proportionnel: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prelevement_forfaitaire: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    emploi_salarie: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tx_deduction_emploi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    csg: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Montant de la CSG déductible, en euros")

    # float4 / Nullable [ ] / Default: 0
    dons_deductible: Mapped[Optional[float]] = mapped_column(Float, nullable=True,
                                                             comment="% de réduction d'impôt applicable")
    retenue_source: Mapped[Optional[float]] = mapped_column(Float, nullable=True,
                                                            comment="Montant de l'impôt retenu à la source")
    acompte: Mapped[Optional[float]] = mapped_column(Float, nullable=True,
                                                     comment="Acompte prélevé sur le compte bancaire")
    avance: Mapped[Optional[float]] = mapped_column(Float, nullable=True,
                                                    comment="Avance perçue sur les réductions et crédits d'impôt")
    prelevements_sociaux: Mapped[Optional[float]] = mapped_column(Float, nullable=True,
                                                                  comment="Somme des prélèvements sociaux")

    # float4 / Nullable [ ] / Default: 0
    syndicat_deductible: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0, server_default="0",
                                                                 comment="Montant de la cotisation syndicale qui peut être déduit")

    def __repr__(self) -> str:
        return f"<Impot(id_impot={self.id_impot}, annee={self.annee})>"


from datetime import date
from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, String, Date, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Declarant(Base):
    """
    Modélise l'identité de la personne qui déclare ses revenus (ex: Conjoint A, Conjoint B).
    """
    __tablename__ = "declarant"

    id_declarant: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    declarant: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # Relations
    salaires: Mapped[List["SalaireNew"]] = relationship("SalaireNew", back_populates="declarant_rel")

    def __repr__(self) -> str:
        return f"<Declarant(id={self.id_declarant}, nom='{self.declarant}')>"


class SalaireNew(Base):
    """
    Représente l'entête d'une fiche de paie mensuelle pour un déclarant et une entreprise donnés.
    """
    __tablename__ = "salaire"

    id_salaire: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mois: Mapped[date] = mapped_column(Date, nullable=False)
    id_declarant: Mapped[int] = mapped_column(Integer, ForeignKey("declarant.id_declarant"), nullable=False)
    entreprise: Mapped[str] = mapped_column(String, nullable=False)

    # Relations
    declarant_rel: Mapped["Declarant"] = relationship("Declarant", back_populates="salaires")
    components: Mapped[List["SalaireComponents"]] = relationship("SalaireComponents", back_populates="salaire_rel",
                                                                 cascade="all, delete-orphan")

    def __repr__(self) -> str:
        # Formatage de la date en YYYY-MM si elle est présente
        mois_str = self.mois.strftime("%Y-%m") if isinstance(self.mois, date) else str(self.mois)
        return f"<Salaire(id={self.id_salaire}, mois={mois_str}, entreprise='{self.entreprise}')>"


class SalairePostes(Base):
    """
    Référentiel des types de lignes d'un bulletin de salaire (ex: Salaire de base, Primes, Tickets Resto).
    """
    __tablename__ = "salaire_postes"

    id_poste: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    poste: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    poste_groupe: Mapped[str] = mapped_column(String, nullable=False)

    # Relations
    components: Mapped[List["SalaireComponents"]] = relationship("SalaireComponents", back_populates="poste_rel")

    def __repr__(self) -> str:
        return f"<SalairePoste(id={self.id_poste}, poste='{self.poste}', groupe='{self.poste_groupe}')>"


class SalaireComponents(Base):
    """
    Table d'association (composants) qui stocke le montant (valeur) de chaque poste pour un salaire donné.
    """
    __tablename__ = "salaire_components"

    id_component: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_salaire: Mapped[int] = mapped_column(Integer, ForeignKey("salaire.id_salaire"), nullable=False)
    id_poste: Mapped[int] = mapped_column(Integer, ForeignKey("salaire_postes.id_poste"), nullable=False)
    valeur: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relations
    salaire_rel: Mapped["SalaireNew"] = relationship("SalaireNew", back_populates="components")
    poste_rel: Mapped["SalairePostes"] = relationship("SalairePostes", back_populates="components")

    def __repr__(self) -> str:
        return f"<SalaireComponent(id={self.id_component}, id_salaire={self.id_salaire}, id_poste={self.id_poste}, valeur={self.valeur})>"
