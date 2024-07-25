from bigsdb.script import Script

DATABASE = 'pubmlst_neisseria_isolates'

def main():
    script = Script(
        database = DATABASE,
    )
    fields = script.parser.get_field_list();
    print('Fields:')
    print(fields)
    print('\nExample query results:')
    print(script.datastore.run_query('SELECT id FROM isolates WHERE id<?', 10, {'fetch':'col_arrayref'}))
    print(script.datastore.run_query('SELECT id,country,year FROM isolates WHERE id=?', 5, {'fetch':'all_arrayref','slice':{}}))

if __name__ == "__main__":
    main()
