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
import bigsdb.utils
from bigsdb.plugin import Plugin

HIDE_VALUES = 8


class PyDatabaseFields(Plugin):

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
            'image': None,
            'requires': ''
        }

    def get_plugin_javascript(self):
        return '''
$(function () {
    $('.expand_link').on('click', function(){    
        var field = this.id.replace('expand_','');
          if ($('#' + field).hasClass('expandable_expanded')) {
          $('#' + field).switchClass('expandable_expanded',
          'expandable_retracted',1000, "easeInOutQuad", function(){
              $('#expand_' + field)
              .html('<span class="fas fa-chevron-down"></span>');
          });        
    } else {
          $('#' + field).switchClass('expandable_retracted',
          'expandable_expanded',1000, "easeInOutQuad", function(){
              $('#expand_' + field)
              .html('<span class="fas fa-chevron-up"></span>');
          });        
    }
    });    
});        
    '''
    
    def run(self):
        print('<h1>Description of database fields</h1>')
        print('<div class="box" id="large_resultstable"><div class="scrollable">')
    
        eav_fields = self.datastore.get_eav_fieldnames()
        
        if (len(eav_fields)):
            print('<span class="info_icon fas fa-2x fa-fw fa-globe fa-pull-left" ' 
                'style="margin-top:0.2em"></span>')
            print('<h2>Provenance/primary metadata</h2>');
        print('<p>Order columns by clicking their headings. '
            f'<a href="{self.script_name}?db={self.instance}&amp;'
            'page=plugin&amp;name=PyDatabaseFields">Reset default order</a>.'
            '</p>')
        self.__print_provenance_fields()
        eav_fields = self.datastore.get_eav_fieldnames()
        if len(eav_fields):
            self.__print_eav_fields()
        print('</div></div>')
    
    def get_initiation_values(self):
        return { 'jQuery.tablesort': 1 }
        
    def __print_provenance_fields(self):
        is_curator = self.is_curator(self.args.get('username'))        
        field_list = self.parser.get_field_list(
            { 'no_curate_only': not is_curator });
        
        td = 1;
        print('<table class="tablesorter" style="margin-bottom:1em"><thead>'
               '<tr><th>field name</th><th>comments</th><th>data type</th>'
               '<th class="sorter-false">allowed values</th><th>required</th>'
               '<th class="sorter-false">maximum length (characters)</th>'
               '</tr></thead><tbody>')
    
        for field in field_list:
            att = self.parser.get_field_attributes(field)
            if (att['type'].startswith('int')):
                att['type'] = 'integer'
            att['comments'] = att.get('comments', '')
            if (att.get('warning')):
                warning = att.get('warning')
                att['comments'] += f'<div class="field_warning">{warning}</div>'
            comments = att['comments']
            print(f'<tr class="td{td}"><td>{field}</td>'
            f'<td style="text-align:left">{comments}</td>');
            multiple = ' (multiple)' if att.get('multiple', '') == 'yes' else ''
            type = att['type']
            print (f'<td>{type}{multiple}</td><td>')
            self.__print_allowed_values(field);
            print ('</td>')
            required_allowed = set(
                ['yes', 'no', 'expected', 'genome_required', 'genome_expected'])
            att['required'] = att.get('required', 'yes')
            required = att['required'] if att['required'] \
                in required_allowed else 'yes';
            required_label = {
                'genome_required': 'if submitting a genome assembly',
                'genome_expected': 'expected if submitting a genome assembly'
                }
            value = required_label[required] if required_label.get(required) \
                else required
            print(f'<td>{value}</td>')
            length = att.get('length', '-')
            if att.get('optlist', '') == 'yes':
                length = '-'
            print(f'<td>{length}</td>')
            print('</tr>');
            td = 2 if td == 1 else 1;
    
            if field == self.system['labelfield']:
                print(f'<tr class="td{td}"><td>aliases</td>'
                '<td style="text-align:left">'
                f'alternative names for {field}</td><td>text (multiple)</td>'
                '<td>-</td><td>no</td><td>-</td></tr>');
                td = 2 if td == 1 else 1;

                print(f'<tr class="td{td}"><td>references</td>'
                '<td style="text-align:left">PubMed ids that link to '
                'publications that describe or include record</td>'
                '<td>integer (multiple)</td><td>-</td><td>no</td><td>-</td>'
                '</tr>')
                td = 2 if td == 1 else 1;
        print('</tbody></table>')
    
    def __print_eav_fields(self):
        field_name    = self.system.get('eav_fields', 'secondary metadata')
        uc_field_name = field_name.capitalize()
        icon = self.system.get('eav_field_icon','fas fa-microscope')
        categories = self.datastore.run_query( 
            'SELECT DISTINCT category FROM eav_fields ORDER BY category '
            'NULLS LAST', None, { 'fetch' : 'col_arrayref' } )
        print(f'<span class="info_icon fa-2x fa-fw {icon} fa-pull-left" ' 
         'style="margin-top:-0.2em"> </span><h2 style="display:inline">'
         f'{uc_field_name}</h2>')
        eav_fields = self.datastore.get_eav_fields()
        for cat in categories:
            if categories[0] != None:
                group_icon = self.get_eav_group_icon(cat)
                print('<div style="margin-top:1.5em;padding-left:0.5em">')
                if group_icon != None:
                    print(f'<span class="subinfo_icon fa-lg fa-fw {group_icon} '
                        'fa-pull-left" style="margin-right:0.5em"></span>'
                        f'<h3 style="display:inline">{cat}</h3>')
                else:
                    print(f'<h3>{cat}</h3>') if cat != None else \
                    '<h3>Other</h3>'
                print('</div>')
            td = 1
            print('<table class="tablesorter" style="margin-top:1em">'
                  '<thead><tr><th>field name</th><th>comments</th>'
                  '<th>data type</th><th class="sorter-false">'
                  'allowed values</th><th>required</th>'
                  '<th class="sorter-false">maximum length '
                  '(characters)</th></tr></thead><tbody>')
            for field in eav_fields:
                if field.get('category'):
                    if cat == None or cat != field['category']:
                        continue
                elif cat != None:
                    continue
                print('<tr class="td{0}"><td>{1}</td>'
                      '<td style="text-align:left">{2}</td><td>{3}</td>' 
                      .format(td,field['field'],
                        field.get('description') or '', 
                        field['value_format']))
                if field.get('option_list'):
                    values = field.get('option_list').split(';')
                    hide = len(values) > HIDE_VALUES
                    my_class = 'expandable_retracted' if hide else ''
                    print('<td><div id="{0}" style="overflow:hidden" class="{1}">'
                          .format(field['field'],my_class))
                    for option in values:
                        option = bigsdb.utils.escape_html(option)
                        print(f'{option}<br />')
                    print('</div>')
                    if hide:
                        print('<div class="expand_link" id="expand_{0}">'
                              '<span class="fas fa-chevron-down"></span></div>'
                              .format(field['field']));
                    print('</td>')
                else:
                    print('<td>')
                    if field.get('min_value') or field.get('max_value'):
                        if field.get('min_value'):
                            print('min: ' + str(field['min_value']))
                        if field.get('min_value') and field.get('max_value'):
                            print('; ')
                        if field.get('max_value'):
                            print('max: ' + str(field['max_value']))
                    else:
                        print('-')
                    print('</td>')
                print('<td>no</td>')
                length = field.get('length') or '-'
                print(f'<td>{length}</td>')
                td = 2 if td == 1 else 1;
            print('</tbody></table>')
    
    def __print_allowed_values(self, field):
        att = self.parser.get_field_attributes(field)
        if att.get('optlist', 'no') == 'yes':
            option_list = self.parser.get_field_option_list(field)
            hide = len(option_list) > HIDE_VALUES
            my_class = 'expandable_retracted' if hide else ''
            print (f'<div id="{field}" style="overflow:hidden" '
                   f'class="{my_class}">')
            for option in option_list:
                option = bigsdb.utils.escape_html(option)
                print(f'{option}<br />')
            print('</div>')
            if hide:
                print(f'<div class="expand_link" id="expand_{field}">'
                      '<span class="fas fa-chevron-down"></span></div>');
    
            return
        if att.get('min') or att.get('max'):
            if att.get('min'): print('min: ' + att['min']) 
            if att.get('min') and att.get('max'): print('; ')
            if att.get('max'): print('max: ' + att['max'])
            return

        if field == 'sender' or field == 'sequenced_by' or att.get('userfield', '') == 'yes': 
            print('<a href="{0}?db={1}&amp;page=fieldValues&amp;field=f_sender" '
                  'target="_blank">Click for list of sender ids</a>' \
                  .format(self.script_name, self.instance))
            return

        if field == 'curator':
            print('<a href="{0}?db={1}&amp;page=fieldValues&amp;field=f_curator" '
                  'target="_blank">Click for list of curator ids</a>' \
                  .format(self.script_name, self.instance))
            return
        
        if att.get('type', '') == 'geography_point':
            print('latitude [min: -90; max: 90], longitude [min: -180; max: 180]')
            return

        if att.get('regex'):
            print('Must match <a target="_blank" '
                  'href="https://en.wikipedia.org/wiki/Regular_expression">'
                  'regular expression</a>: {0}' . format(att['regex']))
            return
        print('-')
    
