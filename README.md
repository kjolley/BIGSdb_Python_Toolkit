# BIGSdb_Python_Toolkit
Python libraries for interacting with local BIGSdb databases.

The modules included in this package enable scripts to be written in Python
that can query and update local BIGSdb databases using similar method calls as
used in the main [BIGSdb Perl](https://github.com/kjolley/BIGSdb) package.

A script object that is passed a database config name will automatically parse
the BIGSdb configuration and database configuration files, and set up the 
required database connections. Methods for querying databases are included in
the Datastore module. More methods will be added as required to replicate the
Perl BIGSdb libraries.

BIGSdb plugins can also now be written in Python so that additional analysis
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

You can also clone the git repository and install dependencies. You will need 
to clone the repository to access various scripts needed to enable plugins.

```
git clone https://github.com/kjolley/BIGSdb_Python_Toolkit.git
cd BIGSdb_Python_Toolkit
pip install -r requirements.txt
```

## Initiating plugins
BIGSdb needs to know about any plugins. In order to enable this, there is a
script called `create_plugin_list.py` found in the scripts directory. Run this
and save the output to a file called `python_plugins.json` and copy this to
/etc/bigsdb. This contains everything that BIGSdb needs to know about each 
plugin including descriptive attributes, Javascript libraries needed and any 
inline Javascript that should be added to the page.

```
python create_plugin_list.py --plugin_dir ../sample_plugins/
```

BIGSdb will call a script called `plugin_runner.py` and it needs to know the
location of this as well as the location of the Python plugins. Set the 
`python_plugin_runner_path` and `python_plugin_dir` in `bigsdb.conf`, e.g.

```
python_plugin_runner_path=/home/bigsdb/BIGSdb_Python_Toolkit/.venv/bin/python /home/bigsdb/BIGSdb_Python_Toolkit/plugin_runner.py
python_plugin_dir=/home/bigsdb/BIGSdb_Python_Toolkit/sample_plugins
```

## Tests
Many of the tests involve creating and dropping a test database. The user
running the tests must have permissions set to enable this. They will also
need to be able to modify tables which may be owned by the apache user. 
If running as the bigsdb user, run the following to set these permissions:

```
psql
ALTER USER bigsdb createdb;
ALTER USER bigsdb createrole;
GRANT postgres TO bigsdb;
GRANT apache TO bigsdb;
```

Tests can be run from the tests/ directory with the following:

```
python -m unittest discover
```