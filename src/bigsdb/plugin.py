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

MAX_ISOLATES_DROPDOWN = 1000


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
        if self.system.get('dbtype', '') == 'isolates':
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
                
    def print_bad_status(self, options):
        
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
                      None, {'fetch': 'col_arrayref'})  
                if len(self.cache.get('set_list', [])):
                    return self.cache.get('set_list')
    
    def __get_query(self, query_file):
        view = self.system.get('view')  # TODO Will need to initiate view  
        if query_file == None:
            qry = f'SELECT * FROM {view} WHERE new_version IS NULL ORDER BY id'
        else:
            full_path = self.config.get('secure_tmp_dir') + '/' + query_file
            if os.path.exists(full_path):
                try:
                    with open(full_path) as x: qry = x.read()
                except IOError:
                    if self.params.get('format', '') == 'text':
                        print('Cannot open temporary file.')
                    else:
                       self.print_bad_status(
                           { 'message': 'Cannot open temporary file.' })
                    self.logger.error(f'Cannot open temporary file {full_path}')
                    return
            else:
                if self.params.get('format', '') == 'text':
                    print('The temporary file containing your query does '
                          'not exist. Please repeat your query.')
                else:
                    self.print_bad_status({ 'message': 
                        'The temporary file containing your query does '
                        'not exist. Please repeat your query.' })
        if self.system.get('dbtype', '') == 'isolates':
            qry = re.sub(r'([\s\(])datestamp', r'\1view.datestamp', qry)
            qry = re.sub(r'([\s\(])date_entered', r'\1view.date_entered', qry)
        return qry
    
    def __get_ids_from_query(self, qry):
        if qry == None:
            return []
        qry = re.sub(r'ORDER\sBY.*$', '', qry)
 #       return if !$self->create_temp_tables($qry_ref); #TODO
        view = self.system.get('view')
        qry = re.sub(r'SELECT\s(view\.\*|\*)', 'SELECT id', qry)
        qry += f' ORDER BY {view}.id'
        ids = self.datastore.run_query(qry, None, {'fetch':'col_arrayref'})
        return ids
    
    def get_selected_ids(self):
        query_file = self.params.get('query_file')
        if self.params.get('isolate_id'):
            selected_ids = self.params.get('isolate_id')
        elif query_file != None:
            qry = self.__get_query(query_file)
            selected_ids = self.__get_ids_from_query(qry)
        else:
            selected_ids = []
        return selected_ids
    
    def print_seqbin_isolate_fieldset(self, options):
        seqbin_count = self.datastore.get_seqbin_count()
        print('<fieldset style="float:left"><legend>Isolates</legend>')
        if seqbin_count or options.get('use_all'):
            size = options.get('size', 8)
            list_box_size = size - 0.2
            print('<div style="float:left">')
            if (seqbin_count <= MAX_ISOLATES_DROPDOWN and not options['use_all']) \
            or not options['isolate_paste_list']:
                default = self.params.get('isolate_id')
                if default:
                    selected_ids = {int(x) for x in default.split("\u0000")}
                else:
                    selected_ids = set(options.get('selected_ids', []))
                ids, labels = self.datastore.get_isolates_with_seqbin(options)
                print('<select name="isolate_id" id="isolate_id" '
                      f'style="min-width:12em;height:{size}em" multiple>')
                for id in ids:
                    selected = ' selected' if id in selected_ids else ''
                    label = labels.get(id, id)
                    print(f'<option value="{id}"{selected}>{label}</option>')
                print('</select>')
                list_button = ''
                if options['isolate_paste_list']:
                    show_button_display = 'none' \
                        if self.params.get('isolate_paste_list') else 'display'
                    hide_button_display = 'display' \
                        if self.params.get('isolate_paste_list') else 'none'
                    list_button = ('<input type="button" id="isolate_list_show_button" '
                    'onclick="isolate_list_show()" value="Paste list" '
                    f'style="margin:1em 0 0 0.2em; display:{show_button_display}" '
                    'class="small_submit" />')
                    list_button += ('<input type="button" '
                    'id="isolate_list_hide_button" onclick="isolate_list_hide()" '
                    'value="Hide list" style="margin:1em 0 0 0.2em; '
                    f'display:{hide_button_display}" class="small_submit" />')
                print('<div style="text-align:center">'
                      '<input type="button" onclick="listbox_selectall(\'isolate_id\',true)" '
                      'value="All" style="margin-top:1em" class="small_submit" />')
                print('<input type="button" onclick="listbox_selectall(\'isolate_id\',false)" '
                      'value="None" style="margin:1em 0 0 0.2em" class="small_submit" />'
                      f'{list_button}</div></div>')
                if options['isolate_paste_list']:
                    display = 'block' if self.params.get('isolate_paste_list') \
                    else 'none'
                    default = self.params.get('isolate_paste_list','')
                    print('<div id="isolate_paste_list_div" style="float:left; '
                          f'display:{display}">')
                    print('<textarea name="isolate_paste_list" id="isolate_paste_list" '
                          f'style="height:{list_box_size}em" '
                          'placeholder="Paste list of isolate ids (one per line)...">'
                          f'{default}</textarea>')
            else:
                default = self.params.get('isolate_paste_list','')
                print('<textarea name="isolate_paste_list" id="isolate_paste_list" '
                      f'style="height:{list_box_size}em" '
                      'placeholder="Paste list of isolate ids (one per line)...">')
                if default:
                    print(default, end='')
                else:
                    print('\n'.join(map(str, options.get('selected_ids'))), end='')
                print('</textarea>')
                print('<div style="text-align:center"><input type="button" '
                      'onclick="listbox_clear(\'isolate_paste_list\')" '
                      'value="Clear" style="margin-top:1em" class="small_submit" />')
                if options.get('only_genomes'):
                    print('<input type="button" '
                          'onclick="listbox_listgenomes(\'isolate_paste_list\')" '
                          'value="List all" style="margin-top:1em" '
                          'class="small_submit" /></div>')
                else:
                    print('<input type="button" '
                          'onclick="listbox_listall(\'isolate_paste_list\')" '
                          'value="List all" style="margin-top:1em" '
                          'class="small_submit" /></div>')
            print('</div>')
        else:
            print('No isolates available<br />for analysis')            
        print('</fieldset>')

    def print_action_fieldset(self, options=None):
        if options is None:
            options = {}
        page = options.get('page', self.params.get('page'))
        submit_name = options.get('submit_name', 'submit')
        submit_label = options.get('submit_label', 'Submit')
        reset_label = options.get('reset_label', 'Reset')
        legend = options.get('legend', 'Action')
        buffer = f'<fieldset style="float:left"><legend>{legend}</legend>\n'
        if 'text' in options:
            buffer += options['text'] 
        url = '{0}?db={1}&amp;page={2}'.format(self.script_name, self.instance, page)
        fields = ['isolate_id', 'id', 'scheme_id', 'table', 'name', 'ruleset',
                   'locus', 'profile_id', 'simple', 'set_id', 'modify',
                   'project_id', 'edit', 'private', 'user_header', 'interface']
    
        if 'table' in options:
            raise NotImplementedError  # TODO datastore.get_table_pks
            pk_fields = self.datastore.get_table_pks(options['table'])
            fields.extend(pk_fields)
        for field in set(fields):
            if field in options:
                url += f"&amp;{field}={options[field]}"
        if not options.get('no_reset'):
            buffer += f'<a href="{url}" class="reset"><span>{reset_label}</span></a>\n'
        id = {'id': options['id']} if 'id' in options else {}
        buffer += (f'<input type="submit" id="{submit_name}" name="{submit_name}" '
                   f'value="{submit_label}" class="submit" {id}>\n')
        if 'submit2' in options:
            options['submit2_label'] = options.get('submit2_label',
                                                   options['submit2'])
            buffer += (f'<input type="submit" name="{options["submit2"]}" '
                       f'value="{options["submit2_label"]}" class="submit" '
                       'style="margin-left:0.2em">\n')
        buffer += '</fieldset>'
        if not options.get('no_clear'):
            buffer += '<div style="clear:both"></div>'
        if options.get('get_only'):
            return buffer
        print(buffer)
        
    def start_form(self):
        print(f'<form method="post" action="{self.script_name}" enctype="multipart/form-data">')
        
    def print_hidden(self, param_list):
        for param in param_list:
            if self.params.get(param):
                value = self.params.get(param)
                print(f'<input type="hidden" name="{param}" value="{value}" />')
                
    def end_form(self):
        print('</form>')
        
    def filter_list_to_ids(self, list=[]):   
        returned_list = []
        for value in list:
            if bisdb.utils.is_integer(value):
                returned_list.append(value)
        return returned_list

    def get_ids_from_pasted_list(self):
        cleaned_ids = []
        invalid_ids = []
        if self.params.get('isolate_paste_list'):
            list = self.params.get('isolate_paste_list').split('\n')
            for id in list:
                id = id.strip()
                if bigsdb.utils.is_integer(id) and self.datastore.isolate_exists(id):
                    cleaned_ids.append(int(id))
                else:
                    if bigsdb.utils.is_integer(id):
                        invalid_ids.append(int(id))
                    else:
                        invalid_ids.append(id)
        return cleaned_ids, invalid_ids
        
