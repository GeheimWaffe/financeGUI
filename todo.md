## List of remaining user stories

### Déterminer la performance de mes algorithmes de reconnaissance - DONE
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

### Désactiver en masse
Plutôt qu'une désactivation unitaire

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



