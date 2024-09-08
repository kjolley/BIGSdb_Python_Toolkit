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

    # designations is a dict containing a list of allele_designations for each locus.
    def get_field_values_by_designations(self, designations, options={}):
        loci = self.loci
        fields = self.fields

        used_loci = []
        missing_loci = {}
        values = {}

        for locus in loci:
            if locus not in designations:
                if options.get("dont_match_missing_loci"):
                    continue
                values[locus] = {"allele_ids": [-999], "allele_count": 1}
                missing_loci[locus] = 1
            else:
                if (
                    options.get("dont_match_missing_loci")
                    and designations[locus][0]["allele_id"] == "N"
                ):
                    continue
                values[locus] = {"allele_count": len(designations[locus])}
                allele_ids = []
                for designation in designations[locus]:
                    if designation["allele_id"] == "0":
                        missing_loci[locus] = 1
                    if "allele_id" in designation:
                        designation["allele_id"] = designation["allele_id"].replace(
                            "'", "\\'"
                        )
                    else:
                        self.logger.error(
                            f"{self['instance']}: Undefined allele for locus {locus}"
                        )
                    allele_ids.append(designation["allele_id"])
                values[locus]["allele_ids"] = allele_ids
            used_loci.append(locus)

        if not values:
            return {}

        locus_terms = []
        for locus in used_loci:
            if not options.get("dont_match_missing_loci", True):
                if self["allow_missing_loci"]:
                    values[locus]["allele_ids"].append("N")
                if self["allow_presence"] and locus not in missing_loci:
                    values[locus]["allele_ids"].append("P")
            allele_ids = values[locus]["allele_ids"]
            formatted_allele_ids = ",".join(
                [f"E'{allele_id}'" for allele_id in allele_ids]
            )
            locus_terms.append(
                f"profile[{self.locus_index[locus]}] IN " f"({formatted_allele_ids})"
            )

        locus_term_string = " AND ".join(locus_terms)
        table = f"mv_scheme_{self.dbase_id}"
        # Ensure field names are case-sensitive in output
        field_list = []
        for field in fields:
            field_list.append(field + ' AS "' + field + '"')
        qry = f"SELECT {','.join(field_list)} FROM {table} WHERE {locus_term_string}"
        cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cursor.execute(qry)
        except Exception as e:
            self.logger.warn(
                "Check database attributes in the scheme_fields table for "
                f"scheme#{self.id} ({self.name})! {e}"
            )
            self.db.rollback()
            raise ValueError("Scheme configuration error")

        field_data = [dict(row) for row in cursor.fetchall()]
        self.db.commit()
        return field_data
