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

import xml.etree.ElementTree as ET
import pyuca
import bigsdb.utils
from bigsdb.constants import COUNTRIES


class XMLParser(object):
    def __init__(self):
        self.fields = []
        self.system = {}
        self.attributes = {}
        self.optlists = {}
        self.prefixes_already_defined = False

    def parse(self, xml_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        system = root.find("system")
        self.system = system.attrib
        fields = root.findall("field")
        for field in fields:
            field_name = field.text.strip()
            self.fields.append(field_name)
            for attribute in field.attrib:
                if field_name not in self.attributes:
                    self.attributes[field_name] = {}
                self.attributes[field_name][attribute] = self._process_value(
                    field.attrib[attribute]
                )
            if "optlist" in field.attrib and field.attrib["optlist"] == "yes":
                optlist = field.find("optlist")
                if field_name not in self.optlists:
                    self.optlists[field_name] = []
                for option in optlist:
                    self.optlists[field_name].append(option.text)

    def get_system(self):
        return self.system

    def get_field_list(self, options={}):
        fields = []
        for field in self.fields:
            if (
                options.get("no_curate_only", False)
                and self.attributes[field].get("curate_only", "") == "yes"
            ):
                continue
            if (
                options.get("multivalue_only", False)
                and self.attributes[field].get("multiple", "") != "yes"
            ):
                continue
            if (
                not options.get("show_hidden", False)
                and self.attributes[field].get("hide", "") == "yes"
            ):
                continue
            fields.append(field)
        return fields

    def get_all_field_attributes(self):
        self._set_prefix_fields()
        return self.attributes

    def get_field_attributes(self, field):
        self._set_prefix_fields()
        return self.attributes[field]

    def get_field_option_list(self, field):
        list = []
        if "values" in self.attributes[field]:
            special_values = self._get_special_optlist_values(
                self.attributes[field]["values"]
            )
            for value in special_values:
                list.append(value)
        for value in self.optlists[field]:
            list.append(value)
        if "sort" in self.attributes[field] and self.attributes[field]["sort"] == "yes":
            collator = pyuca.Collator()
            list = sorted(list, key=collator.sort_key)
        return list

    def _set_prefix_fields(self):
        if self.prefixes_already_defined == True:
            return
        for field_name in self.fields:
            if "prefixes" not in self.attributes[field_name]:
                continue
            if self.attributes[field_name]["prefixes"] in self.fields:
                self.attributes[self.attributes[field_name]["prefixes"]][
                    "prefixed_by"
                ] = field_name
                if "separator" in self.attributes[field_name]:
                    self.attributes[self.attributes[field_name]["prefixes"]][
                        "prefix_separator"
                    ] = self.attributes[field_name]["separator"]
            else:
                raise ValueError(
                    f"Field {field_name} prefixes "
                    + self.attributes[field_name]["prefixes"]
                    + " but this is not defined."
                )

        self.prefixes_already_defined = True

    def _process_value(self, value):
        if value == "CURRENT_DATE":
            return bigsdb.utils.get_datestamp()
        if value == "CURRENT_YEAR":
            return bigsdb.utils.get_current_year()
        return value

    def _get_special_optlist_values(self, values):
        if values == "COUNTRIES":
            return bigsdb.constants.COUNTRIES.keys()

    def is_field(self, field):
        if field == None:
            return
        return field in self.fields
