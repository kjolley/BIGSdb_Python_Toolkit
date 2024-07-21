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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bigsdb.plugin import Plugin

class DatabaseFields(Plugin):

    def get_attributes(self):
        return {
            'name': 'Database Fields (PYTHON TEST)',
            'authors': [
                {
                    'name': 'Keith Jolley',
                    'affiliation': 'University of Oxford, UK',
                    'email': 'keith.jolley@biology.ox.ac.uk',
                }
            ],
            'description': 'Display description of fields defined for the '
                'current database',
            'full_description': 'This plugin fully describes primary and '
                'secondary metadata fields defined in the database. The data '
                'type (integer, float, text, or date), lists of allowed values '
                'or ranges, whether the field is compulsory or optional and the '
                'maximum length of values is displayed.',
            'menutext': 'Description of database fields (Python test)',
            'module': 'PyDatabaseFields',
            'version': '1.0.0',
            'section': 'info',
            'order': 15,
            'dbtype': 'isolates',
            'image': None
        }


