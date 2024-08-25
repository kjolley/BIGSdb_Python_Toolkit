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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from bigsdb.base_application import BaseApplication

dir = pathlib.Path(__file__).parent.resolve()


class TestBaseApplication(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestBaseApplication, self).__init__(*args, **kwargs)
        self.application = BaseApplication(testing=True)

    def test_read_config_file(self):
        conf_file = f"{dir}/config_files/bigsdb.conf"
        config = self.application._read_config_file(filename=conf_file)
        self.assertEqual(config["auth_db"], "bigsdb_auth")
        self.assertTrue(
            isinstance(config["embargo_enabled"], int),
            "Config embargo_enabled value is not an int",
        )

    def test_read_db_conf_file(self):
        conf_file = f"{dir}/config_files/db.conf"
        self.application.config = {}
        self.application._read_db_config_file(filename=conf_file)
        self.assertEqual(self.application.config["dbhost"], "server1")

    def test_read_host_mapping_file(self):
        conf_file = f"{dir}/config_files/host_mapping.conf"
        self.application.config = {}
        self.application._read_host_mapping_file(filename=conf_file)
        self.assertTrue(self.application.config["host_map"]["server1"] == "server2")

    def test_read_system_overrides(self):
        dbase_config = f"{dir}/config_files/config.xml"
        overrides_file = f"{dir}/config_files/system.overrides"
        self.application._read_dbase_config_xml_file(filename=dbase_config)
        self.application._set_system_overrides(filename=overrides_file)
        self.assertEqual(self.application.system["max_total_length"], 2800000)
