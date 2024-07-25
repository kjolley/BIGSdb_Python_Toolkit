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
import os
import json
import re
import bigsdb.utils
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
        self.cache = {}
    
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
        self.params = self.args.get('cgi_params')
        self.script_name = os.environ.get('SCRIPT_NAME', '') or 'bigsdb.pl'
        if self.system.get('dbtype','') == 'isolates':
            self.datastore.initiate_view(
                username=self.args.get('username'), 
                curate=self.args.get('curate', False), 
                set_id=self.get_set_id()
            )

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
                
    def print_bad_status(self,options):
        
        options['message'] = options.get('message', 'Failed!')
        buffer = ('<div class="box statusbad" style="min-height:5em"><p>' + 
        '<span class="failure fas fa-times fa-5x fa-pull-left"></span>' +
        '</p><p class="outcome_message">{0}</p>'.format(options.get('message')))
        if options.get('detail'):
            buffer += '<p class="outcome_detail">{0}</p>' \
            .format(options.get('detail'))
        buffer += '</div>';
        if not options.get('get_only'):
            print(buffer)
        return buffer
    
    def has_set_changed(self):
        set_id = self.args.get('set_id')
        if self.params.get('set_id') and set_id != None:
            if self.params.get('set_id') != set_id:
                self.print_bad_status({'message':
                    'The dataset has been changed since this plugin was '
                    'started. Please repeat the query.'})
                return 1
            
    def get_set_id(self):
        if self.system.get('sets', '') == 'yes':
            set_id = self.system.get('set_id') or self.params.get('set_id')
            if set_id != None and bigsdb.utils.is_integer(set_id):
                return set_id
            if self.datastore == None:
                return
            if self.system.get('only_sets', '') == 'yes' and not self.args.get('curate'):
                if not self.cache.get('set_list'):
                  self.cache['set_list'] = self.datastore.run_query(
                      'SELECT id FROM sets ORDER BY display_order,description',
                      None, {'fetch' : 'col_arrayref'})  
                if len(self.cache.get('set_list',[])):
                    return self.cache.get('set_list')
    
    def get_query(self, query_file):
        view = self.system.get('view')    #TODO Will need to initiate view  
        if query_file == None:
            qry = f'SELECT * FROM {view} WHERE new_version IS NULL ORDER BY id'
        else:
            full_path = self.config.get('secure_tmp_dir') + '/' + query_file
            if os.path.exists(full_path):
                try:
                    with open(full_path) as x: qry = x.read()
                except IOError:
                    if self.params.get('format','') == 'text':
                        print('Cannot open temporary file.')
                    else:
                       self.print_bad_status( 
                           { 'message' : 'Cannot open temporary file.' })
                    self.logger.error(f'Cannot open temporary file {full_path}')
                    return
            else:
                if self.params.get('format','') == 'text':
                    print('The temporary file containing your query does '
                          'not exist. Please repeat your query.')
                else:
                    self.print_bad_status( { 'message' : 
                        'The temporary file containing your query does '
                        'not exist. Please repeat your query.' })
        if self.system.get('dbtype', '') == 'isolates':
            qry = re.sub(r'([\s\(])datestamp', r'\1view.datestamp', qry)
            qry = re.sub(r'([\s\(])date_entered', r'\1view.date_entered', qry)
        return qry
    
    def get_ids_from_query(self, qry):
        if qry == None:
            return []
        qry = re.sub(r'ORDER\sBY.*$', '', qry)
 #       return if !$self->create_temp_tables($qry_ref); #TODO
        view = self.system.get('view')
        qry = re.sub(r'SELECT\s(view\.\*|\*)', 'SELECT id', qry)
        qry += f' ORDER BY {view}.id'
        ids = self.datastore.run_query(qry,None,{'fetch':'col_arrayref'})
        return ids

