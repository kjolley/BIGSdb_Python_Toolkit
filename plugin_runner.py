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

import argparse
import importlib
import sys
import os

parser = argparse.ArgumentParser()
parser.add_argument('--database', required=True, help='Database config')
parser.add_argument('--module', required=True, help='Plugin module name')
parser.add_argument('--module_dir', required=True, help='Plugin module directory')
parser.add_argument('--arg_file', required=False, help='Argument JSON file')
parser.add_argument('--run_job', type=bool, default=False)
args = parser.parse_args()

sys.path.insert(0, args.module_dir)


def main():
    module = importlib.import_module(args.module)
    plugin = getattr(module, args.module)(
        database=args.database,
        arg_file=args.arg_file
    )
    if args.run_job:
        plugin.run_job()
    else:
        plugin.run()

if __name__ == "__main__":
    main()



