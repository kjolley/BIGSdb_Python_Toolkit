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
        self.username_cache = {}
        self.user_dbs = {}
        
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
                return [{key: dict(row)[key] for key in options['slice']} for 
                        row in cursor.fetchall()]
            elif 'slice' in options:  # slice = {}
                return [dict(row) for row in cursor.fetchall()]
            else:
                return cursor.fetchall()
        self.logger.error('Query failed - invalid fetch method specified.')
        return None

    def initiate_user_dbs(self):
        configs = self.run_query('SELECT * FROM user_dbases ORDER BY id', 
                                 None, {'fetch': 'all_arrayref', 'slice': {}})
        for config in configs:
            try:
                self.user_dbs[config['id']] = {
                    'db': self.data_connector.get_connection(
                        dbase_name = config.get('dbase_name'),
                        host = config.get('dbase_host') or self.config.get('dbhost') or self.system.get('host'),
                        port = config.get('dbase_port') or self.config.get('dbport') or self.system.get('port'),
                        user = config.get('dbase_user') or self.config.get('dbuser') or self.system.get('user'),
                        password = config.get('dbase_password') or self.config.get('dbpassword') or self.system.get('password')
                    ),
                    'name': self.config.get('dbase_name')
                }
            except Exception as e:
                self.logger.error(str(e))
  
    def get_user_info_from_username(self, username):
        if username == None:
            return
        if self.username_cache.get(username) == None:
            user_info = self.run_query('SELECT * FROM users WHERE user_name=?',
                                        username,{'fetch': 'row_hashref'})
            if (user_info and user_info.get('user_db')) != None:
                remote_user = self.get_remote_user_info(username, 
                                        user_info.get('user_db'))
                if (remote_user.get('user_name') != None):
                    for att in ['first_name', 'surname', 'email', 
                        'affiliation', 'submission_digests', 
                        'submission_email_cc', 'absent_until']:
                        if remote_user.get(att):
                            user_info[att] = remote_user.get(att)
            self.username_cache[username] = user_info
        return self.username_cache.get(username)
    
    def get_remote_user_info(self, username, user_db_id):
        user_db = self.get_user_db(user_db_id)
        user_data = self.run_query(
            'SELECT user_name,first_name,surname,email,affiliation '
            'FROM users WHERE user_name=?',
            username,{'db':user_db,'fetch':'row_hashref'})
        user_prefs = self.run_query(
            'SELECT * FROM curator_prefs WHERE user_name=?',
            username,{'db': user_db,'fetch': 'row_hashref'})
        for key in user_prefs.keys():
            user_data[key] = user_prefs[key]
        return user_data
    
    def get_user_db(self,id):
        try:
            return self.user_dbs[id]['db']
        except:
            self.logger.error('Cannot get user db')
               
    def get_eav_fields(self):
        return self.run_query( 
            'SELECT * FROM eav_fields ORDER BY field_order,field',  
                None, { 'fetch' : 'all_arrayref', 'slice' : {} })
    
    def get_eav_fieldnames(self, options={}):        
        no_curate = ' WHERE NOT no_curate' if options.get('curate') else ''
        return self.run_query(
            f'SELECT field FROM eav_fields{no_curate} ORDER BY '
            'field_order,field',
                None, { 'fetch': 'col_arrayref' })

    
# BIGSdb Perl DBI code uses ? as placeholders in SQL queries. psycopg2 uses
# %s. Rewrite so that the same SQL works with both.
def replace_placeholders(query):
    return re.sub(r'\?', '%s', query)
