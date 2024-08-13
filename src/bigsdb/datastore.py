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
import bigsdb.utils


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
        self.cache = {}
        self.user_dbs = {}

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

    def get_eav_fieldnames(self, options={}):
        no_curate = " WHERE NOT no_curate" if options.get("curate") else ""
        return self.run_query(
            f"SELECT field FROM eav_fields{no_curate} ORDER BY " "field_order,field",
            None,
            {"fetch": "col_arrayref"},
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

                def __admin():
                    return [ALL_ISOLATES]

                def __submitter():
                    return [
                        OWN_SUBMITTED_ISOLATES,
                        OWN_PRIVATE_ISOLATES,
                        PUBLIC_ISOLATES_FROM_SAME_USER_GROUP,
                        PRIVATE_ISOLATES_FROM_SAME_USER_GROUP,
                    ]

                def __private_submitter():
                    return [OWN_PRIVATE_ISOLATES, PRIVATE_ISOLATES_FROM_SAME_USER_GROUP]

                def __curator():
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
                    "admin": __admin,
                    "submitter": __submitter,
                    "private_submitter": __private_submitter,
                    "curator": __curator,
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


# BIGSdb Perl DBI code uses ? as placeholders in SQL queries. psycopg2 uses
# %s. Rewrite so that the same SQL works with both.
def replace_placeholders(query):
    return re.sub(r"\?", "%s", query)
