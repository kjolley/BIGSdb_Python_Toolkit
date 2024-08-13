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
from pathlib import Path
import bigsdb.utils
from bigsdb.plugin import Plugin


class PyExport(Plugin):
    def get_attributes(self):
        return {
            "name": "Export (PYTHON TEST)",
            "authors": [
                {
                    "name": "Keith Jolley",
                    "affiliation": "University of Oxford, UK",
                    "email": "keith.jolley@biology.ox.ac.uk",
                }
            ],
            "description": "Export dataset generated from query results",
            "full_description": "The Export plugin creates a download file "
            "of any primary metadata, secondary metadata, allele designations, "
            "scheme designations, or publications for isolates within a "
            "selected dataset or for the whole database. The output file is "
            "in Excel format.",
            "category": "Export",
            "menutext": "Dataset (Python test)",
            "module": "PyExport",
            "version": "1.0.0",
            "section": "export,postquery",
            "url": "{0}/data_export/isolate_export.html".format(
                self.config.get("doclink")
            ),
            "input": "query",
            "requires": "ref_db,js_tree,offline_jobs",
            "help": "tooltips",
            "order": 15,
            "dbtype": "isolates",
            "image": None,
            "system_flag": "DatasetExport",
            "enabled_by_default": 1,
        }

    def run(self):
        print("<h1>Export dataset</h1>")
        if self.system.get("DatasetExport", "") == "no":
            self.print_bad_status({"message": "Dataset exports are disabled."})
            return
        if self.has_set_changed():
            return
        if self.params.get("submit"):
            self.__submit()
            return
        self.__print_interface()

    def __print_interface(self):
        set_id = self.get_set_id()
        selected_ids = self.get_selected_ids()
        print(
            '<div class="box" id="queryform"><div class="scrollable">'
            "<p>Currently this is just a demonstration of a plugin that uses the "
            "offline job manager. You can select isolate ids and the job will "
            "get sent to the queue. When run, it will create a tab-delimited "
            "text file containing the primary metadata for each selected isolate "
            "record.</p>"
            "<p>New methods will be added later to support selecting specific fields, "
            "loci, and schemes.</p>"
        )
        self.start_form()
        self.print_seqbin_isolate_fieldset(
            {
                "use_all": 1,
                "selected_ids": selected_ids,
                "isolate_paste_list": 1,
            }
        )
        self.print_action_fieldset({"no_reset": 1})
        self.print_hidden(["db", "page", "name", "set_id"])
        self.end_form()
        print("</div></div>")

    def __submit(self):
        ids, invalid_ids = self.process_selected_ids()
        if len(ids) == 0:
            self.print_bad_status({"message": "No valid ids have been selected!"})
            self.__print_interface()
            return
        if len(invalid_ids):
            print(invalid_ids)
            list_string = ", ".join(map(str, invalid_ids))
            self.print_bad_status(
                {
                    "message": f"The following isolates in your pasted list are invalid: {list_string}."
                }
            )
            self.__print_interface()
            return
        attributes = self.get_attributes()
        if self.args.get("curate"):
            self.params["curate"] = 1
        if self.args.get("set_id"):
            self.params["set_id"] = self.args.get("set_id")
        job_id = self.job_manager.add_job(
            {
                "dbase_config": self.instance,
                "ip_address": self.params.get("remote_host"),
                "module": attributes.get("module"),
                "priority": attributes.get("priority"),
                "parameters": self.params,
                "isolates": ids,
                "username": self.username,
                "email": self.email,
            }
        )
        print(self.get_job_redirect(job_id))

    def get_initiation_values(self):
        return {"jQuery.jstree": 1, "jQuery.multiselect": 1}

    def run_job(self, job_id):
        view = self.system.get("view")
        ids = self.job_manager.get_job_isolates(job_id)
        table = self.datastore.create_temp_list_table_from_list("int", ids)
        outfile = f"{self.config['tmp_dir']}/{job_id}.txt"
        fields = self.parser.get_field_list()
        qry = (
            "SELECT "
            + ",".join(fields)
            + f" FROM {view} v JOIN {table} l ON v.id=l.value ORDER BY id"
        )
        results = self.datastore.run_query(qry, None, {"fetch": "all_arrayref"})
        with open(outfile, "w") as f:
            f.write("\t".join(fields) + "\n")
            for record in results:
                f.write(
                    "\t".join("" if item is None else str(item) for item in record)
                    + "\n"
                )
        if not Path(outfile).is_file():
            self.logger.error(f"File {outfile} does not exist")
            return
        self.job_manager.update_job_output(
            job_id,
            {
                "filename": f"{job_id}.txt",
                "description": "01_Export table (text)",
                "compress": 1,
            },
        )
