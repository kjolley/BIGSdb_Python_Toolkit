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


class Scheme:
    def __init__(self, attributes, logger=None):
        for key, value in attributes.items():
            setattr(self, key, value)
        if logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())
        else:
            self.logger = logger
        self._initiate()

    def _initiate(self):
        cursor = self.db.cursor()
        qry = "SELECT locus,index FROM scheme_warehouse_indices WHERE scheme_id=%s"
        try:
            cursor.execute(qry, [self.id])
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
        data = cursor.fetchall()
        indices = {row[0]: row[1] for row in data}
        self.locus_index = indices

    def get_profile_by_primary_keys(self, values):
        if not self.db:
            return
        if type(values) is not list:
            values = [values]
        table = f"mv_scheme_{self.dbase_id}"
        qry = f"SELECT profile FROM {table} WHERE "
        primary_keys = self.primary_keys
        qry += " AND ".join([f"{key}=%s" for key in primary_keys])
        cursor = self.db.cursor()

        try:
            cursor.execute(qry, values)
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
            raise  # Rethrow exception
        else:
            profile = cursor.fetchone()
            if profile == None:
                return
            return profile[0]
