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

import re
import logging
import psycopg2.extras
import random
from io import StringIO
from collections import defaultdict
import bigsdb.utils
from bigsdb.scheme import Scheme
from bigsdb.locus import Locus


class Datastore(object):
    def __init__(
        self,
        db,
        data_connector=None,
        system=None,
        config=None,
        parser=None,
        logger=None,
        curate=False,
    ):
        if system == None:
            raise ValueError("No system parameter passed.")
        if config == None:
            raise ValueError("No config parameter passed.")
        self.db = db
        self.data_connector = data_connector
        self.config = config
        self.system = system
        if logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())
        else:
            self.logger = logger
        self.curate = curate
        self.username_cache = {}
        self.cache = defaultdict(nested_defaultdict)
        self.prefs = defaultdict(nested_defaultdict)
        self.user_dbs = {}
        self.scheme = {}
        self.locus = {}

    def run_query(self, qry, values=[], options={}):
        if type(values) is not list:
            values = [values]
        db = options.get("db", self.db)
        fetch = options.get("fetch", "row_array")
        qry = replace_placeholders(qry)
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cursor.execute(qry, values)
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")

        if fetch == "col_arrayref":
            data = None
            try:
                data = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                self.logger.error(f"{e} Query:{qry}")
            return data

        # No differentiation between Perl DBI row_array and row_arrayref in Python.
        if fetch == "row_arrayref" or fetch == "row_array":
            value = cursor.fetchone()
            if value == None:
                return
            if len(value) == 1:
                return value[0]
            else:
                return value
        if fetch == "row_hashref":
            row = cursor.fetchone()
            if row is not None:
                return dict(row)
            else:
                return
        if fetch == "all_hashref":
            if "key" not in options:
                raise ValueError("Key field(s) needs to be passed.")
            return {row[options["key"]]: dict(row) for row in cursor.fetchall()}
        if fetch == "all_arrayref":
            if "slice" in options and options["slice"]:
                return [
                    {key: dict(row)[key] for key in options["slice"]}
                    for row in cursor.fetchall()
                ]
            elif "slice" in options:  # slice = {}
                return [dict(row) for row in cursor.fetchall()]
            else:
                return cursor.fetchall()
        self.logger.error("Query failed - invalid fetch method specified.")
        return None

    def initiate_user_dbs(self):
        configs = self.run_query(
            "SELECT * FROM user_dbases ORDER BY id",
            None,
            {"fetch": "all_arrayref", "slice": {}},
        )
        for config in configs:
            try:
                self.user_dbs[config["id"]] = {
                    "db": self.data_connector.get_connection(
                        dbase_name=config.get("dbase_name"),
                        host=config.get("dbase_host")
                        or self.config.get("dbhost")
                        or self.system.get("host"),
                        port=config.get("dbase_port")
                        or self.config.get("dbport")
                        or self.system.get("port"),
                        user=config.get("dbase_user")
                        or self.config.get("dbuser")
                        or self.system.get("user"),
                        password=config.get("dbase_password")
                        or self.config.get("dbpassword")
                        or self.system.get("password"),
                    ),
                    "name": self.config.get("dbase_name"),
                }
            except Exception as e:
                self.logger.error(str(e))

    def add_user_db(self, id=None, db=None, name=None):  # Just used for tests
        if id == None:
            raise ValueError("id parameter not passed")
        if db == None:
            raise ValueError("db parameter not passed")
        if name == None:
            raise ValueError("name parameter not passed")
        self.user_dbs[id] = {"db": db, "name": name}

    def get_user_info_from_username(self, username):
        if username == None:
            return
        if self.username_cache.get(username) == None:
            user_info = self.run_query(
                "SELECT * FROM users WHERE user_name=?",
                username,
                {"fetch": "row_hashref"},
            )
            if (user_info and user_info.get("user_db")) != None:
                remote_user = self.get_remote_user_info(
                    username, user_info.get("user_db")
                )
                if remote_user.get("user_name") != None:
                    for att in [
                        "first_name",
                        "surname",
                        "email",
                        "affiliation",
                        "submission_digests",
                        "submission_email_cc",
                        "absent_until",
                    ]:
                        if remote_user.get(att):
                            user_info[att] = remote_user.get(att)
            self.username_cache[username] = user_info
        return self.username_cache.get(username)

    def get_remote_user_info(self, username, user_db_id):
        user_db = self.get_user_db(user_db_id)
        user_data = self.run_query(
            "SELECT user_name,first_name,surname,email,affiliation "
            "FROM users WHERE user_name=?",
            username,
            {"db": user_db, "fetch": "row_hashref"},
        )
        user_prefs = self.run_query(
            "SELECT * FROM curator_prefs WHERE user_name=?",
            username,
            {"db": user_db, "fetch": "row_hashref"},
        )
        if user_prefs == None:
            return user_data
        for key in user_prefs.keys():
            user_data[key] = user_prefs[key]
        return user_data

    def get_user_db(self, id):
        try:
            return self.user_dbs[id]["db"]
        except:
            self.logger.error("Cannot get user db")

    def get_eav_fields(self):
        return self.run_query(
            "SELECT * FROM eav_fields ORDER BY field_order,field",
            None,
            {"fetch": "all_arrayref", "slice": {}},
        )

    def get_eav_field(self, field):
        return self.run_query(
            "SELECT * FROM eav_fields WHERE field=?", field, {"fetch": "row_hashref"}
        )

    def get_eav_fieldnames(self, options={}):
        no_curate = " WHERE NOT no_curate" if options.get("curate") else ""
        return self.run_query(
            f"SELECT field FROM eav_fields{no_curate} ORDER BY " "field_order,field",
            None,
            {"fetch": "col_arrayref"},
        )

    def is_eav_field(self, field):
        return self.run_query(
            "SELECT EXISTS(SELECT * FROM eav_fields WHERE field=?)", field
        )

    def get_eav_field_table(self, field):
        if not self.cache["eav_field_table"][field]:
            eav_field = self.get_eav_field(field)
            if not eav_field:
                self.logger.error(f"EAV field {field} does not exist.")
                return
            type = eav_field.get("value_format")
            table = self.get_eav_table(type)
            if table:
                self.cache["eav_field_table"][field] = table
            else:
                self.logger.error(f"EAV field {field} has invalid field type.")
                return
        return self.cache["eav_field_table"][field]

    def get_eav_table(self, type):
        table = {
            "integer": "eav_int",
            "float": "eav_float",
            "text": "eav_text",
            "date": "eav_date",
            "boolean": "eav_boolean",
        }
        if not table.get(type):
            self.logger.error("Invalid EAV type")
            return
        return table.get(type)

    def get_eav_field_value(self, isolate_id, field):
        table = self.get_eav_field_table(field)
        return self.run_query(
            f"SELECT value FROM {table} WHERE (isolate_id,field)=(?,?)",
            [isolate_id, field],
        )

    def initiate_view(self, username=None, curate=False, set_id=None):
        user_info = self.get_user_info_from_username(username)
        if self.system.get("dbtype", "") == "sequences":
            if user_info == None:  # Not logged in.
                pass  # TODO Add date restriction
            self.system["temp_sequences_view"] = self.system.get(
                "temp_sequences_view", "sequences"
            )
        if self.system.get("dbtype", "") != "isolates":
            return
        if self.system.get("view") and set_id:
            if self.system.get("views") and bigsdb.utils.is_integer(set_id):
                set_view = self.run_query(
                    "SELECT view FROM set_view WHERE set_id=?", set_id
                )
                if set_view:
                    self.system["view"] = set_view

        view = self.system.get("view")
        qry = (
            f"CREATE TEMPORARY VIEW temp_view AS SELECT v.* FROM {view} v LEFT "
            + "JOIN private_isolates p ON v.id=p.isolate_id WHERE "
        )
        OWN_SUBMITTED_ISOLATES = "v.sender=?"
        OWN_PRIVATE_ISOLATES = "p.user_id=?"
        PUBLIC_ISOLATES_FROM_SAME_USER_GROUP = (
            "(EXISTS(SELECT 1 FROM "
            + "user_group_members ugm JOIN user_groups ug ON ugm.user_group=ug.id "
            + "WHERE ug.co_curate AND ugm.user_id=v.sender AND EXISTS(SELECT 1 "
            + "FROM user_group_members WHERE (user_group,user_id)=(ug.id,?))) "
            + "AND p.user_id IS NULL)"
        )
        PRIVATE_ISOLATES_FROM_SAME_USER_GROUP = (
            "(EXISTS(SELECT 1 FROM "
            + "user_group_members ugm JOIN user_groups ug ON ugm.user_group=ug.id "
            + "WHERE ug.co_curate_private AND ugm.user_id=v.sender AND "
            + "EXISTS(SELECT 1 FROM user_group_members WHERE (user_group,user_id)="
            + "(ug.id,?))) AND p.user_id IS NOT NULL)"
        )
        EMBARGOED_ISOLATES = "p.embargo IS NOT NULL"
        PUBLIC_ISOLATES = "p.user_id IS NULL"
        ISOLATES_FROM_USER_PROJECT = (
            "EXISTS(SELECT 1 FROM project_members pm "
            + "JOIN merged_project_users mpu ON pm.project_id=mpu.project_id WHERE "
            + "(mpu.user_id,pm.isolate_id)=(?,v.id))"
        )
        PUBLICATION_REQUESTED = "p.request_publish"
        PUBLICATION_REQUESTED = "p.request_publish"
        ALL_ISOLATES = "EXISTS(SELECT 1)"

        if user_info == None:
            qry += PUBLIC_ISOLATES
            args = []
            # TODO Add date restriction
        else:
            user_terms = []
            has_user_project = self.run_query(
                "SELECT EXISTS(SELECT * FROM merged_project_users WHERE user_id=?)",
                user_info.get("id"),
            )
            if curate:
                status = user_info.get("status")

                def _admin():
                    return [ALL_ISOLATES]

                def _submitter():
                    return [
                        OWN_SUBMITTED_ISOLATES,
                        OWN_PRIVATE_ISOLATES,
                        PUBLIC_ISOLATES_FROM_SAME_USER_GROUP,
                        PRIVATE_ISOLATES_FROM_SAME_USER_GROUP,
                    ]

                def _private_submitter():
                    return [OWN_PRIVATE_ISOLATES, PRIVATE_ISOLATES_FROM_SAME_USER_GROUP]

                def _curator():
                    user_terms = [
                        PUBLIC_ISOLATES,
                        OWN_PRIVATE_ISOLATES,
                        EMBARGOED_ISOLATES,
                        PUBLICATION_REQUESTED,
                    ]
                    if has_user_project:
                        user_terms.append(ISOLATES_FROM_USER_PROJECT)
                    return user_terms

                dispatch_table = {
                    "admin": _admin,
                    "submitter": _submitter,
                    "private_submitter": _private_submitter,
                    "curator": _curator,
                }
                if status == "submitter":
                    only_private = self.run_query(
                        "SELECT EXISTS(SELECT * "
                        "FROM permissions WHERE (user_id,permission)=(?,?))",
                        [user_info.get("id"), "only_private"],
                    )
                    if only_private:
                        status = "private_submitter"
                action = dispatch_table.get(status)
                user_terms = action()
            else:
                user_terms = [PUBLIC_ISOLATES]
                # Simplify view definition by only looking for private/project
                # isolates if the user has any.
                has_private_isolates = self.run_query(
                    "SELECT EXISTS(SELECT " "* FROM private_isolates WHERE user_id=?)",
                    user_info.get("id"),
                )
                if has_private_isolates:
                    user_terms.append(OWN_PRIVATE_ISOLATES)

                if has_user_project:
                    user_terms.append(ISOLATES_FROM_USER_PROJECT)
            qry += " OR ".join(user_terms)

            user_term_count = qry.count("?")
            args = [user_info.get("id")] * user_term_count
        qry = replace_placeholders(qry)
        try:
            cursor = self.db.cursor()
            cursor.execute(qry, args)
            self.db.commit()
        except Exception as e:
            self.logger.error(e)
            self.db.rollback()
        self.system["view"] = "temp_view"

    def get_seqbin_count(self):
        if self.cache.get("seqbin_count") != None:
            return self.cache.get("seqbin_count")
        view = self.system.get("view")
        self.cache["seqbin_count"] = self.run_query(
            "SELECT COUNT(*) FROM " f"{view} v JOIN seqbin_stats s ON v.id=s.isolate_id"
        )
        return self.cache.get("seqbin_count")

    def get_isolates_with_seqbin(self, options={}):
        view = self.system.get("view")
        labelfield = self.system.get("labelfield", "isolate")
        if options.get("id_list"):
            raise NotImplementedError
        elif options.get("use_all"):
            qry = (
                f"SELECT {view}.id,{view}.{labelfield},new_version "
                f"FROM {view} ORDER BY {view}.id"
            )
        else:
            qry = (
                f"SELECT {view}.id,{view}.{labelfield},new_version FROM "
                f"{view} WHERE EXISTS (SELECT * FROM seqbin_stats WHERE "
                f"{view}.id=seqbin_stats.isolate_id) ORDER BY {view}.id"
            )
        data = self.run_query(qry, None, {"fetch": "all_arrayref"})
        ids = []
        labels = {}
        for record in data:
            id, isolate, new_version = record
            if (
                isolate is None
            ):  # One database on PubMLST uses a restricted view that hides some isolate names.
                isolate = ""
            ids.append(id)
            labels[id] = (
                f"{id}) {isolate} [old version]" if new_version else f"{id}) {isolate}"
            )
        return ids, labels

    def isolate_exists(self, isolate_id=None):
        if isolate_id == None:
            raise ValueError("No isolate_id parameter passed.")
        if not bigsdb.utils.is_integer(isolate_id):
            raise ValueError("Isolate id parameter must be an integer.")
        view = self.system.get("view")
        return self.run_query(
            f"SELECT EXISTS(SELECT * FROM {view} WHERE id=?)", isolate_id
        )

    def isolate_exists_batch(self, isolate_ids=[]):
        for isolate_id in isolate_ids:
            if not bigsdb.utils.is_integer(isolate_id):
                raise ValueError(f"Isolate id {isolate_id} must be an integer.")
        view = self.system.get("view")
        placeholders = ",".join(["%s"] * len(isolate_ids))
        qry = f"SELECT id FROM {view} WHERE id IN ({placeholders})"
        existing_ids = self.run_query(qry, isolate_ids, {"fetch": "col_arrayref"})
        return existing_ids

    def create_temp_list_table_from_list(self, data_type, list, options={}):
        pg_data_type = data_type
        if data_type == "geography_point":
            pg_data_type = "geography(POINT, 4326)"
        table = options.get("table", "temp_list" + str(random.randint(0, 99999999)))
        db = options.get("db", self.db)

        # Convert list to a file-like object
        list_as_str = "\n".join(str(item) for item in list)
        list_file_like_object = StringIO(list_as_str)

        with db.cursor() as cursor:
            if not options.get("no_check_exists", False):
                cursor.execute(
                    "SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name=%s)",
                    (table,),
                )
                if cursor.fetchone()[0]:
                    return
            try:
                cursor.execute(f"CREATE TEMP TABLE {table} (value {pg_data_type});")
                cursor.copy_from(
                    file=list_file_like_object, table=table, sep="\t", null=""
                )
                db.commit()
            except Exception as e:
                self.logger.error(f"Cannot put data into temp table: {e}")
                db.rollback()
                raise Exception("Cannot put data into temp table")
        return table

    def get_loci(self, options={}):
        defined_clause = (
            "WHERE dbase_name IS NOT NULL OR reference_sequence IS NOT NULL"
            if options.get("seq_defined")
            else ""
        )

        set_clause = ""
        if options.get("set_id"):
            set_clause = "AND" if defined_clause else "WHERE"
            set_clause += (
                f" (id IN (SELECT locus FROM scheme_members WHERE scheme_id IN "
                f"(SELECT scheme_id FROM set_schemes WHERE set_id={options['set_id']})) "
                f"OR id IN (SELECT locus FROM set_loci WHERE set_id={options['set_id']}))"
            )

        if any(options.get(key) for key in ["query_pref", "analysis_pref"]):
            qry = (
                "SELECT id, scheme_id FROM loci LEFT JOIN scheme_members ON loci.id = "
                f"scheme_members.locus {defined_clause} {set_clause}"
            )
            if not options.get("do_not_order"):
                qry += (
                    " ORDER BY scheme_members.scheme_id, scheme_members.field_order, id"
                )
        else:
            qry = f"SELECT id FROM loci {defined_clause} {set_clause}"
            if not options.get("do_not_order"):
                qry += " ORDER BY id"

        query_loci = []
        data = self.run_query(qry, None, {"fetch": "all_arrayref"})
        for row in data:
            if options.get("query_pref") and (
                not self.prefs["query_field_loci"].get(row[0])
                or (
                    row[1] is not None
                    and not self.prefs["query_field_schemes"].get(row[1])
                )
            ):
                continue
            if options.get("analysis_pref") and (
                not self.prefs["analysis_loci"].get(row[0])
                or (
                    row[1] is not None
                    and not self.prefs["analysis_schemes"].get(row[1])
                )
            ):
                continue
            query_loci.append(row[0])

        query_loci = list(set(query_loci))
        return query_loci

    def get_loci_in_no_scheme(self, options={}):

        if options.get("set_id"):
            qry = (
                f"SELECT locus FROM set_loci WHERE set_id={options['set_id']} AND "
                "locus NOT IN (SELECT locus FROM scheme_members WHERE scheme_id IN "
                f"(SELECT scheme_id FROM set_schemes WHERE set_id={options['set_id']})) "
                "ORDER BY locus"
            )
        else:
            qry = (
                "SELECT id FROM loci LEFT JOIN scheme_members ON loci.id="
                "scheme_members.locus WHERE scheme_id IS NULL ORDER BY id"
            )

        data = self.run_query(
            qry, None, {"fetch": "col_arrayref", "cache": "get_loci_in_no_scheme"}
        )

        if not options.get("analyse_pref"):
            return data

        loci = [locus for locus in data if self.prefs["analysis_loci"].get(locus)]
        return loci

    def update_prefs(self, prefs):
        self.prefs = bigsdb.utils.convert_to_defaultdict(prefs)

    def is_locus(self, id, options={}):
        if id is None:
            return None
        key = options.get("set_id", "All")
        if key not in self.cache["locus_hash"]:
            loci = self.get_loci(
                {"do_not_order": True, "set_id": options.get("set_id")}
            )
            self.cache["locus_hash"][key] = {locus: 1 for locus in loci}
        if id in self.cache["locus_hash"][key]:
            return 1
        return None

    def get_set_locus_real_id(self, locus, set_id):
        qry = "SELECT locus FROM set_loci WHERE set_name=%s AND set_id=%s"
        real_id = self.run_query(
            qry,
            [locus, set_id],
            {"fetch": "row_array"},
        )
        return real_id if real_id else locus

    def get_allele_designations(self, isolate_id, locus):
        qry = (
            "SELECT * FROM allele_designations WHERE (isolate_id,locus)=(?,?) "
            "ORDER BY status,(substring (allele_id, '^[0-9]+'))::int,allele_id"
        )
        return self.run_query(
            qry, [isolate_id, locus], {"fetch": "all_arrayref", "slice": {}}
        )

    def get_allele_designations_with_locus_list_table(
        self, isolate_id, locus_list_table
    ):
        qry = (
            "SELECT locus,allele_id,status FROM allele_designations ad JOIN "
            f"{locus_list_table} l ON ad.locus=l.value WHERE isolate_id=? ORDER BY "
            "locus,status,(substring (allele_id, '^[0-9]+'))::int,allele_id"
        )
        return self.run_query(qry, isolate_id, {"fetch": "all_arrayref", "slice": {}})

    def get_scheme_group_info(self, group_id):
        return self.run_query(
            "SELECT * FROM scheme_groups WHERE id=?",
            group_id,
            {"fetch": "row_hashref", "cache": "get_scheme_group_info"},
        )

    def get_scheme_info(self, scheme_id, options={}):

        scheme_info = self.run_query(
            "SELECT * FROM schemes WHERE id=?",
            scheme_id,
            {
                "fetch": "row_hashref",
            },
        )

        if "set_id" in options:
            desc = self.run_query(
                "SELECT set_name FROM set_schemes WHERE set_id=? AND scheme_id=?",
                [options["set_id"], scheme_id],
                {
                    "fetch": "row_array",
                },
            )
            if desc:
                scheme_info["name"] = desc[0]

        if "get_pk" in options:
            pk = self.run_query(
                "SELECT field FROM scheme_fields WHERE scheme_id=? AND primary_key",
                scheme_id,
                {"fetch": "row_array"},
            )
            if pk:
                scheme_info["primary_key"] = pk

        return scheme_info

    def get_scheme_loci(self, scheme_id, options={}):

        if scheme_id not in self.cache.get("scheme_loci", {}):
            qry = (
                "SELECT locus"
                + (",profile_name" if self.system["dbtype"] == "isolates" else "")
                + " FROM scheme_members WHERE scheme_id=? ORDER BY field_order,locus"
            )
            self.cache.setdefault("scheme_loci", {})[scheme_id] = self.run_query(
                qry, scheme_id, {"fetch": "all_arrayref"}
            )

        loci = []
        for locus_info in self.cache["scheme_loci"][scheme_id]:
            locus, profile_name = (
                locus_info if len(locus_info) > 1 else (locus_info[0], None)
            )
            if options.get("analysis_pref"):
                if self.prefs["analysis_loci"].get(locus) and self.prefs[
                    "analysis_schemes"
                ].get(scheme_id):
                    loci.append(
                        profile_name or locus if options.get("profile_name") else locus
                    )
            else:
                loci.append(
                    profile_name or locus if options.get("profile_name") else locus
                )
        return loci

    # NOTE: Data are returned in a cached reference that may be needed more than once.
    # If calling code needs to modify returned values then you MUST make a local copy.
    def get_all_scheme_fields(self):
        if self.cache.get("all_scheme_fields") is None:
            data = self.run_query(
                "SELECT scheme_id, field FROM scheme_fields ORDER BY field_order, field",
                None,
                {"fetch": "all_arrayref"},
            )
            self.cache["all_scheme_fields"] = {}
            for row in data:
                scheme_id, field = row
                if scheme_id not in self.cache["all_scheme_fields"]:
                    self.cache["all_scheme_fields"][scheme_id] = []
                self.cache["all_scheme_fields"][scheme_id].append(field)

        return self.cache["all_scheme_fields"]

    def get_scheme_fields(self, scheme_id):
        fields = self.get_all_scheme_fields()
        return fields.get(scheme_id, [])

    def get_scheme(self, scheme_id):
        if scheme_id not in self.scheme:
            attributes = self.get_scheme_info(scheme_id)
            if attributes.get("dbase_name"):
                try:
                    attributes["db"] = self.data_connector.get_connection(
                        dbase_name=attributes["dbase_name"],
                        host=attributes["dbase_host"]
                        or self.config.get("dbase_host")
                        or self.config.get("dbhost")
                        or self.system.get("host"),
                        user=attributes["dbase_user"]
                        or self.config.get("dbase_user")
                        or self.config.get("dbuser")
                        or self.system.get("user"),
                        password=attributes["dbase_password"]
                        or self.config.get("dbase_password")
                        or self.config.get("dbpassword")
                        or self.system.get("password"),
                    )

                except Exception as e:
                    self.logger.error(
                        f"Error connecting scheme database scheme:{scheme_id}: {e}"
                    )

                attributes["fields"] = self.get_scheme_fields(scheme_id)
                attributes["loci"] = self.get_scheme_loci(
                    scheme_id, ({"profile_name": 1, "analysis_pref": 0})
                )
                attributes["primary_keys"] = self.run_query(
                    "SELECT field FROM scheme_fields WHERE scheme_id=%s AND "
                    "primary_key ORDER BY field_order",
                    scheme_id,
                    {"fetch": "col_arrayref"},
                )
                self.scheme[scheme_id] = Scheme(
                    attributes=attributes, logger=self.logger
                )
        return self.scheme[scheme_id]

    def get_scheme_field_values_by_designations(
        self, scheme_id, designations, options={}
    ):
        field_data = []
        scheme = None
        try:
            scheme = self.get_scheme(scheme_id)
        except Exception as e:
            self.logger.warn(f"Scheme {scheme_id} database is not configured correctly")

        if scheme is None:
            return

        if not options.get("no_convert"):
            self._convert_designations_to_profile_names(scheme_id, designations)

        try:
            field_data = scheme.get_field_values_by_designations(designations)
        except Exception as e:
            logger.warn(f"Scheme {scheme_id} database is not configured correctly")

        if options.get("no_status"):
            return field_data

        values = {}
        loci = self.get_scheme_loci(scheme_id)
        fields = self.get_scheme_fields(scheme_id)

        for data in field_data:
            status = "confirmed"
            for locus in loci:
                if designations.get(locus) is None:
                    continue
                for designation in designations[locus]:
                    if (
                        designation["allele_id"] in ["N", "0"]
                        or designation.get("status") == "confirmed"
                    ):
                        continue
                    status = "provisional"
                    break
                if status == "provisional":
                    break

            for field in fields:

                data[field] = data.get(field, "")
                if values.get(field, {}).get(data[field], "") != "confirmed":
                    values.setdefault(field, {})[data[field]] = {"status": status}

        return values

    def get_scheme_field_values_by_isolate_id(self, isolate_id, scheme_id, options={}):
        designations = self.get_scheme_allele_designations(isolate_id, scheme_id)

        if options.get("allow_presence"):
            present = self.run_query(
                "SELECT a.locus FROM allele_sequences a JOIN scheme_members s "
                "ON a.locus=s.locus WHERE (a.isolate_id,s.scheme_id)=(?,?)",
                [isolate_id, scheme_id],
                {
                    "fetch": "col_arrayref",
                },
            )
            for locus in present:
                if locus not in designations:
                    designations[locus] = [{"allele_id": "P", "status": "confirmed"}]

        if not designations:
            return {}

        field_values = self.get_scheme_field_values_by_designations(
            scheme_id, designations, options
        )
        return field_values

    def _convert_designations_to_profile_names(self, scheme_id, designations):
        data = self.run_query(
            "SELECT locus, profile_name FROM scheme_members WHERE scheme_id=?",
            scheme_id,
            {"fetch": "all_arrayref"},
        )
        for locus, profile_name in data:
            if profile_name is None or locus == profile_name:
                continue
            designations[profile_name] = designations.pop(locus, None)
        return

    def get_scheme_allele_designations(self, isolate_id, scheme_id, options={}):
        designations = {}

        if scheme_id:
            data = self.run_query(
                "SELECT * FROM allele_designations WHERE isolate_id=? AND locus IN "
                "(SELECT locus FROM scheme_members WHERE scheme_id=?) ORDER BY status, "
                "(substring(allele_id, '^[0-9]+'))::int, allele_id",
                [isolate_id, scheme_id],
                {
                    "fetch": "all_arrayref",
                    "slice": {},
                },
            )
            for designation in data:
                if designation["locus"] not in designations:
                    designations[designation["locus"]] = []
                designations[designation["locus"]].append(designation)
        else:
            set_clause = (
                "SELECT locus FROM scheme_members WHERE scheme_id IN (SELECT "
                f"scheme_id FROM set_schemes WHERE set_id={options['set_id']})"
                if options.get("set_id")
                else "SELECT locus FROM scheme_members"
            )
            data = self.run_query(
                "SELECT * FROM allele_designations WHERE isolate_id=? AND locus "
                f"NOT IN ({set_clause}) ORDER BY status, date_entered, allele_id",
                [isolate_id],
                {
                    "fetch": "all_arrayref",
                    "slice": {},
                },
            )
            for designation in data:
                if designation["locus"] not in designations:
                    designations[designation["locus"]] = []
                designations[designation["locus"]].append(designation)

        return designations

    def get_locus(self, locus):
        if locus not in self.locus:
            attributes = self.get_locus_info(locus)
            if attributes.get("dbase_name"):
                try:
                    attributes["db"] = self.data_connector.get_connection(
                        dbase_name=attributes["dbase_name"],
                        host=attributes["dbase_host"]
                        or self.config.get("dbase_host")
                        or self.config.get("dbhost")
                        or self.system.get("host"),
                        user=attributes["dbase_user"]
                        or self.config.get("dbase_user")
                        or self.config.get("dbuser")
                        or self.system.get("user"),
                        password=attributes["dbase_password"]
                        or self.config.get("dbase_password")
                        or self.config.get("dbpassword")
                        or self.system.get("password"),
                    )

                except Exception as e:
                    self.logger.error(f"Error connecting locus database :{locus}: {e}")

                self.locus[locus] = Locus(attributes=attributes, logger=self.logger)
        return self.locus[locus]

    def get_locus_info(self, locus, options={}):
        if self.cache["locus_info"].get(locus):
            return self.cache["locus_info"][locus]
        locus_info = self.run_query(
            "SELECT * FROM loci WHERE id=%s", locus, {"fetch": "row_hashref"}
        )
        if options.get("set_id"):
            set_locus = self.run_query(
                "SELECT * FROM set_loci WHERE set_id=%s AND locus=%s",
                [options["set_id"], locus],
                {"fetch": "row_hashref"},
            )
            for key in [
                "set_name",
                "set_common_name",
                "formatted_set_name",
                "formatted_set_common_name",
            ]:
                locus_info[key] = set_locus.get(key)
        self.cache["locus_info"][locus] = locus_info
        return self.cache["locus_info"][locus]


# BIGSdb Perl DBI code uses ? as placeholders in SQL queries. psycopg2 uses
# %s. Rewrite so that the same SQL works with both.
def replace_placeholders(query):
    return re.sub(r"\?", "%s", query)


def nested_defaultdict():
    return defaultdict(nested_defaultdict)
