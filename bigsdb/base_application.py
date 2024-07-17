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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BIGSdb Python Toolkit. If not, see 
# <http://www.gnu.org/licenses/>.

import configparser
import bigsdb.utils

CONFIG_DIR = '/etc/bigsdb'
DBASE_CONFIG_DIR = '/etc/bigsdb/dbases'

class Base_Application(object):
    
    def __init__(self, database=None, config_dir=CONFIG_DIR, dbase_config_dir=DBASE_CONFIG_DIR, testing = False):
        self.config_dir = config_dir
        self.dbase_config_dir = dbase_config_dir
        if testing:
            return
        if database == None:
            raise ValueError('No database parameter passed.')
        self.config = self.__read_config_file()
        print(self.config)
        
    def __read_config_file(self, filename=None):
        filename = filename or f"{self.config_dir}/bigsdb.conf"
        with open(filename, 'r') as f:
             ini_data =  '[General]\n' + f.read()
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
        return dict
    

