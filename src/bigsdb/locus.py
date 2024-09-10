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


class Locus:
    def __init__(self, attributes, logger=None):
        for key, value in attributes.items():
            setattr(self, key, value)
        if logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())
        else:
            self.logger = logger

    def get_description(self):
        if not self.db:
            self.logger.error(f"No connection to locus {self.id} database")
            return {}
        qry = "SELECT * FROM locus_descriptions WHERE locus=%s"
        cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cursor.execute(qry, [self.id])
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
            raise  # Rethrow exception
        else:
            row = cursor.fetchone()
            if row is not None:
                return dict(row)
            else:
                return

    def get_allele_sequence(self, allele_id):
        qry = "SELECT sequence FROM sequences WHERE (locus,allele_id)=(%s,%s)"
        cursor = self.db.cursor()
        try:
            cursor.execute(qry, [self.id, allele_id])
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
            raise  # Rethrow exception
        else:
            value = cursor.fetchone()
            if value == None:
                return
            else:
                return value[0]

    def get_all_sequences(self, options={}):
        qry = "SELECT allele_id,sequence FROM sequences WHERE locus=%s"
        if options.get("exemplar"):
            qry += " AND exemplar"
        if options.get("type_alleles"):
            qry += " AND type_allele"
        cursor = self.db.cursor()
        try:
            cursor.execute(qry, [self.id])
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
            raise  # Rethrow exception
        else:
            data = cursor.fetchall()
            return {item[0]: item[1] for item in data}

    def get_allele_id_from_sequence(self, sequence):
        qry = (
            "SELECT allele_id FROM sequences WHERE (md5(UPPER(sequence)),locus)="
            "(md5(UPPER(%s)),%s)"
        )
        cursor = self.db.cursor()
        try:
            cursor.execute(qry, [sequence, self.id])
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
            raise  # Rethrow exception
        else:
            value = cursor.fetchone()
            if value == None:
                return
            else:
                return value[0]
