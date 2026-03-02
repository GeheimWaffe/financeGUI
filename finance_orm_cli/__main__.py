from finance_orm_cli.masterdata import comptes, categories, mouvements, database, list_mouvements

print('Welcome to the5 overall finance CLI interface !')
print('1 : Comptes')
print('2 : Catégories')
print('3 : Mouvements')
print('4 : Database')
print('5 : Mouvements')
choice = input('What do you want ?')
if choice == '1':
    comptes()
if choice == '2':
    categories()
if choice == '3':
    mouvements()
if choice == '4':
    database()
if choice == '5':
    list_mouvements()
