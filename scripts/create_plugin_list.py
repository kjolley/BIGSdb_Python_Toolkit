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

# This script is used to generate a list of BIGSdb Python plugins that can be
# read by the BIGSdb program.
# Run the script and save the output as python_plugins.json in the 
#/etc/bigsdb/ directory.

#Version 20240721

import os
import argparse
import importlib.util
import inspect
import json

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--plugin_dir', required=True, help='Plugin directory')
args = parser.parse_args()


def main():
    module_files = [f for f in os.listdir(args.plugin_dir) if f.endswith('.py')]
    results = []
    for module_file in module_files:
        
        # Create a module spec
        spec = importlib.util.spec_from_file_location(module_file, os.path.join(args.plugin_dir, module_file))

        # Create a module from the spec
        module = importlib.util.module_from_spec(spec)

        # Load the module
        spec.loader.exec_module(module)
        
        # Get the name of the plugin class in the module
        class_name = [name for name, obj in inspect.getmembers(module) if inspect.isclass(obj)][0]
        
        # If the module has the class
        if hasattr(module, class_name):
            # Create an instance of the class
            instance = getattr(module, class_name)()

            # If the instance has the method
            if hasattr(instance, 'get_attributes'):
                 results.append(instance.get_attributes())
    
    print(json.dumps(results))


if __name__ == "__main__":
    main()
