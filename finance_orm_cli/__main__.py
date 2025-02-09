from finance_orm_cli.masterdata import comptes, categories, mouvements, database

print('Welcome to the overall finance CLI interface !')
print('1 : Comptes')
print('2 : Catégories')
print('3 : Mouvements')
print('4 : Database')
choice = input('What do you want ?')
if choice == '1':
    comptes()
if choice == '2':
    categories()
if choice == '3':
    mouvements()
if choice == '4':
    database()
