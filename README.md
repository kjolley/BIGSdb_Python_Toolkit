# BIGSdb_Python_Toolkit
Python libraries for interacting with BIGSdb databases.

The modules included in this package enable scripts to be written in Python
that can query and update BIGSdb databases using similar method calls as used
in the main [BIGSdb Perl](https://github.com/kjolley/BIGSdb) package.

A script object that is passed a database config name will automatically parse
the BIGSdb configuration and database configuration files, and set up the 
required database connections. Methods for querying databases are included in
the Datastore module.

BIGSdb plugins can also now be written in Python so that additonal analysis
functionality can be added to the platform without having to write Perl code.

## Tests
Tests can be run from the tests/ directory with the following:

```
python -m unittest discover
```