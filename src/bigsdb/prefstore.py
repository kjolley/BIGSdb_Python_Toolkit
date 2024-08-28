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
import psycopg2.extras
from bigsdb.constants import CONNECTION_DETAILS, LOGS


class Prefstore:
    def __init__(
        self,
        data_connector=None,
        config=None,
        logger=None,
    ):
        self._check_required_parameters(data_connector=data_connector, config=config)
        self.data_connector = data_connector
        self.config = config
        self._init_logger(logger=logger)
        self._db_connect()

    def _init_logger(self, logger=None):
        if logger:
            self.logger = logger
            return
        self.logger = logging.getLogger(__name__)
        f_handler = logging.FileHandler(LOGS["JOBS_LOG"])
        f_handler.setLevel(logging.INFO)
        f_format = logging.Formatter(
            "%(asctime)s - %(levelname)s: - %(module)s:%(lineno)d - %(message)s"
        )
        f_handler.setFormatter(f_format)
        self.logger.addHandler(f_handler)

    def _db_connect(self, options={}):
        if self.config.get("prefs_db") == None:
            raise ValueError("prefs_db not defined in bigsdb.conf")
        if options.get("reconnect"):
            self.data_connector.drop_all_connections()
        self.db = self.data_connector.get_connection(
            dbase_name=self.config["prefs_db"],
            host=self.config.get("dbhost") or CONNECTION_DETAILS["HOST"],
            port=self.config.get("dbport") or CONNECTION_DETAILS["PORT"],
            user=self.config.get("dbuser") or CONNECTION_DETAILS["USER"],
            password=self.config.get("dbpassword") or CONNECTION_DETAILS["PASSWORD"],
        )

    def _check_required_parameters(self, **kwargs):
        for key, value in kwargs.items():
            if value is None:
                raise ValueError(f"Parameter '{key}' has not been passed.")

    def get_all_locus_prefs(self, guid, dbname):
        if not guid:
            self.logger.error("No guid passed.")
            return {}
        prefs = {}
        qry = "SELECT locus,action,value FROM locus WHERE (guid,dbase)=(%s,%s)"
        cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cursor.execute(qry, [guid, dbname])
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
        return [dict(row) for row in cursor.fetchall()]

    def get_all_scheme_prefs(self, guid, dbname):
        if not guid:
            self.logger.error("No guid passed.")
            return {}
        prefs = {}
        qry = "SELECT scheme_id,action,value FROM scheme WHERE (guid,dbase)=(%s,%s)"
        cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cursor.execute(qry, [guid, dbname])
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
        return [dict(row) for row in cursor.fetchall()]
