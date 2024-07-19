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
# along with BIGSdb Python Toolkit. If not, see 
# <https://www.gnu.org/licenses/>.

import re
import logging
import psycopg2.extras


class Datastore(object):

    def __init__(self, db, data_connector, system, config, parser,
                 logger=None, curate=False):
        if system == None:
            raise ValueError('No system parameter passed.')
        if config == None:
            raise ValueError('No config parameter passed.')
        self.db = db
        self.data_connector = data_connector
        self.config = config
        self.system = system
        self.logger = logger
        self.curate = curate
        
    def run_query(self, qry, values=[], options={}):
        if type(values) is not list:
            values = [values]
        db = options.get('db', self.db)
        fetch = options.get('fetch', 'row_array')
        qry = replace_placeholders(qry)

        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cursor.execute(qry, values)
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")        
        
        if fetch == 'col_arrayref':
            data = None
            try:
                data = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                self.logger.error(f"{e} Query:{qry}")
            return data

        # No differentiation between Perl DBI row_array and row_arrayref in Python.
        if fetch == 'row_arrayref' or fetch == 'row_array':
            return cursor.fetchone()
        if fetch == 'row_hashref':
            return dict(cursor.fetchone())
        if fetch == 'all_hashref':
            if 'key' not in options:
                self.logger.error('Key field(s) needs to be passed.')
            return {row[options['key']]: dict(row) for row in cursor.fetchall()}
        if fetch == 'all_arrayref':
            if 'slice' in options and options['slice']:
                return [{key: dict(row)[key] for key in options['slice']} for row in cursor.fetchall()]
            elif 'slice' in options:  # slice = {}
                return [dict(row) for row in cursor.fetchall()]
            else:
                return cursor.fetchall()
        self.logger.error('Query failed - invalid fetch method specified.')
        return None

    
# BIGSdb Perl DBI code uses ? as placeholders in SQL queries. psycopg2 uses
# %s. Rewrite so that the same SQL works with both.
def replace_placeholders(query):
    return re.sub(r'\?', '%s', query)
