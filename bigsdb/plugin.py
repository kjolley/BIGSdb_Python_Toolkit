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

from bigsdb.base_application import BaseApplication

class Plugin(BaseApplication):

#    def __init__(self):
#        pass
        
    # Override the following functions in subclass
    def get_attributes(): raise NotImplementedError

    def get_hidden_attributes(): return []

    def get_plugin_javascript(): return ''

    def run(): raise NotImplementedError

    def run_job(): pass
    
if __name__ == "__main__":
    run()
