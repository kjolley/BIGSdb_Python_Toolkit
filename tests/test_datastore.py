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

TEST_ISOLATE_DATABASE = "bigsdb_test_isolates"
TEST_USERS_DATABASE = "bigsdb_test_users"
HOST = "localhost"
PORT = 5432
USER = "bigsdb_tests"
PASSWORD = "test"
PERSIST = True  # Set to False to drop and recreate test databases each time.


class TestDatastore(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestDatastore, self).__init__(*args, **kwargs)

    def test_get_eav_fieldnames(self):
        eav_fieldnames = self.datastore.get_eav_fieldnames()
        self.assertEqual(len(eav_fieldnames), 4)
        self.assertTrue("Bexsero_reactivity" in eav_fieldnames)

    def test_get_eav_fields(self):
        fields = self.datastore.get_eav_fields()
        self.assertTrue(len(fields) > 1)
        all_have_name = True
        all_have_type = True
        for field in fields:
            if not field.get("field"):
                all_have_name = False
            if not field.get("value_format"):
                all_have_type = False
        self.assertTrue(all_have_name and all_have_type)

    def test_isolates_with_seqbin(self):
        ids, labels = self.datastore.get_isolates_with_seqbin()
        self.assertEqual(len(ids), 3)
        self.assertEqual(labels.get(1, ""), "1) A4/M1027")

    def test_get_remote_user_info(self):
        user_info = self.datastore.get_remote_user_info("jdoe", 1)
        self.assertEqual(user_info.get("first_name"), "John")
        self.assertEqual(user_info.get("surname"), "Doe")
        self.assertEqual(user_info.get("email"), "john.doe@test.com")

    def test_get_seqbin_count(self):
        count = self.datastore.get_seqbin_count()
        self.assertEqual(count, 3)

    def test_get_user_info_from_username(self):
        user_info = self.datastore.get_user_info_from_username("test")
        self.assertEqual(user_info.get("first_name"), "Test")
        self.assertEqual(user_info.get("surname"), "User")
        self.assertEqual(user_info.get("email"), "test@test.com")
        remote_user_info = self.datastore.get_user_info_from_username("jdoe")
        self.assertEqual(remote_user_info.get("email"), "john.doe@test.com")

    def test_isolate_exists(self):
        self.assertTrue(self.datastore.isolate_exists(1))
        self.assertFalse(self.datastore.isolate_exists(1200))

    def test_isolate_exists_batch(self):
        exists = self.datastore.isolate_exists_batch([1, 2, 3, 1200])
        self.assertTrue(1 in exists)
        self.assertTrue(2 in exists)
        self.assertFalse(1200 in exists)

    def test_run_query(self):
        list = self.datastore.run_query(
            "SELECT id FROM isolates", None, {"fetch": "col_arrayref"}
        )
        self.assertTrue(len(list) > 1)
        empty_list = self.datastore.run_query(
            "SELECT id FROM isolates WHERE id > 1000", None, {"fetch": "col_arrayref"}
        )
        self.assertTrue(len(empty_list) == 0)
        list = self.datastore.run_query(
            "SELECT id,isolate,country FROM isolates WHERE id=?",
            3,
            {"fetch": "row_arrayref"},
        )
        self.assertEqual(len(list), 3)
        self.assertEqual(list[2], "UK")
        empty_list = self.datastore.run_query(
            "SELECT id,isolate,country FROM isolates WHERE id=?",
            1000,
            {"fetch": "row_arrayref"},
        )
        self.assertTrue(empty_list == None)
        dict = self.datastore.run_query(
            "SELECT id,isolate,country FROM isolates WHERE id=?",
            3,
            {"fetch": "row_hashref"},
        )
        self.assertEqual(dict.get("isolate"), "M00242905")
        self.assertEqual(dict.get("country"), "UK")
        empty_dict = self.datastore.run_query(
            "SELECT id,isolate,country FROM isolates WHERE id=?",
            1000,
            {"fetch": "row_hashref"},
        )
        self.assertTrue(empty_dict == None)
        dict = self.datastore.run_query(
            "SELECT id,isolate,country FROM isolates WHERE id<=2",
            None,
            {"key": "id", "fetch": "all_hashref"},
        )
        self.assertEqual(len(dict.keys()), 2)
        self.assertEqual(dict.get(1).get("country"), "USA")
        self.assertEqual(dict.get(1).get("isolate"), "A4/M1027")
        self.assertEqual(dict.get(2).get("country"), "Pakistan")
        empty_dict = self.datastore.run_query(
            "SELECT id,isolate,country FROM isolates WHERE id>1000",
            None,
            {"key": "id", "fetch": "all_hashref"},
        )
        self.assertTrue(len(empty_dict.keys()) == 0)
        list = self.datastore.run_query(
            "SELECT id,isolate,country FROM isolates WHERE id<=2",
            None,
            {"fetch": "all_arrayref"},
        )
        self.assertEqual(len(list), 2)
        self.assertEqual(list[1][2], "Pakistan")
        empty_list = self.datastore.run_query(
            "SELECT id,isolate,country FROM isolates WHERE id>1000",
            None,
            {"fetch": "all_arrayref"},
        )
        self.assertTrue(len(empty_list) == 0)
        list = self.datastore.run_query(
            "SELECT id,isolate,country FROM isolates WHERE id<=2",
            None,
            {"fetch": "all_arrayref", "slice": {}},
        )
        self.assertEqual(len(list), 2)
        self.assertEqual(list[0].get("country"), "USA")
        self.assertEqual(list[0].get("isolate"), "A4/M1027")
        self.assertEqual(list[1].get("country"), "Pakistan")

    def test_create_temp_list_table_from_list(self):
        table = self.datastore.create_temp_list_table_from_list("int", [1, 2, 3, 4, 5])
        qry = f"SELECT COUNT(*) FROM {table}"
        count = self.datastore.run_query(qry)
        self.assertEqual(count, 5)

    @classmethod
    def setUpClass(cls):
        cls.con = psycopg2.connect(dbname="postgres")
        dir = pathlib.Path(__file__).parent.resolve()
        drop_and_recreate = True
        if PERSIST:
            isolatedb_exists = database_exists(cls.con, TEST_ISOLATE_DATABASE)
            userdb_exists = database_exists(cls.con, TEST_USERS_DATABASE)
            if isolatedb_exists and userdb_exists:
                drop_and_recreate = False

        if drop_and_recreate:  # Setup test isolate database
            cls.con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = cls.con.cursor()
            cur.execute(f"DROP DATABASE IF EXISTS {TEST_ISOLATE_DATABASE}")
            cur.execute(f"DROP DATABASE IF EXISTS {TEST_USERS_DATABASE}")
            cur.execute(f"DROP USER IF EXISTS {USER}")
            cur.execute(f"CREATE USER {USER}")
            cur.execute(f"ALTER USER {USER} WITH PASSWORD '{PASSWORD}'")

            cur.execute(f"CREATE DATABASE {TEST_ISOLATE_DATABASE}")
            cur.execute(f"CREATE DATABASE {TEST_USERS_DATABASE}")
            cls.con.commit()
            cls.con.close()
            cls.con = psycopg2.connect(dbname=TEST_ISOLATE_DATABASE)
            cur = cls.con.cursor()

            with open(f"{dir}/databases/bigsdb_test_isolates.sql", "r") as f:
                cur.copy_expert(sql=f.read(), file=f)
            cur.execute(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                f"IN SCHEMA public TO {USER}"
            )
            cls.con.commit()
            cur.close()
            cls.con.close()
            cls.con = psycopg2.connect(dbname=TEST_USERS_DATABASE)
            cur = cls.con.cursor()

            with open(f"{dir}/databases/bigsdb_test_users.sql", "r") as f:
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
            dbase_name=TEST_ISOLATE_DATABASE,
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
        )
        cls.user_db = cls.data_connector.get_connection(
            dbase_name=TEST_USERS_DATABASE,
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
        cls.datastore.add_user_db(1, cls.user_db, TEST_USERS_DATABASE)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.user_db.close()
        if PERSIST:
            return
        cls.con = psycopg2.connect(dbname="postgres")
        cls.con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = cls.con.cursor()
        cur.execute(f"DROP DATABASE {TEST_ISOLATE_DATABASE}")
        cur.execute(f"DROP DATABASE {TEST_USERS_DATABASE}")
        cur.execute(f"DROP USER {USER}")


def database_exists(conn, db_name):
    cursor = conn.cursor()
    query = "SELECT 1 FROM pg_database WHERE datname = %s"
    cursor.execute(query, (db_name,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None
