# Written by Keith Jolley
# Copyright (c) 2024, University of Oxford
# E-mail: keith.jolley@biology.ox.ac.uk
#
# This file is part of BIGSdb Python Toolkit.
#
# BIGSdb Python Toolkit is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BIGSdb Python Toolkit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BIGSdb Python Toolkit. If not,
# see <https://www.gnu.org/licenses/>.

import sys
import os
import pathlib
import unittest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bigsdb.base_application import BaseApplication
from bigsdb.data_connector import DataConnector
from bigsdb.constants import CONNECTION_DETAILS
from bigsdb.datastore import Datastore
from bigsdb.xml_parser import XMLParser

TEST_DATABASE = "bigsdb_test_isolates2"
HOST = "localhost"
PORT = 5432
USER = "bigsdb_tests"
PASSWORD = "test"


class TestIsolateDB(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestIsolateDB, self).__init__(*args, **kwargs)

    def test_get_eav_fieldnames(self):
        eav_fieldnames = self.datastore.get_eav_fieldnames()
        self.assertEqual(len(eav_fieldnames), 4)
        self.assertTrue("Bexsero_reactivity" in eav_fieldnames)

    @classmethod
    def setUpClass(cls):
        # Setup test isolate database

        cls.con = psycopg2.connect(dbname="postgres")
        cls.con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = cls.con.cursor()
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DATABASE}")
        cur.execute(f"DROP USER IF EXISTS {USER}")
        cur.execute(f"CREATE USER {USER}")
        cur.execute(f"ALTER USER {USER} WITH PASSWORD '{PASSWORD}'")

        cur.execute(f"CREATE DATABASE {TEST_DATABASE}")
        cls.con.commit()
        cls.con.close()
        cls.con = psycopg2.connect(dbname=TEST_DATABASE)
        cur = cls.con.cursor()
        dir = pathlib.Path(__file__).parent.resolve()
        with open(f"{dir}/databases/bigsdb_test_isolates.sql", "r") as f:
            cur.copy_expert(sql=f.read(), file=f)
        cur.execute(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
            f"IN SCHEMA public TO {USER}"
        )
        cls.con.commit()
        cur.close()
        cls.con.close()

        # Read BIGSdb config file
        conf_file = f"{dir}/config_files/bigsdb.conf"
        cls.application = BaseApplication(testing=True)
        cls.config = cls.application._BaseApplication__read_config_file(
            filename=conf_file
        )
        cls.config["host_map"] = {}

        # Read database config
        dbase_config = f"{dir}/config_files/config.xml"
        cls.parser = XMLParser()
        cls.parser.parse(dbase_config)
        cls.system = cls.parser.get_system()

        # Connect
        cls.data_connector = DataConnector(system=cls.system, config=cls.config)
        cls.db = cls.data_connector.get_connection(
            dbase_name=TEST_DATABASE,
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
        )

        # Set up datastore
        cls.datastore = Datastore(
            db=cls.db,
            system=cls.system,
            config=cls.config,
            parser=cls.parser,
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.con = psycopg2.connect(dbname="postgres")
        cls.con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = cls.con.cursor()
        cur.execute(f"DROP DATABASE {TEST_DATABASE}")
        cur.execute(f"DROP USER {USER}")
