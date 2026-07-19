
## List of remaining user stories
### Bug : la date de remboursement est mise à zéro
lorsque je fais un mass update dans le formulaire Main

### Catégorie :ajouter un flag de désactivation
- rajouter le champ dans la base

###

### Initialiser des provisions annuelles
- changer le form crud_provisions
Il ne faut pas quitter lorsque je fais un update. 
- 

#### Contexte de départ
J'arrive en fin d'année. J'ai besoin d'initialiser, pour l'année suivante, les provisions. 

#### Déroulé
Le plus simple est de partir de l'année en cours. J'ai une vue d'ensemble des dépenses et recettes réalisées, par catégorie.
A chaque fois je vois ce qui a été réellement dépensé ou récupéré, avec la provision restante. 

Pour chaque catégorie, je sais si j'ai déjà créé des provisions pour l'année suivante car je vois 
la somme de la provision (dépense ou recette). Un code couleur me dit si c'est créé ou pas. 

je ne vois que les catégories pérennes. Les catégories inutiles sont masquées. 

Je peux flagger les catégories inutiles ou qui ne sont plus actives. 

#### Prompt

Propose-moi une fonction permettant d'afficher une page Streamlit, "Budget Planning".
La page commence par un selectbox permettant de choisir l'année. Elle contient deux choix : l'année actuelle, et l'an prochain.
Par défaut, la valeur est réglée sur l'an prochain. 
Un autre paramètre de type booléen permet de choisir entre "Courant" ou "Economie". 
Sur la base de ces paramètre, la page appelle la fonction get_yearly_provision en initialisant une session. 
Le résultat de la fonction est affiché sous forme de dataframe. 
Lorsque les colonnes Dépense Provisionnée année A ou Recette Provisionnée année A contiennent une valeur supérieure à O, 
un code couleur ou un logo marquent le fait que l'action a été réalisée. 
Lorsque je sélectionne une ligne, j'ai deux boutons d'action qui apparaissent : "Budgétiser Dépense", "Budgétiser Recette"



### Créer des règles de salaires
Je me connecte à l'application. J'ouvre "Salary Monitor". 
Là, je peux créer une nouvelle règle. Lorsque je clique sur le formulaire. 
Je renseigne : 
- un pattern : expression regex qui va regarder l'ensemble des transactions
- un déclarant parmi une liste de déclarants identifiée
- un compte bancaire parmi la liste des comptes
Je clique sur valider, et la transaction est sauvegardée. 

Cela flagge la ligne en question avec un tag qui l'identifie comme un salaire, avec un déclarant. 


Attention : si il existe une règle précédemment créée avec le même pattern, et qui est active, ma règle
ne sera pas sauvegardée. 

### Désactiver une règle de salaire
Il est impossible de modifier une règle de salaire. Je ne peux que la désactiver.

### Tester la règle
J'ai ouvert le formulaire. Je sélectionne une règle. 
Je teste la règle. Cela me ramène toutes les transactions qui matchent avec la règle, 
triées par date descendante. 

### Appliquer les règles automatiquement
A l'ouverture de l'application, les règles sont appliquées. 
Pour chaque règle
- récupérer l'ensemble des jobs dont le timestamp d'exécution est supérieur au timestamp de la dernière exécution de la règle
- récupérer l'ensemble des transactions associées

## Done
### Désactiver en masse
Plutôt qu'une désactivation unitaire.

### Générer un plan de remboursement
Je choisis un compte qui représente le plan de remboursement (exemple : emprunt maison viroflay)
Je définis un montant du prêt (exemple : 100.000€)
Je fixe  un taux de remboursement (exemple : 4,5%)
Je définis une durée, en mois (exemple : 60)
Je définis un mois de départ (exemple : 1er avril 2025)
Je définis un jour de référence pour le paiement des mensualités (exemple : 10)

Je clique sur "Simuler". 

L'interface me calcule le montant de l'échéance, ainsi que les dix prochains remboursements de capital.

Si je suis satisfait, je clique sur "Sauvegarder"

A ce moment, l'application

- supprime l'ensemble des mensualités pour ce compte, à partir du mois sélectionné (en se basant sur la date)
- génère un ensemble de mensualités, à partir d'un dataframe contenant les remboursements
- les ajoute à la session
- affiche un message de statut : les imports ont été faits

### Déterminer la performance de mes algorithmes de reconnaissance
Lorsque j'arrive sur l'interface d'accueil.
Je sélectionne un compte bancaire : Crédit Agricole. 

Cela m'affiche les cinquante dernières transactions. 
Je voudrais qu'il scanne les transactions, et que dans une fenêtre il m'affiche les transactions inclassables;
Genre il me dit : sur 50 transactions, 25 n'ont pu être classés automatiquement (50%)
A partir de là je peux cliquer sur une transaction.
Cela met le texte de la transaction dans un text box. 
Je manipule le texte pour en faire un keyword.
Lorsque je suis satisfait, je clique sur "Sauvegarder".
Cela a pour effect de sauvegarder la paire (keyword, catégorie de la transaction sélectionnée)

### Affecter en masse les mois des provisions
Lorsque je sélectionne en masse, je peux mettre à jour le mois. 

### Répliquer systématiquement le déclarant
Lorsque je duplique une transaction, je dois pouvoir dupliquer le déclarant
### Nettoyage des termes inutiles
Je veux créer un code qui, quand je lui donne une liste de transactions (issues de l'ORM)
enlève du texte inutile, de type "Paiement par carte"

### Filtrer par job
Lorsque j'ouvre le formulaire principal, je vois un combobox avec les derniers jobs exécutés. Lorsque je clique sur un job, 
le formulaire filtre sur les transactions associées au job.

