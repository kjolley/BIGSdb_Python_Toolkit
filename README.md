# BIGSdb_Python_Toolkit
Python libraries for interacting with BIGSdb databases.

The modules included in this package enable scripts to be written in Python
that can query and update BIGSdb databases using similar method calls as used
in the main [BIGSdb Perl](https://github.com/kjolley/BIGSdb) package.

A script object that is passed a database config name will automatically parse
the BIGSdb configuration and database configuration files, and set up the 
required database connections. Methods for querying databases are included in
the Datastore module. More methods will be added as required.

BIGSdb plugins can also now be written in Python so that additonal analysis
functionality can be added to the platform without having to write Perl code.

# Installation
It is recommended that you install this in a virtual environment, e.g.

```
python -m venv .venv
source .venv/bin/activate
```

Install with pip:

```
pip install bigsdb
```

You can de-activate the virtual environment with:

```
deactivate
```

You can also clone the git repo and install dependencies:

```
git clone https://github.com/kjolley/BIGSdb_Python_Toolkit.git
cd BIGSdb_Python_Toolkit
pip install -r requirements.txt
```

## Tests
Tests can be run from the tests/ directory with the following. These currently
only cover parsing of config files and utility functions:

```
python -m unittest discover
```