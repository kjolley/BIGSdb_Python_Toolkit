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

import os
import signal
import logging
import psycopg2.extras
from psycopg2 import sql
import gzip
import shutil
import io
import bigsdb.utils
from bigsdb.base_application import BaseApplication
from bigsdb.constants import CONNECTION_DETAILS, LOGS

DBASE_QUOTA_EXCEEDED = 1
USER_QUOTA_EXCEEDED = 2


class JobManager(BaseApplication):
    def __init__(
        self,
        data_connector=None,
        system=None,
        config=None,
        logger=None,
    ):
        self.check_required_parameters(
            data_connector=data_connector, system=system, config=config
        )
        self.data_connector = data_connector
        self.system = system
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
        if self.config.get("jobs_db") == None:
            raise ValueError("jobs_db not defined in bigsdb.conf")
        if options.get("reconnect"):
            self.data_connector.drop_all_connections()
        self.db = self.data_connector.get_connection(
            dbase_name=self.config["jobs_db"],
            host=self.config.get("dbhost") or CONNECTION_DETAILS["HOST"],
            port=self.config.get("dbport") or CONNECTION_DETAILS["PORT"],
            user=self.config.get("dbuser") or CONNECTION_DETAILS["USER"],
            password=self.config.get("dbpassword") or CONNECTION_DETAILS["PASSWORD"],
        )

    def _has_ip_address_got_queued_jobs(self, ip_address):
        cursor = self.db.cursor()
        qry = "SELECT EXISTS(SELECT * FROM jobs WHERE (ip_address,status)=(%s,%s))"
        try:
            cursor.execute(qry, [ip_address, "submitted"])
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
        return cursor.fetchone()[0]

    def _make_job_fingerprint(self, params):
        key = ""
        for value in params:
            if value == None or value == "":
                continue
            key += str(value)
        return bigsdb.utils.get_md5_hash(key)

    def _dict_to_string_sorted(self, d):
        sorted_keys = sorted(k for k in d if d[k] is not None)
        return "".join(str(d[k]) for k in sorted_keys)

    def _jobs_require_login(self):
        if self.system.get("jobs_require_login", "") == "no":
            return
        if not (
            self.config.get("jobs_require_login")
            or self.system.get("jobs_require_login", "") == "yes"
        ):
            return
        return True

    def _get_duplicate_job_id(self, fingerprint=None, username=None, ip_address=None):
        cursor = self.db.cursor()
        qry = (
            "SELECT id FROM jobs WHERE fingerprint=%s AND (status='started' OR "
            "status='submitted') AND "
        )
        check_ip_address = (
            self.system.get("read_access", "") == "public"
            and not self._jobs_require_login()
        )
        qry += "ip_address=%s" if check_ip_address else "username=%s"
        try:
            cursor.execute(
                qry, [fingerprint, (ip_address if check_ip_address else username)]
            )
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
        row = cursor.fetchone()
        if row == None:
            return
        return row[0]

    def _is_quota_exceeded(self, params):
        cursor = self.db.cursor()
        if bigsdb.utils.is_integer(self.system.get("job_quota")):
            qry = (
                "SELECT COUNT(*) FROM jobs WHERE dbase_config=%s AND "
                "status IN ('submitted','started')"
            )
            try:
                cursor.execute(qry, [params.get("dbase_config")])
            except Exception as e:
                self.logger.error(f"{e} Query:{qry}")
            job_count = cursor.fetchone()[0]
            if job_count >= int(self.system.get("job_quota")):
                return DBASE_QUOTA_EXCEEDED
        if bigsdb.utils.is_integer(self.system.get("user_job_quota")) and params.get(
            "username"
        ):
            qry = (
                "SELECT COUNT(*) FROM jobs WHERE (dbase_config,username)=(%s,%s) "
                "AND status IN ('submitted','started')"
            )
            try:
                cursor.execute(
                    qry, [params.get("dbase_config"), params.get("username")]
                )
            except Exception as e:
                self.logger.error(f"{e} Query:{qry}")
            job_count = cursor.fetchone()[0]
            if job_count >= int(self.system.get("user_job_quota")):
                return USER_QUOTA_EXCEEDED

    def _get_status(self, params={}, fingerprint=None):
        if params.get("mark_started"):
            return
        duplicate_job = self._get_duplicate_job_id(
            fingerprint, params.get("username", ""), params.get("ip_address", "")
        )
        quota_exceeded = self._is_quota_exceeded(params)
        if duplicate_job:
            status = f"rejected - duplicate job ({duplicate_job})"
        elif quota_exceeded:
            status = self._get_quota_status(quota_exceeded)
        else:
            status = "submitted"
        return status

    def _get_quota_status(self, quota_status):
        if quota_status == DBASE_QUOTA_EXCEEDED:
            plural = "" if self.system.get("job_quota") == 1 else "s"
            job_quota = self.system.get("job_quota")
            return (
                "rejected - database jobs exceeded. This database has a quota of "
                f"{job_quota} concurrent job{plural}. Please try again later."
            )
        elif quota_status == USER_QUOTA_EXCEEDED:
            plural = "" if self.system.get("user_job_quota") == 1 else "s"
            user_job_quota = self.system.get("user_job_quota")
            return (
                "rejected = database jobs exceeded. This database has a quota of "
                f"{user_job_quota} concurrent job{plural} for any user. "
                "Please try again later."
            )
        self.logger.error("Invalid job quota status - this should not be possible.")

    def add_job(self, params={}):
        self.check_required_parameters(
            dbase_config=params.get("dbase_config"),
            ip_address=params.get("ip_address"),
            module=params.get("module"),
        )

        if bigsdb.utils.is_integer(self.system.get("job_priority")):
            priority = self.system.get("job_priority")
        else:
            priority = 5

        # Adjust for plugin level priority.
        if bigsdb.utils.is_integer(params.get("priority")):
            priority += params.get("priority")

        # If IP address already has jobs queued, i.e. not started, then lower the
        # priority on any new jobs from them. This will prevent a single user from
        # flooding the queue and preventing other user jobs from running.

        if self._has_ip_address_got_queued_jobs(params.get("ip_address")):
            priority += 2
        job_id = params.get("job_id") or bigsdb.utils.get_random()

        fingerprint_params = params.get("parameters", {}).copy()
        for key in fingerprint_params:
            if bigsdb.utils.is_integer(key):
                params["parameters"].pop(
                    key, None
                )  # Treeview implementation has integer node ids.
        for key in [
            "submit",
            "page",
            "update_options",
            "format",
            "dbase_config_dir",
            "instance",
            "isolate_paste_list",
            "isolate_id",
            "name",
            "remote_host",
            "db",
            "locus",
            "locus_paste_list",
        ]:
            params["parameters"].pop(key, None)

        fingerprint = self._make_job_fingerprint(
            [
                params.get("dbase_config"),
                params.get("ip_address"),
                params.get("module"),
                params.get("username", ""),
                bigsdb.utils.create_string_from_list(params.get("isolates", [])),
                bigsdb.utils.create_string_from_list(params.get("profiles", [])),
                bigsdb.utils.create_string_from_list(params.get("loci", [])),
                self._dict_to_string_sorted(params.get("parameters", {})),
            ]
        )
        status = self._get_status(params, fingerprint)
        cursor = self.db.cursor()
        qry = (
            "INSERT INTO jobs (id,dbase_config,username,email,ip_address,"
            "submit_time,start_time,module,status,pid,percent_complete,priority,"
            "fingerprint) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        )
        try:
            cursor.execute(
                qry,
                [
                    job_id,
                    params.get("dbase_config"),
                    params.get("username", ""),
                    params.get("email", ""),
                    params.get("ip_address"),
                    "now",
                    ("now" if params.get("mark_started") else None),
                    params.get("module"),
                    status,
                    (os.getpid() if params.get("mark_started") else None),
                    (-1 if params.get("no_progress") else 0),
                    priority,
                    fingerprint,
                ],
            )

            qry = "INSERT INTO params (job_id,key,value) VALUES (%s,%s,%s)"
            cgi_parameters = params.get("parameters", {})
            for param in cgi_parameters.keys():
                value = cgi_parameters.get(param)
                if value != None and value != "":
                    if isinstance(value, list):
                        value = "||".join(value)
                    cursor.execute(qry, [job_id, param, value])

            # Use copy_from file-like-object to speed up populating isolates table.
            isolates = params.get("isolates", [])
            qry = None  # In case we get an exception
            for batch_isolates in bigsdb.utils.batch(isolates, 100):
                isolate_data = "\n".join(
                    [f"{job_id}\t{isolate_id}" for isolate_id in batch_isolates]
                )
                data_io = io.StringIO(isolate_data)
                cursor.copy_from(
                    data_io, "isolates", columns=("job_id", "isolate_id"), sep="\t"
                )

            qry = "INSERT INTO profiles (job_id,scheme_id,profile_id) VALUES (%s,%s,%s)"
            profiles = params.get("profiles", [])
            for profile_id in profiles:
                cursor.execute(
                    qry, [job_id, cgi_parameters.get("scheme_id"), profile_id]
                )
            qry = "INSERT INTO loci(job_id,locus) VALUES (%s,%s)"
            loci = params.get("loci", [])
            for locus in loci:
                cursor.execute(qry, [job_id, locus])
            self.db.commit()
        except Exception as e:
            self.logger.error(f"{e}; Query:{qry}")
            self.db.rollback()

        return job_id

    def get_job(self, job_id):
        qry = (
            "SELECT *,extract(epoch FROM now() - start_time) AS elapsed,"
            "extract(epoch FROM stop_time - start_time) AS total_time, localtimestamp "
            "AS query_time FROM jobs WHERE id=%s"
        )
        cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cursor.execute(qry, [job_id])
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
        row = cursor.fetchone()
        if row is not None:
            return dict(row)
        else:
            return

    def get_job_status(self, job_id):
        qry = "SELECT status,cancel,pid FROM jobs WHERE id=%s"
        cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cursor.execute(qry, [job_id])
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
        row = cursor.fetchone()
        if row is not None:
            return dict(row)
        else:
            return {}

    def get_job_params(self, job_id):
        cursor = self.db.cursor()
        qry = "SELECT key,value FROM params WHERE job_id=%s"
        try:
            cursor.execute(qry, [job_id])
            params = {}
            for key, value in cursor.fetchall():
                params[key] = value
            return params

        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")

    def get_job_isolates(self, job_id):
        cursor = self.db.cursor()
        qry = "SELECT isolate_id FROM isolates WHERE job_id=%s ORDER BY isolate_id"
        try:
            cursor.execute(qry, [job_id])
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")

    def get_job_loci(self, job_id):
        cursor = self.db.cursor()
        qry = "SELECT locus FROM loci WHERE job_id=%s ORDER BY LOWER(locus)"
        try:
            cursor.execute(qry, [job_id])
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")

    def update_job_output(self, job_id, output_dict={}):
        if output_dict.get("filename") == None:
            raise ValueError("filename not passed.")
        if output_dict.get("description") == None:
            raise ValueError("description not passed.")
        if self.db.closed:
            self._db_connect({"reconnect": True})
        if output_dict.get("compress"):
            full_path = os.path.join(self.config["tmp_dir"], output_dict["filename"])
            if os.path.getsize(full_path) > (10 * 1024 * 1024):  # >10 MB
                gzipped_path = f"{full_path}.gz"
                if output_dict.get("keep_original"):
                    with open(full_path, "rb") as f_in, gzip.open(
                        gzipped_path, "wb"
                    ) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                else:
                    with open(full_path, "rb") as f_in, gzip.open(
                        gzipped_path, "wb"
                    ) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    os.remove(full_path)

                if not os.path.exists(gzipped_path):
                    self.logger.error(f"Cannot gzip file {full_path}")
                else:
                    output_dict["filename"] += ".gz"
                    output_dict["description"] += " [gzipped file]"
        cursor = self.db.cursor()
        qry = "INSERT INTO output (job_id,filename,description) VALUES (%s,%s,%s)"
        try:
            cursor.execute(
                qry, [job_id, output_dict["filename"], output_dict["description"]]
            )
            self.db.commit()
        except:
            self.logger.error(f"{e} Query:{qry}")
            self.db.rollback()

    def update_job_status(self, job_id, status_dict={}):
        if self.db.closed:
            self._db_connect({"reconnect": True})
        if self.db.closed:
            self._db_connect(reconnect=True)

        keys = sorted(status_dict.keys())
        values = [status_dict[key] for key in keys]

        cursor = self.db.cursor()
        qry = sql.SQL("UPDATE jobs SET {} WHERE id=%s").format(
            sql.SQL(", ").join(sql.Identifier(key) + sql.SQL("=%s") for key in keys)
        )

        try:
            cursor.execute(qry, values + [job_id])
            self.db.commit()
        except Exception as e:
            self.logger.error(f"{e} Query:{qry}")
            self.db.rollback()

        if status_dict.get("status") == "failed":
            return

        job = self.get_job_status(job_id)
        if job.get("status", "") == "cancelled" or job.get("cancel"):
            if job.get("pid"):
                os.kill(job.get("pid"), signal.SIGTERM)
