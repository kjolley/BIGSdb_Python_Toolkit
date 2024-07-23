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

import logging
import cgi
import os
import json
from bigsdb.base_application import BaseApplication
from bigsdb.constants import DIRS


class Plugin(BaseApplication):

    def __init__(self, database=None, config_dir=DIRS['CONFIG_DIR'],
                 dbase_config_dir=DIRS['DBASE_CONFIG_DIR'], arg_file=None,
                 retrieving_attributes=False):
        if not retrieving_attributes:
            if database == None:
                raise ValueError('No database parameter passed.')
        self.__init_logger()
        super(Plugin, self).__init__(database=database, config_dir=config_dir,
            dbase_config_dir=dbase_config_dir, logger=self.logger,
            testing=retrieving_attributes)
        if (arg_file != None):
            self.__read_arg_file(arg_file)
        self.__initiate()
    
    # Override the following functions in subclass
    def get_attributes(self): raise NotImplementedError

    def get_hidden_attributes(self): return []

    def get_plugin_javascript(self): return ''
    
    def get_initiation_values(self): return {}

    def run(self): raise NotImplementedError

    def run_job(self): pass
    
    def __init_logger(self, logger=None):
        if logger:
            return
        self.logger = logging.getLogger(__name__)
        log_file = '/var/log/bigsdb.log'

        f_handler = logging.FileHandler(log_file)
        f_handler.setLevel(logging.INFO)

        f_format = logging.Formatter('%(asctime)s - %(levelname)s: - %(module)s:%(lineno)d - %(message)s')
        f_handler.setFormatter(f_format)

        self.logger.addHandler(f_handler)
    
    def __initiate(self):
        form = cgi.FieldStorage()
        self.script_name = os.environ.get('SCRIPT_NAME', '') or 'bigsdb.pl'

    def __read_arg_file(self, arg_file):
        full_path = self.config.get('secure_tmp_dir') + f'/{arg_file}'
        if not os.path.isfile(full_path):
            self.logger.error(f'Argument file {full_path} does not exist.')
            self.args = {}
            return;
        with open(full_path, 'r') as f:
            self.args = json.load(f)
    
    def is_curator(self, username):
        if username == None:
            return False
        user_info = self.datastore.get_user_info_from_username(username);
        if user_info == None or (user_info['status'] != 'curator' and user_info['status'] != 'admin'):
            return False
        return True
    
    def get_eav_group_icon(self, group):
        if group == None: return
        group_values = [];
        if self.system.get('eav_groups'):
            group_values = self.system.get('eav_groups').split(',')
            for value in group_values:
                [name, icon] = value.split('|')
                if name == group:
                    return icon

