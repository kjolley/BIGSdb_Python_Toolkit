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

import configparser
from pathlib import Path
import bigsdb.utils
from bigsdb.xml_parser import XMLParser
from bigsdb.data_connector import DataConnector
from bigsdb.constants import DIRS, CONNECTION_DETAILS 


class BaseApplication(object):
    
    def __init__(self, database=None, config_dir=DIRS['CONFIG_DIR'],
                 dbase_config_dir=DIRS['DBASE_CONFIG_DIR'], host=None,
                 port=None, user=None, password=None, testing=False):
        self.config_dir = config_dir
        self.dbase_config_dir = dbase_config_dir
        if testing:
            return
        if database == None:
            raise ValueError('No database parameter passed.')
        self.instance = database
        self.config = self.__read_config_file()
        self.__read_db_config_file()
        self.__read_host_mapping_file()
        self.__read_dbase_config_xml_file()
        self.__set_system_overrides()
        self.system['host'] = host or self.system.get('host') \
            or self.config.get('host', CONNECTION_DETAILS['HOST'])
        self.system['port'] = port or self.system.get('port') \
            or self.config.get('port', CONNECTION_DETAILS['PORT'])
        self.system['user'] = user or self.system.get('user') \
            or self.config.get('user', CONNECTION_DETAILS['USER'])
        self.system['password'] = password or self.system.get('password') \
            or self.config.get('password', CONNECTION_DETAILS['PASSWORD'])
        if self.system.get('dbtype', '') == 'isolates':
            self.system['view'] = self.system.get('view', 'isolates')
            self.system['labelfield'] = self.system.get('labelfield', 'isolate')
        self.data_connector = DataConnector(system=self.system, config=self.config)
        self.__initiate_auth_db()
        
    def __read_config_file(self, filename=None):
        filename = filename or f"{self.config_dir}/bigsdb.conf"
        if not Path(filename).is_file():
           raise ValueError(f'Main config file {filename} does not exist.') 
        with open(filename, 'r') as f:
             ini_data = '[General]\n' + f.read()
        config = configparser.ConfigParser()
        config.read_string(ini_data)
        dict = {}
        for key in config['General']:
            value = config['General'][key]
            if (bigsdb.utils.is_integer(value)):
                value = int(value)
            elif (bigsdb.utils.is_float(value)):
                value = float(value)
            elif (bigsdb.utils.is_date(value)):
                value = date(value)          
            dict[key] = value
        # refdb attribute has been renamed ref_db for consistency 
        # with other databases (refdb still works)
        dict['ref_db'] = dict.get('ref_db', dict.get('refdb'))
        return dict
    
    def __read_db_config_file(self, filename=None):
        filename = filename or f'{self.config_dir}/db.conf'
        if not Path(filename).is_file():
            return
        with open(filename, 'r') as f:
             ini_data = '[General]\n' + f.read()
        config = configparser.ConfigParser()
        config.read_string(ini_data)
        for key in config['General']:
            value = config['General'][key]
            if (bigsdb.utils.is_integer(value)):
                value = int(value)
            self.config[key] = value
            
    def __read_host_mapping_file(self, filename=None):
        filename = filename or f'{self.config_dir}/host_mapping.conf'
        if not Path(filename).is_file():
            return
        self.config['host_map'] = {}
        with open(filename) as file:
            for line in file:
                if not line.startswith('#') and not line == '':
                    list = line.split()
                    if len(list) >= 2:
                        self.config['host_map'][list[0].strip()] = list[1].strip()

    def __read_dbase_config_xml_file(self, filename=None):
        filename = filename or f'{self.dbase_config_dir}/{self.instance}/config.xml'
        if Path(filename).is_file():
            self.parser = XMLParser()
            self.parser.parse(filename)
            self.system = self.parser.get_system()
        else:
            raise ValueError(f'Database config file {filename} does not exist.')
    
    def __set_system_overrides(self, filename=None):
        filename = filename or f'{self.dbase_config_dir}/{self.instance}/system.overrides'
        if not Path(filename).is_file():
            return
        with open(filename, 'r') as f:
             ini_data = '[General]\n' + f.read()
        config = configparser.ConfigParser()
        config.read_string(ini_data)
        for key in config['General']:
            value = config['General'][key]
            value = value.strip('"')
            if (bigsdb.utils.is_integer(value)):
                value = int(value)
            elif (bigsdb.utils.is_float(value)):
                value = float(value)
            elif (bigsdb.utils.is_date(value)):
                value = date(value) 
            self.system[key] = value
            
    def __initiate_auth_db(self):
        host = self.config['dbhost'] or self.system['host']
        port = self.config['dbport'] or self.system['port']
        user = self.config['dbuser'] or self.system['user']
        password = self.config['dbpassword'] or self.system['password']
        self.auth_db = self.data_connector.get_connection(
            dbase_name=self.config['auth_db'], host=host, port=port,
            user=user, password=password)
        
