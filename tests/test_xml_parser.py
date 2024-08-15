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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bigsdb.xml_parser as xml_parser

dir = pathlib.Path(__file__).parent.resolve()
xml_file = f"{dir}/config_files/config.xml"


class TestXmlParser(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestXmlParser, self).__init__(*args, **kwargs)
        self.parser = xml_parser.XMLParser()
        self.parser.parse(xml_file)

    def test_system(self):
        system = self.parser.get_system()
        self.assertEqual(system["db"], "bigsdb_test_isolates")

    def test_field_list(self):
        fields = self.parser.get_field_list()
        self.assertEqual(len(fields), 71)
        self.assertIn("country", fields)

    def test_all_field_attributes(self):
        attributes = self.parser.get_all_field_attributes()
        self.assertEqual(attributes["year"]["required"], "expected")

    def test_field_attributes(self):
        attributes = self.parser.get_field_attributes("year")
        self.assertEqual(attributes["required"], "expected")

    def test_field_option_list(self):
        options = self.parser.get_field_option_list("source")
        self.assertEqual(len(options), 10)
        self.assertEqual(options[2], "eye")

    def test_is_field(self):
        self.assertTrue(self.parser.is_field("isolate"))
        self.assertFalse(self.parser.is_field("area"))


if __name__ == "__main__":
    unittest.main()
