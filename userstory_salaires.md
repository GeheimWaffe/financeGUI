# User story - Salaires

En tant qu'utilisateur de l'application, je souhaite voir une page me permettant de gérer mes salaires. 
La page commence par un selectbox affichant les différents déclarants, à partir du contenu de la table Declarant
de ma base de données. 
Ensuite elle se divise en deux sections. 
La section de gauche affiche la liste des salaires déjà saisis pour ce déclarant, correspondant à l'objet Salaire, sous forme de table. Cette table
affiche le mois du salaire, l'entreprise, ainsi que la somme des SalaireComponent, affiché en euros avec deux chiffres après la virgule. 
La section de droite se compose de deux tabs. 
Le tab 1, intitulé "Edition", affiche le détail des SalaireComponent pour le Salaire sélectionné par l'utilisateur
dans la liste des salaires. Elle permet d'éditer et de sauvegarder chaque SalaireComponent. 
Le tab 2, intitulé "Création", permet de créer un nouveau salaire
Il commence par un selectbox "SelectPrevious" contenant les différents mois des salaires déjà créés, intitulé "Copy From", d'un sélecteur de dates
permettant de choisir le mois du salaire ("MoisSelector"), et d'un textbox permettant de saisir l'entreprise ("EntrepriseSelector"), et d'un bouton "New".
Lorsque je clique sur New : il faut que MoisSelector et EntrepriseSelector soients saisis, sinon une erreur est renvoyée. 
Si c'est bien saisi, alors deux cas de figures :
soit SelectPrevious contient une valeur ; alors un dataframe editor est initialisé avec les différents postes du salaire
correspondant à SelectPrevious. Sinon, un dataframe editor est initialisé mais reste vide. 
Je peux alors saisir ligne à ligne les nouveaux SalaireComponent. 
Lorsque j'ai terminé, je peux cliquer sur "Sauvegarder". La page sauvegarde alors le nouveau salaire ainsi 
que ses SalaireComponent. Le formulaire m'affiche un message de succès et le nombre de lignes insérées en base. 

## Master data
Un bouton en forme de roue dentée en haut à droite de la page permet de configurer les master data. Lorsque j'appuie sur ce bouton, 
Je peux créer de nouveaux déclarants via des dataframes.
Je peux créer de nouveaux SalairesPostes via des dataframes. 
Lorsque je clique à nouveau sur la roue dentée, cela masque cette interface de création et revient à l'affichage normal.

## Clôture du formulaire. 
Un bouton "Fermer" permet de revenir à la page Main de mon application.

## Consignes
Crée tout cela pour que cela rentre dans un module python. Encapsule les méthodes interagissant avec la base de données dans des fonctions spécifiques.


