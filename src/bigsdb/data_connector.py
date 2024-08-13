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

import psycopg2


class DataConnector(object):
    def __init__(self, system=None, config=None, logger=None):
        if system == None:
            raise ValueError("No system parameter passed.")
        if config == None:
            raise ValueError("No config parameter passed.")
        self.db = {}
        self.config = config
        self.system = system
        self.logger = logger

    def get_connection(
        self, dbase_name, host=None, port=None, user=None, password=None
    ):
        if dbase_name == None:
            raise ValueError("No dbase_name parameter passed.")

        host = self.config["host_map"].get(host) or host or self.system.get("host")
        port = port or self.system.get("port")
        user = user or self.system.get("user")
        password = password or self.system.get("password")
        cache_name = f"{host}|{dbase_name}"
        if cache_name not in self.db:
            conn = psycopg2.connect(
                dbname=dbase_name, host=host, port=port, user=user, password=password
            )
            self.db[cache_name] = conn
        return self.db[cache_name]

    def drop_all_connections(self, except_list=None):
        if except_list is None or not isinstance(except_list, list):
            except_list = []
            except_set = set(except_list)
        for db in list(self.db.keys()):
            if db in except_set:
                continue
            try:
                self.db[db].close()
            except Exception as e:
                self.logger.error(
                    f"Error disconnecting from database {self.db[db]}: {e}"
                )
            del self.db[db]
